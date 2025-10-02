from rest_framework import serializers
from wildfire_assessment.models import EcologicalReserve


class EcologicalReserveSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EcologicalReserve
        fields = ["id", "name", "polygon_path", "municipio", "site", "codigo_ibge", "area_ha"]
