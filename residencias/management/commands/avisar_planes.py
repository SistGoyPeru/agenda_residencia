from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone

from residencias.models import Perfil


class Command(BaseCommand):
    help = "Avisa a los usuarios con plan Pro 4 dias antes de que expire"

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        aviso = hoy + timedelta(days=4)
        perfiles = (
            Perfil.objects.filter(plan="PRO")
            .exclude(activo_hasta__isnull=True)
            .filter(activo_hasta__gte=hoy, activo_hasta__lte=aviso)
        )
        enviados = 0
        for perfil in perfiles:
            if not perfil.usuario.email:
                continue
            send_mail(
                subject="Tu plan Pro vence en breve",
                message=(
                    "Hola {usuario}, tu plan Pro de Ruta Residencias vence el {fecha}. "
                    "Si no se mantiene activado, la suscripcion terminara.".format(
                        usuario=perfil.usuario.username, fecha=perfil.activo_hasta
                    )
                ),
                from_email="SistGoy <alexgoyzueta2018@gmail.com>",
                recipient_list=[perfil.usuario.email],
                fail_silently=False,
            )
            enviados += 1
        self.stdout.write(f"Avisos de vencimiento enviados: {enviados}")
