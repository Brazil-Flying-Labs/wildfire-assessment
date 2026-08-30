import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from pyproj import Geod
from rest_framework import serializers
from shapely.geometry import mapping, shape
from shapely.ops import orient
from shapely.validation import explain_validity
from wildfire_assessment.models import (
    AnalysisRun,
    AnalysisRunProvenance,
    AreaOfInterest,
    Country,
    Notification,
    UserProfile,
)
from wildfire_assessment.svc.object_storage import (
    delete_polygon,
    get_signed_image_url,
    upload_polygon,
)
from wildfire_assessment.svc.dashboard import invalidate_dashboard_cache
from wildfire_assessment.translations import get_error_translation, get_user_language

logger = logging.getLogger(__name__)

User = get_user_model()

MAX_AREA_HA = 110_000

# Minimum geodesic area (m²) for any individual polygon part inside a
# MultiPolygon. Parts smaller than this are almost always digitization
# artifacts (stray slivers) that inflate the bounding box and break image
# generation. A parking space is ~12 m², so 10 m² is well below any
# legitimate user polygon but easily catches sub-meter slivers.
MIN_MULTIPOLYGON_PART_AREA_M2 = 10.0


def generate_polygon_filename(name):
    """Generate a unique polygon filename from a human-readable name."""
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return f"{safe_name}_{uuid.uuid4().hex[:8]}.geojson"


def compute_area_ha(geojson_data):
    """Compute the total geodesic area of all geometries in hectares."""
    try:
        geod = Geod(ellps="WGS84")
        geojson_type = geojson_data.get("type")
        total_area_m2 = 0

        if geojson_type == "Feature":
            geom = shape(geojson_data["geometry"])
            area_m2, _ = geod.geometry_area_perimeter(geom)
            total_area_m2 = abs(area_m2)
        elif geojson_type == "FeatureCollection":
            for feature in geojson_data.get("features", []):
                geom = shape(feature["geometry"])
                area_m2, _ = geod.geometry_area_perimeter(geom)
                total_area_m2 += abs(area_m2)
        else:
            geom = shape(geojson_data)
            area_m2, _ = geod.geometry_area_perimeter(geom)
            total_area_m2 = abs(area_m2)

        return round(total_area_m2 / 10_000, 3)
    except Exception:
        return None


def compute_centroid(geojson_data):
    """Compute centroid from GeoJSON data. Returns (lat, lng) or None."""
    try:
        geojson_type = geojson_data.get("type")
        if geojson_type == "Feature":
            geom = shape(geojson_data["geometry"])
        elif geojson_type == "FeatureCollection":
            geom = shape(geojson_data["features"][0]["geometry"])
        else:
            geom = shape(geojson_data)
        centroid = geom.centroid
        return round(centroid.y, 7), round(centroid.x, 7)
    except Exception:
        return None


def check_duplicate_area_name(name, country, instance=None):
    """Return True if an area with this name already exists in the given country."""
    qs = AreaOfInterest.objects.filter(name=name, country=country)
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    return qs.exists()


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


class AreaSerializerMixin:
    """Shared translation, country validation, and duplicate-name check."""

    _country_error_key = "error.no_permission_create"

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
                raise serializers.ValidationError(self._t(self._country_error_key))
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        name = attrs.get("name", getattr(self.instance, "name", None))
        country = attrs.get("country", getattr(self.instance, "country", None))
        if name and country:
            if check_duplicate_area_name(name, country, self.instance):
                raise serializers.ValidationError(
                    {"name": self._t("error.duplicate_name")}
                )
        return attrs


class AreaOfInterestCreateSerializer(AreaSerializerMixin, serializers.ModelSerializer):
    """Serializer for creating areas of interest with GeoJSON upload."""

    geojson = serializers.JSONField(write_only=True, required=True)

    class Meta:
        model = AreaOfInterest
        fields = ["id", "name", "country", "geojson"]

    def validate_geojson(self, value):
        """
        Validate GeoJSON structure and geometry per RFC 7946 + GEE compatibility.

        Validates:
        - RFC 7946 structure (type, geometry, properties, id, bbox)
        - Coordinate positions (numeric, 2D only, lon/lat ranges)
        - Polygon rings (closure, min positions, winding order)
        - Shapely structural validity
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(self._t("error.geojson_not_object"))

        # Strip deprecated CRS member (RFC 7946 Section 4)
        value.pop("crs", None)

        geojson_type = value.get("type")
        if not geojson_type:
            raise serializers.ValidationError(self._t("error.geojson_no_type"))

        # Validate bbox if present (RFC 7946 Section 5)
        self._validate_bbox(value)

        # Extract geometry based on GeoJSON type
        geometry = None
        if geojson_type == "Feature":
            value.pop("crs", None)
            geometry = value.get("geometry")
            if not geometry:
                raise serializers.ValidationError(self._t("error.feature_no_geometry"))
            # RFC 7946 Section 3.2: Feature must have "properties"
            if "properties" not in value:
                raise serializers.ValidationError(
                    self._t("error.feature_no_properties", context="Feature")
                )
            # RFC 7946 Section 3.2: Feature "id" must be string or number
            self._validate_feature_id(value, "Feature")
        elif geojson_type == "FeatureCollection":
            features = value.get("features", [])
            if not features:
                raise serializers.ValidationError(
                    self._t("error.featurecollection_empty")
                )
            # Validate each feature
            for i, feature in enumerate(features):
                if not isinstance(feature, dict):
                    raise serializers.ValidationError(
                        self._t("error.feature_not_object", index=i)
                    )
                # RFC 7946 Section 3.3: each element must be a Feature
                if feature.get("type") != "Feature":
                    raise serializers.ValidationError(
                        self._t("error.fc_feature_missing_type", index=i)
                    )
                feature.pop("crs", None)
                # RFC 7946 Section 3.2: Feature must have "properties"
                if "properties" not in feature:
                    raise serializers.ValidationError(
                        self._t("error.feature_no_properties", context=f"Feature[{i}]")
                    )
                # RFC 7946 Section 3.2: Feature "id" must be string or number
                self._validate_feature_id(feature, f"Feature[{i}]")
                # RFC 7946 Section 5: validate bbox on each feature
                self._validate_bbox(feature)
                # RFC 7946 Section 3.2: Feature must have non-null geometry
                feat_geom = feature.get("geometry")
                if not feat_geom:
                    raise serializers.ValidationError(
                        self._t("error.fc_feature_no_geometry", index=i)
                    )
                self._validate_geometry(feat_geom, f"Feature[{i}]")
            self._validate_area(value)
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

        self._validate_area(value)
        return value

    def _validate_geometry(self, geometry, context="geometry"):
        """Validate a GeoJSON geometry object."""
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
                self._t(
                    "error.geometry_unsupported", context=context, geom_type=geom_type
                )
            )

        # RFC 7946 Section 5: validate bbox on geometry objects
        self._validate_bbox(geometry)

        coords = geometry.get("coordinates")
        if geom_type not in ["GeometryCollection"] and not coords:
            raise serializers.ValidationError(
                self._t("error.geometry_no_coordinates", context=context)
            )

        # Validate coordinate positions (structure, ranges, 3D rejection)
        if coords:
            self._validate_coordinates(coords, context)

        # RFC 7946: ring closure and minimum positions
        if geom_type in ["Polygon", "MultiPolygon"]:
            self._validate_ring_closure(coords, context, geom_type)

        # RFC 7946: no nested GeometryCollections
        if geom_type == "GeometryCollection":
            self._validate_no_nested_geometry_collections(geometry, context)

        # Use shapely to validate geometry structure
        try:
            geom = shape(geometry)
        except Exception as e:
            raise serializers.ValidationError(
                self._t(
                    "error.geometry_invalid_structure", context=context, detail=str(e)
                )
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

        # Reject MultiPolygons with stray/degenerate parts (digitization
        # artifacts that inflate the bounding box and break image generation).
        if geom_type == "MultiPolygon":
            self._validate_multipolygon_parts(geom, context)

        # RFC 7946: fix winding order (exterior CCW, holes CW)
        if geom_type in ["Polygon", "MultiPolygon"]:
            self._fix_winding_order(geometry)

    def _validate_multipolygon_parts(self, multipolygon, context):
        """Reject MultiPolygons whose individual parts are degenerately small.

        A stray sub-threshold sliver (e.g. a 4-vertex ~3 m² artifact left over
        from digitization) inflates the combined bounding box and produces
        tall, mostly-black images downstream. Rather than silently dropping
        it, we reject the upload so the user can clean the source file.
        """
        geod = Geod(ellps="WGS84")
        for idx, part in enumerate(multipolygon.geoms):
            area_m2, _ = geod.geometry_area_perimeter(part)
            area_m2 = abs(area_m2)
            if area_m2 < MIN_MULTIPOLYGON_PART_AREA_M2:
                raise serializers.ValidationError(
                    self._t(
                        "error.degenerate_multipolygon_part",
                        context=context,
                        index=idx,
                        area=f"{area_m2:.2f}",
                        threshold=f"{MIN_MULTIPOLYGON_PART_AREA_M2:.0f}",
                    )
                )

    def _validate_coordinates(self, coords, context, depth=0):
        """Recursively validate coordinate positions per RFC 7946 Section 3.1.1.

        Detects positions (flat arrays of all numbers) and validates:
        - At least 2 elements (lon, lat)
        - No more than 2 elements (GEE rejects 3D coordinates)
        - Longitude in [-180, 180], latitude in [-90, 90]
        Non-position lists are treated as containers and recursed into.
        """
        if depth > 10:
            return

        if isinstance(coords, (int, float)):
            return

        if not isinstance(coords, list):
            raise serializers.ValidationError(
                self._t("error.position_not_all_numbers", context=context)
            )

        if len(coords) == 0:
            return

        all_numeric = all(isinstance(c, (int, float)) for c in coords)

        if all_numeric:
            # This is a position
            if len(coords) < 2:
                raise serializers.ValidationError(
                    self._t("error.position_too_few_elements", context=context)
                )
            if len(coords) > 2:
                raise serializers.ValidationError(
                    self._t("error.coordinates_3d", context=context)
                )
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
            # Container — check for mixed types like [1, "b"]
            has_number = any(isinstance(c, (int, float)) for c in coords)
            has_invalid = any(not isinstance(c, (int, float, list)) for c in coords)
            if has_number and has_invalid:
                raise serializers.ValidationError(
                    self._t("error.position_not_all_numbers", context=context)
                )
            for item in coords:
                self._validate_coordinates(item, context, depth + 1)

    def _validate_ring_closure(self, coords, context, geom_type):
        """Validate RFC 7946 linear ring rules: closure and minimum positions."""
        try:
            if geom_type == "Polygon":
                polygon_list = [coords]
            else:  # MultiPolygon
                polygon_list = coords

            for polygon_coords in polygon_list:
                for ring in polygon_coords:
                    if not isinstance(ring, list) or len(ring) == 0:
                        continue
                    if len(ring) < 4:
                        raise serializers.ValidationError(
                            self._t("error.ring_too_few_positions", context=context)
                        )
                    if ring[0] != ring[-1]:
                        raise serializers.ValidationError(
                            self._t("error.ring_not_closed", context=context)
                        )
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(
                self._t(
                    "error.geometry_invalid_structure",
                    context=context,
                    detail=str(e),
                )
            )

    def _validate_no_nested_geometry_collections(self, geometry, context):
        """Validate RFC 7946: GeometryCollections cannot contain GeometryCollections."""
        try:
            for sub in geometry.get("geometries", []):
                if isinstance(sub, dict) and sub.get("type") == "GeometryCollection":
                    raise serializers.ValidationError(
                        self._t("error.nested_geometry_collection", context=context)
                    )
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(
                self._t(
                    "error.geometry_invalid_structure",
                    context=context,
                    detail=str(e),
                )
            )

    def _fix_winding_order(self, geometry):
        """Apply RFC 7946 right-hand rule: exterior CCW, holes CW."""
        try:
            geom = shape(geometry)
            oriented = orient(geom, sign=1.0)
            geometry["coordinates"] = mapping(oriented)["coordinates"]
        except Exception:
            logger.warning(
                "Failed to fix winding order for geometry, skipping",
                exc_info=True,
            )

    def _validate_bbox(self, obj):
        """Validate bbox member if present (RFC 7946 Section 5).

        For 2D geometries, bbox must be [west, south, east, north] (4 numbers).
        Latitude values must be in [-90, 90].
        """
        try:
            bbox = obj.get("bbox")
            if bbox is None:
                return
            if not isinstance(bbox, list) or len(bbox) != 4:
                raise serializers.ValidationError(self._t("error.bbox_invalid_length"))
            if not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in bbox
            ):
                raise serializers.ValidationError(self._t("error.bbox_invalid_length"))
            south, north = bbox[1], bbox[3]
            if not (-90 <= south <= 90) or not (-90 <= north <= 90):
                raise serializers.ValidationError(
                    self._t("error.bbox_latitude_out_of_range")
                )
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(
                self._t(
                    "error.geometry_invalid_structure",
                    context="bbox",
                    detail=str(e),
                )
            )

    def _validate_feature_id(self, feature, context):
        """Validate Feature 'id' type if present (RFC 7946 Section 3.2)."""
        if "id" not in feature:
            return
        feat_id = feature["id"]
        if feat_id is None:
            return
        if isinstance(feat_id, bool) or not isinstance(feat_id, (str, int, float)):
            raise serializers.ValidationError(
                self._t("error.feature_invalid_id", context=context)
            )

    def _validate_area(self, geojson_data):
        """Validate that the total geodesic area does not exceed MAX_AREA_HA."""
        area_ha = compute_area_ha(geojson_data)
        if area_ha is not None and area_ha > MAX_AREA_HA:
            raise serializers.ValidationError(
                self._t("error.area_too_large", max_ha=f"{MAX_AREA_HA:,}")
            )

    def create(self, validated_data):
        geojson_data = validated_data.pop("geojson")
        filename = generate_polygon_filename(validated_data.get("name"))

        upload_polygon(filename, geojson_data)

        validated_data["polygon_path"] = filename
        validated_data["area_ha"] = compute_area_ha(geojson_data)

        centroid = compute_centroid(geojson_data)
        if centroid:
            validated_data["centroid_lat"], validated_data["centroid_lng"] = centroid

        instance = super().create(validated_data)
        request = self.context.get("request")
        if request and request.user:
            invalidate_dashboard_cache(request.user.id)
        return instance


class AreaOfInterestUpdateSerializer(AreaSerializerMixin, serializers.ModelSerializer):
    """Serializer for updating areas of interest."""

    _country_error_key = "error.no_permission_move"

    geojson = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = AreaOfInterest
        fields = ["id", "name", "country", "geojson"]

    def validate_geojson(self, value):
        """Reuse validation from create serializer."""
        create_serializer = AreaOfInterestCreateSerializer(context=self.context)
        return create_serializer.validate_geojson(value)

    def update(self, instance, validated_data):
        geojson_data = validated_data.pop("geojson", None)

        if geojson_data:
            name = validated_data.get("name", instance.name)
            filename = generate_polygon_filename(name)

            if instance.polygon_path:
                delete_polygon(instance.polygon_path)

            upload_polygon(filename, geojson_data)
            validated_data["polygon_path"] = filename
            validated_data["area_ha"] = compute_area_ha(geojson_data)

            centroid = compute_centroid(geojson_data)
            if centroid:
                validated_data["centroid_lat"], validated_data["centroid_lng"] = (
                    centroid
                )

        instance = super().update(instance, validated_data)
        request = self.context.get("request")
        if request and request.user:
            invalidate_dashboard_cache(request.user.id)
        return instance


class UserMeSerializer(serializers.ModelSerializer):
    default_language = serializers.CharField(
        source="profile.default_language", required=False
    )
    theme = serializers.SerializerMethodField()
    dashboard_widgets = serializers.SerializerMethodField()
    authorized_countries = serializers.SerializerMethodField()
    terms_accepted_at = serializers.SerializerMethodField()
    terms_last_updated = serializers.SerializerMethodField()

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
            "terms_accepted_at",
            "terms_last_updated",
        ]
        read_only_fields = [
            "email",
            "dashboard_widgets",
            "authorized_countries",
            "terms_accepted_at",
            "terms_last_updated",
        ]

    def get_authorized_countries(self, obj):
        countries = Country.objects.filter(authorized_users__user=obj).values(
            "id", "name", "code"
        )
        return list(countries)

    def get_theme(self, obj):
        """Return theme preference, defaulting to 'dark' if not available."""
        try:
            profile = obj.profile
            if profile:
                return getattr(profile, "theme", "dark") or "dark"
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass  # pragma: no cover
        return "dark"  # pragma: no cover

    def get_dashboard_widgets(self, obj):
        """Return dashboard widget layout, or None if not customized."""
        try:
            profile = obj.profile
            if profile:
                return getattr(profile, "dashboard_widgets", None)
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass  # pragma: no cover
        return None  # pragma: no cover

    def get_terms_accepted_at(self, obj):
        """Return terms acceptance timestamp, or None if not accepted."""
        try:
            profile = obj.profile
            if profile and profile.terms_accepted_at:
                return profile.terms_accepted_at.isoformat()
        except UserProfile.DoesNotExist:  # pragma: no cover
            pass  # pragma: no cover
        return None

    def get_terms_last_updated(self, obj):
        """Return the date the Terms of Service were last modified."""
        return settings.TERMS_LAST_UPDATED

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})

        # These are sent at top level since they are SerializerMethodFields
        initial = getattr(self, "initial_data", {})
        theme = initial.get("theme")
        dashboard_widgets = initial.get("dashboard_widgets")
        accept_terms = initial.get("accept_terms")

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

        if accept_terms:
            profile.terms_accepted_at = timezone.now()
            update_fields.append("terms_accepted_at")

        if update_fields:
            profile.save(update_fields=update_fields)

        return instance


class AnalysisRunProvenanceSerializer(serializers.ModelSerializer):
    """Serializer for satellite image provenance records."""

    class Meta:
        model = AnalysisRunProvenance
        fields = ["id", "phase", "scene_id", "date", "spacecraft_name", "cloud_percent"]


class AnalysisRunListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for AnalysisRun list (no presigned URLs)."""

    area_name = serializers.CharField(source="area_of_interest.name", read_only=True)
    country_name = serializers.CharField(
        source="area_of_interest.country.name", read_only=True
    )

    class Meta:
        model = AnalysisRun
        fields = [
            "id",
            "area_of_interest",
            "area_name",
            "country_name",
            "pre_fire_date",
            "post_fire_date",
            "status",
            "severity_data",
            "total_burned_ha",
            "created_at",
            "completed_at",
        ]
        read_only_fields = ["id", "created_at"]


class AnalysisRunSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisRun model."""

    area_name = serializers.CharField(source="area_of_interest.name", read_only=True)
    country_name = serializers.CharField(
        source="area_of_interest.country.name", read_only=True
    )
    user_email = serializers.CharField(source="user.email", read_only=True)
    rgb_pre_fire_url = serializers.SerializerMethodField()
    rgb_post_fire_url = serializers.SerializerMethodField()
    dndvi_url = serializers.SerializerMethodField()
    dnbr_url = serializers.SerializerMethodField()
    rbr_url = serializers.SerializerMethodField()
    provenance = AnalysisRunProvenanceSerializer(
        many=True, read_only=True, source="provenance_records"
    )

    class Meta:
        model = AnalysisRun
        fields = [
            "id",
            "area_of_interest",
            "area_name",
            "country_name",
            "user_email",
            "pre_fire_date",
            "post_fire_date",
            "status",
            "severity_data",
            "total_burned_ha",
            "rgb_pre_fire_url",
            "rgb_post_fire_url",
            "dndvi_url",
            "dnbr_url",
            "rbr_url",
            "scientific_rgb_pre_fire_url",
            "scientific_rgb_post_fire_url",
            "scientific_dndvi_url",
            "scientific_dnbr_url",
            "scientific_rbr_url",
            "scientific_rgb_pre_fire_task_id",
            "scientific_rgb_post_fire_task_id",
            "scientific_dndvi_task_id",
            "scientific_dnbr_task_id",
            "scientific_rbr_task_id",
            "scientific_rgb_pre_fire_error",
            "scientific_rgb_post_fire_error",
            "scientific_dndvi_error",
            "scientific_dnbr_error",
            "scientific_rbr_error",
            "created_at",
            "completed_at",
            "roi_only",
            "cloud_threshold",
            "days_before_after",
            "pre_fire_mosaic_strategy",
            "post_fire_mosaic_strategy",
            "roi_only_bg_color",
            "report_summary",
            "report_summary_language",
            "provenance",
        ]
        read_only_fields = ["id", "created_at"]

    def _get_image_url(self, obj, field):
        key = getattr(obj, field)
        if not key:
            return None
        return get_signed_image_url(key)

    def get_rgb_pre_fire_url(self, obj):
        return self._get_image_url(obj, "rgb_pre_fire_image")

    def get_rgb_post_fire_url(self, obj):
        return self._get_image_url(obj, "rgb_post_fire_image")

    def get_dndvi_url(self, obj):
        return self._get_image_url(obj, "dndvi_image")

    def get_dnbr_url(self, obj):
        return self._get_image_url(obj, "dnbr_image")

    def get_rbr_url(self, obj):
        return self._get_image_url(obj, "rbr_image")


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
    date = serializers.CharField()
    avg_severity = serializers.FloatField()


class AreaGeoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    total_burned_ha = serializers.FloatField()
    last_analysis_date = serializers.CharField(allow_null=True)
    run_count = serializers.IntegerField()
    geometry = serializers.JSONField(allow_null=True)


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
    question = serializers.CharField(help_text="Follow-up question about the analysis")


class ReportSummaryRequestSerializer(serializers.Serializer):
    """Serializer for the report summary generation request."""

    language = serializers.CharField(
        required=False,
        default="en",
        help_text="Language code for the report (e.g., en, pt-BR, fr, es-ES)",
    )


class NotificationSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(
        source="analysis_run.area_of_interest.name",
        read_only=True,
        default="",
    )
    analysis_run_id = serializers.IntegerField(
        source="analysis_run.id",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "deliverable_name",
            "message",
            "is_read",
            "analysis_run_id",
            "area_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
