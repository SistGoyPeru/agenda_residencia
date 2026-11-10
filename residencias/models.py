"""Modelos de la agenda de reparto en residencias de ancianos.

La idea es sencilla: se visitan residencias y se registra cada visita
(pendiente, entregada o con incidencia) en la agenda semanal.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Perfil(models.Model):
    """Plan contratado por cada usuario de la agenda."""

    class Plan(models.TextChoices):
        GRATIS = "GRATIS", "Gratis"
        PRO = "PRO", "Pro"

    LIMITE_GRATIS = 3

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuario",
    )
    plan = models.CharField(
        max_length=10,
        choices=Plan.choices,
        default=Plan.GRATIS,
        verbose_name="Plan",
    )
    activo_hasta = models.DateField(
        null=True, blank=True, verbose_name="Activo hasta"
    )
    empresa = models.CharField(
        max_length=120, blank=True, verbose_name="Nombre de la empresa"
    )
    cif = models.CharField(max_length=20, blank=True, verbose_name="CIF/NIF")
    telefono = models.CharField(max_length=30, blank=True, verbose_name="Teléfono")
    email_contacto = models.EmailField(
        blank=True, verbose_name="Email de contacto"
    )
    direccion = models.CharField(
        max_length=200, blank=True, verbose_name="Dirección"
    )
    web = models.URLField(blank=True, verbose_name="Web")
    logo = models.BinaryField(blank=True, null=True, editable=False)
    logo_tipo = models.CharField(max_length=40, blank=True, editable=False)
    logo_actualizado = models.DateTimeField(
        null=True, blank=True, editable=False
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f"{self.usuario} · {self.get_plan_display()}"

    @property
    def es_pro(self):
        if self.plan != self.Plan.PRO:
            return False
        if self.activo_hasta and self.activo_hasta < timezone.localdate():
            return False
        return True

    @property
    def limite_residencias(self):
        return None if self.es_pro else self.LIMITE_GRATIS


def perfil_de(usuario):
    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    return perfil


class Zona(models.Model):
    """Zona o barrio para agrupar las residencias de la ruta."""

    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="zonas",
        verbose_name="Propietario",
    )
    nombre = models.CharField(max_length=80, verbose_name="Nombre")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"
        constraints = [
            models.UniqueConstraint(
                fields=["propietario", "nombre"],
                name="zona_unica_por_propietario",
            )
        ]

    def __str__(self):
        return self.nombre


class DiasSemana(models.TextChoices):
    LUNES = "LUN", "Lunes"
    MARTES = "MAR", "Martes"
    MIERCOLES = "MIE", "Miércoles"
    JUEVES = "JUE", "Jueves"
    VIERNES = "VIE", "Viernes"
    SABADO = "SAB", "Sábado"
    DOMINGO = "DOM", "Domingo"


DIAS_POR_INDICE = [
    DiasSemana.LUNES,
    DiasSemana.MARTES,
    DiasSemana.MIERCOLES,
    DiasSemana.JUEVES,
    DiasSemana.VIERNES,
    DiasSemana.SABADO,
    DiasSemana.DOMINGO,
]


class Residencia(models.Model):
    """Una residencia de ancianos a la que se reparte."""

    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="residencias",
        verbose_name="Propietario",
    )
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    direccion = models.CharField(max_length=200, blank=True, verbose_name="Dirección")
    zona = models.ForeignKey(
        Zona,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residencias",
        verbose_name="Zona",
    )
    contacto = models.CharField(max_length=80, blank=True, verbose_name="Persona de contacto")
    telefono = models.CharField(max_length=30, blank=True, verbose_name="Teléfono")
    horario = models.CharField(
        max_length=80, blank=True, verbose_name="Horario de entrega"
    )
    orden_ruta = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden en la ruta",
        help_text="Número para ordenar las visitas dentro de la zona.",
    )
    frecuencia_semanal = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Visitas por semana",
        help_text="Cuántas veces a la semana hay que ir a esta residencia.",
    )
    dia_preferido = models.CharField(
        max_length=3,
        choices=DiasSemana.choices,
        blank=True,
        verbose_name="Día orientativo",
        help_text=(
            "Opcional. No es una cita fija: la ruta puede cambiar de día. "
            "Solo sirve como referencia."
        ),
    )
    notas = models.TextField(blank=True, verbose_name="Notas de acceso")
    activo = models.BooleanField(default=True, verbose_name="Activa")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["zona__orden", "orden_ruta", "nombre"]
        verbose_name = "Residencia"
        verbose_name_plural = "Residencias"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("residencia_detalle", args=[self.pk])

    def telefono_enlace(self):
        """Teléfono listo para usar en un enlace tel:."""
        limpio = "".join(c for c in self.telefono if c.isdigit() or c == "+")
        return limpio

    def visitas_entregadas_semana(self, referencia=None):
        inicio, fin = rango_semana(referencia)
        return self.visitas.filter(
            estado=Visita.Estado.ENTREGADA, fecha__range=(inicio, fin)
        ).count()

    def pendiente_esta_semana(self, referencia=None):
        return self.visitas_entregadas_semana(referencia) < self.frecuencia_semanal


class Visita(models.Model):
    """Una visita a una residencia (hoja de reparto de ese día)."""

    class Turno(models.TextChoices):
        MANANA = "M", "Mañana"
        TARDE = "T", "Tarde"

    class Estado(models.TextChoices):
        PENDIENTE = "P", "Pendiente"
        ENTREGADA = "E", "Entregada"
        INCIDENCIA = "I", "Incidencia"

    residencia = models.ForeignKey(
        Residencia,
        on_delete=models.PROTECT,
        related_name="visitas",
        verbose_name="Residencia",
    )
    fecha = models.DateField(default=timezone.localdate, verbose_name="Fecha")
    turno = models.CharField(
        max_length=1, choices=Turno.choices, default=Turno.MANANA, verbose_name="Turno"
    )
    estado = models.CharField(
        max_length=1,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name="Estado",
    )
    notas = models.TextField(blank=True, verbose_name="Notas")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "turno", "residencia__orden_ruta", "residencia__nombre"]
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"
        constraints = [
            models.UniqueConstraint(
                fields=["residencia", "fecha", "turno"],
                name="visita_unica_por_residencia_fecha_turno",
            )
        ]

    def __str__(self):
        return f"{self.residencia.nombre} · {self.fecha:%d/%m/%Y}"

    def get_absolute_url(self):
        return reverse("visita_detalle", args=[self.pk])


def rango_semana(referencia=None):
    """Lunes y domingo de la semana de la fecha dada (por defecto hoy)."""
    referencia = referencia or timezone.localdate()
    inicio = referencia - timedelta(days=referencia.weekday())
    return inicio, inicio + timedelta(days=6)


def dia_semana_de(fecha):
    return DIAS_POR_INDICE[fecha.weekday()]


def siguiente_residencia(usuario, referencia=None):
    """Residencia recomendada para la próxima visita de este usuario.

    La ruta no tiene días fijos: primero devuelve una visita pendiente de hoy
    (si existe) y, si no, la residencia a la que todavía le faltan visitas por
    planificar esta semana, sin importar el día en que se hagan.
    """
    referencia = referencia or timezone.localdate()
    hoy_visita = (
        Visita.objects.filter(
            residencia__propietario=usuario,
            fecha=referencia,
            estado=Visita.Estado.PENDIENTE,
        )
        .select_related("residencia", "residencia__zona")
        .order_by(
            "residencia__zona__orden",
            "residencia__orden_ruta",
            "residencia__nombre",
        )
        .first()
    )
    if hoy_visita:
        return {"visita": hoy_visita, "residencia": hoy_visita.residencia, "motivo": "Visita pendiente de hoy"}

    inicio, fin = rango_semana(referencia)
    entregadas = {
        fila["residencia_id"]: fila["total"]
        for fila in Visita.objects.filter(
            residencia__propietario=usuario,
            estado=Visita.Estado.ENTREGADA,
            fecha__range=(inicio, fin),
        )
        .values("residencia_id")
        .annotate(total=models.Count("id"))
    }
    programadas = {
        fila["residencia_id"]: fila["total"]
        for fila in Visita.objects.filter(
            residencia__propietario=usuario,
            estado=Visita.Estado.PENDIENTE,
            fecha__range=(inicio, fin),
        )
        .values("residencia_id")
        .annotate(total=models.Count("id"))
    }
    candidatas = []
    for residencia in (
        Residencia.objects.filter(propietario=usuario, activo=True)
        .select_related("zona")
    ):
        cubiertas = entregadas.get(residencia.pk, 0) + programadas.get(residencia.pk, 0)
        faltan = residencia.frecuencia_semanal - cubiertas
        if faltan > 0:
            candidatas.append((residencia, faltan))
    if not candidatas:
        return None

    candidatas.sort(
        key=lambda item: (
            item[0].zona.orden if item[0].zona else 999,
            item[0].orden_ruta,
            item[0].nombre,
        )
    )
    residencia, faltan = candidatas[0]
    motivo = (
        f"Le faltan {faltan} visita(s) esta semana"
        if faltan > 1
        else "Le falta 1 visita esta semana"
    )
    return {"visita": None, "residencia": residencia, "motivo": motivo}
