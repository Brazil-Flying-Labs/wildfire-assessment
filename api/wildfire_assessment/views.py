import logging
import uuid

from celery.result import AsyncResult
from django.http import JsonResponse, StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_assessment.models import AreaOfInterest
from wildfire_assessment.serializers import (
    AnalysisFollowUpSerializer,
    AnalysisRequestSerializer,
    AnalysisRunSerializer,
    AreaOfInterestCreateSerializer,
    AreaOfInterestSerializer,
    AreaOfInterestUpdateSerializer,
    DashboardStatsSerializer,
    NotificationSerializer,
    UserMeSerializer,
)
from wildfire_assessment.svc.ai_common import (
    PROVIDER_DISPLAY,
    generate_analysis_stream,
    generate_followup_stream,
    get_active_provider,
)
from wildfire_assessment.svc.area_of_interest import (
    delete_polygon_file,
    get_analysis_runs_queryset,
    get_areas_queryset,
    save_analysis_run,
    save_deliverable_task_id,
    user_can_access_area,
)
from wildfire_assessment.svc.dashboard import get_dashboard_stats
from wildfire_assessment.svc.notification import (
    get_notifications_queryset,
    get_unread_count,
    mark_all_notifications_read,
    mark_notification_read,
    mark_notifications_read_by_run,
)
from wildfire_assessment.svc.processor import (
    DELIVERABLE_FIELD_MAP,
    DELIVERABLE_TASK_FIELD_MAP,
    process_fire_assessment,
    process_scientific_deliverable,
)
from wildfire_assessment.translations import get_error_translation, get_user_language

LOG = logging.getLogger(__name__)


def health_status(_request):
    return JsonResponse({"status": "ok"})



class AreaOfInterestPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 999999999


class AreaOfInterestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AreaOfInterest CRUD operations.

    Supports list, retrieve, create, and delete operations.
    Users can only access areas in countries they are authorized for.
    """

    queryset = AreaOfInterest.objects.all().order_by("name")
    serializer_class = AreaOfInterestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AreaOfInterestPagination

    def get_serializer_class(self):
        if self.action == "create":
            return AreaOfInterestCreateSerializer
        if self.action in ["update", "partial_update"]:
            return AreaOfInterestUpdateSerializer
        return AreaOfInterestSerializer

    def get_queryset(self):
        """Filter queryset to only show areas the user has access to."""
        search = self.request.query_params.get("search")
        return get_areas_queryset(self.request.user, search=search)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific AreaOfInterest by its ID."""
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        List all AreaOfInterests.

        Supports pagination (default 20 per page) and search by name or country.
        Query params:
        - page: Page number
        - page_size: Items per page (max 100)
        - search: Search term for name or country name
        """
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new AreaOfInterest with GeoJSON upload."""
        return super().create(request, *args, **kwargs)

    def _check_area_permission(self, request, error_key):
        """Return a 403 Response if the user cannot access the area, else None."""
        instance = self.get_object()
        if not user_can_access_area(request.user, instance):
            lang = get_user_language(request)
            return Response(
                {"error": get_error_translation(lang, error_key)},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def update(self, request, *args, **kwargs):
        """
        Update an AreaOfInterest.

        Allows updating name, country, and optionally uploading a new GeoJSON file.
        """
        denied = self._check_area_permission(request, "error.no_permission_update")
        if denied:  # pragma: no cover
            return denied  # pragma: no cover
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Partially update an AreaOfInterest."""
        denied = self._check_area_permission(request, "error.no_permission_update")
        if denied:  # pragma: no cover
            return denied  # pragma: no cover
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete an AreaOfInterest.

        Also deletes the associated GeoJSON file.
        """
        denied = self._check_area_permission(request, "error.no_permission_delete")
        if denied:
            return denied
        instance = self.get_object()
        delete_polygon_file(instance.polygon_path)
        return super().destroy(request, *args, **kwargs)

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
        Custom action to analyze an AreaOfInterest.
        The 'id' parameter is the id of the AreaOfInterest.
        """
        instance = self.get_object()
        execution_id = uuid.uuid4()

        pre_fire_date = request.query_params.get("pre_fire_date")
        post_fire_date = request.query_params.get("post_fire_date")

        assessment_result = process_fire_assessment(
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            polygon_path=instance.polygon_path,
        )

        analysis_run = save_analysis_run(
            user=request.user,
            area=instance,
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            assessment_result=assessment_result,
        )

        return Response(
            {
                "execution_id": str(execution_id),
                "analysis_run_id": analysis_run.id,
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
            OpenApiParameter(
                name="analysis_run_id",
                description="ID of the AnalysisRun to attach the deliverable URL to",
                type=OpenApiTypes.INT,
                required=False,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="scientific_deliverable")
    def scientific_deliverable(self, request, pk=None):
        """
        Custom action to generate a scientific deliverable for an AreaOfInterest.
        The 'id' parameter is the id of the AreaOfInterest.
        """

        deliverable = request.query_params.get("deliverable")
        if deliverable not in DELIVERABLE_FIELD_MAP:
            lang = get_user_language(request)
            return Response(
                {"error": get_error_translation(lang, "error.invalid_deliverable")},
                status=400,
            )
        deliverable_enum = Deliverable[deliverable]

        instance = self.get_object()

        # Accept explicit analysis_run_id from the client
        analysis_run_id = request.query_params.get("analysis_run_id")
        analysis_run_id = int(analysis_run_id) if analysis_run_id else None

        task = process_scientific_deliverable.delay(
            pre_fire_date=request.query_params.get("pre_fire_date"),
            post_fire_date=request.query_params.get("post_fire_date"),
            polygon_path=instance.polygon_path,
            deliverable_name=deliverable_enum.name,
            email=request.user.email,
            reserve_name=instance.name,
            analysis_run_id=analysis_run_id,
            user_id=request.user.id,
        )

        # Persist the Celery task ID so the frontend can detect in-progress
        # deliverables when loading an existing analysis run.
        if analysis_run_id:
            task_field = DELIVERABLE_TASK_FIELD_MAP.get(deliverable_enum.name)
            if task_field:
                save_deliverable_task_id(analysis_run_id, task_field, task.id)

        return Response({"task_id": task.id})


class AnalysisRunViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AnalysisRun read and delete operations.

    Supports list, retrieve, and destroy operations.
    Users can only access analyses for areas in countries they are authorized for.
    """

    serializer_class = AnalysisRunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to only show analyses the user has access to."""
        return get_analysis_runs_queryset(self.request.user)

    @extend_schema(
        methods=["GET"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                description="Celery task ID to check",
                type=OpenApiTypes.STR,
                required=True,
            ),
            OpenApiParameter(
                name="deliverable",
                description="Deliverable name to retrieve URL for when task completes",
                type=OpenApiTypes.STR,
                required=False,
                enum=[
                    "RGB_PRE_FIRE",
                    "RGB_POST_FIRE",
                    "DNBR",
                    "RBR",
                    "DNDVI",
                ],
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "state": {"type": "string"},
                        "url": {"type": "string"},
                        "error": {"type": "string"},
                    },
                },
                description="Task status and optional deliverable URL",
            )
        },
    )
    @action(detail=True, methods=["get"], url_path="task_status")
    def task_status(self, request, pk=None):
        """Check the status of a Celery task for a scientific deliverable."""
        task_id = request.query_params.get("task_id")
        deliverable = request.query_params.get("deliverable")

        if not task_id:
            return Response(
                {"error": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        result = AsyncResult(task_id)
        state = result.state

        response_data = {"state": state}

        if state == "SUCCESS" and deliverable:
            instance = self.get_object()
            field_name = DELIVERABLE_FIELD_MAP.get(deliverable)
            if field_name:
                response_data["url"] = getattr(instance, field_name, None)

        if state == "FAILURE":
            response_data["error"] = (
                str(result.result) if result.result else "Task failed"
            )

        return Response(response_data)


class UserMeView(generics.RetrieveUpdateAPIView):
    """Return or update the authenticated user's profile."""

    serializer_class = UserMeSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user


class DashboardView(APIView):
    """Return dashboard statistics for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: DashboardStatsSerializer},
    )
    def get(self, request):
        stats = get_dashboard_stats(request.user)
        stats["recent_analyses"] = AnalysisRunSerializer(
            stats["recent_analyses"], many=True
        ).data
        return Response(stats)


def _handle_ai_stream(generate_fn, language, empty_key, failed_key, log_message):
    """Execute an AI stream generator and return a streaming response or error."""
    try:
        provider = get_active_provider()
        provider_display = PROVIDER_DISPLAY.get(provider.provider, provider.provider) if provider else "AI"
        stream, holder = generate_fn()
        first_chunk = next(stream)
    except StopIteration:
        return Response(
            {"error": get_error_translation(language, empty_key)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        LOG.exception(log_message)
        return Response(
            {"error": get_error_translation(language, failed_key, detail=str(e))},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return _build_streaming_response(first_chunk, stream, holder, provider_display)


class AIAnalysisView(APIView):
    """
    Generate AI-powered analysis of wildfire data.

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
            500: OpenApiResponse(description="API error"),
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
        language = get_user_language(request)

        return _handle_ai_stream(
            generate_fn=lambda: generate_analysis_stream(
                pre_fire_date=str(data["pre_fire_date"]),
                post_fire_date=str(data["post_fire_date"]),
                area_of_interest=data["area_of_interest"],
                severity_distribution=data["severity_distribution"],
                image_urls=data.get("image_urls", []),
                language=language,
            ),
            language=language,
            empty_key="error.ai_empty_response",
            failed_key="error.ai_failed",
            log_message="Error generating AI analysis",
        )


class AIAnalysisFollowUpView(APIView):
    """Follow-up questions on a previous AI analysis."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AnalysisFollowUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        language = get_user_language(request)

        return _handle_ai_stream(
            generate_fn=lambda: generate_followup_stream(
                previous_response_id=data["previous_response_id"],
                question=data["question"],
                language=language,
            ),
            language=language,
            empty_key="error.ai_followup_empty",
            failed_key="error.ai_followup_failed",
            log_message="Error generating AI follow-up",
        )


def _build_streaming_response(first_chunk, stream, holder, provider_display="AI"):
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
    response["X-AI-Provider"] = provider_display
    return response


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notifications for the authenticated user."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return get_notifications_queryset(self.request.user)

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request):
        count = get_unread_count(request.user)
        return Response({"unread_count": count})

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        mark_notification_read(notification)
        return Response({"status": "ok"})

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read_batch(self, request):
        analysis_run_id = request.data.get("analysis_run_id")
        if not analysis_run_id:
            return Response(
                {"error": "analysis_run_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = mark_notifications_read_by_run(request.user, analysis_run_id)
        return Response({"marked_read": updated})

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = mark_all_notifications_read(request.user)
        return Response({"marked_read": updated})
