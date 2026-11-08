"""Carga datos de ejemplo para probar la agenda sin empezar de cero."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from residencias.models import (
    MovimientoCupon,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
    Zona,
)


class Command(BaseCommand):
    help = "Crea zonas, productos, residencias y visitas de ejemplo (idempotente)."

    def handle(self, *args, **options):
        zonas = {}
        for orden, nombre in enumerate(["Centro", "Norte", "Sur"], start=1):
            zona, _ = Zona.objects.get_or_create(
                nombre=nombre, defaults={"orden": orden}
            )
            zonas[nombre] = zona

        productos_datos = [
            ("Pañales talla M", "Paquete de pañales absorbentes talla M", 1, 12, 200),
            ("Pañales talla L", "Paquete de pañales absorbentes talla L", 1, 12, 160),
            ("Empapadores", "Empapadores de cama 60x90", 1, 10, 120),
            ("Toallitas", "Paquete de toallitas húmedas", 2, 8, 80),
            ("Crema protectora", "Crema para la piel", 1, 6, 40),
        ]
        productos = {}
        for nombre, descripcion, por_unidad, minimo, carga_inicial in productos_datos:
            producto, _ = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "cupones_por_unidad": por_unidad,
                    "stock_minimo": minimo,
                },
            )
            productos[nombre] = producto
            if not producto.movimientos.exists():
                MovimientoCupon.objects.create(
                    producto=producto,
                    cantidad=carga_inicial,
                    tipo=MovimientoCupon.Tipo.CARGA,
                    notas="Carga inicial de ejemplo",
                )

        residencias_datos = [
            ("Residencia San José", "Centro", "Calle Mayor 12", "Ana", "600 111 222", 1, 1, "LUN"),
            ("Hogar Santa Marta", "Centro", "Avenida Sol 4", "Luis", "600 222 333", 2, 2, "MAR"),
            ("Residencia Los Olivos", "Norte", "Camino del Norte 8", "Marta", "600 333 444", 1, 1, "MIE"),
            ("Residencia El Pinar", "Sur", "Calle Pinar 30", "Jorge", "600 444 555", 1, 2, "JUE"),
            ("Residencia La Paz", "Sur", "Plaza Mayor 2", "Elena", "600 555 666", 2, 1, "VIE"),
        ]
        residencias = {}
        for nombre, zona, direccion, contacto, telefono, orden, frecuencia, dia in residencias_datos:
            residencia, _ = Residencia.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "zona": zonas[zona],
                    "direccion": direccion,
                    "contacto": contacto,
                    "telefono": telefono,
                    "horario": "09:00 - 13:00",
                    "orden_ruta": orden,
                    "frecuencia_semanal": frecuencia,
                    "dia_preferido": dia,
                },
            )
            residencias[nombre] = residencia

        hoy = timezone.localdate()

        pendientes_hoy = [
            ("Residencia San José", Visita.Turno.MANANA),
            ("Hogar Santa Marta", Visita.Turno.TARDE),
        ]
        for nombre, turno in pendientes_hoy:
            Visita.objects.get_or_create(
                residencia=residencias[nombre],
                fecha=hoy,
                turno=turno,
                defaults={"estado": Visita.Estado.PENDIENTE},
            )

        entregadas = [
            (hoy - timedelta(days=2), "Residencia Los Olivos", Visita.Turno.MANANA,
             [("Pañales talla M", 4, 4), ("Toallitas", 2, 4)]),
            (hoy - timedelta(days=1), "Residencia El Pinar", Visita.Turno.MANANA,
             [("Pañales talla L", 3, 3), ("Empapadores", 2, 2)]),
            (hoy - timedelta(days=1), "Residencia La Paz", Visita.Turno.TARDE,
             [("Pañales talla M", 5, 5), ("Crema protectora", 1, 1)]),
        ]
        for fecha, nombre, turno, lineas in entregadas:
            visita, creada = Visita.objects.get_or_create(
                residencia=residencias[nombre],
                fecha=fecha,
                turno=turno,
                defaults={"estado": Visita.Estado.ENTREGADA},
            )
            if creada:
                for producto_nombre, cantidad, cupones in lineas:
                    VisitaProducto.objects.create(
                        visita=visita,
                        producto=productos[producto_nombre],
                        cantidad=cantidad,
                        cupones=cupones,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de ejemplo listos: "
                f"{len(zonas)} zonas, {len(productos)} productos, "
                f"{len(residencias)} residencias."
            )
        )
