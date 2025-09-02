from datetime import datetime, timedelta

from django.contrib.auth.models import Group, User
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from wildfire_assessment.models import EcologicalReserve
from wildfire_assessment.serializers import EcologicalReserveSerializer
from wildfire_assessment.svc.src.analyzer import WildfireAnalyzer
from wildfire_assessment.svc.src.auth import initialize_gee
from wildfire_assessment.utils import load_polygon


class EcologicalReserveViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Ecological Reserves to be viewed or edited.
    """

    queryset = EcologicalReserve.objects.all().order_by("name")
    serializer_class = EcologicalReserveSerializer
    permission_classes = [permissions.IsAuthenticated]

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
                description="Pre-fire date",
                type=OpenApiTypes.DATE,
                required=True,
            ),
            OpenApiParameter(
                name="post_fire_date",
                description="Post-fire date",
                type=OpenApiTypes.DATE,
                required=True,
            ),
        ],
    )

    def calculate_date_range(self, date_str, days_before=60, days_after=60, date_format="%Y-%m-%d"):
        if not date_str or not isinstance(date_str, str):
            return None, None 
        try:
            date = datetime.strptime(date_str, date_format)
            date_before = date - timedelta(days=days_before)
            date_after = date + timedelta(days=days_after)
            return (
                (date.strftime(date_format), date_before.strftime(date_format)),
                (date.strftime(date_format), date_after.strftime(date_format))
            )
        except ValueError:
            return None, None

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        """
        Custom action to analyze an EcologicalReserve.
        The 'pk' parameter is the id of the EcologicalReserve.
        """
        initialize_gee()
        instance = self.get_object()
        polygon_path = instance.polygon_path
        pre_fire_date = request.query_params.get("pre_fire_date")
        post_fire_date = request.query_params.get("post_fire_date")

        pre_fire_date_to, _ = self.calculate_date_range(pre_fire_date)
        print(pre_fire_date_to)
        _, post_fire_date_from = self.calculate_date_range(post_fire_date)
        print(post_fire_date_from)
        polygon = load_polygon(polygon_path)

        # print(polygon)

        result = WildfireAnalyzer(polygon)
        # You can implement your logic here
        # Example: reserve = self.get_object()
        return Response(
            {"rgb_pre_fire": f"https://teste.com/image",
            "polygon_path": polygon_path,
            "pre_fire_date": pre_fire_date_to,
            "post_fire_date": post_fire_date_from,
                "rgb_post_fire": "https://teste.com/image",
                "ndvi_pre_fire": "https://teste.com/image",
                "ndvi_post_fire": "https://teste.com/image",
                "nbr_pre_fire": "https://teste.com/image",
                "nbr_post_fire": "https://teste.com/image",
                "delta_nbr": "https://teste.com/image",
                "rbr": "https://teste.com/image",
                "severity": "https://teste.com/image",
                "severity_sumary": {
                    "unburned": 46.51,
                    "low": 17.64,
                    "moderate": 23.03,
                    "high": 12.74,
                    "very_high": 0.0009
                },
                "polygon_area": 8.955
            }
        )
