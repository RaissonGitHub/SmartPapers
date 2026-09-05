from django.db import models
from django.utils.translation import gettext_lazy as _


class Papel(models.TextChoices):
    USUARIO = "USUARIO", _("Usuário")
    MODELO = "MODELO", _("Modelo")
