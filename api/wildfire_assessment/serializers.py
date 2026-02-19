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


class AnalysisRequestSerializer(serializers.Serializer):
    """Serializer for the AI analysis request."""

    pre_fire_date = serializers.DateField(
        help_text="Pre-fire date in YYYY-MM-DD format"
    )
    post_fire_date = serializers.DateField(
        help_text="Post-fire date in YYYY-MM-DD format"
    )
    area_of_interest = serializers.CharField(
        max_length=255, help_text="Name of the ecological reserve or area"
    )
    severity_distribution = serializers.DictField(
        child=serializers.DictField(),
        help_text="DNBR severity distribution data",
    )
    image_urls = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="List of image objects with 'label' and 'url' keys",
    )


class AnalysisFollowUpSerializer(serializers.Serializer):
    """Serializer for AI analysis follow-up questions."""

    previous_response_id = serializers.CharField(
        help_text="Conversation ID from the previous response"
    )
    question = serializers.CharField(
        help_text="Follow-up question about the analysis"
    )
