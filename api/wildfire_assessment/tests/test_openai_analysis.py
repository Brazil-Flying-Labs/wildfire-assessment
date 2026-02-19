"""Tests for the OpenAI analysis service."""

import os
from unittest.mock import MagicMock, patch

from django.test import TestCase
from wildfire_assessment.svc.openai_analysis import (
    build_analysis_prompt,
    generate_analysis_stream,
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
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            # Remove the key if it exists
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            with self.assertRaises(ValueError) as context:
                get_openai_client()
            self.assertIn("OPENAI_API_KEY", str(context.exception))

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_analysis_stream_yields_chunks(self, mock_get_client):
        """Test that generate_analysis_stream yields text chunks."""
        # Mock the OpenAI client and response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create mock chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello "

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "World"

        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock()]
        mock_chunk3.choices[0].delta.content = None  # End of stream

        mock_client.chat.completions.create.return_value = [
            mock_chunk1,
            mock_chunk2,
            mock_chunk3,
        ]

        # Collect yielded chunks
        chunks = list(
            generate_analysis_stream(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                area_of_interest=self.area_of_interest,
                severity_distribution=self.severity_distribution,
            )
        )

        self.assertEqual(chunks, ["Hello ", "World"])
        mock_client.chat.completions.create.assert_called_once()

    @patch("wildfire_assessment.svc.openai_analysis.get_openai_client")
    def test_generate_analysis_stream_uses_correct_model(self, mock_get_client):
        """Test that generate_analysis_stream uses the specified model."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = []

        list(
            generate_analysis_stream(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                area_of_interest=self.area_of_interest,
                severity_distribution=self.severity_distribution,
                model="gpt-4",
            )
        )

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gpt-4")
        self.assertTrue(call_kwargs["stream"])
