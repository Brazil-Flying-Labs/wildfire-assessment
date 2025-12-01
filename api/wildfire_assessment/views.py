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
from wildfire_assessment.svc.src.processor import (
    deliverable_to_filename,
    process_fire_assessment,
)

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
        instance = self.get_object()
        execution_id = uuid.uuid4()
        polygon_path = instance.polygon_path

        polygon_path = f"../../polygons/{polygon_path}"
        
        pre_fire_date = request.query_params.get("pre_fire_date")
        post_fire_date = request.query_params.get("post_fire_date")

        assessment_result = process_fire_assessment(
            fire_id=instance.id,
            execution_id=execution_id,
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            polygon_path=polygon_path
        )


        presigned_urls = deliverable_to_filename(assessment_result)
        
        return Response({
            "execution_id": str(execution_id),
            **presigned_urls
        })