from django.utils import timezone
from residencias.models import Visita, Residencia, Producto, VisitaProducto, MovimientoCupon
from django.contrib.auth import get_user_model

admin = get_user_model().objects.get(username="admin")
hoy = timezone.localdate()
print("Fecha hoy:", hoy)
print("Mes:", hoy.strftime("%Y-%m"))

# Ver qué visitas existen
visitas = Visita.objects.filter(residencia__propietario=admin)
print("Total visitas:", visitas.count())
for v in visitas:
    print(f"  - {v.residencia.nombre} | {v.fecha} | {v.turno} | {v.estado} | propietario: {v.residencia.propietario.username}")

# Crear entrega entregada hoy si no hay
if visitas.filter(estado="E").count() == 0:
    res_a = Residencia.objects.filter(propietario=admin).first()
    prod_pa = Producto.objects.filter(propietario=admin).first()
    if res_a and prod_pa:
        v, created = Visita.objects.get_or_create(
            residencia=res_a, fecha=hoy, turno="M",
            defaults={"estado": "E", "notas": "Entrega prueba PDF"}
        )
        if v.estado != "E":
            v.estado = "E"
            v.save()
        lp, created2 = VisitaProducto.objects.get_or_create(
            visita=v, producto=prod_pa,
            defaults={"cantidad": 2, "cupones": 2}
        )
        MovimientoCupon.objects.create(producto=prod_pa, cantidad=2, tipo="A", notas="Entrega PDF")
        print(f"Creada visita entregada: {v.residencia.nombre} el {v.fecha}")
        print(f"  Producto: {prod_pa.nombre} x{lp.cantidad}")
    else:
        print("Faltan residencia o producto")
else:
    print("Ya hay entregas entregadas")

print("Visitas entregadas hoy:", Visita.objects.filter(residencia__propietario=admin, fecha=hoy, estado="E").count())
