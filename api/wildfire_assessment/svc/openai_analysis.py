"""
OpenAI service for generating wildfire analysis reports.
"""

import logging
from typing import Generator

from django.conf import settings
from openai import OpenAI

LOG = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = (
    "You are an expert environmental analyst specializing in wildfire damage "
    "assessment and ecological recovery."
)

LANGUAGE_MAP = {
    "en": "English",
    "pt-BR": "Brazilian Portuguese",
    "fr": "French",
}


def _get_instructions(language: str | None = None) -> str:
    lang_name = LANGUAGE_MAP.get(language or "en", "English")
    return f"{SYSTEM_INSTRUCTIONS} Always respond in {lang_name}."


def get_openai_client() -> OpenAI:
    """Get an OpenAI client instance."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def build_analysis_prompt(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
) -> str:
    """
    Build the prompt for wildfire analysis.

    Args:
        pre_fire_date: Pre-fire date in YYYY-MM-DD format
        post_fire_date: Post-fire date in YYYY-MM-DD format
        area_of_interest: Name of the ecological reserve or area
        severity_distribution: Dictionary with severity levels and their areas/percentages

    Returns:
        Formatted prompt string
    """
    # Format severity data for the prompt
    severity_text = ""
    for severity_level, data in severity_distribution.items():
        if isinstance(data, dict):
            area = data.get("area_ha", data.get("area", "N/A"))
            percent = data.get("percent", data.get("percentage", "N/A"))
            severity_text += f"- {severity_level}: {area} ha ({percent}%)\n"
        else:
            severity_text += f"- {severity_level}: {data}\n"

    prompt = f"""You are an expert environmental analyst specializing in wildfire damage assessment.
Analyze the following wildfire data and provide a comprehensive analysis report.

**Fire Event Details:**
- Location: {area_of_interest}
- Pre-fire date: {pre_fire_date}
- Post-fire date: {post_fire_date}

**DNBR Severity Distribution:**
{severity_text}

Satellite imagery is attached (RGB composites, dNBR, RBR, dNDVI maps). Use the visual evidence from these images together with the numerical data above to support your analysis.

Please provide:
1. **Executive Summary**: A brief overview of the fire impact
2. **Severity Analysis**: Interpretation of the burn severity distribution, referencing visual patterns observed in the attached imagery
3. **Environmental Impact**: Potential ecological consequences based on the severity levels and spatial patterns visible in the images
4. **Recovery Recommendations**: Suggested actions for ecosystem recovery
5. **Monitoring Priorities**: Areas that should be prioritized for post-fire monitoring, informed by the spatial distribution of burn severity shown in the maps

Use clear, professional language suitable for environmental agencies and land managers.
Format your response in markdown for readability."""

    return prompt


def _build_image_content(image_urls: list | None) -> list:
    """Build content items for images."""
    items = []
    for img in image_urls or []:
        url = img.get("url")
        label = img.get("label", "")
        if not url:
            continue
        if label:
            items.append({"type": "input_text", "text": f"Image: {label}"})
        items.append(
            {"type": "input_image", "image_url": url, "detail": "low"}
        )
    return items


def generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = "gpt-4o-mini",
) -> tuple[Generator[str, None, None], str | None]:
    """
    Generate a streaming analysis of the wildfire data using OpenAI Responses API.

    Returns:
        A tuple of (generator yielding text chunks, response_id).
        The response_id is available after the generator is exhausted.
    """
    client = get_openai_client()
    prompt = build_analysis_prompt(
        pre_fire_date, post_fire_date, area_of_interest, severity_distribution
    )

    input_content = [{"type": "input_text", "text": prompt}]
    input_content.extend(_build_image_content(image_urls))

    instructions = _get_instructions(language)
    holder = {"response_id": None}

    def stream_chunks():
        stream = client.responses.create(
            model=model,
            instructions=instructions,
            input=[{"role": "user", "content": input_content}],
            stream=True,
            temperature=0.7,
            max_output_tokens=2000,
        )
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
            elif event.type == "response.completed":
                holder["response_id"] = event.response.id

    return stream_chunks(), holder


def generate_followup_stream(
    previous_response_id: str,
    question: str,
    language: str | None = None,
    model: str = "gpt-4o-mini",
) -> tuple[Generator[str, None, None], str | None]:
    """
    Generate a streaming follow-up response using the Responses API context.

    Args:
        previous_response_id: The ID of the previous response to continue from
        question: The user's follow-up question
        model: OpenAI model to use

    Returns:
        A tuple of (generator yielding text chunks, response_id holder).
    """
    client = get_openai_client()
    instructions = _get_instructions(language)

    holder = {"response_id": None}

    def stream_chunks():
        stream = client.responses.create(
            model=model,
            instructions=instructions,
            previous_response_id=previous_response_id,
            input=[{"role": "user", "content": question}],
            stream=True,
            temperature=0.7,
            max_output_tokens=2000,
        )
        for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
            elif event.type == "response.completed":
                holder["response_id"] = event.response.id

    return stream_chunks(), holder
