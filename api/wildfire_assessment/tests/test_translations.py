from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from wildfire_assessment.models import UserProfile
from wildfire_assessment.translations import (
    EMAIL_TRANSLATIONS,
    ERROR_TRANSLATIONS,
    get_email_translation,
    get_error_translation,
    get_user_language,
)


class EmailTranslationsTestCase(TestCase):
    """Tests for email translation functionality."""

    def test_get_email_translation_english(self):
        """Test getting English translations."""
        subject = get_email_translation("en", "email.subject")
        self.assertEqual(subject, "Wildfire Analyser - Scientific Deliverable Ready")

        body = get_email_translation("en", "email.body")
        self.assertIn("{reserve_name}", body)
        self.assertIn("{url}", body)

    def test_get_email_translation_portuguese(self):
        """Test getting Portuguese translations."""
        subject = get_email_translation("pt-BR", "email.subject")
        self.assertEqual(subject, "Wildfire Analyser - Produto Científico Pronto")

        body = get_email_translation("pt-BR", "email.body")
        self.assertIn("{reserve_name}", body)
        self.assertIn("{url}", body)

    def test_get_email_translation_french(self):
        """Test getting French translations."""
        subject = get_email_translation("fr", "email.subject")
        self.assertEqual(subject, "Wildfire Analyser - Livrable Scientifique Prêt")

        body = get_email_translation("fr", "email.body")
        self.assertIn("{reserve_name}", body)
        self.assertIn("{url}", body)

    def test_get_email_translation_spanish(self):
        """Test getting Spanish translations."""
        subject = get_email_translation("es-ES", "email.subject")
        self.assertEqual(subject, "Wildfire Analyser - Producto Científico Listo")

        body = get_email_translation("es-ES", "email.body")
        self.assertIn("{reserve_name}", body)
        self.assertIn("{url}", body)

    def test_get_email_translation_fallback_to_english(self):
        """Test that unknown languages fall back to English."""
        subject = get_email_translation("de", "email.subject")
        self.assertEqual(subject, "Wildfire Analyser - Scientific Deliverable Ready")

    def test_get_email_translation_unknown_key_returns_key(self):
        """Test that unknown keys return the key itself."""
        result = get_email_translation("en", "unknown.key")
        self.assertEqual(result, "unknown.key")

    def test_all_languages_have_same_keys(self):
        """Test that all languages have the same translation keys."""
        english_keys = set(EMAIL_TRANSLATIONS["en"].keys())

        for lang, translations in EMAIL_TRANSLATIONS.items():
            self.assertEqual(
                set(translations.keys()),
                english_keys,
                f"Language '{lang}' has different keys than English",
            )

    def test_body_format_placeholders(self):
        """Test that body translations can be formatted with placeholders."""
        for lang in EMAIL_TRANSLATIONS:
            body = get_email_translation(lang, "email.body")
            formatted = body.format(
                reserve_name="Test Reserve",
                url="https://example.com/download",
            )
            self.assertIn("Test Reserve", formatted)
            self.assertIn("https://example.com/download", formatted)


class ErrorTranslationsTestCase(TestCase):
    """Tests for API error translation functionality."""

    def test_get_error_translation_english(self):
        msg = get_error_translation("en", "error.duplicate_name")
        self.assertIn("already exists", msg)

    def test_get_error_translation_portuguese(self):
        msg = get_error_translation("pt-BR", "error.duplicate_name")
        self.assertIn("Já existe", msg)

    def test_get_error_translation_french(self):
        msg = get_error_translation("fr", "error.duplicate_name")
        self.assertIn("existe déjà", msg)

    def test_get_error_translation_spanish(self):
        msg = get_error_translation("es-ES", "error.duplicate_name")
        self.assertIn("Ya existe", msg)

    def test_get_error_translation_fallback(self):
        msg = get_error_translation("de", "error.duplicate_name")
        self.assertIn("already exists", msg)

    def test_get_error_translation_unknown_key(self):
        result = get_error_translation("en", "error.unknown_key")
        self.assertEqual(result, "error.unknown_key")

    def test_get_error_translation_with_kwargs(self):
        msg = get_error_translation(
            "en", "error.unsupported_geometry", geom_type="LineString"
        )
        self.assertIn("LineString", msg)

    def test_all_error_languages_have_same_keys(self):
        english_keys = set(ERROR_TRANSLATIONS["en"].keys())
        for lang, translations in ERROR_TRANSLATIONS.items():
            self.assertEqual(
                set(translations.keys()),
                english_keys,
                f"Language '{lang}' has different error keys than English",
            )

    def test_get_user_language_with_profile(self):
        user = User.objects.create_user(username="lang_test", password="pw")
        user.profile.default_language = "pt-BR"
        user.profile.save()
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        self.assertEqual(get_user_language(request), "pt-BR")

    def test_get_user_language_no_profile(self):
        user = User.objects.create_user(username="lang_test2", password="pw")
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        self.assertEqual(get_user_language(request), "en")

    def test_get_user_language_no_request(self):
        self.assertEqual(get_user_language(None), "en")
