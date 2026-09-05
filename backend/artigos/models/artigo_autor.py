from typing import ClassVar

from django.db import models

from .artigo import Artigo
from .autor import Autor
from .base import Base


class ArtigoAutor(Base):
    artigo = models.ForeignKey(Artigo, on_delete=models.CASCADE)
    autor = models.ForeignKey(Autor, on_delete=models.CASCADE)

    class Meta:
        db_table = "artigo_autor"
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["artigo", "autor"],
                name="unique_artigo_autor",
            )
        ]
