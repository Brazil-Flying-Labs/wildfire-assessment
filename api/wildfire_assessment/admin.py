from django.contrib import admin
from wildfire_assessment.models import EcologicalReserve

# Register your models here.



class EcologicalReserveAdmin(admin.ModelAdmin):
    list_display = ("name", "polygon_path")
    search_fields = ("name", "polygon_path")


admin.site.register(EcologicalReserve, EcologicalReserveAdmin)
