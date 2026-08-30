"""
DeepSeek service for generating wildfire analysis reports.

DeepSeek exposes an OpenAI-compatible chat completions API but accepts
text only — no image parts. The analysis prompt is therefore built in
text-only mode and no imagery is attached.
"""

import logging
import uuid
from typing import Generator

from django.conf import settings
from django.core.cache import cache
from openai import OpenAI
from wildfire_assessment.svc.ai_common import (
    CONVERSATION_CACHE_TTL,
    _get_instructions,
    _get_report_instructions,
    build_analysis_prompt,
)

LOG = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _get_deepseek_client() -> OpenAI:
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set")
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = DEFAULT_MODEL,
) -> tuple[Generator[str, None, None], dict]:
    """
    Generate a streaming analysis using DeepSeek (text-only).

    ``image_urls`` is accepted for interface parity with the other
    providers but intentionally ignored — DeepSeek does not accept images.
    """
    LOG.info("Starting analysis with DeepSeek (model=%s)", model)
    client = _get_deepseek_client()
    prompt = build_analysis_prompt(
        pre_fire_date,
        post_fire_date,
        area_of_interest,
        severity_distribution,
        include_images=False,
    )

    messages = [
        {"role": "system", "content": _get_instructions(language)},
        {"role": "user", "content": prompt},
    ]

    holder = {"response_id": None}

    def stream_chunks():
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )
        full_text = ""
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
                yield delta.content

        # Store conversation history for follow-ups
        conv_id = str(uuid.uuid4())
        history = messages + [{"role": "assistant", "content": full_text}]
        cache.set(
            f"ai_chat_{conv_id}",
            {
                "history": history,
                "model": model,
                "language": language,
                "provider": "deepseek",
            },
            timeout=CONVERSATION_CACHE_TTL,
        )
        holder["response_id"] = conv_id

    return stream_chunks(), holder


def generate_report(
    prompt: str,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Generate a complete (non-streaming) report using DeepSeek (text-only)."""
    LOG.info("Generating report with DeepSeek (model=%s)", model)
    client = _get_deepseek_client()
    messages = [
        {"role": "system", "content": _get_report_instructions(language)},
        {"role": "user", "content": prompt},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=4096,
    )
    return response.choices[0].message.content or ""


def generate_followup_stream(
    previous_response_id: str,
    question: str,
    language: str | None = None,
    model: str = DEFAULT_MODEL,
) -> tuple[Generator[str, None, None], dict]:
    """
    Generate a streaming follow-up response using cached conversation history.
    """
    LOG.info("Follow-up message with DeepSeek (model=%s)", model)
    conv_data = cache.get(f"ai_chat_{previous_response_id}")
    if not conv_data:
        raise ValueError("Conversation not found or expired")

    client = _get_deepseek_client()
    used_model = conv_data.get("model", model)
    used_language = language or conv_data.get("language")

    messages = list(conv_data["history"])
    # Update system instruction language if changed
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = _get_instructions(used_language)
    messages.append({"role": "user", "content": question})

    holder = {"response_id": None}

    def stream_chunks():
        response = client.chat.completions.create(
            model=used_model,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=4096,
        )
        full_text = ""
        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
                yield delta.content

        # Update conversation history and store with a new ID
        messages.append({"role": "assistant", "content": full_text})
        new_conv_id = str(uuid.uuid4())
        cache.set(
            f"ai_chat_{new_conv_id}",
            {
                "history": messages,
                "model": used_model,
                "language": used_language,
                "provider": "deepseek",
            },
            timeout=CONVERSATION_CACHE_TTL,
        )
        holder["response_id"] = new_conv_id

    return stream_chunks(), holder
