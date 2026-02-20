import json
import uuid

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponseForbidden
from django.shortcuts import render
from wildfire_assessment.models import (
    AnalysisRun,
    AreaOfInterest,
    Country,
    UserCountry,
    UserProfile,
)
from wildfire_assessment.svc.analytics import (
    get_analytics_summary,
    get_monthly_stats,
    get_recent_analyses,
    get_top_areas,
    get_user_stats,
)
from wildfire_assessment.svc.aws import delete_polygon_from_s3, upload_polygon_to_s3


class AreaOfInterestAdminForm(forms.ModelForm):
    geojson_file = forms.FileField(required=False, help_text="Upload a .geojson file")

    class Meta:
        model = AreaOfInterest
        fields = ["name", "country", "polygon_path", "municipio", "site", "codigo_ibge", "area_ha"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["polygon_path"].required = False
        self.fields["polygon_path"].disabled = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        geojson_file = self.cleaned_data.get("geojson_file")

        if geojson_file:
            content = geojson_file.read().decode("utf-8")
            # Validate JSON
            json.loads(content)

            safe_name = "".join(
                c if c.isalnum() or c in "-_" else "_" for c in instance.name
            )
            filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.geojson"

            # Delete old polygon from S3 if replacing
            if instance.polygon_path:
                delete_polygon_from_s3(instance.polygon_path)

            upload_polygon_to_s3(filename, content)
            instance.polygon_path = filename

        if commit:
            instance.save()
        return instance


class AreaOfInterestAdmin(admin.ModelAdmin):
    form = AreaOfInterestAdminForm
    list_display = ("name", "polygon_path", "country")
    search_fields = ("name", "polygon_path")


admin.site.register(AreaOfInterest, AreaOfInterestAdmin)


class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


admin.site.register(Country, CountryAdmin)


class UserCountryInline(admin.TabularInline):
    model = UserCountry
    extra = 0
    autocomplete_fields = ["country"]
    verbose_name = "Authorized country"
    verbose_name_plural = "Authorized countries"


User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "Language preference"
    verbose_name_plural = "Language preference"


class UserAdmin(BaseUserAdmin):
    base_inlines = getattr(BaseUserAdmin, "inlines", None) or []
    inlines = [*base_inlines, UserCountryInline, UserProfileInline]


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)


class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = (
        "area_of_interest",
        "user",
        "pre_fire_date",
        "post_fire_date",
        "total_burned_ha",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "area_of_interest__name",
        "user__email",
    )
    readonly_fields = (
        "user",
        "area_of_interest",
        "pre_fire_date",
        "post_fire_date",
        "status",
        "severity_data",
        "total_burned_ha",
        "created_at",
        "completed_at",
        "image_previews",
    )
    fieldsets = (
        ("Analysis Details", {
            "fields": (
                "user",
                "area_of_interest",
                "pre_fire_date",
                "post_fire_date",
                "status",
                "severity_data",
                "total_burned_ha",
                "created_at",
                "completed_at",
            ),
        }),
        ("Image Previews", {
            "fields": ("image_previews",),
        }),
    )

    def image_previews(self, obj):
        from django.utils.html import format_html
        from wildfire_assessment.svc.aws import get_presigned_image_url

        images = [
            ("Pre-fire RGB", obj.rgb_pre_fire_image),
            ("Post-fire RGB", obj.rgb_post_fire_image),
            ("dNDVI", obj.dndvi_image),
            ("dNBR", obj.dnbr_image),
            ("RBR", obj.rbr_image),
        ]
        parts = []
        for label, key in images:
            if key:
                url = get_presigned_image_url(key)
                parts.append(format_html(
                    '<div style="display:inline-block;margin:8px;text-align:center;">'
                    '<div style="font-weight:bold;margin-bottom:4px;">{}</div>'
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-width:300px;max-height:300px;border:1px solid #ccc;" />'
                    '</a></div>',
                    label, url, url,
                ))
        if not parts:
            return format_html("<em>No images available</em>")
        return format_html("".join(str(p) for p in parts))

    image_previews.short_description = "Images"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(AnalysisRun, AnalysisRunAdmin)


def analytics_dashboard_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Superuser access required.")
    context = {
        **admin.site.each_context(request),
        "title": "Analytics Dashboard",
        "summary": get_analytics_summary(),
        "user_stats": get_user_stats(),
        "monthly_stats": get_monthly_stats(),
        "top_areas": get_top_areas(),
        "recent_analyses": get_recent_analyses(),
    }
    return render(request, "admin/analytics_dashboard.html", context)
