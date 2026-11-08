from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from residencias import views as residencias_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "cuentas/entrar/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "cuentas/salir/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "cuentas/registro/",
        residencias_views.registro,
        name="registro",
    ),
    path(
        "accounts/password_change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change.html"
        ),
        name="password_change",
    ),
    path(
        "accounts/password_change/done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("", include("residencias.urls")),
]
