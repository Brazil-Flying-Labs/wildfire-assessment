from django.conf import settings
from django.db import models


class Country(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=2, unique=True)  # ISO 3166-1 alpha-2 code

    def __str__(self):
        return f"{self.code} - {self.name}"


class AreaOfInterest(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    polygon_path = models.CharField(max_length=255)
    municipio = models.CharField(max_length=255, blank=True, null=True)
    site = models.URLField(max_length=500, blank=True, null=True)
    codigo_ibge = models.CharField(
        max_length=7, blank=True, null=True
    )  # Código IBGE tem 7 dígitos
    area_ha = models.DecimalField(
        max_digits=15, decimal_places=3, blank=True, null=True
    )  # Para suportar valores como 142.545,681
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="areas_of_interest",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "wildfire_assessment_ecologicalreserve"
        verbose_name = "Area of Interest"
        verbose_name_plural = "Areas of Interest"


# Alias for backward compatibility
EcologicalReserve = AreaOfInterest


class UserCountry(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="country_permissions",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="authorized_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "country")
        ordering = ["user", "country"]
        verbose_name = "User country access"
        verbose_name_plural = "User country access"

    def __str__(self):
        return f"{self.user} - {self.country.code}"


LANGUAGE_CHOICES = [
    ("en", "English"),
    ("pt-BR", "Português (Brasil)"),
    ("fr", "Français"),
]

THEME_CHOICES = [
    ("light", "Light"),
    ("dark", "Dark"),
]


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    default_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="en",
    )
    theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default="light",
    )

    def __str__(self):
        return f"{self.user} - {self.default_language}"
