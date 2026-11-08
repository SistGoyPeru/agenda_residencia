from django.utils import timezone
from residencias.models import Visita, Residencia, Producto
from django.contrib.auth import get_user_model
import datetime

admin = get_user_model().objects.get(username="admin")
print("Estado.ENTREGADA =", repr(Visita.Estado.ENTREGADA))
print("dict choices:", dict(Visita.Estado.choices))

hoy = timezone.localdate()
inicio = date(2026, 11, 1)
fin = date(2026, 11, 30)
print("Rango:", inicio, "a", fin)

visitas = Visita.objects.filter(
    residencia__propietario=admin,
    estado=Visita.Estado.ENTREGADA,
    fecha__range=(inicio, fin),
)
print("Visitas encontradas con filtro:", visitas.count())
for v in visitas:
    print(f"  - {v.residencia.nombre} | {v.fecha} | {v.estado} | tipo_estado={type(v.estado)}")
