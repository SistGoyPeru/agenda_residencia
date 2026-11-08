from django.utils import timezone
from residencias.models import Visita, Residencia, Producto, VisitaProducto, MovimientoCupon
from django.contrib.auth import get_user_model

admin = get_user_model().objects.get(username="admin")
hoy = timezone.localdate()
print("Hoy:", hoy)

res_a = Residencia.objects.filter(propietario=admin, nombre__icontains="Residencia").first()
prod_pa = Producto.objects.filter(propietario=admin).first()

if res_a and prod_pa:
    v, created = Visita.objects.get_or_create(
        residencia=res_a, fecha=hoy, turno="M",
        defaults={"estado": "E", "notas": "Entrega prueba PDF hoy"}
    )
    if v.estado != "E":
        v.estado = "E"
        v.save()
    lp, created2 = VisitaProducto.objects.get_or_create(
        visita=v, producto=prod_pa,
        defaults={"cantidad": 2, "cupones": 2}
    )
    MovimientoCupon.objects.create(producto=prod_pa, cantidad=2, tipo="A", notas="Entrega PDF")
    print(f"Creada/actualizada visita: {v.residencia.nombre} | {v.fecha} | {v.estado}")
else:
    print("Faltan residencia o producto")

print("Total entregas hoy:", Visita.objects.filter(residencia__propietario=admin, fecha=hoy, estado="E").count())
