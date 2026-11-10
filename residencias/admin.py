from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import (
    Perfil,
    Residencia,
    Visita,
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


@admin.register(Visita)
class VisitaAdmin(admin.ModelAdmin):
    list_display = ("residencia", "fecha", "turno", "estado")
    list_filter = ("estado", "turno", "fecha")
    search_fields = ("residencia__nombre",)
    date_hierarchy = "fecha"
    autocomplete_fields = ("residencia",)
