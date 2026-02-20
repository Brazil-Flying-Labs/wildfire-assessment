import logging
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from wildfire_assessment.models import AreaOfInterest, Country, UserCountry
from wildfire_assessment.views import health_status


class WildfireAssessmentTests(APITestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.other_country = Country.objects.create(name="Other Country", code="OC")
        self.reserve = AreaOfInterest.objects.create(
            name="Reserve A",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.other_reserve = AreaOfInterest.objects.create(
            name="Reserve B",
            polygon_path="polygon2.json",
            country=self.other_country,
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )

    def test_list_requires_authentication(self):
        url = reverse("areaofinterest-list")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_retrieve_requires_authentication(self):
        url = reverse("areaofinterest-detail", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_analyze_requires_authentication(self):
        base_url = reverse("areaofinterest-analyze", args=[self.reserve.id])
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
            "areaofinterest-scientific-deliverable", args=[self.reserve.id]
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
        url = reverse("areaofinterest-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_list_returns_only_authorized_country_reserves(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["name"], self.reserve.name)

    def test_retrieve_returns_reserve_for_authenticated_user(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], self.reserve.name)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_calls_processor_with_expected_arguments(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])

        mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
        response = self.client.post(f"{url}?{query}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kwargs = mock_process.call_args.kwargs
        self.assertEqual(kwargs["pre_fire_date"], "2023-01-01")
        self.assertEqual(kwargs["post_fire_date"], "2023-01-15")
        self.assertEqual(kwargs["polygon_path"], self.reserve.polygon_path)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    def test_scientific_deliverable_handles_all_deliverables(self, mock_process):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "areaofinterest-scientific-deliverable", args=[self.reserve.id]
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

    def test_search_by_name(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        response = self.client.get(f"{url}?search=Reserve")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Reserve A")

    def test_search_by_country(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        response = self.client.get(f"{url}?search=Test Country")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_search_no_results(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        response = self.client.get(f"{url}?search=NonExistent")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 0)

    @patch("wildfire_assessment.svc.aws.upload_polygon_to_s3")
    def test_create_area_of_interest_success(self, mock_upload):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        payload = {
            "name": "New Area",
            "country": self.country.id,
            "geojson": {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {},
            },
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], "New Area")
        self.assertTrue(AreaOfInterest.objects.filter(name="New Area").exists())

    def test_create_area_of_interest_unauthorized_country(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        payload = {
            "name": "New Area",
            "country": self.other_country.id,  # User doesn't have access
            "geojson": {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {},
            },
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("country", response.json())

    def test_create_area_of_interest_invalid_geojson_not_dict(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        payload = {
            "name": "New Area",
            "country": self.country.id,
            "geojson": "not a dict",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("geojson", response.json())

    def test_create_area_of_interest_invalid_geojson_type(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        payload = {
            "name": "New Area",
            "country": self.country.id,
            "geojson": {"type": "InvalidType"},
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("geojson", response.json())

    def test_delete_area_of_interest_success(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.reserve.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AreaOfInterest.objects.filter(id=self.reserve.id).exists())

    def test_delete_area_of_interest_no_permission(self):
        # User has permission for country but not other_country
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.other_reserve.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_area_of_interest_with_file_cleanup(self):
        from unittest.mock import patch

        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)

        with patch("wildfire_assessment.svc.area_of_interest.delete_polygon_from_s3") as mock_delete:
            mock_delete.return_value = True
            url = reverse("areaofinterest-detail", args=[self.reserve.id])
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_delete.assert_called_once_with(self.reserve.polygon_path)

    def test_delete_area_of_interest_file_deletion_error(self):
        from unittest.mock import patch

        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)

        # Simulate S3 deletion failure
        with patch("wildfire_assessment.svc.area_of_interest.delete_polygon_from_s3") as mock_delete:
            mock_delete.return_value = False
            url = reverse("areaofinterest-detail", args=[self.reserve.id])
            response = self.client.delete(url)
            # Should still succeed even if S3 deletion fails
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_delete.assert_called_once()

    def test_delete_area_of_interest_permission_check_in_destroy(self):
        """Test the defensive permission check in destroy method."""
        from unittest.mock import patch

        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)

        # Patch get_object to return a reserve from a different country
        # This tests the defensive permission check that would normally be unreachable
        with patch(
            "wildfire_assessment.views.AreaOfInterestViewSet.get_object",
            return_value=self.other_reserve,
        ):
            url = reverse("areaofinterest-detail", args=[self.other_reserve.id])
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertIn("permission", response.json()["error"])


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
        mock_generate.return_value = (iter(["Hello ", "World"]), {"response_id": None})

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertEqual(content, "Hello World")

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_passes_correct_parameters(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter(["chunk"]), {"response_id": None})

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

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_returns_502_on_empty_stream(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter([]), {"response_id": None})

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("empty response", response.json()["error"])

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_returns_500_on_generic_exception(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.side_effect = RuntimeError("connection failed")

        logging.disable(logging.CRITICAL)
        response = self.client.post(self.url, self.valid_payload, format="json")
        logging.disable(logging.NOTSET)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("connection failed", response.json()["error"])

    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_streaming_response_includes_response_id(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (
            iter(["chunk"]),
            {"response_id": "resp_abc"},
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("[RESPONSE_ID]resp_abc[/RESPONSE_ID]", content)


class AIAnalysisFollowUpViewTests(APITestCase):
    """Tests for the AI analysis follow-up endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password",
        )
        self.url = reverse("ai-analysis-followup")
        self.valid_payload = {
            "previous_response_id": "resp_123",
            "question": "What about recovery?",
        }

    def test_followup_requires_authentication(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_followup_returns_400_for_invalid_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("wildfire_assessment.views.generate_followup_stream")
    def test_followup_returns_streaming_response(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (
            iter(["Follow ", "up"]),
            {"response_id": "resp_456"},
        )

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("Follow up", content)
        self.assertIn("[RESPONSE_ID]resp_456[/RESPONSE_ID]", content)

    @patch("wildfire_assessment.views.generate_followup_stream")
    def test_followup_passes_correct_parameters(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter(["chunk"]), {"response_id": None})

        self.client.post(self.url, self.valid_payload, format="json")

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        self.assertEqual(call_kwargs["previous_response_id"], "resp_123")
        self.assertEqual(call_kwargs["question"], "What about recovery?")

    @patch("wildfire_assessment.views.generate_followup_stream")
    def test_followup_returns_502_on_empty_stream(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter([]), {"response_id": None})

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("empty response", response.json()["error"])

    @patch("wildfire_assessment.views.generate_followup_stream")
    def test_followup_returns_500_on_value_error(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.side_effect = ValueError("API key not set")

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.json())

    @patch("wildfire_assessment.views.generate_followup_stream")
    def test_followup_returns_500_on_generic_exception(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.side_effect = RuntimeError("connection failed")

        logging.disable(logging.CRITICAL)
        response = self.client.post(self.url, self.valid_payload, format="json")
        logging.disable(logging.NOTSET)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("connection failed", response.json()["error"])


class AnalysisRunViewSetTests(APITestCase):
    """Tests for the AnalysisRun ViewSet."""

    def setUp(self):
        from wildfire_assessment.models import AnalysisRun

        self.country = Country.objects.create(name="Test Country", code="TC")
        self.other_country = Country.objects.create(name="Other Country", code="OC")
        self.area = AreaOfInterest.objects.create(
            name="Test Area",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.other_area = AreaOfInterest.objects.create(
            name="Other Area",
            polygon_path="polygon2.json",
            country=self.other_country,
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.5,
        )
        self.other_analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.other_area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            total_burned_ha=50.0,
        )

    def test_list_requires_authentication(self):
        url = reverse("analysisrun-list")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_retrieve_requires_authentication(self):
        url = reverse("analysisrun-detail", args=[self.analysis.id])
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_list_returns_empty_without_country_permissions(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_list_returns_only_authorized_analyses(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.analysis.id)

    def test_retrieve_returns_analysis_for_authorized_user(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-detail", args=[self.analysis.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.analysis.id)
        self.assertEqual(data["area_name"], "Test Area")

    def test_retrieve_returns_404_for_unauthorized_analysis(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-detail", args=[self.other_analysis.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DashboardViewTests(APITestCase):
    """Tests for the Dashboard View."""

    def setUp(self):
        from wildfire_assessment.models import AnalysisRun

        self.country = Country.objects.create(name="Test Country", code="TC")
        self.area = AreaOfInterest.objects.create(
            name="Test Area",
            polygon_path="polygon.json",
            country=self.country,
            area_ha=1000.0,
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.5,
        )
        self.url = reverse("dashboard")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_dashboard_returns_stats_for_authenticated_user(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_analyses"], 1)
        self.assertEqual(data["total_areas"], 1)
        self.assertIn("recent_analyses", data)

    def test_dashboard_returns_empty_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_analyses"], 0)
        self.assertEqual(data["total_areas"], 0)

    def test_dashboard_includes_total_analyzed_ha(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # total_analyzed_ha should be the sum of area_ha for analyzed areas
        self.assertEqual(float(data["total_analyzed_ha"]), 1000.0)


class AreaOfInterestUpdateTests(APITestCase):
    """Tests for updating areas of interest."""

    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.other_country = Country.objects.create(name="Other Country", code="OC")
        self.area = AreaOfInterest.objects.create(
            name="Original Name",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )

    def test_update_requires_authentication(self):
        url = reverse("areaofinterest-detail", args=[self.area.id])
        response = self.client.put(url, {"name": "New Name"}, format="json")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_update_requires_country_permission(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.area.id])
        response = self.client.put(
            url,
            {"name": "New Name", "country": self.country.id},
            format="json",
        )
        # Without country permission, should get 404 (filtered by queryset)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_success(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.area.id])
        response = self.client.put(
            url,
            {"name": "Updated Name", "country": self.country.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.area.refresh_from_db()
        self.assertEqual(self.area.name, "Updated Name")

    def test_partial_update_success(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.area.id])
        response = self.client.patch(url, {"name": "Patched Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.area.refresh_from_db()
        self.assertEqual(self.area.name, "Patched Name")

    def test_update_forbidden_for_wrong_country(self):
        # User has permission for other_country but not the area's country
        UserCountry.objects.create(user=self.user, country=self.other_country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.area.id])
        response = self.client.put(
            url,
            {"name": "New Name", "country": self.country.id},
            format="json",
        )
        # Should get 404 because queryset filters by country permission
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partial_update_forbidden_for_wrong_country(self):
        UserCountry.objects.create(user=self.user, country=self.other_country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-detail", args=[self.area.id])
        response = self.client.patch(url, {"name": "Patched"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UserMeViewExtendedTests(APITestCase):
    """Extended tests for UserMe View covering profile updates."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password",
        )
        self.url = reverse("user-me")

    def test_patch_first_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"first_name": "NewFirst"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "NewFirst")

    def test_patch_last_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"last_name": "NewLast"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "NewLast")

    def test_patch_theme(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"theme": "dark"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, "dark")

    def test_get_theme_returns_default(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["theme"], "light")

    def test_get_theme_without_profile(self):
        """Test that theme defaults to 'light' when user has no profile."""
        from wildfire_assessment.models import UserProfile

        # Delete the auto-created profile
        UserProfile.objects.filter(user=self.user).delete()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["theme"], "light")
