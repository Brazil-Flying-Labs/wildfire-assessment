"""Tests for the AI analysis service (provider dispatch + Gemini + OpenAI + DeepSeek)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from wildfire_assessment.svc.ai_common import (
    PROVIDER_DISPLAY,
    _get_instructions,
    _get_report_instructions,
    build_analysis_prompt,
    build_report_prompt,
    generate_analysis_stream,
    generate_followup_stream,
    generate_report_summary,
    get_active_provider,
)
from wildfire_assessment.svc.gemini_analysis import (
    _build_image_content,
    _gemini_generate_analysis_stream,
    _gemini_generate_followup_stream,
    _get_gemini_client,
    _parse_data_url,
)
from wildfire_assessment.svc.openai_analysis import (
    _build_user_content,
    _get_openai_client,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_analysis_stream as openai_generate_analysis_stream,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_followup_stream as openai_generate_followup_stream,
)


class SharedHelperTests(TestCase):
    """Tests for shared helper functions."""

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

    def test_build_analysis_prompt_text_only_has_no_imagery_reference(self):
        prompt = build_analysis_prompt(
            self.pre_fire_date,
            self.post_fire_date,
            self.area_of_interest,
            self.severity_distribution,
            include_images=False,
        )
        self.assertNotIn("attached", prompt)
        self.assertNotIn("visual patterns", prompt)
        self.assertIn("No imagery is provided", prompt)
        self.assertIn("numerical severity data", prompt)

    def test_build_analysis_prompt_include_images_default(self):
        prompt = build_analysis_prompt(
            self.pre_fire_date,
            self.post_fire_date,
            self.area_of_interest,
            self.severity_distribution,
        )
        self.assertIn("Satellite imagery is attached", prompt)

    def test_build_report_prompt_text_only_has_no_imagery_reference(self):
        run = MagicMock()
        run.area_of_interest.name = "Test Reserve"
        run.area_of_interest.country.name = "Brazil"
        run.pre_fire_date = self.pre_fire_date
        run.post_fire_date = self.post_fire_date
        run.total_burned_ha = 250.0
        run.severity_data = self.severity_distribution

        prompt = build_report_prompt(run, include_images=False)
        self.assertNotIn("attached", prompt)
        self.assertIn("No imagery is provided", prompt)
        self.assertIn("Test Reserve", prompt)

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
        self.assertIsNotNone(result)
        self.assertEqual(result.inline_data.mime_type, "image/png")
        self.assertEqual(result.inline_data.data, b"ibor")

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
        result = _build_image_content([{"url": "data:image/png;base64,dGVzdA=="}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].inline_data.mime_type, "image/png")

    def test_build_image_content_with_label(self):
        result = _build_image_content(
            [{"url": "data:image/png;base64,dGVzdA==", "label": "dNBR"}]
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "Image: dNBR")
        self.assertEqual(result[1].inline_data.mime_type, "image/png")

    def test_provider_display_map(self):
        self.assertEqual(PROVIDER_DISPLAY["gemini"], "Google Gemini")
        self.assertEqual(PROVIDER_DISPLAY["openai"], "OpenAI")
        self.assertEqual(PROVIDER_DISPLAY["deepseek"], "DeepSeek")

    def test_get_instructions_spanish(self):
        result = _get_instructions("es-ES")
        self.assertIn("Spanish", result)

    def test_get_report_instructions_defaults_to_english(self):
        result = _get_report_instructions()
        self.assertIn("English", result)
        self.assertIn("remote sensing scientist", result)

    def test_get_report_instructions_with_language(self):
        result = _get_report_instructions("pt-BR")
        self.assertIn("Brazilian Portuguese", result)

    def test_get_report_instructions_with_spanish(self):
        result = _get_report_instructions("es-ES")
        self.assertIn("Spanish", result)

    def test_build_report_prompt_contains_metadata(self):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil RPT", code="BT")
        area = AreaOfInterest.objects.create(
            name="Serra da Canastra", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="t", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=500.0,
            severity_data={
                "Unburned": {"area_ha": 100.0, "percent": 20.0},
                "High": {"area_ha": 400.0, "percent": 80.0},
            },
        )
        prompt = build_report_prompt(run)
        self.assertIn("Serra da Canastra", prompt)
        self.assertIn("Brazil", prompt)
        self.assertIn("2024-06-01", prompt)
        self.assertIn("500.0", prompt)
        self.assertIn("High", prompt)
        self.assertIn("80.0", prompt)

    def test_build_report_prompt_handles_empty_severity_data(self):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="TestC", code="TC")
        area = AreaOfInterest.objects.create(
            name="Empty Area", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="t2", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=0.0,
            severity_data={},
        )
        prompt = build_report_prompt(run)
        self.assertIn("Empty Area", prompt)

    def test_build_report_prompt_handles_none_severity_data(self):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="TestC2", code="C2")
        area = AreaOfInterest.objects.create(
            name="Null Area", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="t3", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=0.0,
            severity_data=None,
        )
        prompt = build_report_prompt(run)
        self.assertIn("Null Area", prompt)

    def test_build_report_prompt_handles_simple_severity_values(self):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="TestC3", code="C3")
        area = AreaOfInterest.objects.create(
            name="Simple Area", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="t4", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=100.0,
            severity_data={"High": "400 ha"},
        )
        prompt = build_report_prompt(run)
        self.assertIn("High: 400 ha", prompt)

    def test_build_report_prompt_uses_fallback_keys(self):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="TestC4", code="C4")
        area = AreaOfInterest.objects.create(
            name="Fallback Area", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="t5", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=100.0,
            severity_data={"High": {"area": 40.0, "percentage": 20.0}},
        )
        prompt = build_report_prompt(run)
        self.assertIn("40.0 ha", prompt)
        self.assertIn("20.0%", prompt)


class GeminiClientTests(TestCase):
    """Tests for Gemini client instantiation."""

    def test_get_gemini_client_raises_without_api_key(self):
        with patch("wildfire_assessment.svc.gemini_analysis.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            with self.assertRaises(ValueError) as context:
                _get_gemini_client()
            self.assertIn("GEMINI_API_KEY", str(context.exception))

    @patch("wildfire_assessment.svc.gemini_analysis.settings")
    @patch("wildfire_assessment.svc.gemini_analysis.genai")
    def test_get_gemini_client_returns_client(self, mock_genai, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-key"
        client = _get_gemini_client()
        mock_genai.Client.assert_called_once_with(api_key="test-key")
        self.assertEqual(client, mock_genai.Client.return_value)


class GeminiStreamTests(TestCase):
    """Tests for Gemini streaming functions."""

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

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_stream_yields_chunks(self, mock_get_client, mock_cache):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "World"

        mock_client.models.generate_content_stream.return_value = [
            mock_chunk1,
            mock_chunk2,
        ]

        stream, holder = _gemini_generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello ", "World"])
        self.assertIsNotNone(holder["response_id"])
        mock_client.models.generate_content_stream.assert_called_once()
        mock_cache.set.assert_called_once()

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_stream_uses_correct_model(self, mock_get_client, mock_cache):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.models.generate_content_stream.return_value = []

        stream, holder = _gemini_generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
            model="gemini-1.5-pro",
            language="fr",
        )
        list(stream)

        call_kwargs = mock_client.models.generate_content_stream.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gemini-1.5-pro")

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_stream_with_images(self, mock_get_client, mock_cache):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.models.generate_content_stream.return_value = []

        stream, holder = _gemini_generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
            image_urls=[{"url": "data:image/png;base64,dGVzdA==", "label": "RGB"}],
        )
        list(stream)

        call_kwargs = mock_client.models.generate_content_stream.call_args.kwargs
        contents = call_kwargs["contents"]
        self.assertTrue(len(contents) >= 3)

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_followup_yields_chunks(self, mock_get_client, mock_cache):
        mock_cache.get.return_value = {
            "history": [
                {"role": "user", "parts": ["initial prompt"]},
                {"role": "model", "parts": ["initial response"]},
            ],
            "model": "gemini-2.0-flash",
            "language": "en",
            "provider": "gemini",
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Follow "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "up"
        mock_chat.send_message_stream.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = _gemini_generate_followup_stream(
            previous_response_id="conv_123",
            question="What about recovery?",
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Follow ", "up"])
        self.assertIsNotNone(holder["response_id"])
        mock_cache.get.assert_called_once_with("ai_chat_conv_123")
        mock_chat.send_message_stream.assert_called_once_with(
            message="What about recovery?"
        )

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    def test_gemini_followup_raises_on_missing_conversation(self, mock_cache):
        mock_cache.get.return_value = None

        with self.assertRaises(ValueError) as context:
            _gemini_generate_followup_stream(
                previous_response_id="invalid_id",
                question="test",
            )
        self.assertIn("not found", str(context.exception))

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_followup_uses_language_and_model(self, mock_get_client, mock_cache):
        mock_cache.get.return_value = {
            "history": [],
            "model": "gemini-2.0-flash",
            "language": "en",
        }
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat
        mock_chat.send_message_stream.return_value = []

        stream, holder = _gemini_generate_followup_stream(
            previous_response_id="conv_123",
            question="Details?",
            language="pt-BR",
            model="gemini-1.5-pro",
        )
        list(stream)

        call_kwargs = mock_client.chats.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gemini-2.0-flash")

    @patch("wildfire_assessment.svc.gemini_analysis.cache")
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_stream_skips_empty_chunks(self, mock_get_client, mock_cache):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello"
        mock_chunk2 = MagicMock()
        mock_chunk2.text = None

        mock_client.models.generate_content_stream.return_value = [
            mock_chunk1,
            mock_chunk2,
        ]

        stream, holder = _gemini_generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello"])

    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_generate_report_returns_text(self, mock_client_fn):
        from wildfire_assessment.svc.gemini_analysis import _gemini_generate_report

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# Report\nContent here"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = _gemini_generate_report(prompt="test prompt", language="en")
        self.assertEqual(result, "# Report\nContent here")
        mock_client.models.generate_content.assert_called_once()

    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_generate_report_with_images(self, mock_client_fn):
        from wildfire_assessment.svc.gemini_analysis import _gemini_generate_report

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Report with images"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        images = [{"label": "dNBR", "url": "data:image/png;base64,iVBOR"}]
        result = _gemini_generate_report(
            prompt="test", image_urls=images, language="pt-BR"
        )
        self.assertEqual(result, "Report with images")

    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_generate_report_empty_response(self, mock_client_fn):
        from wildfire_assessment.svc.gemini_analysis import _gemini_generate_report

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = _gemini_generate_report(prompt="test")
        self.assertEqual(result, "")


class DeepSeekAnalysisTests(TestCase):
    """Tests for the DeepSeek provider (text-only)."""

    def _fake_stream(self, chunks):
        for text in chunks:
            chunk = MagicMock()
            if text is None:
                chunk.choices = []
            else:
                delta = MagicMock()
                delta.content = text
                choice = MagicMock()
                choice.delta = delta
                chunk.choices = [choice]
            yield chunk

    @patch("wildfire_assessment.svc.deepseek_analysis.settings")
    def test_get_deepseek_client_raises_without_api_key(self, mock_settings):
        from wildfire_assessment.svc.deepseek_analysis import _get_deepseek_client

        mock_settings.DEEPSEEK_API_KEY = None
        with self.assertRaises(ValueError):
            _get_deepseek_client()

    @patch("wildfire_assessment.svc.deepseek_analysis.OpenAI")
    @patch("wildfire_assessment.svc.deepseek_analysis.settings")
    def test_get_deepseek_client_uses_base_url(self, mock_settings, mock_openai):
        from wildfire_assessment.svc.deepseek_analysis import _get_deepseek_client

        mock_settings.DEEPSEEK_API_KEY = "sk-test"
        client = _get_deepseek_client()
        mock_openai.assert_called_once_with(
            api_key="sk-test", base_url="https://api.deepseek.com"
        )
        self.assertEqual(client, mock_openai.return_value)

    @patch("wildfire_assessment.svc.deepseek_analysis._get_deepseek_client")
    @patch("wildfire_assessment.svc.deepseek_analysis.cache")
    def test_deepseek_stream_yields_chunks(self, mock_cache, mock_get_client):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_analysis_stream as deepseek_generate_analysis_stream,
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._fake_stream(
            ["# Analysis", "\nDeepSeek text"]
        )
        mock_get_client.return_value = mock_client

        stream, holder = deepseek_generate_analysis_stream(
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            area_of_interest="Test Reserve",
            severity_distribution={"High": {"area_ha": 10.0, "percent": 5.0}},
            language="en",
        )
        chunks = list(stream)
        self.assertEqual(chunks, ["# Analysis", "\nDeepSeek text"])
        self.assertIsNotNone(holder["response_id"])
        cache_key, cache_value = mock_cache.set.call_args[0]
        self.assertTrue(cache_key.startswith("ai_chat_"))
        self.assertEqual(cache_value["provider"], "deepseek")
        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        # Text-only: the user message content is a plain string.
        self.assertIsInstance(messages[1]["content"], str)

    @patch("wildfire_assessment.svc.deepseek_analysis._get_deepseek_client")
    @patch("wildfire_assessment.svc.deepseek_analysis.cache")
    def test_deepseek_stream_ignores_image_urls(self, mock_cache, mock_get_client):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_analysis_stream as deepseek_generate_analysis_stream,
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._fake_stream(["ok"])
        mock_get_client.return_value = mock_client

        stream, _ = deepseek_generate_analysis_stream(
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            area_of_interest="Test Reserve",
            severity_distribution={},
            image_urls=[{"label": "dNBR", "url": "http://example.com/img.jpg"}],
        )
        list(stream)
        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        self.assertIsInstance(messages[1]["content"], str)
        self.assertNotIn("image_url", str(messages[1]["content"]))

    @patch("wildfire_assessment.svc.deepseek_analysis._get_deepseek_client")
    @patch("wildfire_assessment.svc.deepseek_analysis.cache")
    def test_deepseek_stream_skips_empty_choices(self, mock_cache, mock_get_client):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_analysis_stream as deepseek_generate_analysis_stream,
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._fake_stream(
            [None, "real chunk"]
        )
        mock_get_client.return_value = mock_client

        stream, _ = deepseek_generate_analysis_stream(
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            area_of_interest="Test Reserve",
            severity_distribution={},
        )
        self.assertEqual(list(stream), ["real chunk"])

    @patch("wildfire_assessment.svc.deepseek_analysis.cache")
    def test_deepseek_followup_raises_on_missing_conversation(self, mock_cache):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_followup_stream as deepseek_generate_followup_stream,
        )

        mock_cache.get.return_value = None
        with self.assertRaises(ValueError):
            stream, _ = deepseek_generate_followup_stream("missing", "question")
            list(stream)

    @patch("wildfire_assessment.svc.deepseek_analysis._get_deepseek_client")
    @patch("wildfire_assessment.svc.deepseek_analysis.cache")
    def test_deepseek_followup_yields_chunks(self, mock_cache, mock_get_client):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_followup_stream as deepseek_generate_followup_stream,
        )

        mock_cache.get.return_value = {
            "history": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
                {"role": "assistant", "content": "assistant"},
            ],
            "model": "deepseek-chat",
            "language": "en",
            "provider": "deepseek",
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._fake_stream(
            ["followup"]
        )
        mock_get_client.return_value = mock_client

        stream, holder = deepseek_generate_followup_stream(
            "conv", "question", language="pt-BR"
        )
        self.assertEqual(list(stream), ["followup"])
        self.assertIsNotNone(holder["response_id"])
        cache_key, cache_value = mock_cache.set.call_args[0]
        self.assertEqual(cache_value["provider"], "deepseek")
        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        self.assertIn("Brazilian Portuguese", messages[0]["content"])

    @patch("wildfire_assessment.svc.deepseek_analysis._get_deepseek_client")
    def test_deepseek_generate_report_returns_text(self, mock_get_client):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_report as deepseek_generate_report,
        )

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "# DeepSeek Report\nContent"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = deepseek_generate_report(prompt="test prompt", language="en")
        self.assertEqual(result, "# DeepSeek Report\nContent")
        mock_client.chat.completions.create.assert_called_once()
        self.assertFalse(
            mock_client.chat.completions.create.call_args[1].get("stream", False)
        )

    @patch("wildfire_assessment.svc.deepseek_analysis._get_deepseek_client")
    def test_deepseek_generate_report_empty_response(self, mock_get_client):
        from wildfire_assessment.svc.deepseek_analysis import (
            generate_report as deepseek_generate_report,
        )

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = deepseek_generate_report(prompt="test")
        self.assertEqual(result, "")


class ProviderDispatchTests(TestCase):
    """Tests for the provider dispatch logic."""

    def setUp(self):
        self.pre_fire_date = "2024-01-01"
        self.post_fire_date = "2024-01-15"
        self.area_of_interest = "Test Reserve"
        self.severity_distribution = {
            "Unburned": {"area_ha": 100.0, "percent": 50.0},
        }

    @patch("wildfire_assessment.svc.ai_common.cache")
    def test_get_active_provider_returns_cached(self, mock_cache):
        mock_provider = MagicMock()
        mock_cache.get.return_value = mock_provider
        result = get_active_provider()
        self.assertEqual(result, mock_provider)
        mock_cache.get.assert_called_once_with("active_ai_provider")

    @patch("wildfire_assessment.svc.ai_common.cache")
    def test_get_active_provider_queries_db_on_cache_miss(self, mock_cache):
        mock_cache.get.return_value = None
        with patch("wildfire_assessment.models.AIProvider.load") as mock_load:
            mock_provider = MagicMock()
            mock_load.return_value = mock_provider
            result = get_active_provider()
            self.assertEqual(result, mock_provider)
            mock_cache.set.assert_called_once_with(
                "active_ai_provider", mock_provider, timeout=60
            )

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_analysis_stream")
    def test_dispatch_to_gemini_when_active(self, mock_gemini, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.provider = "gemini"
        mock_provider.model_name = "gemini-2.0-flash-lite"
        mock_get_provider.return_value = mock_provider
        mock_gemini.return_value = (iter([]), {"response_id": None})

        generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )

        mock_gemini.assert_called_once()
        args = mock_gemini.call_args
        self.assertEqual(args.kwargs["model"], "gemini-2.0-flash-lite")

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common._openai_generate_analysis_stream")
    def test_dispatch_to_openai_when_active(self, mock_openai, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.provider = "openai"
        mock_provider.model_name = "gpt-4o-mini"
        mock_get_provider.return_value = mock_provider
        mock_openai.return_value = (iter([]), {"response_id": None})

        generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )

        mock_openai.assert_called_once()
        args = mock_openai.call_args
        self.assertEqual(args.kwargs["model"], "gpt-4o-mini")

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common._deepseek_generate_analysis_stream")
    def test_dispatch_to_deepseek_when_active(self, mock_deepseek, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.provider = "deepseek"
        mock_provider.model_name = "deepseek-chat"
        mock_get_provider.return_value = mock_provider
        mock_deepseek.return_value = (iter([]), {"response_id": None})

        generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )

        mock_deepseek.assert_called_once()
        args = mock_deepseek.call_args
        self.assertEqual(args.kwargs["model"], "deepseek-chat")
        self.assertNotIn("image_urls", args.kwargs)

    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._deepseek_generate_followup_stream")
    def test_followup_dispatch_uses_cached_provider_deepseek(
        self, mock_deepseek, mock_cache
    ):
        mock_cache.get.return_value = {
            "provider": "deepseek",
            "model": "deepseek-chat",
        }
        mock_deepseek.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="conv", question="question", language="en"
        )

        mock_deepseek.assert_called_once()
        self.assertEqual(mock_deepseek.call_args.kwargs["model"], "deepseek-chat")

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._deepseek_generate_followup_stream")
    def test_followup_fallback_to_deepseek_when_no_cache(
        self, mock_deepseek, mock_cache, mock_get_provider
    ):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.provider = "deepseek"
        mock_provider.model_name = "deepseek-chat"
        mock_get_provider.return_value = mock_provider
        mock_deepseek.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="conv", question="question", language="en"
        )

        mock_deepseek.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common._deepseek_generate_report")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    def test_generate_report_summary_deepseek_skips_images(
        self, mock_signed, mock_report, mock_get_provider
    ):
        mock_provider = MagicMock()
        mock_provider.provider = "deepseek"
        mock_provider.model_name = "deepseek-chat"
        mock_get_provider.return_value = mock_provider
        mock_report.return_value = "# DeepSeek Report"

        run = MagicMock()
        run.area_of_interest.name = "Test Reserve"
        run.area_of_interest.country.name = "Brazil"
        run.pre_fire_date = "2024-01-01"
        run.post_fire_date = "2024-01-15"
        run.total_burned_ha = 250.0
        run.severity_data = self.severity_distribution
        run.report_summary = None
        run.report_summary_language = None

        text = generate_report_summary(run, language="en")
        self.assertEqual(text, "# DeepSeek Report")
        mock_signed.assert_not_called()
        prompt = mock_report.call_args.kwargs["prompt"]
        self.assertIn("No imagery is provided", prompt)
        self.assertEqual(mock_report.call_args.kwargs["model"], "deepseek-chat")
        run.save.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_analysis_stream")
    def test_dispatch_defaults_to_gemini_when_no_provider(
        self, mock_gemini, mock_get_provider
    ):
        mock_get_provider.return_value = None
        mock_gemini.return_value = (iter([]), {"response_id": None})

        generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )

        mock_gemini.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_followup_stream")
    def test_followup_dispatch_uses_cached_provider_gemini(
        self, mock_gemini, mock_cache
    ):
        mock_cache.get.return_value = {
            "history": [],
            "model": "gemini-2.0-flash",
            "language": "en",
            "provider": "gemini",
        }
        mock_gemini.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="conv_123",
            question="test",
        )

        mock_gemini.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._openai_generate_followup_stream")
    def test_followup_dispatch_uses_cached_provider_openai(
        self, mock_openai, mock_cache
    ):
        mock_cache.get.return_value = {
            "history": [],
            "model": "gpt-4o-mini",
            "language": "en",
            "provider": "openai",
        }
        mock_openai.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="conv_123",
            question="test",
        )

        mock_openai.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._openai_generate_followup_stream")
    def test_followup_fallback_to_openai_when_no_cache(
        self, mock_openai, mock_cache, mock_get_provider
    ):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.provider = "openai"
        mock_provider.model_name = "gpt-4o-mini"
        mock_get_provider.return_value = mock_provider
        mock_openai.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="conv_missing",
            question="test",
        )

        mock_openai.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_followup_stream")
    def test_followup_fallback_to_gemini_when_no_cache(
        self, mock_gemini, mock_cache, mock_get_provider
    ):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.provider = "gemini"
        mock_provider.model_name = "gemini-2.0-flash-lite"
        mock_get_provider.return_value = mock_provider
        mock_gemini.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="conv_missing",
            question="test",
        )

        mock_gemini.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._openai_generate_followup_stream")
    def test_followup_dispatch_no_cache_falls_back_to_openai(
        self, mock_openai, mock_cache, mock_get_provider
    ):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.provider = "openai"
        mock_provider.model_name = "gpt-4o-mini"
        mock_get_provider.return_value = mock_provider
        mock_openai.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="missing_conv",
            question="test",
        )

        mock_openai.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    @patch("wildfire_assessment.svc.ai_common.cache")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_followup_stream")
    def test_followup_dispatch_no_cache_falls_back_to_gemini(
        self, mock_gemini, mock_cache, mock_get_provider
    ):
        mock_cache.get.return_value = None
        mock_provider = MagicMock()
        mock_provider.provider = "gemini"
        mock_provider.model_name = "gemini-2.0-flash-lite"
        mock_get_provider.return_value = mock_provider
        mock_gemini.return_value = (iter([]), {"response_id": None})

        generate_followup_stream(
            previous_response_id="missing_conv",
            question="test",
        )

        mock_gemini.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_gemini(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil GEM", code="BG")
        area = AreaOfInterest.objects.create(
            name="Test Area", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="rpt", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.0,
            severity_data={"High": {"area_ha": 100.0, "percent": 100.0}},
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_gemini_report.return_value = "# Generated Report"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "# Generated Report")
        mock_gemini_report.assert_called_once()
        run.refresh_from_db()
        self.assertEqual(run.report_summary, "# Generated Report")
        self.assertEqual(run.report_summary_language, "en")

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    @patch("wildfire_assessment.svc.ai_common._openai_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_openai(
        self, mock_provider, mock_openai_report, mock_presigned, mock_requests
    ):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil OAI", code="B2")
        area = AreaOfInterest.objects.create(
            name="Test Area 2", polygon_path="p2.json", country=country
        )
        user = User.objects.create_user(username="rpt2", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            total_burned_ha=200.0,
            severity_data={"Low": {"area_ha": 200.0, "percent": 100.0}},
        )

        mock_prov = MagicMock()
        mock_prov.provider = "openai"
        mock_prov.model_name = "gpt-4o-mini"
        mock_provider.return_value = mock_prov
        mock_openai_report.return_value = "# OpenAI Report"

        result = generate_report_summary(run, language="pt-BR")
        self.assertEqual(result, "# OpenAI Report")
        mock_openai_report.assert_called_once()
        run.refresh_from_db()
        self.assertEqual(run.report_summary, "# OpenAI Report")
        self.assertEqual(run.report_summary_language, "pt-BR")

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_fetches_images(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil IMG", code="B3")
        area = AreaOfInterest.objects.create(
            name="Test Area 3", polygon_path="p3.json", country=country
        )
        user = User.objects.create_user(username="rpt3", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-03-01",
            post_fire_date="2024-03-15",
            total_burned_ha=50.0,
            severity_data={},
            dnbr_image="test_dnbr.png",
            rbr_image="test_rbr.png",
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_presigned.return_value = "https://s3.example.com/signed"
        mock_resp = MagicMock()
        mock_resp.content = b"fake_image_bytes"
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_resp
        mock_gemini_report.return_value = "Report"

        generate_report_summary(run, language="en")

        # Should have fetched 2 images (dnbr + rbr)
        self.assertEqual(mock_requests.get.call_count, 2)
        image_urls = mock_gemini_report.call_args.kwargs["image_urls"]
        self.assertEqual(len(image_urls), 2)

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_no_provider_defaults_to_gemini(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil NPR", code="B4")
        area = AreaOfInterest.objects.create(
            name="Test Area 4", polygon_path="p4.json", country=country
        )
        user = User.objects.create_user(username="rpt4", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-04-01",
            post_fire_date="2024-04-15",
            total_burned_ha=75.0,
            severity_data={"Low": {"area_ha": 75.0, "percent": 100.0}},
        )

        mock_provider.return_value = None
        mock_gemini_report.return_value = "# Default Report"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "# Default Report")
        mock_gemini_report.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_null_language_cached(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        """Test that report_summary with None language triggers regeneration."""
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil NLC", code="B5")
        area = AreaOfInterest.objects.create(
            name="Test Area 5", polygon_path="p5.json", country=country
        )
        user = User.objects.create_user(username="rpt5", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-05-01",
            post_fire_date="2024-05-15",
            total_burned_ha=60.0,
            severity_data={},
            report_summary="# Old report",
            report_summary_language=None,
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_gemini_report.return_value = "# New Report"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "# New Report")

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.object_storage.get_signed_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_image_fetch_failure_skips(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        """Test that failed image fetches are skipped gracefully."""
        from django.contrib.auth import get_user_model
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country

        User = get_user_model()
        country = Country.objects.create(name="Brazil IFF", code="B6")
        area = AreaOfInterest.objects.create(
            name="Test Area 6", polygon_path="p6.json", country=country
        )
        user = User.objects.create_user(username="rpt6", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=30.0,
            severity_data={},
            dnbr_image="test_dnbr.png",
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_presigned.side_effect = Exception("S3 error")
        mock_gemini_report.return_value = "Report without images"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "Report without images")
        # Images should be empty since fetch failed
        image_urls = mock_gemini_report.call_args.kwargs["image_urls"]
        self.assertEqual(len(image_urls), 0)


class OpenAIAnalysisTests(TestCase):
    """Tests for the OpenAI streaming service."""

    def setUp(self):
        self.pre_fire_date = "2024-01-01"
        self.post_fire_date = "2024-01-15"
        self.area_of_interest = "Test Reserve"
        self.severity_distribution = {
            "Unburned": {"area_ha": 100.0, "percent": 50.0},
        }

    @patch("wildfire_assessment.svc.openai_analysis.settings")
    def test_get_openai_client_raises_without_api_key(self, mock_settings):
        mock_settings.OPENAI_API_KEY = ""
        with self.assertRaises(ValueError) as context:
            _get_openai_client()
        self.assertIn("OPENAI_API_KEY", str(context.exception))

    @patch("wildfire_assessment.svc.openai_analysis.OpenAI")
    @patch("wildfire_assessment.svc.openai_analysis.settings")
    def test_get_openai_client_returns_client(self, mock_settings, mock_openai_cls):
        mock_settings.OPENAI_API_KEY = "test-key"
        client = _get_openai_client()
        mock_openai_cls.assert_called_once_with(api_key="test-key")
        self.assertEqual(client, mock_openai_cls.return_value)

    @patch("wildfire_assessment.svc.openai_analysis.cache")
    @patch("wildfire_assessment.svc.openai_analysis._get_openai_client")
    def test_openai_stream_yields_chunks(self, mock_get_client, mock_cache):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "World"

        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = openai_generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello ", "World"])
        self.assertIsNotNone(holder["response_id"])
        mock_client.chat.completions.create.assert_called_once()

    @patch("wildfire_assessment.svc.openai_analysis.cache")
    @patch("wildfire_assessment.svc.openai_analysis._get_openai_client")
    def test_openai_followup_yields_chunks(self, mock_get_client, mock_cache):
        mock_cache.get.return_value = {
            "history": [
                {"role": "system", "content": "You are an expert..."},
                {"role": "user", "content": "initial prompt"},
                {"role": "assistant", "content": "initial response"},
            ],
            "model": "gpt-4o-mini",
            "language": "en",
            "provider": "openai",
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Follow "
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "up"

        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = openai_generate_followup_stream(
            previous_response_id="conv_123",
            question="What about recovery?",
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Follow ", "up"])
        self.assertIsNotNone(holder["response_id"])

    @patch("wildfire_assessment.svc.openai_analysis.cache")
    def test_openai_followup_raises_on_missing_conversation(self, mock_cache):
        mock_cache.get.return_value = None

        with self.assertRaises(ValueError) as context:
            openai_generate_followup_stream(
                previous_response_id="invalid_id",
                question="test",
            )
        self.assertIn("not found", str(context.exception))

    def test_openai_build_user_content_text_only(self):
        result = _build_user_content("test prompt", None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[0]["text"], "test prompt")

    def test_openai_build_user_content_with_images(self):
        result = _build_user_content(
            "test prompt",
            [{"url": "data:image/png;base64,abc", "label": "dNBR"}],
        )
        # prompt text + label text + image_url
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[1]["type"], "text")
        self.assertIn("dNBR", result[1]["text"])
        self.assertEqual(result[2]["type"], "image_url")

    def test_openai_build_user_content_skips_missing_url(self):
        result = _build_user_content(
            "test prompt",
            [{"label": "dNBR"}, {"url": "", "label": "RBR"}],
        )
        # Only the prompt text, both images skipped (no url / empty url)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "text")

    def test_openai_build_user_content_image_without_label(self):
        result = _build_user_content(
            "test prompt",
            [{"url": "data:image/png;base64,abc"}],
        )
        # prompt text + image_url (no label text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[1]["type"], "image_url")

    @patch("wildfire_assessment.svc.openai_analysis._get_openai_client")
    def test_openai_generate_report_returns_text(self, mock_client_fn):
        from wildfire_assessment.svc.openai_analysis import (
            generate_report as openai_generate_report,
        )

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "# OpenAI Report\nContent"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = openai_generate_report(prompt="test prompt", language="en")
        self.assertEqual(result, "# OpenAI Report\nContent")
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertFalse(call_kwargs.get("stream", False))

    @patch("wildfire_assessment.svc.openai_analysis._get_openai_client")
    def test_openai_generate_report_empty_response(self, mock_client_fn):
        from wildfire_assessment.svc.openai_analysis import (
            generate_report as openai_generate_report,
        )

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = openai_generate_report(prompt="test")
        self.assertEqual(result, "")
