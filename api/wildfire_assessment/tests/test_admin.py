import importlib
from unittest.mock import patch

import wildfire_assessment.admin as admin_module
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from wildfire_assessment.admin import AreaOfInterestAdminForm
from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country


class AdminTests(TestCase):
    def test_unregister_user_not_registered(self):
        User = get_user_model()
        for model in (User, Country, AreaOfInterest, AnalysisRun):
            if admin.site.is_registered(model):
                admin.site.unregister(model)

        importlib.reload(admin_module)

        for model in (User, Country, AreaOfInterest, AnalysisRun):
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
            username="regular", password="pw", email="regular@example.com",
            is_staff=True,
        )
        self.url = reverse("admin-analytics")

    def test_superuser_can_access_dashboard(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Dashboard")

    def test_non_superuser_gets_forbidden(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_gets_redirect(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


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

    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    def test_image_previews_renders_images(self, mock_presign):
        mock_presign.side_effect = lambda key: f"https://s3.example.com/{key}"
        from wildfire_assessment.admin import AnalysisRunAdmin

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
