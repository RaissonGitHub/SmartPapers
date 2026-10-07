from django.db import models


class Base(models.Model):
    class Meta:
        abstract = True
        app_label = "chat"
