from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("agenda/", views.agenda, name="agenda"),
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
