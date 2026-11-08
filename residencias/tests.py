from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    MovimientoCupon,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
    Zona,
    siguiente_residencia,
)


class CuponesTests(TestCase):
    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Pañales talla M", cupones_por_unidad=1, stock_minimo=3
        )
        self.residencia = Residencia.objects.create(nombre="Residencia Test")

    def test_stock_descuenta_solo_visitas_entregadas(self):
        MovimientoCupon.objects.create(producto=self.producto, cantidad=10)
        entregada = Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate(),
            turno=Visita.Turno.MANANA,
            estado=Visita.Estado.ENTREGADA,
        )
        VisitaProducto.objects.create(
            visita=entregada, producto=self.producto, cantidad=2, cupones=2
        )
        pendiente = Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate() + timedelta(days=1),
            turno=Visita.Turno.MANANA,
            estado=Visita.Estado.PENDIENTE,
        )
        VisitaProducto.objects.create(
            visita=pendiente, producto=self.producto, cantidad=5, cupones=5
        )
        self.assertEqual(self.producto.stock_actual(), 8)

    def test_cupones_automaticos_al_guardar_linea(self):
        producto = Producto.objects.create(
            nombre="Toallitas", cupones_por_unidad=2
        )
        visita = Visita.objects.create(
            residencia=self.residencia, fecha=timezone.localdate()
        )
        linea = VisitaProducto.objects.create(
            visita=visita, producto=producto, cantidad=3
        )
        self.assertEqual(linea.cupones, 6)

    def test_borrar_visita_devuelve_cupones(self):
        MovimientoCupon.objects.create(producto=self.producto, cantidad=10)
        visita = Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate(),
            estado=Visita.Estado.ENTREGADA,
        )
        VisitaProducto.objects.create(
            visita=visita, producto=self.producto, cantidad=4, cupones=4
        )
        self.assertEqual(self.producto.stock_actual(), 6)
        visita.delete()
        self.assertEqual(self.producto.stock_actual(), 10)


class SiguienteResidenciaTests(TestCase):
    def test_prioriza_visita_pendiente_de_hoy(self):
        zona = Zona.objects.create(nombre="Centro")
        residencia = Residencia.objects.create(nombre="San José", zona=zona)
        Visita.objects.create(
            residencia=residencia, fecha=timezone.localdate(), turno=Visita.Turno.MANANA
        )
        resultado = siguiente_residencia()
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["residencia"], residencia)
        self.assertIsNotNone(resultado["visita"])


class VistasTests(TestCase):
    def setUp(self):
        zona = Zona.objects.create(nombre="Centro")
        self.residencia = Residencia.objects.create(
            nombre="San José", zona=zona, frecuencia_semanal=1
        )
        self.producto = Producto.objects.create(nombre="Pañales")
        MovimientoCupon.objects.create(producto=self.producto, cantidad=20)
        Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate(),
            turno=Visita.Turno.MANANA,
        )

    def test_paginas_principales(self):
        for nombre in ["dashboard", "agenda", "residencia_list", "cupones", "producto_list"]:
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 200, nombre)

    def test_crear_visita_y_marcar_entregada(self):
        otra = Residencia.objects.create(nombre="Santa Marta")
        respuesta = self.client.post(
            reverse("visita_nueva"),
            {
                "residencia": otra.pk,
                "fecha": timezone.localdate().isoformat(),
                "turno": Visita.Turno.MANANA,
                "estado": Visita.Estado.PENDIENTE,
                "notas": "",
                "lineas-TOTAL_FORMS": "1",
                "lineas-INITIAL_FORMS": "0",
                "lineas-MIN_NUM_FORMS": "0",
                "lineas-MAX_NUM_FORMS": "1000",
                "lineas-0-producto": self.producto.pk,
                "lineas-0-cantidad": "3",
                "lineas-0-cupones": "",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        visita = Visita.objects.get(residencia=otra)
        self.assertEqual(visita.lineas.count(), 1)
        self.assertEqual(visita.total_cupones, 3)

        self.client.post(reverse("visita_estado", args=[visita.pk, "E"]))
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ENTREGADA)
