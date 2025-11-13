
import logging
import uuid
from datetime import datetime

from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from wildfire_assessment.models import EcologicalReserve
from wildfire_assessment.serializers import EcologicalReserveSerializer
from wildfire_assessment.svc.src.analyzer import WildfireAnalyzer
from wildfire_assessment.svc.src.auth import initialize_gee
from wildfire_assessment.svc.src.image_processor import (
    get_best_image,
    get_sentinel_collection,
)
from wildfire_assessment.utils import calculate_date_range, load_polygon

LOG = logging.getLogger(__name__)


def health_status(_request):
    return JsonResponse({"status": "ok"})


class EcologicalReserveViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = EcologicalReserve.objects.all().order_by("name")
    serializer_class = EcologicalReserveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific EcologicalReserve by its ID.

        """
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        List all EcologicalReserves.
        """
        self.pagination_class = None

        # We need to return only ecological reserves that the user has access to throug country
        user = request.user
        if country_ids := user.country_permissions.values_list("country_id", flat=True):
            self.queryset = self.queryset.filter(country_id__in=country_ids)
        else:
            self.queryset = self.queryset.none()

        return super().list(request, *args, **kwargs)

    @extend_schema(
        methods=["POST"],
        request=None,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
                description="A dict with a message string",
            )
        },
        parameters=[
            OpenApiParameter(
                name="pre_fire_date",
                description="Pre-fire date (YYYY-MM-DD)",
                type=OpenApiTypes.DATE,
                required=True,
            ),
            OpenApiParameter(
                name="post_fire_date",
                description="Post-fire date (YYYY-MM-DD)",
                type=OpenApiTypes.DATE,
                required=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        """
        Custom action to analyze an EcologicalReserve.
        The 'id' parameter is the id of the EcologicalReserve.
        """
        initialize_gee()
        instance = self.get_object()

        # Generate unique execution ID
        execution_id = uuid.uuid4()

        polygon_path = instance.polygon_path
        pre_fire_date_to = request.query_params.get("pre_fire_date")
        post_fire_date_from = request.query_params.get("post_fire_date")

        pre_fire_date_to_date = (
            datetime.strptime(pre_fire_date_to, "%Y-%m-%d").date()
            if pre_fire_date_to
            else None
        )
        post_fire_date_from_date = (
            datetime.strptime(post_fire_date_from, "%Y-%m-%d").date()
            if post_fire_date_from
            else None
        )

        pre_fire_date_before, _ = (
            calculate_date_range(pre_fire_date_to_date)
            if pre_fire_date_to_date
            else (None, None)
        )
        _, post_fire_date_after = (
            calculate_date_range(post_fire_date_from_date)
            if post_fire_date_from_date
            else (None, None)
        )
        polygon = load_polygon(polygon_path)

        # Ajuste os ranges para strings formatadas, assumindo que WildfireAnalyzer espera tuplas de strings (start, end)
        pre_fire_range = (
            (
                pre_fire_date_before.strftime("%Y-%m-%d"),
                pre_fire_date_to_date.strftime("%Y-%m-%d"),
            )
            if pre_fire_date_before and pre_fire_date_to_date
            else None
        )
        post_fire_range = (
            (
                post_fire_date_from_date.strftime("%Y-%m-%d"),
                post_fire_date_after.strftime("%Y-%m-%d"),
            )
            if post_fire_date_from_date and post_fire_date_after
            else None
        )

        # Descomente e ajuste se necessário
        analyzer = WildfireAnalyzer(
            polygon, pre_fire_range, post_fire_range, instance.id, execution_id=str(execution_id)
        )
        # Obtenha as datas das melhores imagens
        _, pre_fire_date = get_best_image(
            get_sentinel_collection(polygon), *pre_fire_range, polygon
        )
        _, post_fire_date = get_best_image(
            get_sentinel_collection(polygon), *post_fire_range, polygon
        )

        images = analyzer.calculate_severity()
        _, total_area = analyzer.calculate_area_stats(images["severity"])
        presigned_urls = analyzer.export_results(images, export_full_image=True)

        prefix = str(execution_id) + "_" + str(instance.id)

        presigned_data = {}
        for item in presigned_urls:
            s3_key = item["key"]
            if s3_key.endswith(f"{prefix}_RBR_Pure.tif"):
                presigned_data["rbr_pure_tif"] = item["url"]
            elif s3_key.endswith(f"{prefix}_RBR_Color.tif"):
                presigned_data["rbr_color_tif"] = item["url"]
            elif s3_key.endswith(f"{prefix}_RBR_Color.jpg"):
                presigned_data["rbr_color_jpg"] = item["url"]
            elif s3_key.endswith(f"{prefix}_Severity_RBR_Color.tif"):
                presigned_data["severity_rbr_color_tif"] = item["url"]
            elif s3_key.endswith(f"{prefix}_Severity_RBR_Color.jpg"):
                presigned_data["severity_rbr_color_jpg"] = item["url"]
            elif s3_key.endswith(f"{prefix}_RGB_PreFire.tif"):
                presigned_data["rgb_pre_fire_tif"] = item["url"]
            elif s3_key.endswith(f"{prefix}_RGB_PreFire.jpg"):
                presigned_data["rgb_pre_fire_jpg"] = item["url"]
            elif s3_key.endswith(f"{prefix}_RGB_PostFire.tif"):
                presigned_data["rgb_post_fire_tif"] = item["url"]
            elif s3_key.endswith(f"{prefix}_RGB_PostFire.jpg"):
                presigned_data["rgb_post_fire_jpg"] = item["url"]
            elif s3_key.endswith(f"{prefix}_poligono_geojson.geojson"):
                presigned_data["polygon"] = item["url"]
            elif s3_key.endswith(f"{prefix}_severity_stats.csv"):
                presigned_data["severity_stats"] = item["url"]

        return Response(
            {
                **presigned_data,
                "pre_fire_best_date": pre_fire_date,
                "post_fire_best_date": post_fire_date,
            }
        )
