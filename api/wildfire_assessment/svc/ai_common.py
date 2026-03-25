"""
Shared AI analysis constants, helpers, and provider dispatch.

Both gemini_analysis and openai_analysis import shared code from here.
This module imports from both provider modules to dispatch requests.
"""

import base64
import logging
from typing import Generator

import requests
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
    "es-ES": "Spanish",
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


REPORT_SYSTEM_INSTRUCTIONS = (
    "You are a senior remote sensing scientist specialized in wildfire impact "
    "assessment and post-fire environmental management, with experience "
    "supporting environmental agencies such as state forest foundations.\n\n"
    "Based on the following outputs generated from a Sentinel-2 wildfire burn "
    "severity analysis (including burn severity maps, RGB composites, severity "
    "class statistics, and metadata), produce a structured technical analysis "
    "suitable for inclusion in an official environmental assessment report.\n\n"
    "Your analysis must go beyond describing the data and provide expert "
    "interpretation, spatial reasoning, and actionable recommendations.\n\n"
    "Use a formal, technical, and objective tone appropriate for a scientific "
    "and institutional audience.\n\n"
    "The report should include:\n\n"
    "1. Executive Summary\n"
    "   - Brief overview of the wildfire extent, severity distribution, and key findings.\n\n"
    "2. Burn Severity Analysis\n"
    "   - Interpretation of dNBR, RBR, and dNDVI indices.\n"
    "   - Spatial distribution of severity classes.\n\n"
    "3. Environmental Impact Assessment\n"
    "   - Vegetation loss and ecosystem implications.\n"
    "   - Soil degradation risk.\n"
    "   - Water resource impacts.\n\n"
    "4. Recommendations\n"
    "   - Immediate response priorities.\n"
    "   - Medium-term restoration actions.\n"
    "   - Long-term monitoring needs."
)


def _get_report_instructions(language: str | None = None) -> str:
    lang_name = LANGUAGE_MAP.get(language or "en", "English")
    return f"{REPORT_SYSTEM_INSTRUCTIONS}\n\nAlways respond in {lang_name}."


def build_report_prompt(analysis_run) -> str:
    """Build the user prompt for the report summary using AnalysisRun data."""
    severity_text = ""
    for severity_level, data in (analysis_run.severity_data or {}).items():
        if isinstance(data, dict):
            area = data.get("area_ha", data.get("area", "N/A"))
            percent = data.get("percent", data.get("percentage", "N/A"))
            severity_text += f"- {severity_level}: {area} ha ({percent}%)\n"
        else:
            severity_text += f"- {severity_level}: {data}\n"

    return (
        f"**Fire Event Details:**\n"
        f"- Location: {analysis_run.area_of_interest.name}\n"
        f"- Country: {analysis_run.area_of_interest.country.name}\n"
        f"- Pre-fire date: {analysis_run.pre_fire_date}\n"
        f"- Post-fire date: {analysis_run.post_fire_date}\n"
        f"- Total burned area: {analysis_run.total_burned_ha} ha\n\n"
        f"**DNBR Severity Distribution:**\n"
        f"{severity_text}\n"
        f"Satellite imagery is attached (RGB composites, dNBR, RBR, dNDVI maps). "
        f"Use the visual evidence from these images together with the numerical "
        f"data above to support your analysis.\n\n"
        f"Format your response in markdown for readability."
    )


# ---------------------------------------------------------------------------
# Provider imports — placed after shared code to avoid circular imports.
# Both gemini_analysis and openai_analysis import shared symbols defined above.
# ---------------------------------------------------------------------------
from wildfire_assessment.svc.gemini_analysis import (
    _gemini_generate_analysis_stream,
    _gemini_generate_followup_stream,
    _gemini_generate_report,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_analysis_stream as _openai_generate_analysis_stream,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_followup_stream as _openai_generate_followup_stream,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_report as _openai_generate_report,
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
            model=model
            or (conv_data.get("model") if conv_data else "gemini-2.0-flash-lite"),
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


def generate_report_summary(analysis_run, language: str = "en") -> str:
    """
    Generate a non-streaming report summary using the active AI provider.

    Fetches satellite images from S3, builds the prompt, dispatches to the
    active provider, saves the result to the DB, and returns the markdown.
    """
    from wildfire_assessment.svc.aws import get_presigned_image_url

    prompt = build_report_prompt(analysis_run)

    # Fetch satellite images from S3 as base64 data URLs
    image_fields = [
        ("dNBR", "dnbr_image"),
        ("RBR", "rbr_image"),
        ("dNDVI", "dndvi_image"),
        ("RGB Pre-fire", "rgb_pre_fire_image"),
        ("RGB Post-fire", "rgb_post_fire_image"),
    ]
    image_urls = []
    for label, field in image_fields:
        key = getattr(analysis_run, field)
        if not key:
            continue
        try:
            presigned_url = get_presigned_image_url(key)
            resp = requests.get(presigned_url, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/png")
            b64 = base64.b64encode(resp.content).decode()
            image_urls.append(
                {"label": label, "url": f"data:{content_type};base64,{b64}"}
            )
        except Exception:
            LOG.warning("Failed to fetch image %s for report, skipping", label)

    provider = get_active_provider()
    if provider and provider.provider == "openai":
        model = provider.model_name if provider else "gpt-4o-mini"
        text = _openai_generate_report(
            prompt=prompt,
            image_urls=image_urls,
            language=language,
            model=model,
        )
    else:
        model = provider.model_name if provider else "gemini-2.0-flash-lite"
        text = _gemini_generate_report(
            prompt=prompt,
            image_urls=image_urls,
            language=language,
            model=model,
        )

    # Save to DB (shadow replacement: only on success)
    analysis_run.report_summary = text
    analysis_run.report_summary_language = language
    analysis_run.save(update_fields=["report_summary", "report_summary_language"])

    return text
