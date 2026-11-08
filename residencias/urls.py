from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("inicio/", views.landing, name="landing"),
    path("agenda/", views.agenda, name="agenda"),
    path("cuenta/", views.mi_cuenta, name="mi_cuenta"),
    path("cuenta/logo/", views.mi_logo, name="mi_logo"),
    path("planes/", views.planes, name="planes"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nueva/", views.usuario_crear, name="usuario_nueva"),
    path(
        "usuarios/<int:pk>/editar/",
        views.usuario_editar,
        name="usuario_editar",
    ),
    path(
        "usuarios/<int:pk>/borrar/",
        views.usuario_borrar,
        name="usuario_borrar",
    ),
    path(
        "usuarios/<int:pk>/activar-plan/",
        views.usuario_activar_plan,
        name="usuario_activar_plan",
    ),
    path("reportes/mensual/", views.reporte_mensual, name="reporte_mensual"),
    path(
        "reportes/mensual/pdf/",
        views.reporte_mensual_pdf,
        name="reporte_mensual_pdf",
    ),
    path("zonas/", views.zona_list, name="zona_list"),
    path("zonas/nueva/", views.zona_form, name="zona_nueva"),
    path("zonas/<int:pk>/editar/", views.zona_form, name="zona_editar"),
    path("zonas/<int:pk>/borrar/", views.zona_borrar, name="zona_borrar"),
    path("residencias/", views.residencia_list, name="residencia_list"),
    path("residencias/nueva/", views.residencia_form, name="residencia_nueva"),
    path(
        "residencias/<int:pk>/", views.residencia_detalle, name="residencia_detalle"
    ),
    path(
        "residencias/<int:pk>/editar/",
        views.residencia_form,
        name="residencia_editar",
    ),
    path(
        "residencias/<int:pk>/borrar/",
        views.residencia_borrar,
        name="residencia_borrar",
    ),
    path("productos/", views.producto_list, name="producto_list"),
    path("productos/nuevo/", views.producto_form, name="producto_nuevo"),
    path(
        "productos/<int:pk>/editar/", views.producto_form, name="producto_editar"
    ),
    path(
        "productos/<int:pk>/borrar/", views.producto_borrar, name="producto_borrar"
    ),
    path("cupones/", views.cupones, name="cupones"),
    path("cupones/cargar/", views.cupon_cargar, name="cupon_cargar"),
    path("visitas/nueva/", views.visita_form, name="visita_nueva"),
    path("visitas/<int:pk>/", views.visita_detalle, name="visita_detalle"),
    path(
        "visitas/<int:pk>/editar/", views.visita_form, name="visita_editar"
    ),
    path(
        "visitas/<int:pk>/estado/<str:estado>/",
        views.visita_estado,
        name="visita_estado",
    ),
    path("visitas/<int:pk>/borrar/", views.visita_borrar, name="visita_borrar"),
]
