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
        """
        Validate GeoJSON structure and geometry for Google Earth Engine compatibility.
        
        Validates:
        - Valid GeoJSON structure (type, geometry)
        - Valid geometry using shapely
        - Coordinate ranges (lon: -180 to 180, lat: -90 to 90)
        - Polygon validity (closed rings, no self-intersection)
        """
        from shapely.geometry import shape
        from shapely.validation import explain_validity

        if not isinstance(value, dict):
            raise serializers.ValidationError("GeoJSON must be an object.")

        geojson_type = value.get("type")
        if not geojson_type:
            raise serializers.ValidationError("GeoJSON must have a 'type' field.")

        # Extract geometry based on GeoJSON type
        geometry = None
        if geojson_type == "Feature":
            geometry = value.get("geometry")
            if not geometry:
                raise serializers.ValidationError(
                    "Feature must have a 'geometry' field."
                )
        elif geojson_type == "FeatureCollection":
            features = value.get("features", [])
            if not features:
                raise serializers.ValidationError(
                    "FeatureCollection must have at least one feature."
                )
            # Validate each feature's geometry
            for i, feature in enumerate(features):
                if not isinstance(feature, dict):
                    raise serializers.ValidationError(
                        f"Feature at index {i} must be an object."
                    )
                feat_geom = feature.get("geometry")
                if feat_geom:
                    self._validate_geometry(feat_geom, f"Feature[{i}]")
            return value
        elif geojson_type in ["Polygon", "MultiPolygon", "Point", "LineString", "MultiPoint", "MultiLineString"]:
            geometry = value
        else:
            raise serializers.ValidationError(
                f"Unsupported GeoJSON type: '{geojson_type}'. "
                "Must be Feature, FeatureCollection, or a geometry type."
            )

        if geometry:
            self._validate_geometry(geometry, "geometry")

        return value

    def _validate_geometry(self, geometry, context="geometry"):
        """Validate a GeoJSON geometry object."""
        from shapely.geometry import shape
        from shapely.validation import explain_validity

        if not isinstance(geometry, dict):
            raise serializers.ValidationError(
                f"{context}: Geometry must be an object."
            )

        geom_type = geometry.get("type")
        if not geom_type:
            raise serializers.ValidationError(
                f"{context}: Geometry must have a 'type' field."
            )

        coords = geometry.get("coordinates")
        if geom_type not in ["GeometryCollection"] and not coords:
            raise serializers.ValidationError(
                f"{context}: Geometry must have 'coordinates' field."
            )

        # Validate coordinate ranges
        if coords:
            self._validate_coordinates(coords, context)

        # Use shapely to validate geometry structure
        try:
            geom = shape(geometry)
        except Exception as e:
            raise serializers.ValidationError(
                f"{context}: Invalid geometry structure - {str(e)}"
            )

        # Check if geometry is valid
        if not geom.is_valid:
            reason = explain_validity(geom)
            raise serializers.ValidationError(
                f"{context}: Invalid geometry - {reason}"
            )

        # Check if geometry is empty
        if geom.is_empty:
            raise serializers.ValidationError(
                f"{context}: Geometry cannot be empty."
            )

    def _validate_coordinates(self, coords, context, depth=0):
        """Recursively validate coordinate ranges."""
        if depth > 10:  # Prevent infinite recursion
            return

        if isinstance(coords, (int, float)):
            return

        if isinstance(coords, list):
            if len(coords) >= 2 and all(isinstance(c, (int, float)) for c in coords[:2]):
                # This is a coordinate pair [lon, lat] or [lon, lat, alt]
                lon, lat = coords[0], coords[1]
                if not (-180 <= lon <= 180):
                    raise serializers.ValidationError(
                        f"{context}: Longitude {lon} is out of range [-180, 180]."
                    )
                if not (-90 <= lat <= 90):
                    raise serializers.ValidationError(
                        f"{context}: Latitude {lat} is out of range [-90, 90]."
                    )
            else:
                # Nested array - recurse
                for item in coords:
                    self._validate_coordinates(item, context, depth + 1)

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


class AreaOfInterestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating areas of interest."""

    geojson = serializers.JSONField(write_only=True, required=False)

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
                    "You do not have permission to move areas to this country."
                )
        return value

    def validate_geojson(self, value):
        """Reuse validation from create serializer."""
        # Use the same validation as create
        create_serializer = AreaOfInterestCreateSerializer(context=self.context)
        return create_serializer.validate_geojson(value)

    def update(self, instance, validated_data):
        import json
        import os
        import uuid

        from django.conf import settings

        geojson_data = validated_data.pop("geojson", None)

        # If new GeoJSON provided, save it and update the path
        if geojson_data:
            name = validated_data.get("name", instance.name)
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.geojson"

            polygons_dir = os.path.join(settings.BASE_DIR, "..", "..", "polygons")
            os.makedirs(polygons_dir, exist_ok=True)

            # Delete old file if exists
            if instance.polygon_path:
                old_path = os.path.join(polygons_dir, instance.polygon_path)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass  # Log but don't fail

            # Save new file
            filepath = os.path.join(polygons_dir, filename)
            with open(filepath, "w") as f:
                json.dump(geojson_data, f)

            validated_data["polygon_path"] = filename

        return super().update(instance, validated_data)


# Alias for backward compatibility
EcologicalReserveUpdateSerializer = AreaOfInterestUpdateSerializer


class UserMeSerializer(serializers.ModelSerializer):
    default_language = serializers.CharField(
        source="profile.default_language", required=False
    )
    theme = serializers.SerializerMethodField()
    authorized_countries = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "default_language",
            "theme",
            "authorized_countries",
        ]
        read_only_fields = ["email", "authorized_countries"]

    def get_authorized_countries(self, obj):
        countries = Country.objects.filter(
            authorized_users__user=obj
        ).values("id", "name", "code")
        return list(countries)

    def get_theme(self, obj):
        """Return theme preference, defaulting to 'light' if not available."""
        try:
            if hasattr(obj, 'profile') and obj.profile:
                return getattr(obj.profile, 'theme', 'light') or 'light'
        except Exception:
            pass
        return 'light'

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        
        # Theme is sent at top level since it's a SerializerMethodField
        theme = getattr(self, 'initial_data', {}).get("theme")

        # Update first_name and last_name if provided
        if "first_name" in validated_data:
            instance.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            instance.last_name = validated_data["last_name"]
        instance.save()

        # Update profile preferences
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        update_fields = []

        if "default_language" in profile_data:
            profile.default_language = profile_data["default_language"]
            update_fields.append("default_language")

        if theme is not None:
            profile.theme = theme
            update_fields.append("theme")

        if update_fields:
            profile.save(update_fields=update_fields)

        return instance


class AnalysisRunSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisRun model."""
    
    area_name = serializers.CharField(source='area_of_interest.name', read_only=True)
    country_name = serializers.CharField(source='area_of_interest.country.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        from .models import AnalysisRun
        model = AnalysisRun
        fields = [
            'id',
            'area_of_interest',
            'area_name',
            'country_name',
            'user_email',
            'pre_fire_date',
            'post_fire_date',
            'status',
            'severity_data',
            'total_burned_ha',
            'created_at',
            'completed_at',
        ]
        read_only_fields = ['id', 'created_at']


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""
    
    total_analyses = serializers.IntegerField()
    total_areas = serializers.IntegerField()
    total_analyzed_ha = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    total_burned_ha = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    analyses_this_month = serializers.IntegerField()
    recent_analyses = AnalysisRunSerializer(many=True)


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
