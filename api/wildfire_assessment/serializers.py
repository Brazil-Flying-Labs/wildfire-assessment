from django.contrib.auth import get_user_model
from rest_framework import serializers
from wildfire_assessment.models import AreaOfInterest, Country, UserProfile

User = get_user_model()


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "code"]


class AreaOfInterestSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    country_code = serializers.CharField(source="country.code", read_only=True)

    class Meta:
        model = AreaOfInterest
        fields = [
            "id",
            "name",
            "polygon_path",
            "municipio",
            "site",
            "codigo_ibge",
            "area_ha",
            "country",
            "country_name",
            "country_code",
        ]
        read_only_fields = ["polygon_path", "area_ha"]


# Alias for backward compatibility
EcologicalReserveSerializer = AreaOfInterestSerializer


class AreaOfInterestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating areas of interest with GeoJSON upload."""

    geojson = serializers.JSONField(write_only=True, required=True)

    class Meta:
        model = AreaOfInterest
        fields = ["id", "name", "country", "geojson"]

    def validate_country(self, value):
        """Ensure the user has access to the specified country."""
        request = self.context.get("request")
        if request and request.user:
            user_countries = request.user.country_permissions.values_list(
                "country_id", flat=True
            )
            if value.id not in user_countries:
                raise serializers.ValidationError(
                    "You do not have permission to create areas of interest in this country."
                )
        return value

    def validate_geojson(self, value):
        """Validate that the GeoJSON has the expected structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("GeoJSON must be an object.")

        geojson_type = value.get("type")
        if geojson_type not in [
            "Feature",
            "FeatureCollection",
            "Polygon",
            "MultiPolygon",
        ]:
            raise serializers.ValidationError(
                "GeoJSON must be a Feature, FeatureCollection, Polygon, or MultiPolygon."
            )

        return value

    def create(self, validated_data):
        import json
        import os
        import uuid

        from django.conf import settings

        geojson_data = validated_data.pop("geojson")
        name = validated_data.get("name")

        # Generate a unique filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.geojson"

        # Save to polygons directory
        polygons_dir = os.path.join(
            settings.BASE_DIR, "..", "..", "polygons"
        )
        os.makedirs(polygons_dir, exist_ok=True)

        filepath = os.path.join(polygons_dir, filename)
        with open(filepath, "w") as f:
            json.dump(geojson_data, f)

        # Calculate area if possible (simplified - actual calculation may need geopandas)
        area_ha = None

        validated_data["polygon_path"] = filename
        validated_data["area_ha"] = area_ha

        return super().create(validated_data)


# Alias for backward compatibility
EcologicalReserveCreateSerializer = AreaOfInterestCreateSerializer


class UserMeSerializer(serializers.ModelSerializer):
    default_language = serializers.CharField(source="profile.default_language")
    authorized_countries = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "default_language",
            "authorized_countries",
        ]
        read_only_fields = ["email", "first_name", "last_name", "authorized_countries"]

    def get_authorized_countries(self, obj):
        countries = Country.objects.filter(
            authorized_users__user=obj
        ).values("id", "name", "code")
        return list(countries)

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
