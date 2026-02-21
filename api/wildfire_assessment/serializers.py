from django.contrib.auth import get_user_model
from rest_framework import serializers
from wildfire_assessment.models import AreaOfInterest, Country, UserProfile
from wildfire_assessment.translations import get_error_translation, get_user_language

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


class AreaOfInterestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating areas of interest with GeoJSON upload."""

    geojson = serializers.JSONField(write_only=True, required=True)

    class Meta:
        model = AreaOfInterest
        fields = ["id", "name", "country", "geojson"]

    def _t(self, key, **kwargs):
        """Translate an error message based on the request user's language."""
        lang = get_user_language(self.context.get("request"))
        return get_error_translation(lang, key, **kwargs)

    def validate_country(self, value):
        """Ensure the user has access to the specified country."""
        request = self.context.get("request")
        if request and request.user:
            user_countries = request.user.country_permissions.values_list(
                "country_id", flat=True
            )
            if value.id not in user_countries:
                raise serializers.ValidationError(
                    self._t("error.no_permission_create")
                )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = attrs.get("name")
        country = attrs.get("country")
        if name and country:
            if AreaOfInterest.objects.filter(name=name, country=country).exists():
                raise serializers.ValidationError(
                    {"name": self._t("error.duplicate_name")}
                )
        return attrs

    def validate_geojson(self, value):
        """
        Validate GeoJSON structure and geometry for Google Earth Engine compatibility.

        Validates:
        - Valid GeoJSON structure (type, geometry)
        - Valid geometry using shapely
        - Coordinate ranges (lon: -180 to 180, lat: -90 to 90)
        - Polygon validity (closed rings, no self-intersection)
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(self._t("error.geojson_not_object"))

        geojson_type = value.get("type")
        if not geojson_type:
            raise serializers.ValidationError(self._t("error.geojson_no_type"))

        # Extract geometry based on GeoJSON type
        geometry = None
        if geojson_type == "Feature":
            geometry = value.get("geometry")
            if not geometry:
                raise serializers.ValidationError(
                    self._t("error.feature_no_geometry")
                )
        elif geojson_type == "FeatureCollection":
            features = value.get("features", [])
            if not features:
                raise serializers.ValidationError(
                    self._t("error.featurecollection_empty")
                )
            # Validate each feature's geometry
            for i, feature in enumerate(features):
                if not isinstance(feature, dict):
                    raise serializers.ValidationError(
                        self._t("error.feature_not_object", index=i)
                    )
                feat_geom = feature.get("geometry")
                if feat_geom:
                    self._validate_geometry(feat_geom, f"Feature[{i}]")
            return value
        elif geojson_type in ["Polygon", "MultiPolygon"]:
            geometry = value
        elif geojson_type in ["Point", "LineString", "MultiPoint", "MultiLineString"]:
            raise serializers.ValidationError(
                self._t("error.unsupported_geometry", geom_type=geojson_type)
            )
        else:
            raise serializers.ValidationError(
                self._t("error.unsupported_geojson_type", geojson_type=geojson_type)
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
                self._t("error.geometry_not_object", context=context)
            )

        geom_type = geometry.get("type")
        if not geom_type:
            raise serializers.ValidationError(
                self._t("error.geometry_no_type", context=context)
            )

        if geom_type not in ["Polygon", "MultiPolygon", "GeometryCollection"]:
            raise serializers.ValidationError(
                self._t("error.geometry_unsupported", context=context, geom_type=geom_type)
            )

        coords = geometry.get("coordinates")
        if geom_type not in ["GeometryCollection"] and not coords:
            raise serializers.ValidationError(
                self._t("error.geometry_no_coordinates", context=context)
            )

        # Validate coordinate ranges
        if coords:
            self._validate_coordinates(coords, context)

        # Use shapely to validate geometry structure
        try:
            geom = shape(geometry)
        except Exception as e:
            raise serializers.ValidationError(
                self._t("error.geometry_invalid_structure", context=context, detail=str(e))
            )

        # Check if geometry is valid
        if not geom.is_valid:
            reason = explain_validity(geom)
            raise serializers.ValidationError(
                self._t("error.geometry_invalid", context=context, detail=reason)
            )

        # Check if geometry is empty
        if geom.is_empty:
            raise serializers.ValidationError(
                self._t("error.geometry_empty", context=context)
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
                        self._t("error.longitude_out_of_range", context=context, value=lon)
                    )
                if not (-90 <= lat <= 90):
                    raise serializers.ValidationError(
                        self._t("error.latitude_out_of_range", context=context, value=lat)
                    )
            else:
                # Nested array - recurse
                for item in coords:
                    self._validate_coordinates(item, context, depth + 1)

    def create(self, validated_data):
        import uuid

        from wildfire_assessment.svc.aws import upload_polygon_to_s3

        geojson_data = validated_data.pop("geojson")
        name = validated_data.get("name")

        # Generate a unique filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.geojson"

        # Upload to S3
        upload_polygon_to_s3(filename, geojson_data)

        validated_data["polygon_path"] = filename
        validated_data["area_ha"] = None

        # Compute centroid from GeoJSON
        try:
            from shapely.geometry import shape as shapely_shape

            geojson_type = geojson_data.get("type")
            if geojson_type == "Feature":
                geom = shapely_shape(geojson_data["geometry"])
            elif geojson_type == "FeatureCollection":
                geom = shapely_shape(geojson_data["features"][0]["geometry"])
            else:
                geom = shapely_shape(geojson_data)
            centroid = geom.centroid
            validated_data["centroid_lat"] = round(centroid.y, 7)
            validated_data["centroid_lng"] = round(centroid.x, 7)
        except Exception:
            pass

        return super().create(validated_data)


class AreaOfInterestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating areas of interest."""

    geojson = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = AreaOfInterest
        fields = ["id", "name", "country", "geojson"]

    def _t(self, key, **kwargs):
        """Translate an error message based on the request user's language."""
        lang = get_user_language(self.context.get("request"))
        return get_error_translation(lang, key, **kwargs)

    def validate_country(self, value):
        """Ensure the user has access to the specified country."""
        request = self.context.get("request")
        if request and request.user:
            user_countries = request.user.country_permissions.values_list(
                "country_id", flat=True
            )
            if value.id not in user_countries:
                raise serializers.ValidationError(
                    self._t("error.no_permission_move")
                )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = attrs.get("name", self.instance.name if self.instance else None)
        country = attrs.get("country", self.instance.country if self.instance else None)
        if name and country:
            qs = AreaOfInterest.objects.filter(name=name, country=country)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": self._t("error.duplicate_name")}
                )
        return attrs

    def validate_geojson(self, value):
        """Reuse validation from create serializer."""
        # Use the same validation as create
        create_serializer = AreaOfInterestCreateSerializer(context=self.context)
        return create_serializer.validate_geojson(value)

    def update(self, instance, validated_data):
        import uuid

        from wildfire_assessment.svc.aws import (
            delete_polygon_from_s3,
            upload_polygon_to_s3,
        )

        geojson_data = validated_data.pop("geojson", None)

        # If new GeoJSON provided, upload to S3 and update the path
        if geojson_data:
            name = validated_data.get("name", instance.name)
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            filename = f"{safe_name}_{uuid.uuid4().hex[:8]}.geojson"

            # Delete old file from S3 if exists
            if instance.polygon_path:
                delete_polygon_from_s3(instance.polygon_path)

            # Upload new file to S3
            upload_polygon_to_s3(filename, geojson_data)

            validated_data["polygon_path"] = filename

            # Recompute centroid from new GeoJSON
            try:
                from shapely.geometry import shape as shapely_shape

                geojson_type = geojson_data.get("type")
                if geojson_type == "Feature":
                    geom = shapely_shape(geojson_data["geometry"])
                elif geojson_type == "FeatureCollection":
                    geom = shapely_shape(geojson_data["features"][0]["geometry"])
                else:
                    geom = shapely_shape(geojson_data)
                centroid = geom.centroid
                validated_data["centroid_lat"] = round(centroid.y, 7)
                validated_data["centroid_lng"] = round(centroid.x, 7)
            except Exception:
                pass

        return super().update(instance, validated_data)


class UserMeSerializer(serializers.ModelSerializer):
    default_language = serializers.CharField(
        source="profile.default_language", required=False
    )
    theme = serializers.SerializerMethodField()
    dashboard_widgets = serializers.SerializerMethodField()
    authorized_countries = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "default_language",
            "theme",
            "dashboard_widgets",
            "authorized_countries",
        ]
        read_only_fields = ["email", "dashboard_widgets", "authorized_countries"]

    def get_authorized_countries(self, obj):
        countries = Country.objects.filter(
            authorized_users__user=obj
        ).values("id", "name", "code")
        return list(countries)

    def get_theme(self, obj):
        """Return theme preference, defaulting to 'dark' if not available."""
        try:
            profile = obj.profile
            if profile:
                return getattr(profile, 'theme', 'dark') or 'dark'
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass  # pragma: no cover
        return 'dark'  # pragma: no cover

    def get_dashboard_widgets(self, obj):
        """Return dashboard widget layout, or None if not customized."""
        try:
            profile = obj.profile
            if profile:
                return getattr(profile, 'dashboard_widgets', None)
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass  # pragma: no cover
        return None  # pragma: no cover

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})

        # These are sent at top level since they are SerializerMethodFields
        initial = getattr(self, 'initial_data', {})
        theme = initial.get("theme")
        dashboard_widgets = initial.get("dashboard_widgets")

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

        if dashboard_widgets is not None:
            profile.dashboard_widgets = dashboard_widgets
            update_fields.append("dashboard_widgets")

        if update_fields:
            profile.save(update_fields=update_fields)

        return instance


class AnalysisRunSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisRun model."""

    area_name = serializers.CharField(source='area_of_interest.name', read_only=True)
    country_name = serializers.CharField(source='area_of_interest.country.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    rgb_pre_fire_url = serializers.SerializerMethodField()
    rgb_post_fire_url = serializers.SerializerMethodField()
    dndvi_url = serializers.SerializerMethodField()
    dnbr_url = serializers.SerializerMethodField()
    rbr_url = serializers.SerializerMethodField()

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
            'rgb_pre_fire_url',
            'rgb_post_fire_url',
            'dndvi_url',
            'dnbr_url',
            'rbr_url',
            'scientific_rgb_pre_fire_url',
            'scientific_rgb_post_fire_url',
            'scientific_dndvi_url',
            'scientific_dnbr_url',
            'scientific_rbr_url',
            'scientific_rgb_pre_fire_task_id',
            'scientific_rgb_post_fire_task_id',
            'scientific_dndvi_task_id',
            'scientific_dnbr_task_id',
            'scientific_rbr_task_id',
            'created_at',
            'completed_at',
        ]
        read_only_fields = ['id', 'created_at']

    def _get_image_url(self, obj, field):
        from wildfire_assessment.svc.aws import get_presigned_image_url
        key = getattr(obj, field)
        if not key:
            return None
        return get_presigned_image_url(key)

    def get_rgb_pre_fire_url(self, obj):
        return self._get_image_url(obj, 'rgb_pre_fire_image')

    def get_rgb_post_fire_url(self, obj):
        return self._get_image_url(obj, 'rgb_post_fire_image')

    def get_dndvi_url(self, obj):
        return self._get_image_url(obj, 'dndvi_image')

    def get_dnbr_url(self, obj):
        return self._get_image_url(obj, 'dnbr_image')

    def get_rbr_url(self, obj):
        return self._get_image_url(obj, 'rbr_image')


class SeverityBreakdownItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    area_ha = serializers.DecimalField(max_digits=15, decimal_places=2)


class AreaComparisonItemSerializer(serializers.Serializer):
    area_name = serializers.CharField()
    total_burned_ha = serializers.DecimalField(max_digits=15, decimal_places=2)


class MostAnalyzedAreaSerializer(serializers.Serializer):
    area_name = serializers.CharField()
    run_count = serializers.IntegerField()


class LargestFireSerializer(serializers.Serializer):
    area_name = serializers.CharField()
    burned_ha = serializers.DecimalField(max_digits=15, decimal_places=2)


class SeverityTrendItemSerializer(serializers.Serializer):
    month = serializers.CharField()
    avg_severity = serializers.FloatField()


class AreaGeoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    total_burned_ha = serializers.FloatField()
    last_analysis_date = serializers.CharField(allow_null=True)
    run_count = serializers.IntegerField()


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""

    total_analyses = serializers.IntegerField()
    total_areas = serializers.IntegerField()
    total_analyzed_ha = serializers.DecimalField(
        max_digits=15, decimal_places=2, allow_null=True
    )
    total_burned_ha = serializers.DecimalField(
        max_digits=15, decimal_places=2, allow_null=True
    )
    analyses_this_month = serializers.IntegerField()
    recent_analyses = AnalysisRunSerializer(many=True)
    severity_breakdown = SeverityBreakdownItemSerializer(many=True)
    area_comparison = AreaComparisonItemSerializer(many=True)
    average_burn_severity = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    most_analyzed_area = MostAnalyzedAreaSerializer(allow_null=True)
    largest_fire = LargestFireSerializer(allow_null=True)
    areas_geo = AreaGeoSerializer(many=True)
    severity_trend = SeverityTrendItemSerializer(many=True)


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
