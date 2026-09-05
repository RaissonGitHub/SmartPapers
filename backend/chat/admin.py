from django.contrib import admin

from .models import Mensagem, MensagemAdmin, Sessao, SessaoAdmin

# Register your models here.
admin.site.register(Sessao, SessaoAdmin)
admin.site.register(Mensagem, MensagemAdmin)
