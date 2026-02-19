"""Tests for the Gemini analysis service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from wildfire_assessment.svc.ai_analysis import (
    _build_image_content,
    _get_instructions,
    _parse_data_url,
    build_analysis_prompt,
    generate_analysis_stream,
    generate_followup_stream,
    get_gemini_model,
)


class GeminiAnalysisTests(TestCase):
    """Tests for the Gemini analysis functions."""

    def setUp(self):
        self.pre_fire_date = "2024-01-01"
        self.post_fire_date = "2024-01-15"
        self.area_of_interest = "Test Reserve"
        self.severity_distribution = {
            "Unburned": {"area_ha": 100.0, "percent": 50.0},
            "Low": {"area_ha": 50.0, "percent": 25.0},
            "Moderate": {"area_ha": 30.0, "percent": 15.0},
            "High": {"area_ha": 20.0, "percent": 10.0},
        }

    def test_build_analysis_prompt_contains_all_parameters(self):
        prompt = build_analysis_prompt(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )

        self.assertIn(self.pre_fire_date, prompt)
        self.assertIn(self.post_fire_date, prompt)
        self.assertIn(self.area_of_interest, prompt)
        self.assertIn("Unburned", prompt)
        self.assertIn("100.0 ha", prompt)
        self.assertIn("50.0%", prompt)

    def test_build_analysis_prompt_handles_simple_severity_values(self):
        simple_severity = {
            "Unburned": "100 ha",
            "Low": "50 ha",
        }
        prompt = build_analysis_prompt(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=simple_severity,
        )

        self.assertIn("Unburned: 100 ha", prompt)
        self.assertIn("Low: 50 ha", prompt)

    def test_build_analysis_prompt_uses_fallback_keys(self):
        severity = {
            "High": {"area": 40.0, "percentage": 20.0},
        }
        prompt = build_analysis_prompt(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=severity,
        )
        self.assertIn("40.0 ha", prompt)
        self.assertIn("20.0%", prompt)

    def test_get_gemini_model_raises_without_api_key(self):
        with patch("wildfire_assessment.svc.ai_analysis.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            with self.assertRaises(ValueError) as context:
                get_gemini_model()
            self.assertIn("GEMINI_API_KEY", str(context.exception))

    @patch("wildfire_assessment.svc.ai_analysis.settings")
    @patch("wildfire_assessment.svc.ai_analysis.genai")
    def test_get_gemini_model_returns_model(self, mock_genai, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-key"
        model = get_gemini_model("gemini-2.0-flash", "en")
        mock_genai.configure.assert_called_once_with(api_key="test-key")
        mock_genai.GenerativeModel.assert_called_once()
        self.assertEqual(model, mock_genai.GenerativeModel.return_value)

    def test_get_instructions_defaults_to_english(self):
        result = _get_instructions()
        self.assertIn("English", result)

    def test_get_instructions_with_known_language(self):
        result = _get_instructions("pt-BR")
        self.assertIn("Brazilian Portuguese", result)

    def test_get_instructions_with_unknown_language_falls_back(self):
        result = _get_instructions("de")
        self.assertIn("English", result)

    def test_get_instructions_with_none(self):
        result = _get_instructions(None)
        self.assertIn("English", result)

    def test_parse_data_url_valid(self):
        data_url = "data:image/png;base64,aWJvcg=="
        result = _parse_data_url(data_url)
        self.assertEqual(result["inline_data"]["mime_type"], "image/png")
        self.assertEqual(result["inline_data"]["data"], "aWJvcg==")

    def test_parse_data_url_invalid(self):
        self.assertIsNone(_parse_data_url("not-a-data-url"))

    def test_build_image_content_with_none(self):
        self.assertEqual(_build_image_content(None), [])

    def test_build_image_content_with_empty_list(self):
        self.assertEqual(_build_image_content([]), [])

    def test_build_image_content_skips_missing_url(self):
        result = _build_image_content([{"label": "test"}])
        self.assertEqual(result, [])

    def test_build_image_content_skips_empty_url(self):
        result = _build_image_content([{"url": "", "label": "test"}])
        self.assertEqual(result, [])

    def test_build_image_content_without_label(self):
        result = _build_image_content([{"url": "data:image/png;base64,abc"}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["inline_data"]["mime_type"], "image/png")

    def test_build_image_content_with_label(self):
        result = _build_image_content(
            [{"url": "data:image/png;base64,abc", "label": "dNBR"}]
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "Image: dNBR")
        self.assertEqual(result[1]["inline_data"]["mime_type"], "image/png")

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    @patch("wildfire_assessment.svc.ai_analysis.get_gemini_model")
    def test_generate_analysis_stream_yields_chunks(self, mock_get_model, mock_cache):
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "World"

        mock_model.generate_content.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello ", "World"])
        self.assertIsNotNone(holder["response_id"])
        mock_model.generate_content.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    @patch("wildfire_assessment.svc.ai_analysis.get_gemini_model")
    def test_generate_analysis_stream_uses_correct_model(
        self, mock_get_model, mock_cache
    ):
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.generate_content.return_value = []

        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
            model="gemini-1.5-pro",
            language="fr",
        )
        list(stream)

        mock_get_model.assert_called_once_with("gemini-1.5-pro", "fr")

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    @patch("wildfire_assessment.svc.ai_analysis.get_gemini_model")
    def test_generate_analysis_stream_with_images(self, mock_get_model, mock_cache):
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.generate_content.return_value = []

        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
            image_urls=[{"url": "data:image/png;base64,abc", "label": "RGB"}],
        )
        list(stream)

        call_args = mock_model.generate_content.call_args
        contents = call_args[0][0]
        # Should have: prompt text, "Image: RGB" label, inline_data dict
        self.assertTrue(len(contents) >= 3)

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    @patch("wildfire_assessment.svc.ai_analysis.get_gemini_model")
    def test_generate_followup_stream_yields_chunks(
        self, mock_get_model, mock_cache
    ):
        mock_cache.get.return_value = {
            "history": [
                {"role": "user", "parts": ["initial prompt"]},
                {"role": "model", "parts": ["initial response"]},
            ],
            "model": "gemini-2.0-flash",
            "language": "en",
        }

        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_chat = MagicMock()
        mock_model.start_chat.return_value = mock_chat

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Follow "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "up"
        mock_chat.send_message.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = generate_followup_stream(
            previous_response_id="conv_123",
            question="What about recovery?",
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Follow ", "up"])
        self.assertIsNotNone(holder["response_id"])
        mock_cache.get.assert_called_once_with("ai_chat_conv_123")
        mock_chat.send_message.assert_called_once_with(
            "What about recovery?", stream=True
        )

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    def test_generate_followup_stream_raises_on_missing_conversation(self, mock_cache):
        mock_cache.get.return_value = None

        with self.assertRaises(ValueError) as context:
            generate_followup_stream(
                previous_response_id="invalid_id",
                question="test",
            )
        self.assertIn("not found", str(context.exception))

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    @patch("wildfire_assessment.svc.ai_analysis.get_gemini_model")
    def test_generate_followup_stream_uses_language_and_model(
        self, mock_get_model, mock_cache
    ):
        mock_cache.get.return_value = {
            "history": [],
            "model": "gemini-2.0-flash",
            "language": "en",
        }
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_chat = MagicMock()
        mock_model.start_chat.return_value = mock_chat
        mock_chat.send_message.return_value = []

        stream, holder = generate_followup_stream(
            previous_response_id="conv_123",
            question="Details?",
            language="pt-BR",
            model="gemini-1.5-pro",
        )
        list(stream)

        mock_get_model.assert_called_once_with("gemini-2.0-flash", "pt-BR")

    @patch("wildfire_assessment.svc.ai_analysis.cache")
    @patch("wildfire_assessment.svc.ai_analysis.get_gemini_model")
    def test_generate_analysis_stream_skips_empty_chunks(
        self, mock_get_model, mock_cache
    ):
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello"
        mock_chunk2 = MagicMock()
        mock_chunk2.text = None  # empty chunk

        mock_model.generate_content.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello"])
