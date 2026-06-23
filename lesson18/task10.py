
from django.db import models


class Ogloszenie(models.Model):
    tytul = models.CharField(max_length=100)
    opis = models.TextField()
    cena = models.DecimalField(max_digits=8, decimal_places=2)
    data_dodania = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tytul

#--------------------------------------

from django.contrib import admin

from .models import Ogloszenie


@admin.register(Ogloszenie)
class OgloszenieAdmin(admin.ModelAdmin):
    list_display = ('tytul', 'cena', 'data_dodania')
