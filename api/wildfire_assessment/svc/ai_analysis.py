"""
AI analysis service — dispatches between Google Gemini and OpenAI
based on the active AIProvider configured in the admin.
"""

import logging
import uuid
from typing import Generator

import google.generativeai as genai
from django.conf import settings
from django.core.cache import cache

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
    """Return the active AIProvider row (cached 60s)."""
    from wildfire_assessment.models import AIProvider

    provider = cache.get("active_ai_provider")
    if not provider:
        provider = AIProvider.objects.filter(is_active=True).first()
        if provider:
            cache.set("active_ai_provider", provider, timeout=60)
    return provider


# ---------------------------------------------------------------------------
# Gemini-specific helpers
# ---------------------------------------------------------------------------


def get_gemini_model(
    model_name: str = "gemini-2.0-flash-lite",
    language: str | None = None,
) -> genai.GenerativeModel:
    """Get a configured Gemini model instance."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=_get_instructions(language),
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2000,
        ),
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


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


def _parse_data_url(data_url: str) -> dict | None:
    """Parse a data URL into Gemini inline_data format."""
    try:
        header, data = data_url.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
        return {"inline_data": {"mime_type": mime_type, "data": data}}
    except (ValueError, IndexError):
        return None


def _build_image_content(image_urls: list | None) -> list:
    """Build Gemini content parts for images."""
    items = []
    for img in image_urls or []:
        url = img.get("url")
        label = img.get("label", "")
        if not url:
            continue
        if label:
            items.append(f"Image: {label}")
        parsed = _parse_data_url(url)
        if parsed:
            items.append(parsed)
    return items


# ---------------------------------------------------------------------------
# Gemini streaming implementations
# ---------------------------------------------------------------------------


def _gemini_generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = "gemini-2.0-flash-lite",
) -> tuple[Generator[str, None, None], dict]:
    gemini_model = get_gemini_model(model, language)
    prompt = build_analysis_prompt(
        pre_fire_date, post_fire_date, area_of_interest, severity_distribution
    )

    contents = [prompt]
    contents.extend(_build_image_content(image_urls))

    holder = {"response_id": None}

    def stream_chunks():
        response = gemini_model.generate_content(contents, stream=True)
        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield chunk.text

        conv_id = str(uuid.uuid4())
        history = [
            {"role": "user", "parts": [prompt]},
            {"role": "model", "parts": [full_text]},
        ]
        cache.set(
            f"ai_chat_{conv_id}",
            {"history": history, "model": model, "language": language, "provider": "gemini"},
            timeout=CONVERSATION_CACHE_TTL,
        )
        holder["response_id"] = conv_id

    return stream_chunks(), holder


def _gemini_generate_followup_stream(
    previous_response_id: str,
    question: str,
    language: str | None = None,
    model: str = "gemini-2.0-flash-lite",
) -> tuple[Generator[str, None, None], dict]:
    conv_data = cache.get(f"ai_chat_{previous_response_id}")
    if not conv_data:
        raise ValueError("Conversation not found or expired")

    gemini_model = get_gemini_model(
        conv_data.get("model", model),
        language or conv_data.get("language"),
    )
    chat = gemini_model.start_chat(history=conv_data["history"])

    holder = {"response_id": None}

    def stream_chunks():
        response = chat.send_message(question, stream=True)
        full_text = ""
        for chunk in response:
            if chunk.text:
                full_text += chunk.text
                yield chunk.text

        conv_data["history"].append({"role": "user", "parts": [question]})
        conv_data["history"].append({"role": "model", "parts": [full_text]})
        new_conv_id = str(uuid.uuid4())
        cache.set(
            f"ai_chat_{new_conv_id}",
            conv_data,
            timeout=CONVERSATION_CACHE_TTL,
        )
        holder["response_id"] = new_conv_id

    return stream_chunks(), holder


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
    if provider and provider.name == "openai":
        from wildfire_assessment.svc.openai_analysis import (
            generate_analysis_stream as openai_stream,
        )

        return openai_stream(
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
        from wildfire_assessment.svc.openai_analysis import (
            generate_followup_stream as openai_followup,
        )

        return openai_followup(
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
    if provider and provider.name == "openai":
        from wildfire_assessment.svc.openai_analysis import (
            generate_followup_stream as openai_followup,
        )

        return openai_followup(
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
