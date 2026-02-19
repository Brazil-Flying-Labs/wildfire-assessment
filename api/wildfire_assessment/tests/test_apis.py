from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from wildfire_assessment.models import Country, EcologicalReserve
from wildfire_assessment.views import health_status


class WildfireAssessmentTests(APITestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.other_country = Country.objects.create(name="Other Country", code="OC")
        self.reserve = EcologicalReserve.objects.create(
            name="Reserve A",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.other_reserve = EcologicalReserve.objects.create(
            name="Reserve B",
            polygon_path="polygon2.json",
            country=self.other_country,
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )

    def test_list_requires_authentication(self):
        url = reverse("ecologicalreserve-list")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_retrieve_requires_authentication(self):
        url = reverse("ecologicalreserve-detail", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_analyze_requires_authentication(self):
        base_url = reverse("ecologicalreserve-analyze", args=[self.reserve.id])
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
            }
        )
        response = self.client.post(f"{base_url}?{query}")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_scientific_deliverable_requires_authentication(self):
        base_url = reverse(
            "ecologicalreserve-scientific-deliverable", args=[self.reserve.id]
        )
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "deliverable": "DNBR",
            }
        )
        response = self.client.post(f"{base_url}?{query}")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_list_returns_empty_without_country_permissions(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("ecologicalreserve-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_list_returns_only_authorized_country_reserves(self):
        from wildfire_assessment.models import UserCountry

        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("ecologicalreserve-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], self.reserve.name)

    def test_retrieve_returns_reserve_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("ecologicalreserve-detail", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], self.reserve.name)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_calls_processor_with_expected_arguments(
        self, mock_process, mock_scientific
    ):
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
            }
        )
        url = reverse("ecologicalreserve-analyze", args=[self.reserve.id])

        mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
        response = self.client.post(f"{url}?{query}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kwargs = mock_process.call_args.kwargs
        self.assertEqual(kwargs["pre_fire_date"], "2023-01-01")
        self.assertEqual(kwargs["post_fire_date"], "2023-01-15")
        self.assertEqual(
            kwargs["polygon_path"], f"../../polygons/{self.reserve.polygon_path}"
        )

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    def test_scientific_deliverable_handles_all_deliverables(self, mock_process):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "ecologicalreserve-scientific-deliverable", args=[self.reserve.id]
        )

        for deliverable in [
            "RGB_PRE_FIRE",
            "RGB_POST_FIRE",
            "DNBR",
            "RBR",
            "DNDVI",
        ]:
            query = urlencode(
                {
                    "pre_fire_date": "2023-01-01",
                    "post_fire_date": "2023-01-15",
                    "deliverable": deliverable,
                }
            )
            mock_process.return_value = SimpleNamespace(id=f"task-{deliverable}")
            response = self.client.post(f"{url}?{query}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json(), {"task_id": f"task-{deliverable}"})
            kwargs = mock_process.call_args.kwargs
            self.assertEqual(kwargs["deliverable_name"], deliverable)

        # Invalid deliverable
        response = self.client.post(
            f"{url}?" + urlencode(
                {
                    "pre_fire_date": "2023-01-01",
                    "post_fire_date": "2023-01-15",
                    "deliverable": "INVALID",
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health_status(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class UserMeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password",
            first_name="Test",
            last_name="User",
        )
        self.url = reverse("user-me")

    def test_me_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_me_returns_user_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["email"], "tester@example.com")
        self.assertEqual(data["first_name"], "Test")
        self.assertEqual(data["last_name"], "User")
        self.assertEqual(data["default_language"], "en")

    def test_me_patch_updates_language(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"default_language": "pt-BR"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.default_language, "pt-BR")


class AIAnalysisViewTests(APITestCase):
    """Tests for the AI analysis streaming endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password",
        )
        self.url = reverse("ai-analysis")
        self.valid_payload = {
            "pre_fire_date": "2024-01-01",
            "post_fire_date": "2024-01-15",
            "area_of_interest": "Test Reserve",
            "severity_distribution": {
                "Unburned": {"area_ha": 100.0, "percent": 50.0},
                "Low": {"area_ha": 50.0, "percent": 25.0},
                "High": {"area_ha": 50.0, "percent": 25.0},
            },
        }

    def test_analysis_requires_authentication(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_analysis_returns_400_for_invalid_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analysis_returns_400_for_missing_fields(self):
        self.client.force_authenticate(user=self.user)
        incomplete_payload = {
            "pre_fire_date": "2024-01-01",
            # Missing other fields
        }
        response = self.client.post(self.url, incomplete_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_returns_streaming_response(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = iter(["Hello ", "World"])

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertEqual(content, "Hello World")

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_passes_correct_parameters(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = iter([])

        self.client.post(self.url, self.valid_payload, format="json")

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        self.assertEqual(call_kwargs["pre_fire_date"], "2024-01-01")
        self.assertEqual(call_kwargs["post_fire_date"], "2024-01-15")
        self.assertEqual(call_kwargs["area_of_interest"], "Test Reserve")
        self.assertIn("Unburned", call_kwargs["severity_distribution"])

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_returns_500_on_value_error(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.side_effect = ValueError("API key not set")

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.json())
