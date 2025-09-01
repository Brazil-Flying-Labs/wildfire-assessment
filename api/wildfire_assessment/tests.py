from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import EcologicalReserve


class WildfireAssessmentTests(APITestCase):

    def get_analyze_action_url(self, ecological_reserve_id: str):
        return reverse("ecologicalreserve-analyze", args=[ecological_reserve_id])

    def setUp(self):
        self.reserve = EcologicalReserve.objects.create(
            # Add required fields for EcologicalReserve here
            name="Test Reserve"
        )
        user = User.objects.create_user(username="testuser", password="testpass")
        self.client.force_authenticate(user=user)

    def test_analyze_action(self):
        url = self.get_analyze_action_url(str(self.reserve.id))

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            f"Analyze called for EcologicalReserve {self.reserve.name}",
            response.data.get("message", ""),
        )
