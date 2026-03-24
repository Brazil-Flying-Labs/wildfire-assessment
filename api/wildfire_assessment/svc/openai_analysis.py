"""
OpenAI service for generating wildfire analysis reports.
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
    build_analysis_prompt,
)

LOG = logging.getLogger(__name__)


def _get_openai_client() -> OpenAI:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _build_user_content(prompt: str, image_urls: list | None = None) -> list:
    """Build OpenAI message content with text and optional images."""
    parts = [{"type": "text", "text": prompt}]
    for img in image_urls or []:
        url = img.get("url")
        label = img.get("label", "")
        if not url:
            continue
        if label:
            parts.append({"type": "text", "text": f"Image: {label}"})
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": url, "detail": "low"},
            }
        )
    return parts


def generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = "gpt-4o-mini",
) -> tuple[Generator[str, None, None], dict]:
    """
    Generate a streaming analysis using OpenAI.

    Returns:
        A tuple of (generator yielding text chunks, holder dict).
        holder["response_id"] is set after the generator is exhausted.
    """
    LOG.info("Starting analysis with OpenAI (model=%s)", model)
    client = _get_openai_client()
    prompt = build_analysis_prompt(
        pre_fire_date, post_fire_date, area_of_interest, severity_distribution
    )

    messages = [
        {"role": "system", "content": _get_instructions(language)},
        {"role": "user", "content": _build_user_content(prompt, image_urls)},
    ]

    holder = {"response_id": None}

    def stream_chunks():
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_completion_tokens=2000,
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
                "provider": "openai",
            },
            timeout=CONVERSATION_CACHE_TTL,
        )
        holder["response_id"] = conv_id

    return stream_chunks(), holder


def generate_followup_stream(
    previous_response_id: str,
    question: str,
    language: str | None = None,
    model: str = "gpt-4o-mini",
) -> tuple[Generator[str, None, None], dict]:
    """
    Generate a streaming follow-up response using cached conversation history.
    """
    LOG.info("Follow-up message with OpenAI (model=%s)", model)
    conv_data = cache.get(f"ai_chat_{previous_response_id}")
    if not conv_data:
        raise ValueError("Conversation not found or expired")

    client = _get_openai_client()
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
            max_completion_tokens=2000,
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
                "provider": "openai",
            },
            timeout=CONVERSATION_CACHE_TTL,
        )
        holder["response_id"] = new_conv_id

    return stream_chunks(), holder
