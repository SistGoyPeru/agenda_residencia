"""Modelos de la agenda de reparto en residencias de ancianos.

La idea es sencilla: se visitan residencias, se entregan productos (pañales y
otros) y por cada unidad entregada se gasta un cupón. El stock de cupones se
controla con cargas manuales y se descuenta automáticamente con las visitas
marcadas como entregadas.
"""
from datetime import timedelta

from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone


class Zona(models.Model):
    """Zona o barrio para agrupar las residencias de la ruta."""

    nombre = models.CharField(max_length=80, unique=True, verbose_name="Nombre")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"

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
        verbose_name="Día preferido",
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


class Producto(models.Model):
    """Producto repartido (pañales, empapadores, cremas...)."""

    nombre = models.CharField(max_length=120, verbose_name="Nombre")
    descripcion = models.CharField(
        max_length=200, blank=True, verbose_name="Descripción"
    )
    cupones_por_unidad = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Cupones por unidad",
        help_text="Cuántos cupones se gastan por cada unidad entregada.",
    )
    stock_minimo = models.PositiveIntegerField(
        default=5,
        verbose_name="Aviso de stock bajo",
        help_text="Se avisa cuando quedan estos cupones o menos.",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("producto_editar", args=[self.pk])

    def cupones_cargados(self):
        return self.movimientos.aggregate(total=Sum("cantidad"))["total"] or 0

    def cupones_usados(self):
        return (
            self.lineas_visita.filter(visita__estado=Visita.Estado.ENTREGADA).aggregate(
                total=Sum("cupones")
            )["total"]
            or 0
        )

    def stock_actual(self):
        return self.cupones_cargados() - self.cupones_usados()

    def stock_bajo(self):
        return self.stock_actual() <= self.stock_minimo

    def porcentaje_stock(self):
        cargados = self.cupones_cargados()
        if cargados <= 0:
            return 0
        return max(0, min(100, round(self.stock_actual() * 100 / cargados)))


class MovimientoCupon(models.Model):
    """Carga o ajuste manual de cupones de un producto.

    Solo guarda entradas (positivas) y ajustes (pueden ser negativos). El uso
    de cupones se calcula a partir de las visitas entregadas, así que borrar
    una visita devuelve automáticamente los cupones al stock.
    """

    class Tipo(models.TextChoices):
        CARGA = "C", "Carga de cupones"
        AJUSTE = "A", "Ajuste"

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="movimientos",
        verbose_name="Producto",
    )
    fecha = models.DateField(default=timezone.localdate, verbose_name="Fecha")
    cantidad = models.IntegerField(
        verbose_name="Cantidad",
        help_text="Positivo para cargar cupones, negativo para descontarlos.",
    )
    tipo = models.CharField(
        max_length=1,
        choices=Tipo.choices,
        default=Tipo.CARGA,
        verbose_name="Tipo",
    )
    notas = models.CharField(max_length=200, blank=True, verbose_name="Notas")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Movimiento de cupones"
        verbose_name_plural = "Movimientos de cupones"

    def __str__(self):
        signo = "+" if self.cantidad >= 0 else ""
        return f"{signo}{self.cantidad} {self.producto.nombre}"


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

    @property
    def total_unidades(self):
        return sum(linea.cantidad for linea in self.lineas.all())

    @property
    def total_cupones(self):
        return sum(linea.cupones for linea in self.lineas.all())


class VisitaProducto(models.Model):
    """Producto entregado en una visita y cupones gastados."""

    visita = models.ForeignKey(
        Visita,
        on_delete=models.CASCADE,
        related_name="lineas",
        verbose_name="Visita",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="lineas_visita",
        verbose_name="Producto",
    )
    cantidad = models.PositiveIntegerField(default=1, verbose_name="Unidades")
    cupones = models.PositiveIntegerField(default=0, verbose_name="Cupones")

    class Meta:
        ordering = ["id"]
        verbose_name = "Producto de la visita"
        verbose_name_plural = "Productos de la visita"

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    def save(self, *args, **kwargs):
        if not self.cupones:
            self.cupones = self.cantidad * self.producto.cupones_por_unidad
        super().save(*args, **kwargs)


def rango_semana(referencia=None):
    """Lunes y domingo de la semana de la fecha dada (por defecto hoy)."""
    referencia = referencia or timezone.localdate()
    inicio = referencia - timedelta(days=referencia.weekday())
    return inicio, inicio + timedelta(days=6)


def dia_semana_de(fecha):
    return DIAS_POR_INDICE[fecha.weekday()]


def siguiente_residencia(referencia=None):
    """Residencia recomendada para la próxima visita.

    Prioriza las visitas pendientes de hoy; si no hay, devuelve la residencia
    con menos visitas de las que le tocan esta semana, dando preferencia a la
    que tiene hoy como día preferido y al orden de ruta.
    """
    referencia = referencia or timezone.localdate()
    hoy_visita = (
        Visita.objects.filter(fecha=referencia, estado=Visita.Estado.PENDIENTE)
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
            estado=Visita.Estado.ENTREGADA, fecha__range=(inicio, fin)
        )
        .values("residencia_id")
        .annotate(total=models.Count("id"))
    }
    dia_hoy = dia_semana_de(referencia)
    candidatas = []
    for residencia in Residencia.objects.filter(activo=True).select_related("zona"):
        faltan = residencia.frecuencia_semanal - entregadas.get(residencia.pk, 0)
        if faltan > 0:
            candidatas.append((residencia, faltan))
    if not candidatas:
        return None

    def clave(item):
        residencia, _ = item
        return (
            0 if residencia.dia_preferido == dia_hoy else 1,
            residencia.zona.orden if residencia.zona else 999,
            residencia.orden_ruta,
            residencia.nombre,
        )

    candidatas.sort(key=clave)
    residencia, faltan = candidatas[0]
    motivo = (
        f"Le faltan {faltan} visita(s) esta semana"
        if faltan > 1
        else "Le falta 1 visita esta semana"
    )
    return {"visita": None, "residencia": residencia, "motivo": motivo}
