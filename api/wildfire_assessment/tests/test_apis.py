import logging
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from wildfire_assessment.models import (
    AnalysisRun,
    AreaOfInterest,
    Country,
    Notification,
    UserCountry,
    UserProfile,
)
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
        url = reverse("areaofinterest-scientific-deliverable", args=[self.reserve.id])

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
            f"{url}?"
            + urlencode(
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

    @patch("wildfire_assessment.serializers.upload_polygon_to_s3")
    def test_create_area_of_interest_success(self, mock_upload):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-list")
        payload = {
            "name": "New Area",
            "country": self.country.id,
            "geojson": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
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
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
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
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)

        with patch(
            "wildfire_assessment.svc.area_of_interest.delete_polygon_from_s3"
        ) as mock_delete:
            mock_delete.return_value = True
            url = reverse("areaofinterest-detail", args=[self.reserve.id])
            response = self.client.delete(url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_delete.assert_called_once_with(self.reserve.polygon_path)

    def test_delete_area_of_interest_file_deletion_error(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)

        # Simulate S3 deletion failure
        with patch(
            "wildfire_assessment.svc.area_of_interest.delete_polygon_from_s3"
        ) as mock_delete:
            mock_delete.return_value = False
            url = reverse("areaofinterest-detail", args=[self.reserve.id])
            response = self.client.delete(url)
            # Should still succeed even if S3 deletion fails
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            mock_delete.assert_called_once()

    def test_delete_area_of_interest_permission_check_in_destroy(self):
        """Test the defensive permission check in destroy method."""
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

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon_from_s3")
    def test_geojson_endpoint_success(self, mock_download):
        """Test geojson endpoint returns GeoJSON data."""
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        mock_download.return_value = (
            '{"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,0]]]}'
        )
        url = reverse("areaofinterest-geojson", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["type"], "Polygon")
        self.assertIn("coordinates", data)

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon_from_s3")
    def test_geojson_endpoint_download_failure(self, mock_download):
        """Test geojson endpoint returns 404 on download failure."""
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        mock_download.side_effect = Exception("S3 error")
        url = reverse("areaofinterest-geojson", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_geojson_endpoint_requires_auth(self):
        """Test geojson endpoint requires authentication."""
        url = reverse("areaofinterest-geojson", args=[self.reserve.id])
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_geojson_endpoint_empty_polygon_path(self):
        """Test geojson endpoint returns 404 for empty polygon path."""
        area_no_path = AreaOfInterest.objects.create(
            name="No Path",
            polygon_path="",
            country=self.country,
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-geojson", args=[area_no_path.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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

    def test_me_get_includes_push_token(self):
        UserProfile.objects.update_or_create(
            user=self.user,
            defaults={"expo_push_token": "ExponentPushToken[test]"},
        )
        # Re-fetch user to avoid stale cached profile relation
        user = User.objects.get(pk=self.user.pk)
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["expo_push_token"], "ExponentPushToken[test]")

    def test_me_patch_updates_push_token(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"expo_push_token": "ExponentPushToken[new]"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertEqual(
            self.user.profile.expo_push_token, "ExponentPushToken[new]"
        )

    def test_me_patch_clears_push_token(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.expo_push_token = "ExponentPushToken[old]"
        profile.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"expo_push_token": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.expo_push_token)


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
            severity_data={
                "Total Area": {"area_ha": 1000.0, "ratio_percent": 100.0},
                "Total Burned Area": {"area_ha": 100.5, "ratio_percent": 10.05},
            },
        )
        self.url = reverse("dashboard")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_dashboard_returns_stats_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_analyses"], 1)
        self.assertEqual(data["total_areas"], 1)
        self.assertIn("recent_analyses", data)

    def test_dashboard_returns_empty_for_user_without_runs(self):
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password"
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_analyses"], 0)
        self.assertEqual(data["total_areas"], 0)

    def test_dashboard_includes_total_analyzed_ha(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # total_analyzed_ha comes from severity_data "Total Area" per distinct combo
        self.assertEqual(float(data["total_analyzed_ha"]), 1000.0)

    def test_dashboard_includes_new_widget_fields(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("severity_breakdown", data)
        self.assertIn("area_comparison", data)
        self.assertIn("average_burn_severity", data)
        self.assertIn("most_analyzed_area", data)
        self.assertIn("largest_fire", data)


class AnalysisRunTaskStatusTests(APITestCase):
    """Tests for the task_status action on AnalysisRunViewSet."""

    def setUp(self):
        self.country = Country.objects.create(name="Task Country", code="TK")
        self.area = AreaOfInterest.objects.create(
            name="Task Area",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="taskuser", email="task@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_url="http://example.com/dnbr.tif",
        )

    def test_task_status_requires_task_id(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("task_id is required", response.json()["error"])

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_pending(self, mock_async):
        mock_result = SimpleNamespace(state="PENDING", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["state"], "PENDING")

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_success_with_deliverable(self, mock_async):
        mock_result = SimpleNamespace(state="SUCCESS", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123&deliverable=DNBR")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["state"], "SUCCESS")
        self.assertEqual(data["url"], "http://example.com/dnbr.tif")

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_success_without_deliverable(self, mock_async):
        mock_result = SimpleNamespace(state="SUCCESS", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["state"], "SUCCESS")
        self.assertNotIn("url", data)

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_failure(self, mock_async):
        mock_result = SimpleNamespace(state="FAILURE", result=RuntimeError("Task boom"))
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["state"], "FAILURE")
        self.assertIn("Task boom", data["error"])

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_failure_no_result(self, mock_async):
        mock_result = SimpleNamespace(state="FAILURE", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123")
        data = response.json()
        self.assertEqual(data["error"], "Task failed")


class ScientificDeliverableWithRunIdTests(APITestCase):
    """Tests for scientific_deliverable with analysis_run_id persistence."""

    def setUp(self):
        self.country = Country.objects.create(name="Sci Country", code="SC")
        self.area = AreaOfInterest.objects.create(
            name="Sci Area",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="sciuser", email="sci@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    def test_scientific_deliverable_persists_task_id(self, mock_process):
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-scientific-deliverable", args=[self.area.id])
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "deliverable": "DNBR",
                "analysis_run_id": self.analysis.id,
            }
        )
        mock_process.return_value = SimpleNamespace(id="celery-task-xyz")
        response = self.client.post(f"{url}?{query}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.scientific_dnbr_task_id, "celery-task-xyz")

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    def test_scientific_deliverable_without_run_id(self, mock_process):
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-scientific-deliverable", args=[self.area.id])
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "deliverable": "DNBR",
            }
        )
        mock_process.return_value = SimpleNamespace(id="celery-task-abc")
        response = self.client.post(f"{url}?{query}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["task_id"], "celery-task-abc")


class TaskStatusDbErrorTests(APITestCase):
    """Tests for task_status returning DB-persisted errors on stale PENDING."""

    def setUp(self):
        self.country = Country.objects.create(name="DbErr Country", code="DE")
        self.area = AreaOfInterest.objects.create(
            name="DbErr Area",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="dberruser", email="dberr@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_error="Task is no longer running",
        )

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_returns_db_error_on_stale_pending(self, mock_async):
        """When AsyncResult is PENDING and DB has error, return FAILURE with DB error."""
        mock_result = SimpleNamespace(state="PENDING", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123&deliverable=DNBR")
        data = response.json()
        self.assertEqual(data["state"], "FAILURE")
        self.assertEqual(data["error"], "Task is no longer running")

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_pending_without_db_error_stays_pending(self, mock_async):
        """When AsyncResult is PENDING but no DB error, return PENDING."""
        # Clear the error
        self.analysis.scientific_dnbr_error = None
        self.analysis.save()
        mock_result = SimpleNamespace(state="PENDING", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123&deliverable=DNBR")
        data = response.json()
        self.assertEqual(data["state"], "PENDING")

    @patch("wildfire_assessment.views.AsyncResult")
    def test_task_status_pending_without_deliverable_param(self, mock_async):
        """When AsyncResult is PENDING but no deliverable param, return PENDING."""
        mock_result = SimpleNamespace(state="PENDING", result=None)
        mock_async.return_value = mock_result
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-task-status", args=[self.analysis.id])
        response = self.client.get(f"{url}?task_id=abc-123")
        data = response.json()
        self.assertEqual(data["state"], "PENDING")


class ScientificDeliverableClearsErrorTests(APITestCase):
    """Tests for clearing error on retry of scientific_deliverable."""

    def setUp(self):
        self.country = Country.objects.create(name="Retry Country", code="RT")
        self.area = AreaOfInterest.objects.create(
            name="Retry Area",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="retryuser", email="retry@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_error="Previous failure",
            scientific_dnbr_task_id=None,
        )

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    def test_scientific_deliverable_clears_error_on_retry(self, mock_process):
        """Retrying a failed deliverable clears the error field."""
        self.client.force_authenticate(user=self.user)
        url = reverse("areaofinterest-scientific-deliverable", args=[self.area.id])
        query = urlencode(
            {
                "pre_fire_date": "2024-01-01",
                "post_fire_date": "2024-01-15",
                "deliverable": "DNBR",
                "analysis_run_id": self.analysis.id,
            }
        )
        mock_process.return_value = SimpleNamespace(id="new-celery-task")
        response = self.client.post(f"{url}?{query}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analysis.refresh_from_db()
        self.assertIsNone(self.analysis.scientific_dnbr_error)
        self.assertEqual(self.analysis.scientific_dnbr_task_id, "new-celery-task")


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
        self.assertEqual(response.json()["theme"], "dark")

    def test_get_theme_without_profile(self):
        """Test that theme defaults to 'dark' when user has no profile."""
        # Delete the auto-created profile
        UserProfile.objects.filter(user=self.user).delete()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["theme"], "dark")

    def test_patch_dashboard_widgets(self):
        self.client.force_authenticate(user=self.user)
        widgets = ["summary", "severity_breakdown", "area_comparison"]
        response = self.client.patch(
            self.url, {"dashboard_widgets": widgets}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.dashboard_widgets, widgets)

    def test_get_dashboard_widgets_default(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["dashboard_widgets"])

    def test_get_authorized_countries(self):
        country = Country.objects.create(name="Auth Country", code="AU")
        UserCountry.objects.create(user=self.user, country=country)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        countries = response.json()["authorized_countries"]
        self.assertEqual(len(countries), 1)
        self.assertEqual(countries[0]["code"], "AU")


class UserMeTermsAcceptanceTests(APITestCase):
    """Tests for terms of service acceptance via /me/ endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="password",
        )
        self.url = reverse("user-me")

    def test_get_terms_accepted_at_returns_null_by_default(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["terms_accepted_at"])

    def test_patch_accept_terms_sets_timestamp(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"accept_terms": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.terms_accepted_at)

    def test_get_terms_accepted_at_returns_datetime_after_acceptance(self):
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {"accept_terms": True}, format="json")
        # Re-fetch user to clear cached profile relation
        self.user = User.objects.get(pk=self.user.pk)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.json()["terms_accepted_at"])

    def test_patch_accept_terms_again_updates_timestamp(self):
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {"accept_terms": True}, format="json")
        self.user.profile.refresh_from_db()
        original_timestamp = self.user.profile.terms_accepted_at

        self.client.patch(self.url, {"accept_terms": True}, format="json")
        self.user.profile.refresh_from_db()
        self.assertGreaterEqual(self.user.profile.terms_accepted_at, original_timestamp)

    def test_regular_patch_does_not_affect_terms(self):
        self.client.force_authenticate(user=self.user)
        self.client.patch(
            self.url,
            {"first_name": "Updated"},
            format="json",
        )
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.terms_accepted_at)

    def test_get_returns_terms_last_updated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("terms_last_updated", data)
        self.assertEqual(data["terms_last_updated"], settings.TERMS_LAST_UPDATED)


class AnalysisRunDeleteTests(APITestCase):
    """Tests for deleting analysis runs."""

    def setUp(self):
        self.country = Country.objects.create(name="Del Country", code="DL")
        self.area = AreaOfInterest.objects.create(
            name="Del Area",
            polygon_path="del.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="deluser", email="del@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )

    def test_delete_analysis_run(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-detail", args=[self.analysis.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AnalysisRun.objects.filter(id=self.analysis.id).exists())


class NotificationViewSetTests(APITestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Notif Country", code="NC")
        self.area = AreaOfInterest.objects.create(
            name="Notif Area", polygon_path="notif.geojson", country=self.country
        )
        self.user = User.objects.create_user(
            username="notifuser", email="notif@example.com", password="pw"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pw"
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.notif1 = Notification.objects.create(
            user=self.user,
            analysis_run=self.analysis,
            notification_type="deliverable_ready",
            deliverable_name="DNBR",
            message="DNBR ready",
        )
        self.notif2 = Notification.objects.create(
            user=self.user,
            analysis_run=self.analysis,
            notification_type="deliverable_ready",
            deliverable_name="RBR",
            message="RBR ready",
        )
        # Notification for other user — should never be visible
        self.other_notif = Notification.objects.create(
            user=self.other_user,
            notification_type="deliverable_ready",
            deliverable_name="DNDVI",
            message="Other user notif",
        )

    def test_list_requires_auth(self):
        url = reverse("notification-list")
        response = self.client.get(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_list_returns_own_notifications(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        ids = [n["id"] for n in data["results"]]
        self.assertIn(self.notif1.id, ids)
        self.assertIn(self.notif2.id, ids)
        self.assertNotIn(self.other_notif.id, ids)

    def test_list_does_not_show_other_users_notifications(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("notification-list")
        response = self.client.get(url)
        ids = [n["id"] for n in response.json()["results"]]
        self.assertNotIn(self.notif1.id, ids)

    def test_retrieve_own_notification(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-detail", args=[self.notif1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["deliverable_name"], "DNBR")
        self.assertEqual(data["analysis_run_id"], self.analysis.id)
        self.assertEqual(data["area_name"], "Notif Area")

    def test_retrieve_other_users_notification_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("notification-detail", args=[self.notif1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unread_count(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-unread-count")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["unread_count"], 2)

    def test_unread_count_after_marking_read(self):
        self.notif1.is_read = True
        self.notif1.save()
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-unread-count")
        response = self.client.get(url)
        self.assertEqual(response.json()["unread_count"], 1)

    def test_mark_read_single(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-mark-read", args=[self.notif1.id])
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.is_read)

    def test_mark_read_single_other_user_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("notification-mark-read", args=[self.notif1.id])
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_read_batch(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-mark-read-batch")
        response = self.client.post(
            url,
            {"analysis_run_id": self.analysis.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["marked_read"], 2)
        self.notif1.refresh_from_db()
        self.notif2.refresh_from_db()
        self.assertTrue(self.notif1.is_read)
        self.assertTrue(self.notif2.is_read)

    def test_mark_read_batch_missing_analysis_run_id(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-mark-read-batch")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_read_batch_does_not_affect_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("notification-mark-read-batch")
        response = self.client.post(
            url,
            {"analysis_run_id": self.analysis.id},
            format="json",
        )
        self.assertEqual(response.json()["marked_read"], 0)
        self.notif1.refresh_from_db()
        self.assertFalse(self.notif1.is_read)

    def test_mark_all_read(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-mark-all-read")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["marked_read"], 2)
        self.notif1.refresh_from_db()
        self.notif2.refresh_from_db()
        self.assertTrue(self.notif1.is_read)
        self.assertTrue(self.notif2.is_read)

    def test_mark_all_read_does_not_affect_other_user(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse("notification-mark-all-read")
        response = self.client.post(url)
        self.assertEqual(response.json()["marked_read"], 1)
        self.notif1.refresh_from_db()
        self.assertFalse(self.notif1.is_read)

    def test_mark_all_read_when_none_unread(self):
        self.notif1.is_read = True
        self.notif1.save()
        self.notif2.is_read = True
        self.notif2.save()
        self.client.force_authenticate(user=self.user)
        url = reverse("notification-mark-all-read")
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["marked_read"], 0)
