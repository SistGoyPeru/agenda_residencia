from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import (
    MovimientoCupon,
    Perfil,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
    Zona,
)


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = "Perfil"
    fields = (
        "plan",
        "activo_hasta",
        "empresa",
        "cif",
        "telefono",
        "email_contacto",
        "direccion",
        "web",
    )


class UsuarioAdmin(DjangoUserAdmin):
    inlines = [PerfilInline]
    list_display = ("username", "email", "is_staff", "is_active")


admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)


@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden")
    ordering = ("orden", "nombre")


@admin.register(Residencia)
class ResidenciaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "zona",
        "orden_ruta",
        "frecuencia_semanal",
        "dia_preferido",
        "telefono",
        "activo",
    )
    list_filter = ("activo", "zona", "dia_preferido")
    search_fields = ("nombre", "direccion", "contacto", "telefono")
    ordering = ("zona__orden", "orden_ruta", "nombre")


class MovimientoCuponInline(admin.TabularInline):
    model = MovimientoCupon
    extra = 0
    fields = ("fecha", "cantidad", "tipo", "notas")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "cupones_por_unidad",
        "stock_actual",
        "stock_minimo",
        "activo",
    )
    list_filter = ("activo",)
    search_fields = ("nombre", "descripcion")
    inlines = [MovimientoCuponInline]

    @admin.display(description="Cupones en stock")
    def stock_actual(self, obj):
        return obj.stock_actual()


class VisitaProductoInline(admin.TabularInline):
    model = VisitaProducto
    extra = 0
    fields = ("cupones",)


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = ("residencia", "fecha", "turno", "estado", "total_unidades")
    list_filter = ("estado", "turno", "fecha")
    search_fields = ("residencia__nombre",)
    date_hierarchy = "fecha"
    inlines = [VisitaProductoInline]
    autocomplete_fields = ("residencia",)

    @admin.display(description="Unidades")
    def total_unidades(self, obj):
        return obj.total_unidades
