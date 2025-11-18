
import logging
import uuid
from datetime import datetime

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
    
    def _parse_date(self, date_str):
        """Converts string to date object."""
        return datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None

    def _calculate_date_ranges(self, pre_fire_date, post_fire_date):
        """It calculates the date ranges for analysis."""
        pre_date = self._parse_date(pre_fire_date)
        post_date = self._parse_date(post_fire_date)

        pre_start, post_end = calculate_date_range(pre_date, post_date) if pre_date and post_date else (None, None)

        return {
            'pre_start': pre_start,
            'pre_end': pre_date,
            'post_start': post_date, 
            'post_end': post_end
        }
    
    def _format_date_range(self, start_date, end_date):
        """Formats dates to the format expected by the analyzer.."""
        if start_date and end_date:
            return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        return None

    def _map_presigned_urls(self, presigned_urls, prefix):
        """Maps S3 URLs to standardized keys in the response."""
        file_mapping = {
            f"{prefix}_RBR_Pure.tif": "rbr_pure_tif",
            f"{prefix}_RBR_Color.tif": "rbr_color_tif",
            f"{prefix}_RBR_Color.jpg": "rbr_color_jpg",
            f"{prefix}_Severity_RBR_Color.tif": "severity_rbr_color_tif", 
            f"{prefix}_Severity_RBR_Color.jpg": "severity_rbr_color_jpg",
            f"{prefix}_RGB_PreFire.tif": "rgb_pre_fire_tif",
            f"{prefix}_RGB_PreFire.jpg": "rgb_pre_fire_jpg",
            f"{prefix}_RGB_PostFire.tif": "rgb_post_fire_tif",
            f"{prefix}_RGB_PostFire.jpg": "rgb_post_fire_jpg",
            f"{prefix}_poligono_geojson.geojson": "polygon",
            f"{prefix}_severity_stats.csv": "severity_stats",
        }
        
        mapped_urls = {}
        for item in presigned_urls:
            filename = item["key"].split('/')[-1]  # Get only the file name
            if mapped_key := file_mapping.get(filename):
                mapped_urls[mapped_key] = item["url"]
                
        return mapped_urls

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
        # 1. Initialization and validation
        initialize_gee()
        instance = self.get_object()

        # 2. Request parameters
        pre_fire_date = request.query_params.get("pre_fire_date")
        post_fire_date = request.query_params.get("post_fire_date")
        execution_id = uuid.uuid4()

        # 3. Date calculation
        date_ranges = self._calculate_date_ranges(pre_fire_date, post_fire_date)
        pre_fire_range = self._format_date_range(date_ranges['pre_start'], date_ranges['pre_end'])
        post_fire_range = self._format_date_range(date_ranges['post_start'], date_ranges['post_end'])

        # 4. Load polygon and get best image dates
        polygon = load_polygon(instance.polygon_path)
        
        # 5. Execute analysis
        analyzer = WildfireAnalyzer(
            polygon=polygon,
            pre_fire_dates=pre_fire_range,
            post_fire_dates=post_fire_range, 
            polygon_id=instance.id,
            execution_id=execution_id
        )

        images = analyzer.calculate_severity()
        analyzer.calculate_area_stats(images["severity"])
        presigned_urls = analyzer.export_results(images, export_full_image=True)
        prefix = f"{uuid.uuid4()}_{instance.id}"

        # 6. Map URLs to response keys
        file_urls = self._map_presigned_urls(presigned_urls, prefix)

        # 7. Return response
        return Response({
            **file_urls,
            "pre_fire_best_date": images["pre_fire_best_date"],
            "post_fire_best_date": images["post_fire_best_date"],
        })
