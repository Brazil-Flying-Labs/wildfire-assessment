import json
import logging
import os
import uuid
from datetime import datetime

from django.http import JsonResponse, StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_assessment.models import EcologicalReserve
from wildfire_assessment.serializers import (
    AnalysisFollowUpSerializer,
    AnalysisRequestSerializer,
    EcologicalReserveSerializer,
    UserMeSerializer,
)
from wildfire_assessment.svc.ai_analysis import (
    generate_analysis_stream,
    generate_followup_stream,
)
from wildfire_assessment.svc.processor import (
    process_fire_assessment,
    process_scientific_deliverable,
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
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            polygon_path=polygon_path,
        )

        return Response(
            {
                "execution_id": str(execution_id),
                **assessment_result,
            }
        )

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
            OpenApiParameter(
                name="deliverable",
                description="Type of scientific deliverable to generate",
                type=OpenApiTypes.STR,
                required=True,
                enum=[
                    "RGB_PRE_FIRE",
                    "RGB_POST_FIRE",
                    "DNBR",
                    "RBR",
                    "DNDVI",
                ],
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="scientific_deliverable")
    def scientific_deliverable(self, request, pk=None):
        """
        Custom action to analyze an EcologicalReserve.
        The 'id' parameter is the id of the EcologicalReserve.
        """

        deliverable = request.query_params.get("deliverable")
        if deliverable == "RGB_PRE_FIRE":
            deliverable_enum = Deliverable.RGB_PRE_FIRE
        elif deliverable == "RGB_POST_FIRE":
            deliverable_enum = Deliverable.RGB_POST_FIRE
        elif deliverable == "DNBR":
            deliverable_enum = Deliverable.DNBR
        elif deliverable == "RBR":
            deliverable_enum = Deliverable.RBR
        elif deliverable == "DNDVI":
            deliverable_enum = Deliverable.DNDVI
        else:
            return Response({"error": "Invalid deliverable type"}, status=400)

        instance = self.get_object()
        task = process_scientific_deliverable.delay(
            pre_fire_date=request.query_params.get("pre_fire_date"),
            post_fire_date=request.query_params.get("post_fire_date"),
            polygon_path=instance.polygon_path,
            deliverable_name=deliverable_enum.name,
            email=request.user.email,
            reserve_name=instance.name,
        )

        return Response({"task_id": task.id})


class UserMeView(generics.RetrieveUpdateAPIView):
    """Return or update the authenticated user's profile."""

    serializer_class = UserMeSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


class AIAnalysisView(APIView):
    """
    Generate AI-powered analysis of wildfire data using OpenAI.

    Returns a streaming response with the analysis text.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=AnalysisRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Streaming text response with the AI analysis"
            ),
            400: OpenApiResponse(description="Invalid request data"),
            500: OpenApiResponse(description="OpenAI API error"),
        },
    )
    def post(self, request):
        """
        Generate a streaming AI analysis of wildfire severity data.

        Request body should contain:
        - pre_fire_date: Pre-fire date (YYYY-MM-DD)
        - post_fire_date: Post-fire date (YYYY-MM-DD)
        - area_of_interest: Name of the area/reserve
        - severity_distribution: Dict with severity levels and their areas/percentages
        """
        serializer = AnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        language = getattr(
            getattr(request.user, "profile", None), "default_language", "en"
        )

        try:
            stream, holder = generate_analysis_stream(
                pre_fire_date=str(data["pre_fire_date"]),
                post_fire_date=str(data["post_fire_date"]),
                area_of_interest=data["area_of_interest"],
                severity_distribution=data["severity_distribution"],
                image_urls=data.get("image_urls", []),
                language=language,
            )
            first_chunk = next(stream)
        except StopIteration:
            return Response(
                {"error": "AI analysis returned empty response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            LOG.exception("Error generating AI analysis")
            return Response(
                {"error": f"Failed to generate analysis: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return _build_streaming_response(first_chunk, stream, holder)


class AIAnalysisFollowUpView(APIView):
    """Follow-up questions on a previous AI analysis."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AnalysisFollowUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        language = getattr(
            getattr(request.user, "profile", None), "default_language", "en"
        )

        try:
            stream, holder = generate_followup_stream(
                previous_response_id=data["previous_response_id"],
                question=data["question"],
                language=language,
            )
            first_chunk = next(stream)
        except StopIteration:
            return Response(
                {"error": "AI returned empty response"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            LOG.exception("Error generating AI follow-up")
            return Response(
                {"error": f"Failed to generate response: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return _build_streaming_response(first_chunk, stream, holder)


def _build_streaming_response(first_chunk, stream, holder):
    """Build a StreamingHttpResponse that appends the response_id as a final marker."""

    def stream_with_response_id():
        yield first_chunk
        yield from stream
        # Send response_id as a parseable final line
        response_id = holder.get("response_id")
        if response_id:
            yield f"\n\n[RESPONSE_ID]{response_id}[/RESPONSE_ID]"

    response = StreamingHttpResponse(
        stream_with_response_id(),
        content_type="text/plain; charset=utf-8",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
