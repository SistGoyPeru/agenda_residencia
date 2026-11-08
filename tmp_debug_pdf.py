import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.utils import timezone
from residencias.models import Visita
from residencias.views import datos_reporte_mensual, rangos_del_mes
from django.test import RequestFactory
from django.contrib.auth import get_user_model

admin = get_user_model().objects.get(username="admin")
print("Estado.ENTREGADA =", repr(Visita.Estado.ENTREGADA))
print("Valor ENTREGADA:", Visita.Estado.ENTREGADA.value)

# Ver visitas entregadas en noviembre
visitas = Visita.objects.filter(
    residencia__propietario=admin,
    estado=Visita.Estado.ENTREGADA,
    fecha__range=(timezone.localdate().replace(day=1), timezone.localdate()),
)
print("Visitas entregadas en noviembre:", visitas.count())
for v in visitas:
    print(f"  - {v.residencia.nombre} | {v.fecha} | {v.estado}")

# Llamar a datos_reporte_mensual directamente
rf = RequestFactory()
request = rf.get("/reportes/mensual/?mes=2026-11")
request.user = admin
datos = datos_reporte_mensual(request)
print("Filas en reporte:", len(datos["filas"]))
print("Total visitas en reporte:", datos["total_visitas"])
for f in datos["filas"]:
    print(f"  - {f['visita'].residencia.nombre} | {f['visita'].fecha} | {f['unidades']} unid | {f['cupones']} cup")
