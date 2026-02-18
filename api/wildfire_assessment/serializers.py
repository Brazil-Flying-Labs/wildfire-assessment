from django.contrib.auth import get_user_model
from rest_framework import serializers
from wildfire_assessment.models import EcologicalReserve, UserProfile

User = get_user_model()


class EcologicalReserveSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EcologicalReserve
        fields = ["id", "name", "polygon_path", "municipio", "site", "codigo_ibge", "area_ha"]


class UserMeSerializer(serializers.ModelSerializer):
    default_language = serializers.CharField(source="profile.default_language")

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "default_language"]
        read_only_fields = ["email", "first_name", "last_name"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        if "default_language" in profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            profile.default_language = profile_data["default_language"]
            profile.save(update_fields=["default_language"])
        return instance
