import json
import uuid

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from wildfire_assessment.models import AreaOfInterest, Country, UserCountry, UserProfile
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
