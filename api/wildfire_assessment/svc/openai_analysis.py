"""
OpenAI service for generating wildfire analysis reports.
"""

import os
from typing import Generator

from openai import OpenAI


def get_openai_client() -> OpenAI:
    """Get an OpenAI client instance."""
    api_key = os.environ.get("OPENAI_API_KEY")
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

Please provide:
1. **Executive Summary**: A brief overview of the fire impact
2. **Severity Analysis**: Interpretation of the burn severity distribution
3. **Environmental Impact**: Potential ecological consequences based on the severity levels
4. **Recovery Recommendations**: Suggested actions for ecosystem recovery
5. **Monitoring Priorities**: Areas that should be prioritized for post-fire monitoring

Use clear, professional language suitable for environmental agencies and land managers.
Format your response in markdown for readability."""

    return prompt


def generate_analysis_stream(
    pre_fire_date: str,
    post_fire_date: str,
    area_of_interest: str,
    severity_distribution: dict,
    model: str = "gpt-4o-mini",
) -> Generator[str, None, None]:
    """
    Generate a streaming analysis of the wildfire data using OpenAI.

    Args:
        pre_fire_date: Pre-fire date in YYYY-MM-DD format
        post_fire_date: Post-fire date in YYYY-MM-DD format
        area_of_interest: Name of the ecological reserve or area
        severity_distribution: Dictionary with severity levels and their areas/percentages
        model: OpenAI model to use (default: gpt-4o-mini)

    Yields:
        Chunks of the analysis text as they are generated
    """
    client = get_openai_client()
    prompt = build_analysis_prompt(
        pre_fire_date, post_fire_date, area_of_interest, severity_distribution
    )

    stream = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert environmental analyst specializing in wildfire damage assessment and ecological recovery.",
            },
            {"role": "user", "content": prompt},
        ],
        stream=True,
        temperature=0.7,
        max_tokens=2000,
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
