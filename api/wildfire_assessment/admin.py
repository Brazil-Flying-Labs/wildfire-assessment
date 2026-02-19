from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from wildfire_assessment.models import AreaOfInterest, Country, UserCountry, UserProfile

# Register your models here.


class AreaOfInterestAdmin(admin.ModelAdmin):
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
