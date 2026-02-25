import importlib
import json
from unittest.mock import patch

import wildfire_assessment.admin as admin_module
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from wildfire_assessment.admin import (
    AIProviderAdmin,
    AnalysisRunAdmin,
    AreaOfInterestAdminForm,
    NotificationAdmin,
)
from wildfire_assessment.models import (
    AIProvider,
    AnalysisRun,
    AreaOfInterest,
    Country,
    Notification,
)


class AdminTests(TestCase):
    def test_unregister_user_not_registered(self):
        User = get_user_model()
        for model in (User, Country, AreaOfInterest, AnalysisRun, Notification, AIProvider):
            if admin.site.is_registered(model):
                admin.site.unregister(model)

        importlib.reload(admin_module)

        for model in (User, Country, AreaOfInterest, AnalysisRun, Notification, AIProvider):
            self.assertTrue(admin.site.is_registered(model))


class AreaOfInterestAdminFormTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="Admin Country", code="AC")

    @patch("wildfire_assessment.admin.upload_polygon_to_s3")
    def test_form_save_with_geojson_file(self, mock_upload):
        geojson_content = b'{"type": "Polygon", "coordinates": []}'
        uploaded_file = SimpleUploadedFile(
            "test.geojson", geojson_content, content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            data={"name": "Admin Area", "country": self.country.id},
            files={"geojson_file": uploaded_file},
        )
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertTrue(instance.polygon_path.endswith(".geojson"))
        mock_upload.assert_called_once()

    def test_form_save_without_geojson_file(self):
        area = AreaOfInterest.objects.create(
            name="No File Area",
            polygon_path="existing.geojson",
            country=self.country,
        )
        form = AreaOfInterestAdminForm(
            instance=area,
            data={"name": "No File Area", "country": self.country.id},
        )
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEqual(instance.polygon_path, "existing.geojson")

    @patch("wildfire_assessment.admin.delete_polygon_from_s3")
    @patch("wildfire_assessment.admin.upload_polygon_to_s3")
    def test_form_save_replaces_existing_polygon(self, mock_upload, mock_delete):
        area = AreaOfInterest.objects.create(
            name="Replace Area",
            polygon_path="old.geojson",
            country=self.country,
        )
        geojson_content = b'{"type": "Polygon", "coordinates": []}'
        uploaded_file = SimpleUploadedFile(
            "new.geojson", geojson_content, content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            instance=area,
            data={
                "name": "Replace Area",
                "country": self.country.id,
                "polygon_path": "old.geojson",
            },
            files={"geojson_file": uploaded_file},
        )
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        mock_delete.assert_called_once_with("old.geojson")
        mock_upload.assert_called_once()
        self.assertNotEqual(instance.polygon_path, "old.geojson")


class AnalyticsDashboardViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="superadmin", password="pw", email="super@example.com"
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            password="pw",
            email="regular@example.com",
            is_staff=True,
        )
        self.url = reverse("admin-analytics")

    def test_superuser_can_access_dashboard(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Dashboard")
        self.assertContains(response, "dailyRunsChart")

    def test_non_superuser_gets_forbidden(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_gets_redirect(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class UserActivityReportViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="activityadmin", password="pw", email="activity@example.com"
        )
        self.regular_user = User.objects.create_user(
            username="activityreg",
            password="pw",
            email="activityreg@example.com",
            is_staff=True,
        )
        self.country = Country.objects.create(name="Activity Country", code="AT")
        self.area = AreaOfInterest.objects.create(
            name="Activity Area", polygon_path="act.geojson", country=self.country
        )
        self.url = reverse("admin-user-activity")

    def test_superuser_can_access_report(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User Activity Report")

    def test_non_superuser_gets_forbidden(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_gets_redirect(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_default_date_range_is_90_days(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("start_date", response.context)
        self.assertIn("end_date", response.context)

    def test_custom_date_range(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["start_date"], "2024-01-01")
        self.assertEqual(response.context["end_date"], "2024-12-31")

    def test_invalid_dates_fallback_to_defaults(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            self.url, {"start_date": "bad", "end_date": "invalid"}
        )
        self.assertEqual(response.status_code, 200)
        # Should not crash, falls back to defaults

    def test_shows_user_analysis_counts(self):
        AnalysisRun.objects.create(
            user=self.superuser,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "activity@example.com")

    def test_empty_results(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            self.url, {"start_date": "2020-01-01", "end_date": "2020-01-02"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No analyses found")


class AnalysisRunAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="runadmin", password="pw", email="runadmin@example.com"
        )
        self.country = Country.objects.create(name="Run Country", code="RC")
        self.area = AreaOfInterest.objects.create(
            name="Run Area", polygon_path="r.geojson", country=self.country
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.superuser,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            rgb_pre_fire_image="abc123/pre_fire_rgb.jpg",
            rgb_post_fire_image="abc123/post_fire_rgb.jpg",
            dndvi_image="abc123/dndvi.jpg",
        )

    @patch("wildfire_assessment.admin.get_presigned_image_url")
    def test_image_previews_renders_images(self, mock_presign):
        mock_presign.side_effect = lambda key: f"https://s3.example.com/{key}"
        admin_instance = AnalysisRunAdmin(AnalysisRun, admin.site)
        html = str(admin_instance.image_previews(self.analysis))
        self.assertIn("https://s3.example.com/abc123/pre_fire_rgb.jpg", html)
        self.assertIn("https://s3.example.com/abc123/post_fire_rgb.jpg", html)
        self.assertIn("Pre-fire RGB", html)
        self.assertNotIn("dNBR", html)
        self.assertNotIn("RBR", html)

    def test_image_previews_no_images(self):
        from wildfire_assessment.admin import AnalysisRunAdmin

        analysis_empty = AnalysisRun.objects.create(
            user=self.superuser,
            area_of_interest=self.area,
            pre_fire_date="2024-03-01",
            post_fire_date="2024-03-15",
        )
        admin_instance = AnalysisRunAdmin(AnalysisRun, admin.site)
        html = str(admin_instance.image_previews(analysis_empty))
        self.assertIn("No images available", html)

    def test_has_add_permission_returns_false(self):
        admin_instance = AnalysisRunAdmin(AnalysisRun, admin.site)
        request = RequestFactory().get("/")
        self.assertFalse(admin_instance.has_add_permission(request))

    def test_has_change_permission_returns_false(self):
        admin_instance = AnalysisRunAdmin(AnalysisRun, admin.site)
        request = RequestFactory().get("/")
        self.assertFalse(admin_instance.has_change_permission(request))
        self.assertFalse(
            admin_instance.has_change_permission(request, obj=self.analysis)
        )

    def test_has_delete_permission_returns_false(self):
        admin_instance = AnalysisRunAdmin(AnalysisRun, admin.site)
        request = RequestFactory().get("/")
        self.assertFalse(admin_instance.has_delete_permission(request))
        self.assertFalse(
            admin_instance.has_delete_permission(request, obj=self.analysis)
        )


class AreaOfInterestAdminFormValidationTests(TestCase):
    """Tests for admin form GeoJSON validation and duplicate detection."""

    def setUp(self):
        self.country = Country.objects.create(name="Val Country", code="VC")

    def test_clean_geojson_file_invalid_json(self):
        uploaded_file = SimpleUploadedFile(
            "bad.geojson", b"not valid json", content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            data={"name": "Test Area", "country": self.country.id},
            files={"geojson_file": uploaded_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("geojson_file", form.errors)
        self.assertIn("Invalid JSON", form.errors["geojson_file"][0])

    def test_clean_geojson_file_feature_unsupported_geometry(self):
        geojson = b'{"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {}}'
        uploaded_file = SimpleUploadedFile(
            "point.geojson", geojson, content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            data={"name": "Test Area", "country": self.country.id},
            files={"geojson_file": uploaded_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("geojson_file", form.errors)
        self.assertIn("Unsupported geometry type", form.errors["geojson_file"][0])

    def test_clean_geojson_file_featurecollection_unsupported_geometry(self):
        geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[0, 0], [1, 1]],
                        },
                        "properties": {},
                    }
                ],
            }
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile(
            "lines.geojson", geojson, content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            data={"name": "Test Area", "country": self.country.id},
            files={"geojson_file": uploaded_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("geojson_file", form.errors)
        self.assertIn("Feature[0]", form.errors["geojson_file"][0])

    def test_clean_geojson_file_unsupported_top_level_type(self):
        geojson = b'{"type": "Point", "coordinates": [0, 0]}'
        uploaded_file = SimpleUploadedFile(
            "point.geojson", geojson, content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            data={"name": "Test Area", "country": self.country.id},
            files={"geojson_file": uploaded_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("geojson_file", form.errors)
        self.assertIn("Unsupported GeoJSON type", form.errors["geojson_file"][0])

    def test_clean_duplicate_name_in_same_country(self):
        AreaOfInterest.objects.create(
            name="Duplicate Area", polygon_path="dup.geojson", country=self.country
        )
        form = AreaOfInterestAdminForm(
            data={"name": "Duplicate Area", "country": self.country.id},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("already exists", str(form.errors))

    def test_clean_duplicate_name_allowed_for_same_instance(self):
        area = AreaOfInterest.objects.create(
            name="Existing Area", polygon_path="exist.geojson", country=self.country
        )
        form = AreaOfInterestAdminForm(
            instance=area,
            data={"name": "Existing Area", "country": self.country.id},
        )
        self.assertTrue(form.is_valid(), form.errors)

    @patch("wildfire_assessment.admin.upload_polygon_to_s3")
    def test_clean_geojson_file_valid_feature_collection(self, _mock_upload):
        geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
                        },
                        "properties": {},
                    }
                ],
            }
        ).encode("utf-8")
        uploaded_file = SimpleUploadedFile(
            "fc.geojson", geojson, content_type="application/json"
        )
        form = AreaOfInterestAdminForm(
            data={"name": "FC Area", "country": self.country.id},
            files={"geojson_file": uploaded_file},
        )
        self.assertTrue(form.is_valid(), form.errors)


class NotificationAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="notifadmin", email="notifadmin@example.com", password="pw"
        )
        self.country = Country.objects.create(name="NA Country", code="NA")
        self.area = AreaOfInterest.objects.create(
            name="NA Area", polygon_path="na.geojson", country=self.country
        )
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            analysis_run=self.analysis,
            notification_type="deliverable_ready",
            deliverable_name="DNBR",
            message="Test notification",
        )

    def test_notification_admin_registered(self):
        self.assertTrue(admin.site.is_registered(Notification))

    def test_notification_admin_list_display(self):
        admin_instance = NotificationAdmin(Notification, admin.site)
        self.assertIn("user", admin_instance.list_display)
        self.assertIn("notification_type", admin_instance.list_display)
        self.assertIn("is_read", admin_instance.list_display)
        self.assertIn("created_at", admin_instance.list_display)

    def test_notification_admin_list_filter(self):
        admin_instance = NotificationAdmin(Notification, admin.site)
        self.assertIn("is_read", admin_instance.list_filter)
        self.assertIn("notification_type", admin_instance.list_filter)

    def test_notification_admin_readonly_fields(self):
        admin_instance = NotificationAdmin(Notification, admin.site)
        self.assertIn("user", admin_instance.readonly_fields)
        self.assertIn("message", admin_instance.readonly_fields)
        self.assertIn("created_at", admin_instance.readonly_fields)


class AIProviderAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username="provideradmin", password="pw", email="prov@example.com"
        )
        self.factory = RequestFactory()

    def test_save_model_clears_cache(self):
        cache.set("active_ai_provider", "cached_value")
        admin_instance = AIProviderAdmin(AIProvider, admin.site)
        provider = AIProvider.load()
        request = self.factory.post("/admin/")
        request.user = self.superuser

        admin_instance.save_model(request, provider, form=None, change=True)

        self.assertIsNone(cache.get("active_ai_provider"))

    def test_has_add_permission_returns_false(self):
        admin_instance = AIProviderAdmin(AIProvider, admin.site)
        request = self.factory.get("/admin/")
        self.assertFalse(admin_instance.has_add_permission(request))

    def test_has_delete_permission_returns_false(self):
        admin_instance = AIProviderAdmin(AIProvider, admin.site)
        request = self.factory.get("/admin/")
        self.assertFalse(admin_instance.has_delete_permission(request))

    def test_changelist_view_redirects_to_change(self):
        admin_instance = AIProviderAdmin(AIProvider, admin.site)
        request = self.factory.get("/admin/wildfire_assessment/aiprovider/")
        request.user = self.superuser
        response = admin_instance.changelist_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/1/change/", response.url)
