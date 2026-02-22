"""
Google Gemini streaming service for wildfire analysis reports.
"""

import base64
import binascii
import logging
import uuid
from typing import Generator

from django.conf import settings
from django.core.cache import cache
from google import genai
from google.genai import types
from wildfire_assessment.svc.ai_common import (
    CONVERSATION_CACHE_TTL,
    _get_instructions,
    build_analysis_prompt,
)

LOG = logging.getLogger(__name__)


def _get_gemini_client() -> genai.Client:
    """Get a configured Gemini client instance."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _get_gemini_config(language: str | None = None) -> types.GenerateContentConfig:
    """Build a Gemini generation config."""
    return types.GenerateContentConfig(
        system_instruction=_get_instructions(language),
        temperature=0.7,
        max_output_tokens=2000,
    )


def _parse_data_url(data_url: str):
    """Parse a data URL into a Gemini Part."""
    try:
        header, data = data_url.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
        return types.Part.from_bytes(
            data=base64.b64decode(data), mime_type=mime_type
        )
    except (ValueError, IndexError, binascii.Error):
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


def _gemini_generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = "gemini-2.0-flash-lite",
) -> tuple[Generator[str, None, None], dict]:
    client = _get_gemini_client()
    config = _get_gemini_config(language)
    prompt = build_analysis_prompt(
        pre_fire_date, post_fire_date, area_of_interest, severity_distribution
    )

    contents = [prompt]
    contents.extend(_build_image_content(image_urls))

    holder = {"response_id": None}

    def stream_chunks():
        full_text = ""
        for chunk in client.models.generate_content_stream(
            model=model, contents=contents, config=config,
        ):
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

    client = _get_gemini_client()
    used_model = conv_data.get("model", model)
    config = _get_gemini_config(language or conv_data.get("language"))

    # Convert cached history dicts to Content objects
    history = [
        types.Content(
            role=msg["role"],
            parts=[types.Part.from_text(text=p) for p in msg["parts"]],
        )
        for msg in conv_data["history"]
    ]

    chat = client.chats.create(model=used_model, config=config, history=history)

    holder = {"response_id": None}

    def stream_chunks():
        full_text = ""
        for chunk in chat.send_message_stream(message=question):
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
