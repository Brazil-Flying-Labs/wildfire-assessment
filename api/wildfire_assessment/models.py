from django.db import models


# Create your models here.
class EcologicalReserve(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    polygon_path = models.CharField(max_length=255)
    municipio = models.CharField(max_length=255, blank=True, null=True)
    site = models.URLField(max_length=500, blank=True, null=True)
    codigo_ibge = models.CharField(max_length=7, blank=True, null=True)  # Código IBGE tem 7 dígitos
    area_ha = models.DecimalField(max_digits=15, decimal_places=3, blank=True, null=True)  # Para suportar valores como 142.545,681
