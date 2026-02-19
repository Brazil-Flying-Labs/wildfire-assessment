"""Tests for the OpenAI analysis service."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from wildfire_assessment.svc.openai_analysis import (
    _build_image_content,
    _get_instructions,
    build_analysis_prompt,
    generate_analysis_stream,
    generate_followup_stream,
    get_openai_client,
)


class OpenAIAnalysisTests(TestCase):
    """Tests for the OpenAI analysis functions."""

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
        """Test that the prompt contains all input parameters."""
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
        """Test prompt building with simple severity values."""
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

    def test_get_openai_client_raises_without_api_key(self):
        """Test that get_openai_client raises ValueError without API key."""
        with patch("wildfire_assessment.svc.openai_analysis.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            with self.assertRaises(ValueError) as context:
                get_openai_client()
            self.assertIn("OPENAI_API_KEY", str(context.exception))

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_analysis_stream_yields_chunks(self, mock_get_client):
        """Test that generate_analysis_stream yields text chunks."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create mock streaming events for the Responses API
        mock_event1 = MagicMock()
        mock_event1.type = "response.output_text.delta"
        mock_event1.delta = "Hello "

        mock_event2 = MagicMock()
        mock_event2.type = "response.output_text.delta"
        mock_event2.delta = "World"

        mock_event3 = MagicMock()
        mock_event3.type = "response.completed"
        mock_event3.response.id = "resp_123"

        mock_client.responses.create.return_value = [
            mock_event1,
            mock_event2,
            mock_event3,
        ]

        # generate_analysis_stream returns (generator, holder)
        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Hello ", "World"])
        self.assertEqual(holder["response_id"], "resp_123")
        mock_client.responses.create.assert_called_once()

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_analysis_stream_uses_correct_model(self, mock_get_client):
        """Test that generate_analysis_stream uses the specified model."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.responses.create.return_value = []

        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
            model="gpt-4",
        )
        list(stream)  # exhaust the generator

        call_kwargs = mock_client.responses.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gpt-4")
        self.assertTrue(call_kwargs["stream"])

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

    @patch("wildfire_assessment.svc.openai_analysis.settings")
    @patch("wildfire_assessment.svc.openai_analysis.OpenAI")
    def test_get_openai_client_returns_client(self, mock_openai_cls, mock_settings):
        mock_settings.OPENAI_API_KEY = "test-key"
        client = get_openai_client()
        mock_openai_cls.assert_called_once_with(api_key="test-key")
        self.assertEqual(client, mock_openai_cls.return_value)

    def test_build_analysis_prompt_uses_fallback_keys(self):
        """Test prompt with 'area' and 'percentage' fallback keys."""
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
        result = _build_image_content([{"url": "http://img.png"}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "input_image")
        self.assertEqual(result[0]["image_url"], "http://img.png")

    def test_build_image_content_with_label(self):
        result = _build_image_content([{"url": "http://img.png", "label": "dNBR"}])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {"type": "input_text", "text": "Image: dNBR"})
        self.assertEqual(result[1]["type"], "input_image")

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_analysis_stream_with_images_and_language(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.responses.create.return_value = []

        stream, holder = generate_analysis_stream(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            area_of_interest=self.area_of_interest,
            severity_distribution=self.severity_distribution,
            image_urls=[{"url": "http://img.png", "label": "RGB"}],
            language="fr",
        )
        list(stream)

        call_kwargs = mock_client.responses.create.call_args.kwargs
        self.assertIn("French", call_kwargs["instructions"])
        input_content = call_kwargs["input"][0]["content"]
        image_items = [i for i in input_content if i.get("type") == "input_image"]
        self.assertEqual(len(image_items), 1)

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_followup_stream_yields_chunks(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_event1 = MagicMock()
        mock_event1.type = "response.output_text.delta"
        mock_event1.delta = "Follow "

        mock_event2 = MagicMock()
        mock_event2.type = "response.output_text.delta"
        mock_event2.delta = "up"

        mock_event3 = MagicMock()
        mock_event3.type = "response.completed"
        mock_event3.response.id = "resp_456"

        mock_client.responses.create.return_value = [
            mock_event1,
            mock_event2,
            mock_event3,
        ]

        stream, holder = generate_followup_stream(
            previous_response_id="resp_123",
            question="What about recovery?",
        )
        chunks = list(stream)

        self.assertEqual(chunks, ["Follow ", "up"])
        self.assertEqual(holder["response_id"], "resp_456")
        call_kwargs = mock_client.responses.create.call_args.kwargs
        self.assertEqual(call_kwargs["previous_response_id"], "resp_123")
        self.assertTrue(call_kwargs["stream"])

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_followup_stream_uses_language_and_model(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.responses.create.return_value = []

        stream, holder = generate_followup_stream(
            previous_response_id="resp_123",
            question="Details?",
            language="pt-BR",
            model="gpt-4",
        )
        list(stream)

        call_kwargs = mock_client.responses.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gpt-4")
        self.assertIn("Brazilian Portuguese", call_kwargs["instructions"])
