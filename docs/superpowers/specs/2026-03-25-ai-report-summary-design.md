# AI-Generated Report Summary for Print Reports

## Overview

Replace the hardcoded mock executive summary in the print report with a real AI-generated analysis. When the user clicks "Print Report", the system checks the database for a cached report summary. If none exists, it calls the configured AI provider (Gemini or OpenAI) to generate one, caches it, then renders and prints.

## Requirements

- Generate a structured technical analysis from a senior remote sensing scientist persona
- Backend fetches satellite images from S3 and sends them to the AI provider
- Write the summary in the user's preferred language
- Render formatted markdown (bold, italics, bullets, numbered lists) in the print report
- Cache the generated report in the database to avoid redundant API calls
- Allow users to regenerate the report on demand
- Support both Gemini and OpenAI providers (existing abstraction)

## Architecture

### 1. Model Change

Add two fields to `AnalysisRun`:

```python
report_summary = models.TextField(null=True, blank=True)
report_summary_language = models.CharField(max_length=10, null=True, blank=True)
```

Migration required. Nullable so existing records are unaffected.

`report_summary_language` tracks which language the cached summary was generated in. If the user's current language differs from the cached language, the report is regenerated.

### 2. Service Layer (`svc/ai_common.py`)

**New function:** `generate_report_summary(analysis_run, language="en")`

- **Non-streaming** (unlike the existing chat which streams) — uses the same provider dispatch but collects the full response
- Builds a dedicated prompt via a new `build_report_prompt(analysis_run)` function (separate from the existing `build_analysis_prompt()` used for chat)
- Appends language instruction via existing `_get_instructions(language)` pattern
- Fetches satellite images from S3 server-side using the `AnalysisRun` image URL fields (`dnbr_url`, `rbr_url`, `dndvi_url`, `rgb_pre_fire_url`, `rgb_post_fire_url`) — generates fresh presigned URLs via `get_presigned_image_url()` from `aws.py`, then fetches and converts to base64
- Uses `max_output_tokens=4096` (higher than the chat's 2000) to accommodate the structured multi-section report
- Saves the generated markdown to `analysis_run.report_summary` and `analysis_run.report_summary_language`
- Returns the markdown string

**Language map fix:** Add `"es-ES": "Spanish"` to `LANGUAGE_MAP`. This is a pre-existing gap — `es-ES` is already in `LANGUAGE_CHOICES` on the model but was missing from the map, causing Spanish-language users to get English AI responses in the existing chat feature too.

### 3. API Endpoint

Implemented as a `@action` on `AnalysisRunViewSet` (consistent with existing `task_status` and `validate_urls` actions):

```python
@action(detail=True, methods=["post"], url_path="report")
def report(self, request, pk=None):
    ...
```

This produces the URL `analysis_run/{pk}/report/` via the DRF router.

**Authorization:** Handled implicitly by `AnalysisRunViewSet.get_queryset()` which filters by user country access. `self.get_object()` raises 404 for unauthorized users. This is the same pattern used by all other actions on this ViewSet.

**Request body validated by `ReportSummaryRequestSerializer`:**

```python
class ReportSummaryRequestSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, default="en")
```

No images in the request body — the backend fetches them from S3 directly using the `AnalysisRun` image URL fields. This avoids large base64 payloads (5 satellite images could be 5-15MB base64-encoded, exceeding Django's default 2.5MB upload limit).

**Query params:**
- `?regenerate=true` — forces regeneration even if cached

**Logic:**
1. If `analysis_run.report_summary` exists AND `report_summary_language` matches the requested language AND `regenerate` is not true → return cached summary
2. Otherwise, call `generate_report_summary()` with the requested language
3. On regeneration failure: keep the existing `report_summary` intact (shadow replacement pattern — only overwrite on success)
4. Return `{"report_summary": "..."}`

**Add `report_summary` to `AnalysisRunSerializer.Meta.fields`** so the frontend can detect a cached summary when loading the analysis detail page (avoids unnecessary report endpoint calls).

### 4. Frontend Changes

**AnalysisDetail.js:**
- New state: `reportSummary` (initialized from `analysis.report_summary` if present), `reportLoading`, `reportError`
- On "Print Report" click:
  1. If `reportSummary` already in state, go directly to print
  2. Otherwise show loading overlay, call `POST /analysis_run/{id}/report/` with `{language: currentLanguage}`
  3. On success: set `reportSummary`, trigger `window.print()`
  4. On error: show error toast, don't print
- On "Regenerate" click: call endpoint with `?regenerate=true`, update state on success
- Pass `reportSummary` and `onRegenerate` to `<PrintReport>`

**PrintReport.js:**
- Replace hardcoded mock summary with `<ReactMarkdown>{reportSummary}</ReactMarkdown>` (react-markdown v10.1.0 already installed)
- Show placeholder text when no summary available
- Add small "Regenerate" button near AI badge (hidden during print via `no-print` class)

**PrintReport.css:**
- Add styles for markdown content inside `.pr-summary-body` (headings, lists, bold, italic, paragraphs)

### 5. Prompt

**`build_report_prompt(analysis_run)`** — new function alongside existing `build_analysis_prompt()`.

System instruction (sent as system message to AI provider):

```
You are a senior remote sensing scientist specialized in wildfire impact assessment and post-fire environmental management, with experience supporting environmental agencies such as state forest foundations.

Based on the following outputs generated from a Sentinel-2 wildfire burn severity analysis (including burn severity maps, RGB composites, severity class statistics, and metadata), produce a structured technical analysis suitable for inclusion in an official environmental assessment report.

Your analysis must go beyond describing the data and provide expert interpretation, spatial reasoning, and actionable recommendations.

Use a formal, technical, and objective tone appropriate for a scientific and institutional audience.

The report should include:

1. Executive Summary
   - Brief overview of the wildfire extent, severity distribution, and key findings.

2. Burn Severity Analysis
   - Interpretation of dNBR, RBR, and dNDVI indices.
   - Spatial distribution of severity classes.

3. Environmental Impact Assessment
   - Vegetation loss and ecosystem implications.
   - Soil degradation risk.
   - Water resource impacts.

4. Recommendations
   - Immediate response priorities.
   - Medium-term restoration actions.
   - Long-term monitoring needs.
```

User message includes:
- Severity distribution data (class name, area in hectares, percentage)
- Analysis metadata (area name, country, dates, total burned area)
- Satellite images (fetched server-side from S3, sent as base64 data URLs with labels)

Language instruction appended via `_get_instructions(language)`.

### 6. Cross-Platform Sync

- **Electron app**: Sync PrintReport.js, PrintReport.css, AnalysisDetail.js changes
- **Mobile app**: No print functionality exists — sync only translation files if any new keys are added

## Data Flow

```
User clicks "Print Report"
    -> AnalysisDetail checks if reportSummary in state
    -> If not: POST /analysis_run/{id}/report/ with {language}
        -> ViewSet action uses get_object() (enforces country-based access)
        -> Checks report_summary in DB + language match
        -> If cached and language matches: return it
        -> If not: call generate_report_summary()
            -> build_report_prompt() constructs prompt with severity data + metadata
            -> Fetches images from S3 via get_presigned_image_url()
            -> Dispatches to Gemini/OpenAI via existing provider abstraction
            -> Saves markdown + language to DB (shadow replacement: only on success)
            -> Returns markdown
    -> AnalysisDetail receives markdown, passes to PrintReport
    -> PrintReport renders via ReactMarkdown
    -> window.print() triggers
```

## Error Handling

- AI provider errors: show user-friendly error message, allow retry
- Network errors: show error toast, don't proceed to print
- Empty response from AI: treat as error, prompt retry
- Missing images in S3: still generate report with severity data only (graceful degradation)
- Regeneration failure: keep existing cached summary intact (shadow replacement)

## Testing

Backend (100% coverage required per CLAUDE.md):
- `generate_report_summary()` with mocked Gemini provider
- `generate_report_summary()` with mocked OpenAI provider
- `build_report_prompt()` output validation
- Report endpoint: cached response, fresh generation, regeneration, language mismatch triggering regen
- Report endpoint: authorization (filtered queryset), error cases
- Regeneration failure preserves old summary
- `ReportSummaryRequestSerializer` validation
- `report_summary` and `report_summary_language` in `AnalysisRunSerializer` output
- `es-ES` in LANGUAGE_MAP

Frontend:
- Loading state display
- Error handling
- Cached vs fresh report flow
- ReactMarkdown rendering
