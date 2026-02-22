"""Tests for the AI analysis service (provider dispatch + Gemini + OpenAI)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from wildfire_assessment.svc.ai_common import (
    PROVIDER_DISPLAY,
    _get_instructions,
    build_analysis_prompt,
    generate_analysis_stream,
    generate_followup_stream,
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

        mock_client.models.generate_content_stream.return_value = [mock_chunk1, mock_chunk2]

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

        mock_client.models.generate_content_stream.return_value = [mock_chunk1, mock_chunk2]

        stream, holder = _gemini_generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello"])


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
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_analysis_stream")
    def test_dispatch_defaults_to_gemini_when_no_provider(self, mock_gemini, mock_get_provider):
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
    def test_followup_dispatch_uses_cached_provider_gemini(self, mock_gemini, mock_cache):
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
    def test_followup_dispatch_uses_cached_provider_openai(self, mock_openai, mock_cache):
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
    def test_followup_fallback_to_openai_when_no_cache(self, mock_openai, mock_cache, mock_get_provider):
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
    def test_followup_fallback_to_gemini_when_no_cache(self, mock_gemini, mock_cache, mock_get_provider):
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
