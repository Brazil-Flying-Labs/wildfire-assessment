from django.contrib.auth import get_user_model
from django.test import TestCase
from wildfire_assessment.models import (
    AIProvider,
    AnalysisRun,
    AreaOfInterest,
    Country,
    Notification,
    UserCountry,
    UserProfile,
)


class CountryModelTests(TestCase):
    def test_str_representation(self):
        country = Country.objects.create(name="Chile", code="CL")
        self.assertEqual(str(country), "CL - Chile")

    def test_user_country_str(self):
        user = get_user_model().objects.create(username="tester")
        country = Country.objects.create(name="Peru", code="PE")
        user_country = UserCountry.objects.create(user=user, country=country)
        self.assertEqual(str(user_country), "tester - PE")


class UserProfileModelTests(TestCase):
    def test_str_representation(self):
        user = get_user_model().objects.create(username="profileuser")
        profile = user.profile
        self.assertEqual(str(profile), "profileuser - en")

    def test_default_language_is_english(self):
        user = get_user_model().objects.create(username="languser")
        profile = user.profile
        self.assertEqual(profile.default_language, "en")

    def test_profile_auto_created_on_user_creation(self):
        user = get_user_model().objects.create(username="newuser")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_profile_not_duplicated_on_user_save(self):
        user = get_user_model().objects.create(username="dupecheck")
        user.first_name = "Updated"
        user.save()
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)

    def test_update_language(self):
        user = get_user_model().objects.create(username="updatelang")
        profile = user.profile
        profile.default_language = "pt-BR"
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.default_language, "pt-BR")


class AIProviderModelTests(TestCase):
    def test_save_enforces_singleton(self):
        provider = AIProvider(provider="openai", model_name="gpt-4o-mini")
        provider.save()
        self.assertEqual(provider.pk, 1)

        provider2 = AIProvider(pk=99, provider="gemini", model_name="gemini-2.0-flash-lite")
        provider2.save()
        self.assertEqual(provider2.pk, 1)
        self.assertEqual(AIProvider.objects.count(), 1)

    def test_str_representation(self):
        provider = AIProvider.load()
        result = str(provider)
        self.assertIn("Gemini", result)
        self.assertIn("gemini-2.0-flash-lite", result)

    def test_load_creates_default(self):
        AIProvider.objects.all().delete()
        provider = AIProvider.load()
        self.assertEqual(provider.pk, 1)
        self.assertEqual(provider.provider, "gemini")


class AnalysisRunModelTests(TestCase):
    def test_str_representation(self):
        user = get_user_model().objects.create(username="analyst")
        country = Country.objects.create(name="TestAnalysis Country", code="TA")
        area = AreaOfInterest.objects.create(
            name="Amazon Reserve",
            polygon_path="amazon.geojson",
            country=country,
        )
        analysis = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        self.assertEqual(str(analysis), "Amazon Reserve - 2024-01-01 to 2024-01-15")


class NotificationModelTests(TestCase):
    def test_str_representation(self):
        user = get_user_model().objects.create(username="notifuser")
        country = Country.objects.create(name="Notif Country", code="NC")
        area = AreaOfInterest.objects.create(
            name="Notif Area", polygon_path="notif.geojson", country=country
        )
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        notification = Notification.objects.create(
            user=user,
            analysis_run=run,
            notification_type="deliverable_ready",
            message="Test",
        )
        self.assertEqual(
            str(notification), "Notification for notifuser - deliverable_ready"
        )


class AIProviderModelTests(TestCase):
    def test_str_representation(self):
        provider = AIProvider.load()
        self.assertEqual(str(provider), "Google Gemini — gemini-2.0-flash-lite")

    def test_save_enforces_singleton(self):
        provider = AIProvider(provider="openai", model_name="gpt-4o-mini")
        provider.save()
        self.assertEqual(provider.pk, 1)
        self.assertEqual(AIProvider.objects.count(), 1)

    def test_load_creates_default(self):
        AIProvider.objects.all().delete()
        provider = AIProvider.load()
        self.assertEqual(provider.pk, 1)
        self.assertEqual(provider.provider, "gemini")
