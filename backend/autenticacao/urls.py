from django.urls import path

from .views import (
    CsrfView,
    CurrentUserView,
    LoginView,
    LogoutView,
    PreferenciasView,
    RegistrarView,
)

app_name = "autenticacao"

urlpatterns = [
    path("registrar/", RegistrarView.as_view(), name="registrar"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("preferencias/", PreferenciasView.as_view(), name="preferencias"),
    path("csrf/", CsrfView.as_view(), name="csrf"),
]