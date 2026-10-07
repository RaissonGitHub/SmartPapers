from django.contrib import admin

from .models import Artigo, ArtigoAdmin, ArtigoAutor, Autor, AutorAdmin

# Register your models here.
admin.site.register(Artigo, ArtigoAdmin)
admin.site.register(Autor, AutorAdmin)
admin.site.register(ArtigoAutor)
