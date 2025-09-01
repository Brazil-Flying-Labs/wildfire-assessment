from django.db import models


# Create your models here.
class EcologicalReserve(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    polygon_path = models.CharField(max_length=255)
