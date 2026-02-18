from django.test import TestCase
from wildfire_assessment.translations import EMAIL_TRANSLATIONS, get_email_translation


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
