# Analysis Advanced Settings

Add 5 new configurable parameters to the fire assessment analysis flow: `cloud_threshold`, `days_before_after`, `pre_fire_mosaic_strategy`, `post_fire_mosaic_strategy`, and `roi_only_bg_color`.

## Prerequisites

The `wildfire_analyser` library must be updated to a version that includes commit `1ae1409` (which adds `cloud_threshold`, `days_before_after`, `pre_fire_mosaic_strategy`, `post_fire_mosaic_strategy`, and `roi_only_bg_color` to the `PostFireAssessment` constructor). Update `requirements.txt` accordingly.

## Parameters

| Parameter | Type | Default | UI Control | Notes |
|---|---|---|---|---|
| `cloud_threshold` | int | 100 | Slider 0–100% | Max cloud cover allowed |
| `days_before_after` | int | 30 | Integer input | Search window for better images |
| `pre_fire_mosaic_strategy` | str | `best_available_per_tile_mosaic` | Radio buttons | 4 options from MosaicStrategy enum |
| `post_fire_mosaic_strategy` | str | `best_available_per_tile_mosaic` | Radio buttons | 4 options from MosaicStrategy enum |
| `roi_only_bg_color` | str | `black` | Auto (theme-based) | `black` for dark theme, `white` for light |

### MosaicStrategy Options

| Value | User-Facing Label |
|---|---|
| `best_date_mosaic` | Best Date |
| `best_date_masked_mosaic` | Best Date (Masked) |
| `best_available_per_tile_mosaic` | Best Available Per Tile |
| `cloud_masked_light_mosaic` | Cloud Masked Light |

## Backend

### Model (`AnalysisRun`)

Add 5 fields:

- `cloud_threshold = models.IntegerField(default=100)`
- `days_before_after = models.IntegerField(default=30)`
- `pre_fire_mosaic_strategy = models.CharField(max_length=50, default="best_available_per_tile_mosaic")`
- `post_fire_mosaic_strategy = models.CharField(max_length=50, default="best_available_per_tile_mosaic")`
- `roi_only_bg_color = models.CharField(max_length=10, default="black")`

New migration file required.

### View (`analyze` action)

Extract 5 new query params with defaults. Validate:
- `cloud_threshold`: integer 0–100
- `days_before_after`: positive integer (>= 1)
- `pre_fire_mosaic_strategy` / `post_fire_mosaic_strategy`: must be one of the 4 allowed MosaicStrategy values
- `roi_only_bg_color`: must be `"black"` or `"white"`

Return 400 on invalid values. Pass all params to `process_fire_assessment()` and `save_analysis_run()`.

### Processor (`process_fire_assessment`)

Add 5 new params to signature, pass through to `PostFireAssessment()` constructor.

### Processor (`process_scientific_deliverable`)

This Celery task also creates a `PostFireAssessment` instance. Read the 5 new params from the stored `AnalysisRun` record and pass them through to `PostFireAssessment()`. This ensures scientific deliverables use the same settings as the original analysis.

### Area of Interest Service (`save_analysis_run`)

Add 5 new params to signature, persist on `AnalysisRun.objects.create()`.

### Serializer (`AnalysisRunSerializer`)

Add 5 new fields as read-only. Also add `roi_only` to the serializer fields if not already present.

### Validation Constants

Define allowed mosaic strategy values in a constant (e.g., `VALID_MOSAIC_STRATEGIES`) to avoid repetition between view validation and any future use.

### Tests

100% coverage required. Test all new model fields, view param extraction, validation (invalid cloud_threshold, invalid strategy, negative days, invalid bg_color), processor passthrough, scientific deliverable param reading from AnalysisRun, and service persistence.

## Frontend — Web App & Electron App

Both share identical code in `AnalysisPage.js`.

### State

- `cloudThreshold` (default 100)
- `daysBeforeAfter` (default 30)
- `preFireMosaicStrategy` (default `"best_available_per_tile_mosaic"`)
- `postFireMosaicStrategy` (default `"best_available_per_tile_mosaic"`)
- `advancedOpen` (default false)

### UI

Below the ROI-only checkbox, a collapsible "Advanced Settings" toggle (chevron icon, defaults collapsed). When expanded, two-column grid:

- **Left column:** Cloud threshold slider (0–100%) with live value label; Days before/after integer input with "days" suffix
- **Right column:** Pre-fire mosaic strategy radio group (4 options); Post-fire mosaic strategy radio group (4 options)

### Query Params

Add to `URLSearchParams` on submit:
- `cloud_threshold`, `days_before_after`, `pre_fire_mosaic_strategy`, `post_fire_mosaic_strategy`
- `roi_only_bg_color`: auto-determined from current theme (`"black"` if dark, `"white"` if light)

### Translations

Add keys for all labels and hints across en, pt-BR, es-ES, fr.

## Frontend — Mobile App

Same logic in `/app/analysis/new.tsx`.

### State

Same 5 state variables + `advancedOpen`.

### UI

Below ROI-only switch, pressable "Advanced Settings" row with chevron. When expanded:
- Cloud threshold: React Native Slider (0–100) with value label
- Days before/after: TextInput with `keyboardType="number-pad"`
- Pre/post mosaic: Radio button groups using themed pressable rows

### API Client

Refactor `ApiClient.runAnalysis()` to accept an options object instead of growing positional params:

```typescript
interface AnalysisOptions {
  roiOnly?: boolean;
  cloudThreshold?: number;
  daysBeforeAfter?: number;
  preFireMosaicStrategy?: string;
  postFireMosaicStrategy?: string;
}

async runAnalysis(
  areaId: number,
  preFireDate: string,
  postFireDate: string,
  options?: AnalysisOptions,
  signal?: AbortSignal
): Promise<any>
```

`roi_only_bg_color` determined from theme context, added to URLSearchParams in the method body.

### Translations

Same 4 languages, same keys.

## Cross-Platform Sync

All three platforms (web, mobile, electron) must implement identically and stay in sync. The `roi_only_bg_color` is the only param not exposed in UI — it's derived from the user's theme setting on each platform.
