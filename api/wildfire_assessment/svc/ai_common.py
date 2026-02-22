"""
Shared AI analysis constants, helpers, and provider dispatch.

Both gemini_analysis and openai_analysis import shared code from here.
This module imports from both provider modules to dispatch requests.
"""

import logging
from typing import Generator

from django.core.cache import cache
from wildfire_assessment.models import AIProvider

LOG = logging.getLogger(__name__)

CONVERSATION_CACHE_TTL = 3600  # 1 hour

SYSTEM_INSTRUCTIONS = (
    "You are an expert environmental analyst specializing in wildfire damage "
    "assessment and ecological recovery."
)

LANGUAGE_MAP = {
    "en": "English",
    "pt-BR": "Brazilian Portuguese",
    "fr": "French",
}

PROVIDER_DISPLAY = {
    "gemini": "Google Gemini",
    "openai": "OpenAI",
}


def _get_instructions(language: str | None = None) -> str:
    lang_name = LANGUAGE_MAP.get(language or "en", "English")
    return f"{SYSTEM_INSTRUCTIONS} Always respond in {lang_name}."


def get_active_provider():
    """Return the singleton AIProvider config (cached 60s)."""
    config = cache.get("active_ai_provider")
    if not config:
        config = AIProvider.load()
        cache.set("active_ai_provider", config, timeout=60)
    return config


def build_analysis_prompt(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
) -> str:
    """Build the prompt for wildfire analysis."""
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


# ---------------------------------------------------------------------------
# Provider imports — placed after shared code to avoid circular imports.
# Both gemini_analysis and openai_analysis import shared symbols defined above.
# ---------------------------------------------------------------------------
from wildfire_assessment.svc.gemini_analysis import (
    _gemini_generate_analysis_stream,
    _gemini_generate_followup_stream,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_analysis_stream as _openai_generate_analysis_stream,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_followup_stream as _openai_generate_followup_stream,
)

# ---------------------------------------------------------------------------
# Public dispatch functions (called by views)
# ---------------------------------------------------------------------------


def generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    image_urls: list | None = None,
    language: str | None = None,
    model: str | None = None,
) -> tuple[Generator[str, None, None], dict]:
    """
    Generate a streaming analysis using the active AI provider.

    Returns:
        A tuple of (generator yielding text chunks, holder dict).
        holder["response_id"] is set after the generator is exhausted.
    """
    provider = get_active_provider()
    if provider and provider.provider == "openai":
        return _openai_generate_analysis_stream(
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            area_of_interest=area_of_interest,
            severity_distribution=severity_distribution,
            image_urls=image_urls,
            language=language,
            model=model or (provider.model_name if provider else "gpt-4o-mini"),
        )

    return _gemini_generate_analysis_stream(
        pre_fire_date=pre_fire_date,
        post_fire_date=post_fire_date,
        area_of_interest=area_of_interest,
        severity_distribution=severity_distribution,
        image_urls=image_urls,
        language=language,
        model=model or (provider.model_name if provider else "gemini-2.0-flash-lite"),
    )


def generate_followup_stream(
    previous_response_id: str,
    question: str,
    language: str | None = None,
    model: str | None = None,
) -> tuple[Generator[str, None, None], dict]:
    """
    Generate a streaming follow-up using the appropriate provider.

    The provider is determined by the cached conversation data when available,
    otherwise falls back to the active provider.
    """
    # Check cached conversation to determine which provider was used
    conv_data = cache.get(f"ai_chat_{previous_response_id}")
    cached_provider = conv_data.get("provider") if conv_data else None

    if cached_provider == "openai":
        return _openai_generate_followup_stream(
            previous_response_id=previous_response_id,
            question=question,
            language=language,
            model=model or (conv_data.get("model") if conv_data else "gpt-4o-mini"),
        )

    if cached_provider == "gemini" or conv_data:
        return _gemini_generate_followup_stream(
            previous_response_id=previous_response_id,
            question=question,
            language=language,
            model=model or (conv_data.get("model") if conv_data else "gemini-2.0-flash-lite"),
        )

    # No cached conversation — use active provider
    provider = get_active_provider()
    if provider and provider.provider == "openai":
        return _openai_generate_followup_stream(
            previous_response_id=previous_response_id,
            question=question,
            language=language,
            model=model or provider.model_name,
        )

    return _gemini_generate_followup_stream(
        previous_response_id=previous_response_id,
        question=question,
        language=language,
        model=model or (provider.model_name if provider else "gemini-2.0-flash-lite"),
    )
