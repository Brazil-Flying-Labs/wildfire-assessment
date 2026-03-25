# AI-Generated Report Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded mock executive summary in the print report with a real AI-generated report, cached in the database, fetched via a new API endpoint.

**Architecture:** New `report_summary` + `report_summary_language` fields on `AnalysisRun`. New `generate_report_summary()` non-streaming function in `ai_common.py` dispatches to Gemini/OpenAI. New `@action` on `AnalysisRunViewSet` serves cached or freshly-generated reports. Frontend calls endpoint on "Print Report" click, renders markdown via `ReactMarkdown`.

**Tech Stack:** Django 5 / DRF, Celery, Google Gemini SDK, OpenAI SDK, React 19, react-markdown 10.1.0

**Spec:** `docs/superpowers/specs/2026-03-25-ai-report-summary-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `api/wildfire_assessment/models.py` | Modify (lines 196-198) | Add `report_summary` + `report_summary_language` fields |
| `api/wildfire_assessment/migrations/XXXX_add_report_summary.py` | Create | Migration for new fields |
| `api/wildfire_assessment/svc/ai_common.py` | Modify | Add `REPORT_SYSTEM_INSTRUCTIONS`, `build_report_prompt()`, `generate_report_summary()`, add es-ES to `LANGUAGE_MAP` |
| `api/wildfire_assessment/svc/gemini_analysis.py` | Modify | Add `_gemini_generate_report()` non-streaming function |
| `api/wildfire_assessment/svc/openai_analysis.py` | Modify | Add `_openai_generate_report()` non-streaming function |
| `api/wildfire_assessment/serializers.py` | Modify (lines 693-735, ~849) | Add `report_summary` to `AnalysisRunSerializer.Meta.fields`, add `ReportSummaryRequestSerializer` |
| `api/wildfire_assessment/views.py` | Modify (lines 579-591) | Add `report` action on `AnalysisRunViewSet` |
| `api/wildfire_assessment/tests/test_ai_analysis.py` | Modify | Add tests for `build_report_prompt`, `generate_report_summary`, provider dispatch |
| `api/wildfire_assessment/tests/test_apis.py` | Modify | Add `ReportEndpointTests` class |
| `api/wildfire_assessment/tests/test_serializers.py` | Modify | Add test for `report_summary` in serializer output + `ReportSummaryRequestSerializer` |
| `ui/src/features/analysis-detail/AnalysisDetail.js` | Modify | Add report loading state, print flow, regenerate handler |
| `ui/src/features/analysis-detail/PrintReport.js` | Modify | Replace mock summary with `ReactMarkdown`, add regenerate button |
| `ui/src/features/analysis-detail/PrintReport.css` | Modify | Add markdown rendering styles for print |
| `ui/src/translations/en.json` | Modify | Add new translation keys |
| `ui/src/translations/pt-BR.json` | Modify | Add new translation keys |
| `ui/src/translations/fr.json` | Modify | Add new translation keys |
| `ui/src/translations/es-ES.json` | Modify | Add new translation keys |
| Electron app counterparts | Sync | Copy modified UI files |

---

## Task 1: Model — Add report_summary fields

**Files:**
- Modify: `api/wildfire_assessment/models.py:196-198`
- Create: `api/wildfire_assessment/migrations/XXXX_add_report_summary.py`

- [ ] **Step 1: Add fields to AnalysisRun model**

In `api/wildfire_assessment/models.py`, add after line 198 (`completed_at`):

```python
    # AI-generated report summary (cached)
    report_summary = models.TextField(null=True, blank=True)
    report_summary_language = models.CharField(max_length=10, null=True, blank=True)
```

- [ ] **Step 2: Generate migration**

Run: `docker exec wildfire-api python manage.py makemigrations wildfire_assessment`
Expected: New migration file created.

- [ ] **Step 3: Apply migration**

Run: `docker exec wildfire-api python manage.py migrate`
Expected: Migration applied successfully.

- [ ] **Step 4: Commit**

```bash
git add api/wildfire_assessment/models.py api/wildfire_assessment/migrations/
git commit -m "feat: add report_summary fields to AnalysisRun model"
```

---

## Task 2: Serializer — Expose report_summary + add ReportSummaryRequestSerializer

**Files:**
- Modify: `api/wildfire_assessment/serializers.py:695-734` (Meta.fields list)
- Modify: `api/wildfire_assessment/serializers.py:~849` (add new serializer after AnalysisFollowUpSerializer)
- Test: `api/wildfire_assessment/tests/test_serializers.py`

- [ ] **Step 1: Write failing test for report_summary in AnalysisRunSerializer**

In `api/wildfire_assessment/tests/test_serializers.py`, in the `AnalysisRunSerializerTests` class (line 2266), add:

```python
    def test_report_summary_in_serialized_output(self):
        self.analysis.report_summary = "# Test Report\nSome content"
        self.analysis.report_summary_language = "en"
        self.analysis.save()
        serializer = AnalysisRunSerializer(self.analysis)
        self.assertIn("report_summary", serializer.data)
        self.assertEqual(serializer.data["report_summary"], "# Test Report\nSome content")
        self.assertIn("report_summary_language", serializer.data)
        self.assertEqual(serializer.data["report_summary_language"], "en")
```

- [ ] **Step 2: Write failing test for ReportSummaryRequestSerializer**

In `api/wildfire_assessment/tests/test_serializers.py`, add new class:

```python
class ReportSummaryRequestSerializerTests(TestCase):
    def test_defaults_to_english(self):
        serializer = ReportSummaryRequestSerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["language"], "en")

    def test_accepts_language(self):
        serializer = ReportSummaryRequestSerializer(data={"language": "pt-BR"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["language"], "pt-BR")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_serializers.AnalysisRunSerializerTests.test_report_summary_in_serialized_output wildfire_assessment.tests.test_serializers.ReportSummaryRequestSerializerTests -v2`
Expected: FAIL (field not in serializer, class not found)

- [ ] **Step 4: Add report_summary to AnalysisRunSerializer.Meta.fields**

In `api/wildfire_assessment/serializers.py`, add to the `fields` list (after `"roi_only_bg_color"` at line 733):

```python
            "report_summary",
            "report_summary_language",
```

- [ ] **Step 5: Add ReportSummaryRequestSerializer**

In `api/wildfire_assessment/serializers.py`, after `AnalysisFollowUpSerializer` (after line 849):

```python
class ReportSummaryRequestSerializer(serializers.Serializer):
    """Serializer for the report summary generation request."""

    language = serializers.CharField(
        required=False,
        default="en",
        help_text="Language code for the report (e.g., en, pt-BR, fr, es-ES)",
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_serializers.AnalysisRunSerializerTests.test_report_summary_in_serialized_output wildfire_assessment.tests.test_serializers.ReportSummaryRequestSerializerTests -v2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add api/wildfire_assessment/serializers.py api/wildfire_assessment/tests/test_serializers.py
git commit -m "feat: expose report_summary in serializer, add ReportSummaryRequestSerializer"
```

---

## Task 3: Service — build_report_prompt + generate_report_summary

**Files:**
- Modify: `api/wildfire_assessment/svc/ai_common.py`
- Modify: `api/wildfire_assessment/svc/gemini_analysis.py`
- Modify: `api/wildfire_assessment/svc/openai_analysis.py`
- Test: `api/wildfire_assessment/tests/test_ai_analysis.py`

- [ ] **Step 1: Write failing test for es-ES in LANGUAGE_MAP**

In `api/wildfire_assessment/tests/test_ai_analysis.py`, in `SharedHelperTests`:

```python
    def test_get_instructions_spanish(self):
        result = _get_instructions("es-ES")
        self.assertIn("Spanish", result)
```

- [ ] **Step 2: Write failing test for build_report_prompt**

In `api/wildfire_assessment/tests/test_ai_analysis.py`, add to `SharedHelperTests`:

```python
    def test_build_report_prompt_contains_metadata(self):
        from wildfire_assessment.svc.ai_common import build_report_prompt
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country
        from django.contrib.auth import get_user_model

        User = get_user_model()
        country = Country.objects.create(name="Brazil", code="BR")
        area = AreaOfInterest.objects.create(
            name="Serra da Canastra", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="t", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=500.0,
            severity_data={
                "Unburned": {"area_ha": 100.0, "percent": 20.0},
                "High": {"area_ha": 400.0, "percent": 80.0},
            },
        )
        prompt = build_report_prompt(run)
        self.assertIn("Serra da Canastra", prompt)
        self.assertIn("Brazil", prompt)
        self.assertIn("2024-06-01", prompt)
        self.assertIn("500.0", prompt)
        self.assertIn("High", prompt)
        self.assertIn("80.0", prompt)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_ai_analysis.SharedHelperTests.test_get_instructions_spanish wildfire_assessment.tests.test_ai_analysis.SharedHelperTests.test_build_report_prompt_contains_metadata -v2`
Expected: FAIL

- [ ] **Step 4: Add es-ES to LANGUAGE_MAP and add REPORT_SYSTEM_INSTRUCTIONS + build_report_prompt**

In `api/wildfire_assessment/svc/ai_common.py`:

Add `"es-ES": "Spanish"` to `LANGUAGE_MAP` (line 26, before the closing `}`).

Add after `build_analysis_prompt` (after line 88):

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_ai_analysis.SharedHelperTests.test_get_instructions_spanish wildfire_assessment.tests.test_ai_analysis.SharedHelperTests.test_build_report_prompt_contains_metadata -v2`
Expected: PASS

- [ ] **Step 6: Add non-streaming Gemini report function**

In `api/wildfire_assessment/svc/gemini_analysis.py`, add import at top:

```python
from wildfire_assessment.svc.ai_common import (
    CONVERSATION_CACHE_TTL,
    _get_instructions,
    _get_report_instructions,
    build_analysis_prompt,
)
```

Add new function after `_gemini_generate_analysis_stream` (after line 116):

```python
def _gemini_generate_report(
    prompt: str,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = "gemini-2.0-flash-lite",
) -> str:
    """Generate a complete (non-streaming) report using Gemini."""
    LOG.info("Generating report with Gemini (model=%s)", model)
    client = _get_gemini_client()
    config = types.GenerateContentConfig(
        system_instruction=_get_report_instructions(language),
        temperature=0.7,
        max_output_tokens=4096,
    )

    contents = [prompt]
    contents.extend(_build_image_content(image_urls))

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    return response.text or ""
```

- [ ] **Step 7: Add non-streaming OpenAI report function**

In `api/wildfire_assessment/svc/openai_analysis.py`, add import at top:

```python
from wildfire_assessment.svc.ai_common import (
    CONVERSATION_CACHE_TTL,
    _get_instructions,
    _get_report_instructions,
    build_analysis_prompt,
)
```

Add new function after `generate_analysis_stream` (after line 106):

```python
def generate_report(
    prompt: str,
    image_urls: list | None = None,
    language: str | None = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Generate a complete (non-streaming) report using OpenAI."""
    LOG.info("Generating report with OpenAI (model=%s)", model)
    client = _get_openai_client()
    messages = [
        {"role": "system", "content": _get_report_instructions(language)},
        {"role": "user", "content": _build_user_content(prompt, image_urls)},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_completion_tokens=4096,
    )
    return response.choices[0].message.content or ""
```

- [ ] **Step 8: Add generate_report_summary dispatch function to ai_common.py**

In `api/wildfire_assessment/svc/ai_common.py`, add the new provider imports after the existing ones (after line 104):

```python
from wildfire_assessment.svc.gemini_analysis import (
    _gemini_generate_report,
)
from wildfire_assessment.svc.openai_analysis import (
    generate_report as _openai_generate_report,
)
```

Add new dispatch function after `generate_analysis_stream` (after line 147):

Add module-level imports at the top of `ai_common.py` (after `from wildfire_assessment.models import AIProvider`):

```python
import base64

import requests
```

Then add the dispatch function:

```python
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
            image_urls.append({"label": label, "url": f"data:{content_type};base64,{b64}"})
        except Exception:
            LOG.warning("Failed to fetch image %s for report, skipping", label)

    provider = get_active_provider()
    if provider and provider.provider == "openai":
        model = provider.model_name if provider else "gpt-4o-mini"
        text = _openai_generate_report(
            prompt=prompt, image_urls=image_urls, language=language, model=model
        )
    else:
        model = provider.model_name if provider else "gemini-2.0-flash-lite"
        text = _gemini_generate_report(
            prompt=prompt, image_urls=image_urls, language=language, model=model
        )

    # Save to DB (shadow replacement: only on success)
    analysis_run.report_summary = text
    analysis_run.report_summary_language = language
    analysis_run.save(update_fields=["report_summary", "report_summary_language"])

    return text
```

- [ ] **Step 9: Write tests for Gemini non-streaming report**

In `api/wildfire_assessment/tests/test_ai_analysis.py`, add to `GeminiStreamTests`:

```python
    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_generate_report_returns_text(self, mock_client_fn):
        from wildfire_assessment.svc.gemini_analysis import _gemini_generate_report

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# Report\nContent here"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = _gemini_generate_report(prompt="test prompt", language="en")
        self.assertEqual(result, "# Report\nContent here")
        mock_client.models.generate_content.assert_called_once()

    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_generate_report_with_images(self, mock_client_fn):
        from wildfire_assessment.svc.gemini_analysis import _gemini_generate_report

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Report with images"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        images = [{"label": "dNBR", "url": "data:image/png;base64,iVBOR"}]
        result = _gemini_generate_report(prompt="test", image_urls=images, language="pt-BR")
        self.assertEqual(result, "Report with images")

    @patch("wildfire_assessment.svc.gemini_analysis._get_gemini_client")
    def test_gemini_generate_report_empty_response(self, mock_client_fn):
        from wildfire_assessment.svc.gemini_analysis import _gemini_generate_report

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = _gemini_generate_report(prompt="test")
        self.assertEqual(result, "")
```

- [ ] **Step 10: Write tests for OpenAI non-streaming report**

In `api/wildfire_assessment/tests/test_ai_analysis.py`, add to `OpenAIAnalysisTests`:

```python
    @patch("wildfire_assessment.svc.openai_analysis._get_openai_client")
    def test_openai_generate_report_returns_text(self, mock_client_fn):
        from wildfire_assessment.svc.openai_analysis import generate_report as openai_generate_report

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "# OpenAI Report\nContent"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = openai_generate_report(prompt="test prompt", language="en")
        self.assertEqual(result, "# OpenAI Report\nContent")
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertFalse(call_kwargs.get("stream", False))

    @patch("wildfire_assessment.svc.openai_analysis._get_openai_client")
    def test_openai_generate_report_empty_response(self, mock_client_fn):
        from wildfire_assessment.svc.openai_analysis import generate_report as openai_generate_report

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_fn.return_value = mock_client

        result = openai_generate_report(prompt="test")
        self.assertEqual(result, "")
```

- [ ] **Step 11: Write test for generate_report_summary dispatch**

In `api/wildfire_assessment/tests/test_ai_analysis.py`, add to `ProviderDispatchTests`:

```python
    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_gemini(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        from wildfire_assessment.svc.ai_common import generate_report_summary
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country
        from django.contrib.auth import get_user_model

        User = get_user_model()
        country = Country.objects.create(name="Brazil", code="BR")
        area = AreaOfInterest.objects.create(
            name="Test Area", polygon_path="p.json", country=country
        )
        user = User.objects.create_user(username="rpt", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.0,
            severity_data={"High": {"area_ha": 100.0, "percent": 100.0}},
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_gemini_report.return_value = "# Generated Report"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "# Generated Report")
        mock_gemini_report.assert_called_once()
        run.refresh_from_db()
        self.assertEqual(run.report_summary, "# Generated Report")
        self.assertEqual(run.report_summary_language, "en")

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    @patch("wildfire_assessment.svc.ai_common._openai_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_openai(
        self, mock_provider, mock_openai_report, mock_presigned, mock_requests
    ):
        from wildfire_assessment.svc.ai_common import generate_report_summary
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country
        from django.contrib.auth import get_user_model

        User = get_user_model()
        country = Country.objects.create(name="Brazil", code="BR2")
        area = AreaOfInterest.objects.create(
            name="Test Area 2", polygon_path="p2.json", country=country
        )
        user = User.objects.create_user(username="rpt2", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            total_burned_ha=200.0,
            severity_data={"Low": {"area_ha": 200.0, "percent": 100.0}},
        )

        mock_prov = MagicMock()
        mock_prov.provider = "openai"
        mock_prov.model_name = "gpt-4o-mini"
        mock_provider.return_value = mock_prov
        mock_openai_report.return_value = "# OpenAI Report"

        result = generate_report_summary(run, language="pt-BR")
        self.assertEqual(result, "# OpenAI Report")
        mock_openai_report.assert_called_once()
        run.refresh_from_db()
        self.assertEqual(run.report_summary, "# OpenAI Report")
        self.assertEqual(run.report_summary_language, "pt-BR")

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_fetches_images(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        from wildfire_assessment.svc.ai_common import generate_report_summary
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country
        from django.contrib.auth import get_user_model

        User = get_user_model()
        country = Country.objects.create(name="Brazil", code="BR3")
        area = AreaOfInterest.objects.create(
            name="Test Area 3", polygon_path="p3.json", country=country
        )
        user = User.objects.create_user(username="rpt3", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-03-01",
            post_fire_date="2024-03-15",
            total_burned_ha=50.0,
            severity_data={},
            dnbr_image="test_dnbr.png",
            rbr_image="test_rbr.png",
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_presigned.return_value = "https://s3.example.com/signed"
        mock_resp = MagicMock()
        mock_resp.content = b"fake_image_bytes"
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_resp
        mock_gemini_report.return_value = "Report"

        generate_report_summary(run, language="en")

        # Should have fetched 2 images (dnbr + rbr)
        self.assertEqual(mock_requests.get.call_count, 2)
        image_urls = mock_gemini_report.call_args.kwargs["image_urls"]
        # Check that images were passed to the provider
        self.assertEqual(len(image_urls), 2)

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_no_provider_defaults_to_gemini(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        from wildfire_assessment.svc.ai_common import generate_report_summary
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country
        from django.contrib.auth import get_user_model

        User = get_user_model()
        country = Country.objects.create(name="Brazil", code="BR4")
        area = AreaOfInterest.objects.create(
            name="Test Area 4", polygon_path="p4.json", country=country
        )
        user = User.objects.create_user(username="rpt4", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-04-01",
            post_fire_date="2024-04-15",
            total_burned_ha=75.0,
            severity_data={"Low": {"area_ha": 75.0, "percent": 100.0}},
        )

        mock_provider.return_value = None
        mock_gemini_report.return_value = "# Default Report"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "# Default Report")
        mock_gemini_report.assert_called_once()

    @patch("wildfire_assessment.svc.ai_common.requests")
    @patch("wildfire_assessment.svc.aws.get_presigned_image_url")
    @patch("wildfire_assessment.svc.ai_common._gemini_generate_report")
    @patch("wildfire_assessment.svc.ai_common.get_active_provider")
    def test_generate_report_summary_null_language_cached(
        self, mock_provider, mock_gemini_report, mock_presigned, mock_requests
    ):
        """Test that report_summary with None language triggers regeneration."""
        from wildfire_assessment.svc.ai_common import generate_report_summary
        from wildfire_assessment.models import AnalysisRun, AreaOfInterest, Country
        from django.contrib.auth import get_user_model

        User = get_user_model()
        country = Country.objects.create(name="Brazil", code="BR5")
        area = AreaOfInterest.objects.create(
            name="Test Area 5", polygon_path="p5.json", country=country
        )
        user = User.objects.create_user(username="rpt5", password="p")
        run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-05-01",
            post_fire_date="2024-05-15",
            total_burned_ha=60.0,
            severity_data={},
            report_summary="# Old report",
            report_summary_language=None,
        )

        mock_prov = MagicMock()
        mock_prov.provider = "gemini"
        mock_prov.model_name = "gemini-2.0-flash-lite"
        mock_provider.return_value = mock_prov
        mock_gemini_report.return_value = "# New Report"

        result = generate_report_summary(run, language="en")
        self.assertEqual(result, "# New Report")
```

- [ ] **Step 12: Run all AI tests to verify**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_ai_analysis -v2`
Expected: All tests PASS

- [ ] **Step 13: Commit**

```bash
git add api/wildfire_assessment/svc/ai_common.py api/wildfire_assessment/svc/gemini_analysis.py api/wildfire_assessment/svc/openai_analysis.py api/wildfire_assessment/tests/test_ai_analysis.py
git commit -m "feat: add build_report_prompt, generate_report_summary, non-streaming provider functions"
```

---

## Task 4: API Endpoint — report action on AnalysisRunViewSet

**Files:**
- Modify: `api/wildfire_assessment/views.py:579-591`
- Test: `api/wildfire_assessment/tests/test_apis.py`

- [ ] **Step 1: Write failing tests for the report endpoint**

In `api/wildfire_assessment/tests/test_apis.py`, add new test class:

```python
class ReportEndpointTests(APITestCase):
    """Tests for the POST /analysis_run/{id}/report/ endpoint."""

    def setUp(self):
        self.country = Country.objects.create(name="Test Country", code="TC")
        self.area = AreaOfInterest.objects.create(
            name="Test Area", polygon_path="polygon.json", country=self.country
        )
        self.user = User.objects.create_user(
            username="tester", email="tester@example.com", password="password"
        )
        UserCountry.objects.create(user=self.user, country=self.country)
        self.analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            total_burned_ha=100.5,
            severity_data={"High": {"area_ha": 100.5, "percent": 100.0}},
        )

    def test_report_requires_authentication(self):
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_report_returns_cached_summary(self):
        self.analysis.report_summary = "# Cached Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["report_summary"], "# Cached Report")

    def test_report_regenerates_on_language_mismatch(self):
        self.analysis.report_summary = "# English Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        with patch(
            "wildfire_assessment.views.generate_report_summary"
        ) as mock_gen:
            mock_gen.return_value = "# Relatório em Português"
            response = self.client.post(url, {"language": "pt-BR"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_gen.assert_called_once()
            self.assertEqual(
                response.json()["report_summary"], "# Relatório em Português"
            )

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_generates_fresh_summary(self, mock_gen):
        mock_gen.return_value = "# Fresh Report"

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["report_summary"], "# Fresh Report")
        mock_gen.assert_called_once()

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_regenerate_forces_new_generation(self, mock_gen):
        self.analysis.report_summary = "# Old Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        mock_gen.return_value = "# New Report"

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id]) + "?regenerate=true"
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["report_summary"], "# New Report")
        mock_gen.assert_called_once()

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_preserves_old_on_failure(self, mock_gen):
        self.analysis.report_summary = "# Old Report"
        self.analysis.report_summary_language = "en"
        self.analysis.save()

        mock_gen.side_effect = Exception("AI provider error")

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id]) + "?regenerate=true"
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.analysis.refresh_from_db()
        self.assertEqual(self.analysis.report_summary, "# Old Report")

    @patch("wildfire_assessment.views.generate_report_summary")
    def test_report_returns_502_on_empty_response(self, mock_gen):
        mock_gen.return_value = ""

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[self.analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_report_returns_404_for_unauthorized(self):
        other_country = Country.objects.create(name="Other", code="OC")
        other_area = AreaOfInterest.objects.create(
            name="Other Area", polygon_path="p2.json", country=other_country
        )
        other_analysis = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=other_area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("analysisrun-report", args=[other_analysis.id])
        response = self.client.post(url, {"language": "en"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_apis.ReportEndpointTests -v2`
Expected: FAIL (URL not found)

- [ ] **Step 3: Implement the report action**

In `api/wildfire_assessment/views.py`, add `generate_report_summary` to the existing `from wildfire_assessment.svc.ai_common import (...)` block, and add `ReportSummaryRequestSerializer` to the existing `from wildfire_assessment.serializers import (...)` block.

Add new action after `validate_urls` (after line 590, before the closing of `AnalysisRunViewSet`):

```python
    @extend_schema(
        methods=["POST"],
        request=ReportSummaryRequestSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "report_summary": {"type": "string"},
                    },
                },
                description="Generated or cached report summary in markdown",
            )
        },
    )
    @action(detail=True, methods=["post"], url_path="report")
    def report(self, request, pk=None):
        """Generate or return a cached AI report summary."""
        instance = self.get_object()
        serializer = ReportSummaryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        language = serializer.validated_data["language"]
        regenerate = request.query_params.get("regenerate", "").lower() == "true"

        # Return cached summary if language matches and no regeneration requested
        if (
            instance.report_summary
            and instance.report_summary_language == language
            and not regenerate
        ):
            return Response({"report_summary": instance.report_summary})

        try:
            summary = generate_report_summary(instance, language=language)
            if not summary:
                return Response(
                    {"error": "AI provider returned an empty report"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            return Response({"report_summary": summary})
        except Exception:
            LOG.exception("Failed to generate report summary")
            return Response(
                {"error": "Failed to generate report summary"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_apis.ReportEndpointTests -v2`
Expected: All PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"`
Expected: All tests pass, coverage at 100%

- [ ] **Step 6: Commit**

```bash
git add api/wildfire_assessment/views.py api/wildfire_assessment/tests/test_apis.py
git commit -m "feat: add report action on AnalysisRunViewSet for AI report summary"
```

---

## Task 5: Frontend — AnalysisDetail print flow with loading state

**Files:**
- Modify: `ui/src/features/analysis-detail/AnalysisDetail.js`
- Modify: `ui/src/translations/en.json`
- Modify: `ui/src/translations/pt-BR.json`
- Modify: `ui/src/translations/fr.json`
- Modify: `ui/src/translations/es-ES.json`

- [ ] **Step 1: Add new translation keys**

Add to all 4 translation files:

**en.json:**
```json
"report.generating": "Generating AI report summary...",
"report.generateError": "Failed to generate report. Please try again.",
"report.regenerate": "Regenerate",
"report.regenerating": "Regenerating...",
"report.noSummary": "No AI summary available. Click Print Report to generate one."
```

**pt-BR.json:**
```json
"report.generating": "Gerando resumo do relatório com IA...",
"report.generateError": "Falha ao gerar relatório. Tente novamente.",
"report.regenerate": "Regenerar",
"report.regenerating": "Regenerando...",
"report.noSummary": "Nenhum resumo de IA disponível. Clique em Imprimir Relatório para gerar."
```

**fr.json:**
```json
"report.generating": "Génération du résumé du rapport par IA...",
"report.generateError": "Échec de la génération du rapport. Veuillez réessayer.",
"report.regenerate": "Régénérer",
"report.regenerating": "Régénération...",
"report.noSummary": "Aucun résumé IA disponible. Cliquez sur Imprimer le rapport pour en générer un."
```

**es-ES.json:**
```json
"report.generating": "Generando resumen del informe con IA...",
"report.generateError": "Error al generar el informe. Inténtelo de nuevo.",
"report.regenerate": "Regenerar",
"report.regenerating": "Regenerando...",
"report.noSummary": "No hay resumen de IA disponible. Haga clic en Imprimir informe para generar uno."
```

- [ ] **Step 2: Update AnalysisDetail.js with report flow**

Add new state variables and the print handler. Key changes:

1. Add `useLanguage` import for current language code
2. Add state: `reportSummary`, `reportLoading`, `reportError`
3. Initialize `reportSummary` from `analysis.report_summary` when analysis loads
4. Replace direct `window.print()` with `handlePrintReport()` that:
   - If `reportSummary` exists, print immediately
   - Otherwise, call the report endpoint, set state, then print
5. Add `handleRegenerate()` for the regenerate button
6. Pass `reportSummary`, `reportLoading`, `onRegenerate`, `reportError` to `<PrintReport>`

In `AnalysisDetail.js`, at the top, add to the `useLanguage` import:

```javascript
const { t, language } = useLanguage();
```

Add state after existing state declarations:

```javascript
const [reportSummary, setReportSummary] = useState(null);
const [reportLoading, setReportLoading] = useState(false);
const [reportError, setReportError] = useState(null);
```

Add effect to initialize from cached analysis data (after `loadAnalysis` effect):

```javascript
useEffect(() => {
  if (analysis?.report_summary) {
    setReportSummary(analysis.report_summary);
  }
}, [analysis]);
```

Add print handler:

```javascript
const handlePrintReport = useCallback(async () => {
  if (reportSummary) {
    window.print();
    return;
  }

  setReportLoading(true);
  setReportError(null);

  try {
    const response = await authorizedFetch(
      `${baseUrl}/analysis_run/${analysisId}/report/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language }),
      }
    );

    if (!response.ok) {
      throw new Error(t("report.generateError"));
    }

    const data = await response.json();
    setReportSummary(data.report_summary);
    setTimeout(() => window.print(), 100);
  } catch (err) {
    console.error("Failed to generate report:", err);
    setReportError(err.message || t("report.generateError"));
  } finally {
    setReportLoading(false);
  }
}, [reportSummary, authorizedFetch, baseUrl, analysisId, language, t]);
```

Add regenerate handler:

```javascript
const handleRegenerate = useCallback(async () => {
  setReportLoading(true);
  setReportError(null);

  try {
    const response = await authorizedFetch(
      `${baseUrl}/analysis_run/${analysisId}/report/?regenerate=true`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language }),
      }
    );

    if (!response.ok) {
      throw new Error(t("report.generateError"));
    }

    const data = await response.json();
    setReportSummary(data.report_summary);
  } catch (err) {
    console.error("Failed to regenerate report:", err);
    setReportError(err.message || t("report.generateError"));
  } finally {
    setReportLoading(false);
  }
}, [authorizedFetch, baseUrl, analysisId, language, t]);
```

Replace the print button's `onClick={() => window.print()}` with `onClick={handlePrintReport}`.

Update `<PrintReport>` props:

```jsx
<PrintReport
  analysis={analysis}
  severityEntries={severityEntries}
  imageEntries={imageEntries}
  reportSummary={reportSummary}
  reportLoading={reportLoading}
  reportError={reportError}
  onRegenerate={handleRegenerate}
  t={t}
/>
```

Add loading overlay after the print button (inside the header div):

```jsx
{reportLoading && (
  <div className="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center no-print"
    style={{ backgroundColor: "rgba(0,0,0,0.5)", zIndex: 9999 }}>
    <div className="bg-white rounded p-4 text-center shadow">
      <div className="spinner-border text-primary mb-3" role="status">
        <span className="visually-hidden">{t("common.loading")}</span>
      </div>
      <p className="mb-0">{t("report.generating")}</p>
    </div>
  </div>
)}
```

Add error toast after loading overlay:

```jsx
{reportError && (
  <div className="alert alert-danger alert-dismissible fade show position-fixed bottom-0 end-0 m-3 no-print" style={{ zIndex: 9999 }} role="alert">
    {reportError}
    <button type="button" className="btn-close" onClick={() => setReportError(null)} />
  </div>
)}
```

- [ ] **Step 3: Commit**

```bash
git add ui/src/features/analysis-detail/AnalysisDetail.js ui/src/translations/
git commit -m "feat: add report generation flow to AnalysisDetail with loading state"
```

---

## Task 6: Frontend — PrintReport.js with ReactMarkdown

**Files:**
- Modify: `ui/src/features/analysis-detail/PrintReport.js`
- Modify: `ui/src/features/analysis-detail/PrintReport.css`

- [ ] **Step 1: Update PrintReport.js to accept and render reportSummary**

Key changes:
1. Add `import ReactMarkdown from "react-markdown"` at the top
2. Add `reportSummary`, `onRegenerate`, `reportLoading` to props
3. Replace the entire hardcoded executive summary section with:

```jsx
{/* Executive Summary */}
<div className="pr-section">
  <div className="pr-section-head">
    <svg className="pr-section-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
    <h3>{t("report.executiveSummary")}</h3>
    <span className="pr-ai-badge">{t("report.aiGenerated")}</span>
    {onRegenerate && (
      <button
        type="button"
        className="btn btn-outline-primary btn-sm ms-auto no-print"
        onClick={onRegenerate}
        disabled={reportLoading}
      >
        {reportLoading ? t("report.regenerating") : t("report.regenerate")}
      </button>
    )}
  </div>
  <div className="pr-summary-body pr-markdown">
    {reportSummary ? (
      <ReactMarkdown>{reportSummary}</ReactMarkdown>
    ) : (
      <p className="text-muted fst-italic">{t("report.noSummary")}</p>
    )}
  </div>
</div>
```

4. Remove the `summary` useMemo, `computeSummaryData`, `getSeverityAssessmentKey` and all the hardcoded summary paragraphs/recommendations — they are fully replaced by the AI content.

- [ ] **Step 2: Add markdown print styles to PrintReport.css**

Add inside the `@media print` block:

```css
  /* ── Markdown content in summary ── */
  .pr-markdown h1 {
    font-size: 13pt !important;
    font-weight: 700 !important;
    margin: 14px 0 6px 0 !important;
    border-bottom: 1px solid #ddd !important;
    padding-bottom: 4px;
  }

  .pr-markdown h2 {
    font-size: 12pt !important;
    font-weight: 700 !important;
    margin: 12px 0 5px 0 !important;
  }

  .pr-markdown h3 {
    font-size: 11pt !important;
    font-weight: 600 !important;
    margin: 10px 0 4px 0 !important;
  }

  .pr-markdown p {
    margin: 0 0 8px 0 !important;
    color: #333 !important;
  }

  .pr-markdown ul,
  .pr-markdown ol {
    margin: 4px 0 8px 0 !important;
    padding-left: 20px !important;
  }

  .pr-markdown li {
    margin-bottom: 3px !important;
    color: #333 !important;
  }

  .pr-markdown strong {
    font-weight: 700 !important;
  }

  .pr-markdown em {
    font-style: italic !important;
  }

  .pr-markdown hr {
    border: none !important;
    border-top: 1px solid #ddd !important;
    margin: 10px 0 !important;
  }
```

- [ ] **Step 3: Commit**

```bash
git add ui/src/features/analysis-detail/PrintReport.js ui/src/features/analysis-detail/PrintReport.css
git commit -m "feat: replace mock summary with ReactMarkdown rendering in PrintReport"
```

---

## Task 7: Cross-Platform Sync

**Files:**
- Sync all modified UI files to Electron app
- Sync translation files to mobile app

- [ ] **Step 1: Sync to Electron app**

Copy these files from `wildfire-assessment/ui/src/` to `wildfire-assessment-electron/src/`:

```bash
cp ui/src/features/analysis-detail/AnalysisDetail.js /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/features/analysis-detail/AnalysisDetail.js
cp ui/src/features/analysis-detail/PrintReport.js /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/features/analysis-detail/PrintReport.js
cp ui/src/features/analysis-detail/PrintReport.css /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/features/analysis-detail/PrintReport.css
```

- [ ] **Step 2: Sync translations to Electron app**

```bash
cp ui/src/translations/en.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/en.json
cp ui/src/translations/pt-BR.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/pt-BR.json
cp ui/src/translations/fr.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/fr.json
cp ui/src/translations/es-ES.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/es-ES.json
```

- [ ] **Step 3: Sync translations to mobile app**

```bash
cp ui/src/translations/en.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/en.json
cp ui/src/translations/pt-BR.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/pt-BR.json
cp ui/src/translations/fr.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/fr.json
cp ui/src/translations/es-ES.json /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/es-ES.json
```

- [ ] **Step 4: Commit Electron app changes**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron
git add src/features/analysis-detail/ src/translations/
git commit -m "feat: sync AI report summary changes from web app"
```

- [ ] **Step 5: Commit mobile app translation changes**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app
git add translations/
git commit -m "feat: sync translation keys for AI report summary"
```

---

## Task 8: Full Verification

- [ ] **Step 1: Run full backend test suite with coverage**

Run: `docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"`
Expected: All tests pass, 100% coverage

- [ ] **Step 2: Build frontend**

Run: `docker exec wildfire-ui npx react-scripts build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Format backend code**

Run: `docker exec wildfire-api bash -c "cd /api && black wildfire_assessment --config pyproject.toml && isort wildfire_assessment --profile black"`
Expected: No formatting changes needed (or auto-fixed)

- [ ] **Step 4: Final commit if formatting changes were needed**

```bash
git add -A
git commit -m "chore: format code with black and isort"
```
