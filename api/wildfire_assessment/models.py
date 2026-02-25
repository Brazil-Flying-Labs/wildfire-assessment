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
    centroid_lat = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    centroid_lng = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )

    class Meta:
        verbose_name = "Area of Interest"
        verbose_name_plural = "Areas of Interest"


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
        default="dark",
    )
    dashboard_widgets = models.JSONField(
        null=True,
        blank=True,
        default=None,
        help_text="Ordered list of visible dashboard widget IDs",
    )
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.default_language}"


class AnalysisRun(models.Model):
    """Stores information about each wildfire analysis run."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_runs",
    )
    area_of_interest = models.ForeignKey(
        AreaOfInterest,
        on_delete=models.CASCADE,
        related_name="analysis_runs",
    )
    pre_fire_date = models.DateField()
    post_fire_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="completed",
    )

    # Severity data stored as JSON
    severity_data = models.JSONField(null=True, blank=True)

    # Total burned area in hectares
    total_burned_ha = models.DecimalField(
        max_digits=15, decimal_places=3, null=True, blank=True
    )

    # S3 image keys from fire assessment visual deliverables
    rgb_pre_fire_image = models.CharField(max_length=255, null=True, blank=True)
    rgb_post_fire_image = models.CharField(max_length=255, null=True, blank=True)
    dndvi_image = models.CharField(max_length=255, null=True, blank=True)
    dnbr_image = models.CharField(max_length=255, null=True, blank=True)
    rbr_image = models.CharField(max_length=255, null=True, blank=True)

    # Scientific deliverable URLs (GCS export links, populated async)
    scientific_rgb_pre_fire_url = models.URLField(max_length=500, null=True, blank=True)
    scientific_rgb_post_fire_url = models.URLField(
        max_length=500, null=True, blank=True
    )
    scientific_dndvi_url = models.URLField(max_length=500, null=True, blank=True)
    scientific_dnbr_url = models.URLField(max_length=500, null=True, blank=True)
    scientific_rbr_url = models.URLField(max_length=500, null=True, blank=True)

    # Celery task IDs for in-progress scientific deliverables
    scientific_rgb_pre_fire_task_id = models.CharField(
        max_length=255, null=True, blank=True
    )
    scientific_rgb_post_fire_task_id = models.CharField(
        max_length=255, null=True, blank=True
    )
    scientific_dndvi_task_id = models.CharField(max_length=255, null=True, blank=True)
    scientific_dnbr_task_id = models.CharField(max_length=255, null=True, blank=True)
    scientific_rbr_task_id = models.CharField(max_length=255, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"

    def __str__(self):
        return f"{self.area_of_interest.name} - {self.pre_fire_date} to {self.post_fire_date}"


class Notification(models.Model):
    """In-app notifications for users."""

    NOTIFICATION_TYPES = [
        ("deliverable_ready", "Deliverable Ready"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default="deliverable_ready",
    )
    deliverable_name = models.CharField(max_length=30, blank=True)
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"Notification for {self.user} - {self.notification_type}"


class AIProvider(models.Model):
    """Singleton configuration for the active AI provider."""

    PROVIDER_CHOICES = [
        ("gemini", "Google Gemini"),
        ("openai", "OpenAI"),
    ]

    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default="gemini",
    )
    model_name = models.CharField(
        max_length=100,
        default="gemini-2.0-flash-lite",
        help_text="Model identifier, e.g. gemini-2.0-flash-lite or gpt-4o-mini",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Provider Configuration"
        verbose_name_plural = "AI Provider Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_provider_display()} — {self.model_name}"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
