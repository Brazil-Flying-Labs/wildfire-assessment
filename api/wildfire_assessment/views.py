from django.contrib.auth.models import Group, User
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from wildfire_assessment.models import EcologicalReserve
from wildfire_assessment.serializers import EcologicalReserveSerializer


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
    )
    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        """
        Custom action to analyze an EcologicalReserve.
        The 'pk' parameter is the id of the EcologicalReserve.
        """
        instance = self.get_object()
        # You can implement your logic here
        # Example: reserve = self.get_object()
        return Response(
            {"message": f"Analyze called for EcologicalReserve {instance.name}"}
        )
