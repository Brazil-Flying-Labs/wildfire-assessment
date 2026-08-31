import logging
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import override_settings
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
        self.assertTrue(kwargs["roi_only"])

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_passes_roi_only_false(self, mock_process, mock_scientific):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "roi_only": "false",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
        self.client.post(f"{url}?{query}")
        kwargs = mock_process.call_args.kwargs
        self.assertFalse(kwargs["roi_only"])

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_passes_advanced_settings(self, mock_process, mock_scientific):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "roi_only": "true",
                "cloud_threshold": "50",
                "days_before_after": "15",
                "pre_fire_mosaic_strategy": "best_date_mosaic",
                "post_fire_mosaic_strategy": "cloud_masked_light_mosaic",
                "roi_only_bg_color": "white",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        self.client.post(f"{url}?{query}")
        kwargs = mock_process.call_args.kwargs
        self.assertEqual(kwargs["cloud_threshold"], 50)
        self.assertEqual(kwargs["days_before_after"], 15)
        self.assertEqual(kwargs["pre_fire_mosaic_strategy"], "best_date_mosaic")
        self.assertEqual(
            kwargs["post_fire_mosaic_strategy"], "cloud_masked_light_mosaic"
        )
        self.assertEqual(kwargs["roi_only_bg_color"], "white")

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_advanced_settings_defaults(self, mock_process, mock_scientific):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        self.client.post(f"{url}?{query}")
        kwargs = mock_process.call_args.kwargs
        self.assertEqual(kwargs["cloud_threshold"], 100)
        self.assertEqual(kwargs["days_before_after"], 30)
        self.assertEqual(
            kwargs["pre_fire_mosaic_strategy"], "best_available_per_tile_mosaic"
        )
        self.assertEqual(
            kwargs["post_fire_mosaic_strategy"], "best_available_per_tile_mosaic"
        )
        self.assertEqual(kwargs["roi_only_bg_color"], "black")

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_cloud_threshold_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "cloud_threshold": "150",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)
        mock_process.assert_not_called()

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_cloud_threshold_negative_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "cloud_threshold": "-1",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_cloud_threshold_non_integer_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "cloud_threshold": "abc",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_negative_days_before_after_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "days_before_after": "-1",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_days_before_after_non_integer_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "days_before_after": "abc",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_pre_fire_mosaic_strategy_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "pre_fire_mosaic_strategy": "invalid_strategy",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_post_fire_mosaic_strategy_returns_400(
        self, mock_process, mock_scientific
    ):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "post_fire_mosaic_strategy": "invalid_strategy",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_invalid_bg_color_returns_400(self, mock_process, mock_scientific):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
                "roi_only_bg_color": "red",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 400)

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_ee_no_band_returns_422_with_message(
        self, mock_process, mock_scientific
    ):
        import ee

        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        mock_process.side_effect = ee.EEException("No band named B4.")
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data["code"], "NO_SATELLITE_IMAGERY")
        self.assertIn("satellite imagery", data["error"])

    @patch("wildfire_assessment.views.process_scientific_deliverable.delay")
    @patch("wildfire_assessment.views.process_fire_assessment")
    def test_analyze_ee_other_error_still_raises(self, mock_process, mock_scientific):
        import ee

        UserCountry.objects.create(user=self.user, country=self.country)
        self.client.force_authenticate(user=self.user)
        mock_process.side_effect = ee.EEException("Some other GEE error.")
        query = urlencode(
            {
                "pre_fire_date": "2023-01-01",
                "post_fire_date": "2023-01-15",
            }
        )
        url = reverse("areaofinterest-analyze", args=[self.reserve.id])
        response = self.client.post(f"{url}?{query}")
        self.assertEqual(response.status_code, 500)

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

    @patch("wildfire_assessment.serializers.upload_polygon")
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
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
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
                    "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]],
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
            "wildfire_assessment.svc.area_of_interest.delete_polygon"
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
            "wildfire_assessment.svc.area_of_interest.delete_polygon"
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

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon")
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

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon")
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

    def test_me_delete_requires_authentication(self):
        response = self.client.delete(self.url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    @patch("wildfire_assessment.views.delete_user_account")
    def test_me_delete_removes_user(self, mock_delete):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_delete.assert_called_once_with(self.user)


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

    @override_settings(AI_ENABLED=False)
    def test_analysis_disabled_returns_503(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.json())

    @patch("wildfire_assessment.svc.object_storage.download_polygon")
    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_passes_polygon_geojson(self, mock_generate, mock_download):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter(["ok"]), {"response_id": None})
        mock_download.return_value = '{"type": "FeatureCollection"}'

        payload = {**self.valid_payload, "polygon_path": "some/polygon.geojson"}
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_download.assert_called_once_with("some/polygon.geojson")
        self.assertEqual(
            mock_generate.call_args.kwargs["polygon_geojson"],
            '{"type": "FeatureCollection"}',
        )

    @patch("wildfire_assessment.svc.object_storage.download_polygon")
    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_tolerates_polygon_download_failure(
        self, mock_generate, mock_download
    ):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter(["ok"]), {"response_id": None})
        mock_download.side_effect = Exception("boom")

        payload = {**self.valid_payload, "polygon_path": "missing.geojson"}
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_generate.call_args.kwargs["polygon_geojson"], "")

    @patch("wildfire_assessment.svc.object_storage.download_polygon")
    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_passes_user_question(self, mock_generate, mock_download):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter(["ok"]), {"response_id": None})
        mock_download.return_value = ""

        payload = {**self.valid_payload, "question": "Nearest town?"}
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            mock_generate.call_args.kwargs["user_question"], "Nearest town?"
        )

    @patch("wildfire_assessment.svc.object_storage.download_polygon")
    @patch("wildfire_assessment.views.generate_analysis_stream")
    def test_analysis_without_polygon_path_skips_download(
        self, mock_generate, mock_download
    ):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = (iter(["ok"]), {"response_id": None})

        response = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_download.assert_not_called()
        self.assertEqual(mock_generate.call_args.kwargs["polygon_geojson"], "")

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

    @override_settings(AI_ENABLED=False)
    def test_followup_disabled_returns_503(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.json())

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
        self.other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password"
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.5,
        )
        self.other_analysis = AnalysisRun.objects.create(
            user=self.other_user,
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

    def test_list_returns_only_own_analyses(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.analysis.id)
        # List uses lightweight serializer (no presigned URLs)
        self.assertNotIn("rgb_pre_fire_url", data["results"][0])
        self.assertNotIn("provenance", data["results"][0])

    def test_list_excludes_other_users_analyses(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-list")
        response = self.client.get(url)
        data = response.json()
        ids = [r["id"] for r in data["results"]]
        self.assertNotIn(self.other_analysis.id, ids)

    def test_retrieve_returns_own_analysis(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-detail", args=[self.analysis.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.analysis.id)
        self.assertEqual(data["area_name"], "Test Area")
        self.assertEqual(data["area_polygon_path"], "polygon.json")

    def test_retrieve_returns_404_for_other_users_analysis(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-detail", args=[self.other_analysis.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_paginates_at_10_per_page(self):
        for i in range(10):
            AnalysisRun.objects.create(
                user=self.user,
                area_of_interest=self.area,
                pre_fire_date="2024-03-01",
                post_fire_date="2024-03-15",
                total_burned_ha=10.0 + i,
            )
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 11)
        self.assertEqual(len(data["results"]), 10)
        self.assertIsNotNone(data["next"])

    def test_list_respects_page_size_query_param(self):
        for i in range(5):
            AnalysisRun.objects.create(
                user=self.user,
                area_of_interest=self.area,
                pre_fire_date="2024-03-01",
                post_fire_date="2024-03-15",
                total_burned_ha=10.0 + i,
            )
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-list")
        response = self.client.get(url, {"page_size": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 6)
        self.assertEqual(len(data["results"]), 3)


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


class DashboardCacheTests(APITestCase):
    """Tests for dashboard Redis caching and invalidation."""

    def setUp(self):
        cache.clear()
        self.country = Country.objects.create(name="Cache Country", code="CC")
        self.area = AreaOfInterest.objects.create(
            name="Cache Area",
            polygon_path="cache_polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="cacheuser", email="cache@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={
                "Total Area": {"area_ha": 500.0},
                "Total Burned Area": {"area_ha": 50.0},
            },
        )
        self.url = reverse("dashboard")

    def tearDown(self):
        cache.clear()

    def test_dashboard_cache_hit(self):
        """Second request returns cached data without re-computing."""
        self.client.force_authenticate(user=self.user)

        # First request populates cache
        response1 = self.client.get(self.url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        data1 = response1.json()

        # Verify cache is populated
        cache_key = f"dashboard_{self.user.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Modify DB behind the cache (add a new run)
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            severity_data={
                "Total Area": {"area_ha": 1000.0},
                "Total Burned Area": {"area_ha": 100.0},
            },
        )

        # Second request returns stale cached data (total_analyses still 1)
        response2 = self.client.get(self.url)
        data2 = response2.json()
        self.assertEqual(data2["total_analyses"], data1["total_analyses"])

    def test_dashboard_cache_invalidated_on_area_create(self):
        """Creating a new area clears the dashboard cache."""
        self.client.force_authenticate(user=self.user)

        # Populate cache
        self.client.get(self.url)
        cache_key = f"dashboard_{self.user.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Create a new area (triggers cache invalidation in serializer)
        geojson = {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-47.0, -15.0],
                        [-47.0, -14.9],
                        [-46.9, -14.9],
                        [-46.9, -15.0],
                        [-47.0, -15.0],
                    ]
                ],
            },
        }
        with patch("wildfire_assessment.serializers.upload_polygon"):
            create_url = reverse("areaofinterest-list")
            self.client.post(
                create_url,
                {
                    "name": "New Area",
                    "country": self.country.id,
                    "geojson": geojson,
                },
                format="json",
            )

        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))

    def test_dashboard_cache_invalidated_on_area_delete(self):
        """Deleting an area clears the dashboard cache."""
        self.client.force_authenticate(user=self.user)

        # Populate cache
        self.client.get(self.url)
        cache_key = f"dashboard_{self.user.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Delete the area (triggers cache invalidation in view)
        with patch("wildfire_assessment.svc.area_of_interest.delete_polygon"):
            delete_url = reverse("areaofinterest-detail", args=[self.area.id])
            self.client.delete(delete_url)

        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))

    def test_dashboard_cache_invalidated_on_analyze(self):
        """Running an analysis clears the dashboard cache."""
        self.client.force_authenticate(user=self.user)

        # Populate cache
        self.client.get(self.url)
        cache_key = f"dashboard_{self.user.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Run analysis (triggers cache invalidation in view)
        with (
            patch("wildfire_assessment.views.process_fire_assessment") as mock_process,
            patch("wildfire_assessment.views.save_analysis_run") as mock_save,
        ):
            mock_process.return_value = {"severity_map": "{}"}
            mock_save.return_value = AnalysisRun(id=999)
            analyze_url = reverse("areaofinterest-analyze", args=[self.area.id])
            self.client.post(
                f"{analyze_url}?pre_fire_date=2024-01-01&post_fire_date=2024-01-15"
            )

        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))

    def test_dashboard_cache_invalidated_on_area_update(self):
        """Updating an area clears the dashboard cache."""
        self.client.force_authenticate(user=self.user)

        # Populate cache
        self.client.get(self.url)
        cache_key = f"dashboard_{self.user.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Update area name (triggers cache invalidation in serializer)
        update_url = reverse("areaofinterest-detail", args=[self.area.id])
        self.client.patch(
            update_url,
            {"name": "Updated Name"},
            format="json",
        )

        # Cache should be cleared
        self.assertIsNone(cache.get(cache_key))

    def test_dashboard_cache_per_user(self):
        """Each user has their own cache entry."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="password"
        )

        # Populate cache for first user
        self.client.force_authenticate(user=self.user)
        self.client.get(self.url)

        # Populate cache for second user
        self.client.force_authenticate(user=other_user)
        self.client.get(self.url)

        # Both cache entries exist
        self.assertIsNotNone(cache.get(f"dashboard_{self.user.id}"))
        self.assertIsNotNone(cache.get(f"dashboard_{other_user.id}"))

        # Invalidating one doesn't affect the other
        from wildfire_assessment.svc.dashboard import invalidate_dashboard_cache

        invalidate_dashboard_cache(self.user.id)
        self.assertIsNone(cache.get(f"dashboard_{self.user.id}"))
        self.assertIsNotNone(cache.get(f"dashboard_{other_user.id}"))


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


class AnalysisRunValidateUrlsTests(APITestCase):
    """Tests for the validate_urls action on AnalysisRunViewSet."""

    def setUp(self):
        self.country = Country.objects.create(name="ValUrl Country", code="VU")
        self.area = AreaOfInterest.objects.create(
            name="ValUrl Area",
            polygon_path="polygon.json",
            country=self.country,
        )
        self.user = User.objects.create_user(
            username="valurluser",
            email="valurl@example.com",
            password="password",
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_url="https://storage.googleapis.com/bucket/dnbr.tif",
        )

    def test_validate_urls_requires_authentication(self):
        url = reverse("analysisrun-validate-urls", args=[self.analysis.id])
        response = self.client.post(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    @patch("wildfire_assessment.svc.area_of_interest.requests.head")
    def test_validate_urls_clears_expired(self, mock_head):
        mock_head.return_value = SimpleNamespace(status_code=404)
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-validate-urls", args=[self.analysis.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["scientific_dnbr_url"])

    @patch("wildfire_assessment.svc.area_of_interest.requests.head")
    def test_validate_urls_keeps_valid(self, mock_head):
        mock_head.return_value = SimpleNamespace(status_code=200)
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-validate-urls", args=[self.analysis.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["scientific_dnbr_url"],
            "https://storage.googleapis.com/bucket/dnbr.tif",
        )

    def test_validate_urls_returns_404_for_other_users_analysis(self):
        other_user = User.objects.create_user(
            username="other_val", email="other_val@example.com", password="password"
        )
        other_analysis = AnalysisRun.objects.create(
            user=other_user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-validate-urls", args=[other_analysis.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReportEndpointTests(APITestCase):
    """Tests for the POST /analysis_run/{id}/report/ endpoint."""

    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.area = AreaOfInterest.objects.create(
            name="Test Area", polygon_path="polygon.json", country=self.country
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.5,
            severity_data={"High": {"area_ha": 100.5, "percent": 100.0}},
        )

    def test_report_requires_authentication(self):
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_report_returns_cached_summary(self):
        self.analysis.report_summary = "# Cached Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["report_summary"], "# Cached Report")

    def test_report_regenerates_on_language_mismatch(self):
        self.analysis.report_summary = "# English Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        with patch("wildfire_assessment.views.generate_report_summary") as mock_gen:
            mock_gen.return_value = "# Relatório em Português"
            response = self.client.post(url, {"language": "pt-BR"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_gen.assert_called_once()
            self.assertEqual(
                response.json()["report_summary"], "# Relatório em Português"
            )

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_generates_fresh_summary(self, mock_gen):
        mock_gen.return_value = "# Fresh Report"

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["report_summary"], "# Fresh Report")
        mock_gen.assert_called_once()

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_regenerate_forces_new_generation(self, mock_gen):
        self.analysis.report_summary = "# Old Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        mock_gen.return_value = "# New Report"

        self.client.force_authenticate(user=self.user)
        url = (
            reverse("analysisrun-report", args=[self.analysis.id]) + "?regenerate=true"
        )
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["report_summary"], "# New Report")
        mock_gen.assert_called_once()

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_preserves_old_on_failure(self, mock_gen):
        self.analysis.report_summary = "# Old Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        mock_gen.side_effect = Exception("AI provider error")

        self.client.force_authenticate(user=self.user)
        url = (
            reverse("analysisrun-report", args=[self.analysis.id]) + "?regenerate=true"
        )
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.report_summary, "# Old Report")

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_returns_502_on_empty_response(self, mock_gen):
        mock_gen.return_value = ""

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_report_returns_404_for_other_users_analysis(self):
        other_user = User.objects.create_user(
            username="other_rpt", email="other_rpt@example.com", password="password"
        )
        other_analysis = AnalysisRun.objects.create(
            user=other_user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[other_analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
