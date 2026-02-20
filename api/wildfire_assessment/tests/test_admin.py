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
