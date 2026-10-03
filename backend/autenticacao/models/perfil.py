from django.conf import settings
from django.db import models

from .base import Base


class Perfil(Base):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    tutorial_visto = models.BooleanField(default=False)

    class Meta:
        db_table = "perfil_usuario"

    def __str__(self):
        return f"perfil de {self.usuario}"


def perfil_de(user):
    """Devolve o perfil do usuário, criando-o na primeira chamada."""
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    return perfil