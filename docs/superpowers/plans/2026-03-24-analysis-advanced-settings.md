# Analysis Advanced Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 5 new configurable parameters (cloud_threshold, days_before_after, pre_fire_mosaic_strategy, post_fire_mosaic_strategy, roi_only_bg_color) to the fire assessment analysis flow across backend and all 3 frontend platforms.

**Architecture:** Follow the established `roi_only` pattern: query params in view → processor → wildfire_analyser library, with values persisted on `AnalysisRun`. Frontend adds a collapsible "Advanced Settings" section (two-column grid) below the ROI-only checkbox. `roi_only_bg_color` is auto-determined from user theme, not exposed in UI.

**Tech Stack:** Django 5.2, DRF, Celery, React 19, React Native (Expo), Bootstrap 5

**Spec:** `docs/superpowers/specs/2026-03-24-analysis-advanced-settings-design.md`

---

## File Map

### Backend (modify)
- `requirements.txt` — bump wildfire_analyser version to 1.0.1 (if not already bumped)
- `api/wildfire_assessment/models.py:139` — add 5 fields after `roi_only`
- `api/wildfire_assessment/svc/processor.py:33-84` — add params to `process_fire_assessment`, add params reading in `process_scientific_deliverable`
- `api/wildfire_assessment/svc/area_of_interest.py:77-119` — add params to `save_analysis_run`
- `api/wildfire_assessment/views.py:199-235` — extract/validate new query params in `analyze`
- `api/wildfire_assessment/serializers.py:710-745` — add fields to `AnalysisRunSerializer`
- `api/wildfire_assessment/tests/test_services.py` — tests for processor and service
- `api/wildfire_assessment/tests/test_apis.py` — tests for view validation
- `api/wildfire_assessment/tests/test_models.py` — test model defaults

### Backend (create)
- `api/wildfire_assessment/migrations/0031_analysisrun_advanced_settings.py` — migration

### Web App (modify)
- `ui/src/features/analysis/AnalysisPage.js` — state, UI, query params
- `ui/src/translations/en.json` — new translation keys
- `ui/src/translations/pt-BR.json` — Portuguese translations
- `ui/src/translations/es-ES.json` — Spanish translations
- `ui/src/translations/fr.json` — French translations

### Electron App (modify)
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/features/analysis/AnalysisPage.js` — identical changes to web
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/en.json` — same keys
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/pt-BR.json`
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/es-ES.json`
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/fr.json`

### Mobile App (modify)
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/app/analysis/new.tsx` — state, UI, API call
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/services/api.ts:172-193` — refactor to options object
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/en.json`
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/pt-BR.json`
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/es-ES.json`
- `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/fr.json`

---

## Task 1: Update wildfire_analyser library version

**Files:**
- Modify: `requirements.txt:1`

- [ ] **Step 1: Check current installed version and available versions**

```bash
docker exec wildfire-api pip show wildfire-analyser
```

Expected: version 1.0.1 currently installed. We need the version containing commit `1ae1409`.

- [ ] **Step 2: Update requirements.txt**

Change line 1 from:
```
wildfire_analyser==1.0.1
```
to the version that includes the new parameters. Check the package index or repo tags for the correct version. If the version with these params hasn't been released yet, pin to the commit:
```
wildfire_analyser @ git+https://github.com/Brazil-Flying-Labs/wildfire-analyser.git@1ae1409
```

- [ ] **Step 3: Rebuild the API container**

```bash
docker exec wildfire-api pip install -r /api/requirements.txt
```

Verify the new params are available:
```bash
docker exec wildfire-api python -c "from wildfire_analyser.fire_assessment.post_fire_assessment import PostFireAssessment; import inspect; print(inspect.signature(PostFireAssessment.__init__))"
```

Expected: signature shows `cloud_threshold`, `days_before_after`, `pre_fire_mosaic_strategy`, `post_fire_mosaic_strategy`, `roi_only_bg_color` params.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: bump wildfire_analyser to version with advanced settings params"
```

---

## Task 2: Add model fields and migration

**Files:**
- Modify: `api/wildfire_assessment/models.py:139`
- Create: migration file

- [ ] **Step 1: Write failing test for model defaults**

Add a `setUp` method to `AnalysisRunModelTests` in `api/wildfire_assessment/tests/test_models.py` (the existing class has no setUp — the existing test creates fixtures inline). Then add the new test methods:

```python
class AnalysisRunModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="analyst")
        country = Country.objects.create(name="TestAnalysis Country", code="TA")
        self.area = AreaOfInterest.objects.create(
            name="Amazon Reserve",
            polygon_path="amazon.geojson",
            country=country,
        )
```

Also update the existing `test_str_representation` to use `self.user` and `self.area` instead of creating inline fixtures (since setUp now provides them).

Add the new test methods to the class:

```python
def test_analysis_run_cloud_threshold_default(self):
    run = AnalysisRun.objects.create(
        user=self.user,
        area_of_interest=self.area,
        pre_fire_date="2023-01-01",
        post_fire_date="2023-02-01",
    )
    self.assertEqual(run.cloud_threshold, 100)

def test_analysis_run_days_before_after_default(self):
    run = AnalysisRun.objects.create(
        user=self.user,
        area_of_interest=self.area,
        pre_fire_date="2023-01-01",
        post_fire_date="2023-02-01",
    )
    self.assertEqual(run.days_before_after, 30)

def test_analysis_run_mosaic_strategy_defaults(self):
    run = AnalysisRun.objects.create(
        user=self.user,
        area_of_interest=self.area,
        pre_fire_date="2023-01-01",
        post_fire_date="2023-02-01",
    )
    self.assertEqual(run.pre_fire_mosaic_strategy, "best_available_per_tile_mosaic")
    self.assertEqual(run.post_fire_mosaic_strategy, "best_available_per_tile_mosaic")

def test_analysis_run_roi_only_bg_color_default(self):
    run = AnalysisRun.objects.create(
        user=self.user,
        area_of_interest=self.area,
        pre_fire_date="2023-01-01",
        post_fire_date="2023-02-01",
    )
    self.assertEqual(run.roi_only_bg_color, "black")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_models -v2
```

Expected: FAIL — fields don't exist yet.

- [ ] **Step 3: Add fields to AnalysisRun model**

In `api/wildfire_assessment/models.py`, after line 139 (`roi_only = models.BooleanField(default=True)`), add:

```python
    cloud_threshold = models.IntegerField(default=100)
    days_before_after = models.IntegerField(default=30)
    pre_fire_mosaic_strategy = models.CharField(
        max_length=50, default="best_available_per_tile_mosaic"
    )
    post_fire_mosaic_strategy = models.CharField(
        max_length=50, default="best_available_per_tile_mosaic"
    )
    roi_only_bg_color = models.CharField(max_length=10, default="black")
```

- [ ] **Step 4: Generate migration**

```bash
docker exec wildfire-api python manage.py makemigrations wildfire_assessment
```

Expected: creates `0031_analysisrun_advanced_settings.py` (or similar numbered migration).

- [ ] **Step 5: Run migration**

```bash
docker exec wildfire-api python manage.py migrate
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_models -v2
```

Expected: PASS — all new field default tests green.

- [ ] **Step 7: Commit**

```bash
git add api/wildfire_assessment/models.py api/wildfire_assessment/migrations/ api/wildfire_assessment/tests/test_models.py
git commit -m "feat: add advanced settings fields to AnalysisRun model"
```

---

## Task 3: Update processor service

**Files:**
- Modify: `api/wildfire_assessment/svc/processor.py:33-84` (process_fire_assessment)
- Modify: `api/wildfire_assessment/svc/processor.py:117-310` (process_scientific_deliverable)
- Test: `api/wildfire_assessment/tests/test_services.py`

- [ ] **Step 1: Write failing tests for process_fire_assessment**

Add to `test_services.py` in the `ProcessorTests` class, near the existing `test_process_fire_assessment_passes_roi_only_false` test:

```python
@patch("wildfire_assessment.svc.processor.os.unlink")
@patch("wildfire_assessment.svc.processor.PostFireAssessment")
@patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
@patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
def test_process_fire_assessment_passes_advanced_settings(
    self, mock_secret, mock_download, mock_assessment, mock_unlink
):
    mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
    mock_download.return_value = '{"type": "Polygon"}'
    assessment_instance = MagicMock()
    assessment_instance.run.return_value = {
        "visual": {
            "RGB_PRE_FIRE_VISUAL": {"url": ""},
            "RGB_POST_FIRE_VISUAL": {"url": ""},
            "DNDVI_VISUAL": {"url": ""},
            "DNBR_VISUAL": {"url": ""},
            "RBR_VISUAL": {"url": ""},
        },
        "statistics": {"DNBR_AREA_STATISTICS": {}},
    }
    mock_assessment.return_value = assessment_instance

    processor.process_fire_assessment(
        pre_fire_date=self.pre_fire_date,
        post_fire_date=self.post_fire_date,
        polygon_path=self.polygon_path,
        roi_only=True,
        cloud_threshold=50,
        days_before_after=15,
        pre_fire_mosaic_strategy="best_date_mosaic",
        post_fire_mosaic_strategy="cloud_masked_light_mosaic",
        roi_only_bg_color="white",
    )

    call_kwargs = mock_assessment.call_args.kwargs
    self.assertEqual(call_kwargs["cloud_threshold"], 50)
    self.assertEqual(call_kwargs["days_before_after"], 15)
    self.assertEqual(call_kwargs["pre_fire_mosaic_strategy"], "best_date_mosaic")
    self.assertEqual(call_kwargs["post_fire_mosaic_strategy"], "cloud_masked_light_mosaic")
    self.assertEqual(call_kwargs["roi_only_bg_color"], "white")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.ProcessorTests.test_process_fire_assessment_passes_advanced_settings -v2
```

Expected: FAIL — `process_fire_assessment()` doesn't accept these params yet.

- [ ] **Step 3: Add validation constant and update process_fire_assessment**

In `api/wildfire_assessment/svc/processor.py`, add after the imports (around line 28):

```python
VALID_MOSAIC_STRATEGIES = {
    "best_date_mosaic",
    "best_date_masked_mosaic",
    "best_available_per_tile_mosaic",
    "cloud_masked_light_mosaic",
}
```

Update `process_fire_assessment` signature (line 33-38) to:

```python
def process_fire_assessment(
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
    roi_only: bool = True,
    cloud_threshold: int = 100,
    days_before_after: int = 30,
    pre_fire_mosaic_strategy: str = "best_available_per_tile_mosaic",
    post_fire_mosaic_strategy: str = "best_available_per_tile_mosaic",
    roi_only_bg_color: str = "black",
) -> dict:
```

Update the `PostFireAssessment` constructor call (line 57-71) to pass all new params:

```python
        runner = PostFireAssessment(
            get_gee_private_key_json(),
            tmp.name,
            pre_fire_date,
            post_fire_date,
            deliverables=[
                Deliverable.RGB_PRE_FIRE_VISUAL,
                Deliverable.RGB_POST_FIRE_VISUAL,
                Deliverable.DNDVI_VISUAL,
                Deliverable.DNBR_VISUAL,
                Deliverable.RBR_VISUAL,
                Deliverable.DNBR_AREA_STATISTICS,
            ],
            roi_only=roi_only,
            cloud_threshold=cloud_threshold,
            days_before_after=days_before_after,
            pre_fire_mosaic_strategy=pre_fire_mosaic_strategy,
            post_fire_mosaic_strategy=post_fire_mosaic_strategy,
            roi_only_bg_color=roi_only_bg_color,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.ProcessorTests.test_process_fire_assessment_passes_advanced_settings -v2
```

Expected: PASS

- [ ] **Step 5: Write failing test for process_scientific_deliverable reading from AnalysisRun**

Add to `test_services.py` in the `ProcessorTests` class. Since `ProcessorTests` doesn't have `self.user` or `self.area`, create fixtures inline (matching the pattern of `test_process_scientific_deliverable_updates_analysis_run` in the codebase):

```python
@patch("wildfire_assessment.svc.processor.os.unlink")
@patch("wildfire_assessment.svc.processor.send_gmail_email")
@patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
@patch("wildfire_assessment.svc.processor.ee")
@patch("wildfire_assessment.svc.processor.PostFireAssessment")
@patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
@patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
def test_scientific_deliverable_reads_advanced_settings_from_run(
    self,
    mock_secret,
    mock_download,
    mock_assessment,
    mock_ee,
    _mock_sleep,
    mock_send_email,
    mock_unlink,
):
    user = get_user_model().objects.create(username="sci_adv_user")
    country = Country.objects.create(name="SciAdv Country", code="SA")
    area = AreaOfInterest.objects.create(
        name="SciAdv Reserve",
        polygon_path="sciadv.geojson",
        country=country,
    )
    run = AnalysisRun.objects.create(
        user=user,
        area_of_interest=area,
        pre_fire_date="2023-01-01",
        post_fire_date="2023-02-01",
        cloud_threshold=50,
        days_before_after=15,
        pre_fire_mosaic_strategy="best_date_mosaic",
        post_fire_mosaic_strategy="cloud_masked_light_mosaic",
        roi_only=False,
        roi_only_bg_color="white",
    )

    mock_secret.return_value = json.dumps(
        {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
    )
    mock_download.return_value = '{"type": "Polygon"}'
    assessment_instance = MagicMock()
    assessment_instance.run.return_value = {
        "scientific": {
            "RGB_PRE_FIRE": {"gee_task_id": "task-1", "url": "http://files/pre.tif"}
        }
    }
    mock_assessment.return_value = assessment_instance
    mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

    processor.process_scientific_deliverable(
        pre_fire_date="2023-01-01",
        post_fire_date="2023-02-01",
        polygon_path="sciadv.geojson",
        deliverable_name=Deliverable.RGB_PRE_FIRE.name,
        email="sciadv@example.com",
        reserve_name="SciAdv Reserve",
        analysis_run_id=run.id,
        user_id=user.id,
    )

    pfa_kwargs = mock_assessment.call_args.kwargs
    self.assertEqual(pfa_kwargs.get("cloud_threshold"), 50)
    self.assertEqual(pfa_kwargs.get("days_before_after"), 15)
    self.assertEqual(pfa_kwargs.get("pre_fire_mosaic_strategy"), "best_date_mosaic")
    self.assertEqual(pfa_kwargs.get("post_fire_mosaic_strategy"), "cloud_masked_light_mosaic")
    self.assertFalse(pfa_kwargs.get("roi_only"))
    self.assertEqual(pfa_kwargs.get("roi_only_bg_color"), "white")
```

- [ ] **Step 6: Run test to verify it fails**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.ProcessorTests.test_scientific_deliverable_reads_advanced_settings_from_run -v2
```

Expected: FAIL — `process_scientific_deliverable` doesn't read from AnalysisRun yet.

- [ ] **Step 7: Update process_scientific_deliverable to read settings from AnalysisRun**

In `process_scientific_deliverable` (around line 180-195), after downloading the polygon and before creating `PostFireAssessment`, add logic to read settings from the AnalysisRun:

```python
    # Read advanced settings from the AnalysisRun if available
    advanced_kwargs = {}
    if analysis_run_id:
        try:
            run = AnalysisRun.objects.get(id=analysis_run_id)
            advanced_kwargs = {
                "roi_only": run.roi_only,
                "cloud_threshold": run.cloud_threshold,
                "days_before_after": run.days_before_after,
                "pre_fire_mosaic_strategy": run.pre_fire_mosaic_strategy,
                "post_fire_mosaic_strategy": run.post_fire_mosaic_strategy,
                "roi_only_bg_color": run.roi_only_bg_color,
            }
        except AnalysisRun.DoesNotExist:
            pass
```

Then update the `PostFireAssessment` constructor call to include `**advanced_kwargs`:

```python
        runner = PostFireAssessment(
            get_gee_private_key_json(),
            tmp.name,
            pre_fire_date,
            post_fire_date,
            deliverables=[deliverable],
            gcs_bucket="wildfire-analyser-outputs",
            verbose=False,
            **advanced_kwargs,
        )
```

- [ ] **Step 8: Run test to verify it passes**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.ProcessorTests.test_scientific_deliverable_reads_advanced_settings_from_run -v2
```

Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add api/wildfire_assessment/svc/processor.py api/wildfire_assessment/tests/test_services.py
git commit -m "feat: pass advanced settings through processor to PostFireAssessment"
```

---

## Task 4: Update area_of_interest service (save_analysis_run)

**Files:**
- Modify: `api/wildfire_assessment/svc/area_of_interest.py:77-119`
- Test: `api/wildfire_assessment/tests/test_services.py`

- [ ] **Step 1: Write failing tests**

Add to `test_services.py` in the `AreaOfInterestServiceTests` class:

```python
@patch("wildfire_assessment.svc.area_of_interest._download_and_store_image", return_value=None)
def test_save_analysis_run_persists_advanced_settings(self, mock_img):
    result = {
        "severity_map": '{"Total Burned Area": {"area_ha": 10}}',
    }
    run = aoi_service.save_analysis_run(
        self.user,
        self.area,
        "2023-01-01",
        "2023-02-01",
        result,
        roi_only=False,
        cloud_threshold=50,
        days_before_after=15,
        pre_fire_mosaic_strategy="best_date_mosaic",
        post_fire_mosaic_strategy="cloud_masked_light_mosaic",
        roi_only_bg_color="white",
    )
    self.assertEqual(run.cloud_threshold, 50)
    self.assertEqual(run.days_before_after, 15)
    self.assertEqual(run.pre_fire_mosaic_strategy, "best_date_mosaic")
    self.assertEqual(run.post_fire_mosaic_strategy, "cloud_masked_light_mosaic")
    self.assertEqual(run.roi_only_bg_color, "white")

@patch("wildfire_assessment.svc.area_of_interest._download_and_store_image", return_value=None)
def test_save_analysis_run_advanced_settings_defaults(self, mock_img):
    result = {"severity_map": "{}"}
    run = aoi_service.save_analysis_run(
        self.user, self.area, "2023-01-01", "2023-02-01", result
    )
    self.assertEqual(run.cloud_threshold, 100)
    self.assertEqual(run.days_before_after, 30)
    self.assertEqual(run.pre_fire_mosaic_strategy, "best_available_per_tile_mosaic")
    self.assertEqual(run.post_fire_mosaic_strategy, "best_available_per_tile_mosaic")
    self.assertEqual(run.roi_only_bg_color, "black")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.AreaOfInterestServiceTests -v2
```

Expected: FAIL — `save_analysis_run()` doesn't accept these params yet.

- [ ] **Step 3: Update save_analysis_run signature and implementation**

In `api/wildfire_assessment/svc/area_of_interest.py`, update `save_analysis_run` (line 77):

```python
def save_analysis_run(
    user,
    area,
    pre_fire_date,
    post_fire_date,
    assessment_result,
    roi_only=True,
    cloud_threshold=100,
    days_before_after=30,
    pre_fire_mosaic_strategy="best_available_per_tile_mosaic",
    post_fire_mosaic_strategy="best_available_per_tile_mosaic",
    roi_only_bg_color="black",
):
```

Update the `AnalysisRun.objects.create()` call (line 108-119) to include new fields:

```python
    return AnalysisRun.objects.create(
        user=user,
        area_of_interest=area,
        pre_fire_date=pre_fire_date,
        post_fire_date=post_fire_date,
        status="completed",
        severity_data=severity_data,
        total_burned_ha=total_burned_ha,
        roi_only=roi_only,
        cloud_threshold=cloud_threshold,
        days_before_after=days_before_after,
        pre_fire_mosaic_strategy=pre_fire_mosaic_strategy,
        post_fire_mosaic_strategy=post_fire_mosaic_strategy,
        roi_only_bg_color=roi_only_bg_color,
        completed_at=timezone.now(),
        **image_keys,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_services.AreaOfInterestServiceTests -v2
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/wildfire_assessment/svc/area_of_interest.py api/wildfire_assessment/tests/test_services.py
git commit -m "feat: persist advanced settings in save_analysis_run"
```

---

## Task 5: Update view (extract, validate, pass params)

**Files:**
- Modify: `api/wildfire_assessment/views.py:199-235`
- Test: `api/wildfire_assessment/tests/test_apis.py`

- [ ] **Step 1: Write failing tests for the analyze endpoint**

Add to `test_apis.py` in the analyze test class:

```python
@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_passes_advanced_settings(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "roi_only": "true",
        "cloud_threshold": "50",
        "days_before_after": "15",
        "pre_fire_mosaic_strategy": "best_date_mosaic",
        "post_fire_mosaic_strategy": "cloud_masked_light_mosaic",
        "roi_only_bg_color": "white",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    self.client.post(f"{url}?{query}")
    kwargs = mock_process.call_args.kwargs
    self.assertEqual(kwargs["cloud_threshold"], 50)
    self.assertEqual(kwargs["days_before_after"], 15)
    self.assertEqual(kwargs["pre_fire_mosaic_strategy"], "best_date_mosaic")
    self.assertEqual(kwargs["post_fire_mosaic_strategy"], "cloud_masked_light_mosaic")
    self.assertEqual(kwargs["roi_only_bg_color"], "white")

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_advanced_settings_defaults(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    self.client.post(f"{url}?{query}")
    kwargs = mock_process.call_args.kwargs
    self.assertEqual(kwargs["cloud_threshold"], 100)
    self.assertEqual(kwargs["days_before_after"], 30)
    self.assertEqual(kwargs["pre_fire_mosaic_strategy"], "best_available_per_tile_mosaic")
    self.assertEqual(kwargs["post_fire_mosaic_strategy"], "best_available_per_tile_mosaic")
    self.assertEqual(kwargs["roi_only_bg_color"], "black")

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_cloud_threshold_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "cloud_threshold": "150",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)
    mock_process.assert_not_called()

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_cloud_threshold_negative_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "cloud_threshold": "-1",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_cloud_threshold_non_integer_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "cloud_threshold": "abc",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_days_before_after_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "days_before_after": "0",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_days_before_after_non_integer_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "days_before_after": "abc",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_pre_fire_mosaic_strategy_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "pre_fire_mosaic_strategy": "invalid_strategy",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_post_fire_mosaic_strategy_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "post_fire_mosaic_strategy": "invalid_strategy",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)

@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_invalid_bg_color_returns_400(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode({
        "pre_fire_date": "2023-01-01",
        "post_fire_date": "2023-01-15",
        "roi_only_bg_color": "red",
    })
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    response = self.client.post(f"{url}?{query}")
    self.assertEqual(response.status_code, 400)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_apis.WildfireAssessmentTests -v2
```

Expected: FAIL

- [ ] **Step 3: Update the analyze view action**

In `api/wildfire_assessment/views.py`, add import at top:

```python
from wildfire_assessment.svc.processor import (
    DELIVERABLE_ERROR_FIELD_MAP,
    DELIVERABLE_FIELD_MAP,
    DELIVERABLE_TASK_FIELD_MAP,
    VALID_MOSAIC_STRATEGIES,
    process_fire_assessment,
    process_scientific_deliverable,
)
```

Update the `analyze` method (lines 199-235). After extracting `roi_only` (line 210), add validation and extraction:

```python
    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        instance = self.get_object()
        execution_id = uuid.uuid4()

        pre_fire_date = request.query_params.get("pre_fire_date")
        post_fire_date = request.query_params.get("post_fire_date")
        roi_only = request.query_params.get("roi_only", "true").lower() != "false"

        # Extract and validate advanced settings
        try:
            cloud_threshold = int(
                request.query_params.get("cloud_threshold", "100")
            )
        except (ValueError, TypeError):
            return Response(
                {"error": "cloud_threshold must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (0 <= cloud_threshold <= 100):
            return Response(
                {"error": "cloud_threshold must be between 0 and 100"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            days_before_after = int(
                request.query_params.get("days_before_after", "30")
            )
        except (ValueError, TypeError):
            return Response(
                {"error": "days_before_after must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if days_before_after < 1:
            return Response(
                {"error": "days_before_after must be >= 1"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pre_fire_mosaic_strategy = request.query_params.get(
            "pre_fire_mosaic_strategy", "best_available_per_tile_mosaic"
        )
        if pre_fire_mosaic_strategy not in VALID_MOSAIC_STRATEGIES:
            return Response(
                {"error": "Invalid pre_fire_mosaic_strategy"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post_fire_mosaic_strategy = request.query_params.get(
            "post_fire_mosaic_strategy", "best_available_per_tile_mosaic"
        )
        if post_fire_mosaic_strategy not in VALID_MOSAIC_STRATEGIES:
            return Response(
                {"error": "Invalid post_fire_mosaic_strategy"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roi_only_bg_color = request.query_params.get("roi_only_bg_color", "black")
        if roi_only_bg_color not in ("black", "white"):
            return Response(
                {"error": "roi_only_bg_color must be 'black' or 'white'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment_result = process_fire_assessment(
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            polygon_path=instance.polygon_path,
            roi_only=roi_only,
            cloud_threshold=cloud_threshold,
            days_before_after=days_before_after,
            pre_fire_mosaic_strategy=pre_fire_mosaic_strategy,
            post_fire_mosaic_strategy=post_fire_mosaic_strategy,
            roi_only_bg_color=roi_only_bg_color,
        )

        analysis_run = save_analysis_run(
            user=request.user,
            area=instance,
            pre_fire_date=pre_fire_date,
            post_fire_date=post_fire_date,
            assessment_result=assessment_result,
            roi_only=roi_only,
            cloud_threshold=cloud_threshold,
            days_before_after=days_before_after,
            pre_fire_mosaic_strategy=pre_fire_mosaic_strategy,
            post_fire_mosaic_strategy=post_fire_mosaic_strategy,
            roi_only_bg_color=roi_only_bg_color,
        )
        invalidate_dashboard_cache(request.user.id)

        return Response(
            {
                "execution_id": str(execution_id),
                "analysis_run_id": analysis_run.id,
                **assessment_result,
            }
        )
```

Also update the `@extend_schema` `parameters` list (lines 178-197) to include the 5 new params after the existing `roi_only` parameter:

```python
            OpenApiParameter(
                name="cloud_threshold",
                description="Max cloud cover percentage allowed (0-100, default: 100)",
                type=OpenApiTypes.INT,
                required=False,
            ),
            OpenApiParameter(
                name="days_before_after",
                description="Search window in days before/after fire dates (>= 1, default: 30)",
                type=OpenApiTypes.INT,
                required=False,
            ),
            OpenApiParameter(
                name="pre_fire_mosaic_strategy",
                description="Pre-fire mosaic strategy (default: best_available_per_tile_mosaic)",
                type=OpenApiTypes.STR,
                required=False,
            ),
            OpenApiParameter(
                name="post_fire_mosaic_strategy",
                description="Post-fire mosaic strategy (default: best_available_per_tile_mosaic)",
                type=OpenApiTypes.STR,
                required=False,
            ),
            OpenApiParameter(
                name="roi_only_bg_color",
                description="Background color for ROI-only mode (black or white, default: black)",
                type=OpenApiTypes.STR,
                required=False,
            ),
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker exec wildfire-api python manage.py test wildfire_assessment.tests.test_apis -v2
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add api/wildfire_assessment/views.py api/wildfire_assessment/tests/test_apis.py
git commit -m "feat: extract, validate, and pass advanced settings in analyze endpoint"
```

---

## Task 6: Update serializer

**Files:**
- Modify: `api/wildfire_assessment/serializers.py:710-745`

- [ ] **Step 1: Add fields to AnalysisRunSerializer**

In `api/wildfire_assessment/serializers.py`, update the `AnalysisRunSerializer.Meta.fields` list (line 712-745) to include the new fields. Add after `"completed_at"`:

```python
            "roi_only",
            "cloud_threshold",
            "days_before_after",
            "pre_fire_mosaic_strategy",
            "post_fire_mosaic_strategy",
            "roi_only_bg_color",
```

- [ ] **Step 2: Run full test suite to verify nothing broke**

```bash
docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"
```

Expected: ALL PASS, coverage at or near 100%.

- [ ] **Step 3: Commit**

```bash
git add api/wildfire_assessment/serializers.py
git commit -m "feat: add advanced settings fields to AnalysisRunSerializer"
```

---

## Task 7: Web App — translations

**Files:**
- Modify: `ui/src/translations/en.json`
- Modify: `ui/src/translations/pt-BR.json`
- Modify: `ui/src/translations/es-ES.json`
- Modify: `ui/src/translations/fr.json`

- [ ] **Step 1: Add translation keys to all 4 language files**

**en.json** — add after `"app.roiOnlyHint"` line:

```json
  "app.advancedSettings": "Advanced Settings",
  "app.cloudThreshold": "Cloud Threshold",
  "app.cloudThresholdHint": "Maximum cloud cover percentage allowed in satellite images",
  "app.daysBeforeAfter": "Days Before/After",
  "app.daysBeforeAfterHint": "Number of days to search before and after the fire dates for better images",
  "app.daysBeforeAfterSuffix": "days",
  "app.preFireMosaicStrategy": "Pre-fire Mosaic Strategy",
  "app.postFireMosaicStrategy": "Post-fire Mosaic Strategy",
  "app.mosaicBestDate": "Best Date",
  "app.mosaicBestDateMasked": "Best Date (Masked)",
  "app.mosaicBestAvailable": "Best Available Per Tile",
  "app.mosaicCloudMasked": "Cloud Masked Light",
```

**pt-BR.json** — add matching keys:

```json
  "app.advancedSettings": "Configurações Avançadas",
  "app.cloudThreshold": "Limite de Nuvens",
  "app.cloudThresholdHint": "Porcentagem máxima de cobertura de nuvens permitida nas imagens de satélite",
  "app.daysBeforeAfter": "Dias Antes/Depois",
  "app.daysBeforeAfterHint": "Número de dias para buscar antes e depois das datas do incêndio por melhores imagens",
  "app.daysBeforeAfterSuffix": "dias",
  "app.preFireMosaicStrategy": "Estratégia de Mosaico Pré-incêndio",
  "app.postFireMosaicStrategy": "Estratégia de Mosaico Pós-incêndio",
  "app.mosaicBestDate": "Melhor Data",
  "app.mosaicBestDateMasked": "Melhor Data (Mascarada)",
  "app.mosaicBestAvailable": "Melhor Disponível por Tile",
  "app.mosaicCloudMasked": "Máscara de Nuvens Leve",
```

**es-ES.json** — add matching keys:

```json
  "app.advancedSettings": "Configuración Avanzada",
  "app.cloudThreshold": "Umbral de Nubes",
  "app.cloudThresholdHint": "Porcentaje máximo de cobertura de nubes permitido en las imágenes de satélite",
  "app.daysBeforeAfter": "Días Antes/Después",
  "app.daysBeforeAfterHint": "Número de días para buscar antes y después de las fechas del incendio por mejores imágenes",
  "app.daysBeforeAfterSuffix": "días",
  "app.preFireMosaicStrategy": "Estrategia de Mosaico Pre-incendio",
  "app.postFireMosaicStrategy": "Estrategia de Mosaico Post-incendio",
  "app.mosaicBestDate": "Mejor Fecha",
  "app.mosaicBestDateMasked": "Mejor Fecha (Enmascarada)",
  "app.mosaicBestAvailable": "Mejor Disponible por Tile",
  "app.mosaicCloudMasked": "Máscara de Nubes Ligera",
```

**fr.json** — add matching keys:

```json
  "app.advancedSettings": "Paramètres Avancés",
  "app.cloudThreshold": "Seuil de Nuages",
  "app.cloudThresholdHint": "Pourcentage maximal de couverture nuageuse autorisé dans les images satellite",
  "app.daysBeforeAfter": "Jours Avant/Après",
  "app.daysBeforeAfterHint": "Nombre de jours de recherche avant et après les dates d'incendie pour de meilleures images",
  "app.daysBeforeAfterSuffix": "jours",
  "app.preFireMosaicStrategy": "Stratégie de Mosaïque Pré-incendie",
  "app.postFireMosaicStrategy": "Stratégie de Mosaïque Post-incendie",
  "app.mosaicBestDate": "Meilleure Date",
  "app.mosaicBestDateMasked": "Meilleure Date (Masquée)",
  "app.mosaicBestAvailable": "Meilleur Disponible par Tuile",
  "app.mosaicCloudMasked": "Masque de Nuages Léger",
```

- [ ] **Step 2: Commit**

```bash
git add ui/src/translations/
git commit -m "feat: add advanced settings translation keys for all 4 languages"
```

---

## Task 8: Web App — AnalysisPage UI and query params

**Files:**
- Modify: `ui/src/features/analysis/AnalysisPage.js`

The web app needs to access the user's theme to determine `roi_only_bg_color`. The theme is set via `document.documentElement.getAttribute("data-theme")` (set by `useProfile`). Since `AnalysisPage` doesn't have direct access to `useProfile`, we'll read the theme from the DOM attribute.

- [ ] **Step 1: Add state declarations**

After line 21 (`const [roiOnly, setRoiOnly] = useState(true);`), add:

```javascript
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [cloudThreshold, setCloudThreshold] = useState(100);
  const [daysBeforeAfter, setDaysBeforeAfter] = useState(30);
  const [preFireMosaicStrategy, setPreFireMosaicStrategy] = useState("best_available_per_tile_mosaic");
  const [postFireMosaicStrategy, setPostFireMosaicStrategy] = useState("best_available_per_tile_mosaic");
```

- [ ] **Step 2: Add mosaic strategy options constant**

After the imports (around line 8), add:

```javascript
const MOSAIC_STRATEGIES = [
  { value: "best_date_mosaic", labelKey: "app.mosaicBestDate" },
  { value: "best_date_masked_mosaic", labelKey: "app.mosaicBestDateMasked" },
  { value: "best_available_per_tile_mosaic", labelKey: "app.mosaicBestAvailable" },
  { value: "cloud_masked_light_mosaic", labelKey: "app.mosaicCloudMasked" },
];
```

- [ ] **Step 3: Update query params in handleSubmit**

Replace the `queryParams` construction (lines 386-390):

```javascript
      const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
      const queryParams = new URLSearchParams({
        pre_fire_date: preFireDate,
        post_fire_date: postFireDate,
        roi_only: String(roiOnly),
        cloud_threshold: String(cloudThreshold),
        days_before_after: String(daysBeforeAfter),
        pre_fire_mosaic_strategy: preFireMosaicStrategy,
        post_fire_mosaic_strategy: postFireMosaicStrategy,
        roi_only_bg_color: currentTheme === "light" ? "white" : "black",
      });
```

- [ ] **Step 4: Add Advanced Settings UI**

After the ROI-only checkbox section (after line 540, before `</form>`), add the collapsible Advanced Settings section:

```jsx
              <div className="mt-3 pt-3 border-top">
                <div
                  className="d-flex align-items-center gap-2 mb-0"
                  style={{ cursor: "pointer", color: "var(--bs-primary)", fontWeight: 600 }}
                  onClick={() => setAdvancedOpen(!advancedOpen)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setAdvancedOpen(!advancedOpen); }}
                >
                  <svg
                    width="12" height="12" viewBox="0 0 12 12" fill="currentColor"
                    style={{ transform: advancedOpen ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s" }}
                  >
                    <path d="M2 4l4 4 4-4" />
                  </svg>
                  {t("app.advancedSettings")}
                </div>
                {advancedOpen ? (
                  <div className="mt-3 p-3 border rounded" style={{ background: "var(--card-bg, inherit)" }}>
                    <div className="row g-3">
                      {/* Left column: Cloud threshold + Days */}
                      <div className="col-12 col-md-6">
                        <div className="mb-3">
                          <label htmlFor="cloudThreshold" className="form-label fw-semibold">
                            {t("app.cloudThreshold")}
                          </label>
                          <div className="d-flex align-items-center gap-2">
                            <input
                              type="range"
                              className="form-range flex-grow-1"
                              id="cloudThreshold"
                              min="0"
                              max="100"
                              value={cloudThreshold}
                              onChange={(e) => setCloudThreshold(Number(e.target.value))}
                            />
                            <span className="fw-semibold" style={{ minWidth: "40px", textAlign: "right" }}>
                              {cloudThreshold}%
                            </span>
                          </div>
                          <div className="form-text">{t("app.cloudThresholdHint")}</div>
                        </div>
                        <div>
                          <label htmlFor="daysBeforeAfter" className="form-label fw-semibold">
                            {t("app.daysBeforeAfter")}
                          </label>
                          <div className="d-flex align-items-center gap-2">
                            <input
                              type="number"
                              className="form-control"
                              id="daysBeforeAfter"
                              min="1"
                              step="1"
                              value={daysBeforeAfter}
                              onChange={(e) => {
                                const val = parseInt(e.target.value, 10);
                                if (!Number.isNaN(val) && val >= 1) setDaysBeforeAfter(val);
                              }}
                              style={{ width: "100px" }}
                            />
                            <span className="text-muted">{t("app.daysBeforeAfterSuffix")}</span>
                          </div>
                          <div className="form-text">{t("app.daysBeforeAfterHint")}</div>
                        </div>
                      </div>
                      {/* Right column: Mosaic strategies */}
                      <div className="col-12 col-md-6">
                        <div className="mb-3">
                          <label className="form-label fw-semibold">{t("app.preFireMosaicStrategy")}</label>
                          {MOSAIC_STRATEGIES.map(({ value, labelKey }) => (
                            <div className="form-check" key={`pre-${value}`}>
                              <input
                                className="form-check-input"
                                type="radio"
                                name="preFireMosaicStrategy"
                                id={`pre-${value}`}
                                value={value}
                                checked={preFireMosaicStrategy === value}
                                onChange={(e) => setPreFireMosaicStrategy(e.target.value)}
                              />
                              <label className="form-check-label" htmlFor={`pre-${value}`}>
                                {t(labelKey)}
                              </label>
                            </div>
                          ))}
                        </div>
                        <div>
                          <label className="form-label fw-semibold">{t("app.postFireMosaicStrategy")}</label>
                          {MOSAIC_STRATEGIES.map(({ value, labelKey }) => (
                            <div className="form-check" key={`post-${value}`}>
                              <input
                                className="form-check-input"
                                type="radio"
                                name="postFireMosaicStrategy"
                                id={`post-${value}`}
                                value={value}
                                checked={postFireMosaicStrategy === value}
                                onChange={(e) => setPostFireMosaicStrategy(e.target.value)}
                              />
                              <label className="form-check-label" htmlFor={`post-${value}`}>
                                {t(labelKey)}
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
```

- [ ] **Step 5: Commit**

```bash
git add ui/src/features/analysis/AnalysisPage.js
git commit -m "feat: add advanced settings UI to web app analysis form"
```

---

## Task 9: Electron App — mirror web app changes

**Files:**
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/features/analysis/AnalysisPage.js`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/en.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/pt-BR.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/es-ES.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron/src/translations/fr.json`

- [ ] **Step 1: Copy AnalysisPage.js changes to Electron**

Apply the exact same changes from Task 8 (MOSAIC_STRATEGIES constant, state declarations, query params update, and Advanced Settings UI) to the Electron app's `AnalysisPage.js`.

- [ ] **Step 2: Copy translation keys to Electron**

Apply the same translation keys from Task 7 to the Electron app's 4 translation files.

- [ ] **Step 3: Commit in Electron repo**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron
git add src/features/analysis/AnalysisPage.js src/translations/
git commit -m "feat: add advanced settings UI to electron app analysis form"
```

---

## Task 10: Mobile App — API client refactor

**Files:**
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/services/api.ts:172-193`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/app/analysis/new.tsx` (update callsite)

- [ ] **Step 1: Add AnalysisOptions interface and refactor runAnalysis**

In `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/services/api.ts`, add an interface before the `ApiClient` class and update `runAnalysis`:

```typescript
export interface AnalysisOptions {
  roiOnly?: boolean;
  cloudThreshold?: number;
  daysBeforeAfter?: number;
  preFireMosaicStrategy?: string;
  postFireMosaicStrategy?: string;
  roiOnlyBgColor?: string;
}
```

Replace the `runAnalysis` method:

```typescript
  async runAnalysis(
    areaId: number,
    preFireDate: string,
    postFireDate: string,
    options: AnalysisOptions = {},
    signal?: AbortSignal
  ): Promise<any> {
    const {
      roiOnly = true,
      cloudThreshold = 100,
      daysBeforeAfter = 30,
      preFireMosaicStrategy = "best_available_per_tile_mosaic",
      postFireMosaicStrategy = "best_available_per_tile_mosaic",
      roiOnlyBgColor = "black",
    } = options;
    const qs = new URLSearchParams({
      pre_fire_date: preFireDate,
      post_fire_date: postFireDate,
      roi_only: String(roiOnly),
      cloud_threshold: String(cloudThreshold),
      days_before_after: String(daysBeforeAfter),
      pre_fire_mosaic_strategy: preFireMosaicStrategy,
      post_fire_mosaic_strategy: postFireMosaicStrategy,
      roi_only_bg_color: roiOnlyBgColor,
    });
    const res = await this.authorizedFetch(
      `${API_URL}/area_of_interest/${areaId}/analyze/?${qs}`,
      { method: "POST", signal }
    );
    // ... rest stays the same
```

- [ ] **Step 2: Update the callsite in new.tsx**

In `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/app/analysis/new.tsx`, update the `runAnalysis` call to use the options object. The exact location and code depends on the current callsite, which passes `roiOnly` as a positional param. Change:

```typescript
const result = await apiClient.runAnalysis(
  selectedAreaId,
  preFireDate,
  postFireDate,
  roiOnly,
  abortRef.current.signal
);
```

to:

```typescript
const result = await apiClient.runAnalysis(
  selectedAreaId,
  preFireDate,
  postFireDate,
  {
    roiOnly,
    cloudThreshold,
    daysBeforeAfter,
    preFireMosaicStrategy,
    postFireMosaicStrategy,
    roiOnlyBgColor: isDark ? "black" : "white",
  },
  abortRef.current.signal
);
```

Where `isDark` comes from `useTheme()` (already imported in the mobile app).

- [ ] **Step 3: Commit in mobile repo**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app
git add services/api.ts app/analysis/new.tsx
git commit -m "feat: refactor runAnalysis to options object, add advanced settings params"
```

---

## Task 11: Mobile App — translations + UI

**Files:**
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/en.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/pt-BR.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/es-ES.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/translations/fr.json`
- Modify: `/Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app/app/analysis/new.tsx`

- [ ] **Step 1: Add translation keys to all 4 language files**

Same keys as web app (Task 7). Add to each translation file.

- [ ] **Step 2: Add state declarations to new.tsx**

After the existing `roiOnly` state, add:

```typescript
const [advancedOpen, setAdvancedOpen] = useState(false);
const [cloudThreshold, setCloudThreshold] = useState(100);
const [daysBeforeAfter, setDaysBeforeAfter] = useState(30);
const [preFireMosaicStrategy, setPreFireMosaicStrategy] = useState("best_available_per_tile_mosaic");
const [postFireMosaicStrategy, setPostFireMosaicStrategy] = useState("best_available_per_tile_mosaic");
```

Also destructure `isDark` from `useTheme()` if not already available:

```typescript
const { theme, isDark } = useTheme();
```

- [ ] **Step 3: Add mosaic strategy options constant**

```typescript
const MOSAIC_STRATEGIES = [
  { value: "best_date_mosaic", labelKey: "app.mosaicBestDate" },
  { value: "best_date_masked_mosaic", labelKey: "app.mosaicBestDateMasked" },
  { value: "best_available_per_tile_mosaic", labelKey: "app.mosaicBestAvailable" },
  { value: "cloud_masked_light_mosaic", labelKey: "app.mosaicCloudMasked" },
];
```

- [ ] **Step 4: Add Advanced Settings UI**

After the ROI-only switch in the JSX, add a collapsible section. Use React Native `Pressable`, `Slider` (from `@react-native-community/slider` or equivalent already in the project), `TextInput`, and custom radio buttons:

```tsx
{/* Advanced Settings Toggle */}
<Pressable
  onPress={() => setAdvancedOpen(!advancedOpen)}
  style={[styles.advancedToggle, { borderTopColor: theme.border }]}
>
  <Text style={[styles.advancedToggleText, { color: theme.primary }]}>
    {advancedOpen ? "▼" : "▶"} {t("app.advancedSettings")}
  </Text>
</Pressable>

{advancedOpen && (
  <View style={[styles.advancedSection, { borderColor: theme.border }]}>
    {/* Cloud Threshold Slider */}
    <View style={styles.fieldGroup}>
      <Text style={[styles.fieldLabel, { color: theme.text }]}>
        {t("app.cloudThreshold")}
      </Text>
      <View style={styles.sliderRow}>
        <Slider
          style={{ flex: 1 }}
          minimumValue={0}
          maximumValue={100}
          step={1}
          value={cloudThreshold}
          onValueChange={setCloudThreshold}
          minimumTrackTintColor={theme.primary}
          maximumTrackTintColor={theme.border}
        />
        <Text style={[styles.sliderValue, { color: theme.text }]}>
          {cloudThreshold}%
        </Text>
      </View>
      <Text style={[styles.fieldHint, { color: theme.textSecondary }]}>
        {t("app.cloudThresholdHint")}
      </Text>
    </View>

    {/* Days Before/After */}
    <View style={styles.fieldGroup}>
      <Text style={[styles.fieldLabel, { color: theme.text }]}>
        {t("app.daysBeforeAfter")}
      </Text>
      <View style={styles.inputRow}>
        <TextInput
          style={[styles.numberInput, { color: theme.text, borderColor: theme.border }]}
          keyboardType="number-pad"
          value={String(daysBeforeAfter)}
          onChangeText={(text) => {
            const val = parseInt(text, 10);
            if (!isNaN(val) && val >= 1) setDaysBeforeAfter(val);
          }}
        />
        <Text style={[styles.inputSuffix, { color: theme.textSecondary }]}>
          {t("app.daysBeforeAfterSuffix")}
        </Text>
      </View>
      <Text style={[styles.fieldHint, { color: theme.textSecondary }]}>
        {t("app.daysBeforeAfterHint")}
      </Text>
    </View>

    {/* Pre-fire Mosaic Strategy */}
    <View style={styles.fieldGroup}>
      <Text style={[styles.fieldLabel, { color: theme.text }]}>
        {t("app.preFireMosaicStrategy")}
      </Text>
      {MOSAIC_STRATEGIES.map(({ value, labelKey }) => (
        <Pressable
          key={`pre-${value}`}
          onPress={() => setPreFireMosaicStrategy(value)}
          style={styles.radioRow}
        >
          <View style={[
            styles.radioOuter,
            { borderColor: preFireMosaicStrategy === value ? theme.primary : theme.border }
          ]}>
            {preFireMosaicStrategy === value && (
              <View style={[styles.radioInner, { backgroundColor: theme.primary }]} />
            )}
          </View>
          <Text style={[
            styles.radioLabel,
            { color: preFireMosaicStrategy === value ? theme.primary : theme.text }
          ]}>
            {t(labelKey)}
          </Text>
        </Pressable>
      ))}
    </View>

    {/* Post-fire Mosaic Strategy */}
    <View style={styles.fieldGroup}>
      <Text style={[styles.fieldLabel, { color: theme.text }]}>
        {t("app.postFireMosaicStrategy")}
      </Text>
      {MOSAIC_STRATEGIES.map(({ value, labelKey }) => (
        <Pressable
          key={`post-${value}`}
          onPress={() => setPostFireMosaicStrategy(value)}
          style={styles.radioRow}
        >
          <View style={[
            styles.radioOuter,
            { borderColor: postFireMosaicStrategy === value ? theme.primary : theme.border }
          ]}>
            {postFireMosaicStrategy === value && (
              <View style={[styles.radioInner, { backgroundColor: theme.primary }]} />
            )}
          </View>
          <Text style={[
            styles.radioLabel,
            { color: postFireMosaicStrategy === value ? theme.primary : theme.text }
          ]}>
            {t(labelKey)}
          </Text>
        </Pressable>
      ))}
    </View>
  </View>
)}
```

- [ ] **Step 5: Add styles**

Add to the existing `StyleSheet.create`:

```typescript
advancedToggle: {
  paddingVertical: 12,
  borderTopWidth: 1,
  marginTop: 12,
},
advancedToggleText: {
  fontWeight: "600",
  fontSize: 15,
},
advancedSection: {
  borderWidth: 1,
  borderRadius: 8,
  padding: 16,
  marginTop: 8,
},
fieldGroup: {
  marginBottom: 16,
},
fieldLabel: {
  fontWeight: "600",
  fontSize: 14,
  marginBottom: 8,
},
fieldHint: {
  fontSize: 12,
  marginTop: 4,
},
sliderRow: {
  flexDirection: "row",
  alignItems: "center",
  gap: 8,
},
sliderValue: {
  fontWeight: "600",
  minWidth: 45,
  textAlign: "right",
},
inputRow: {
  flexDirection: "row",
  alignItems: "center",
  gap: 8,
},
numberInput: {
  borderWidth: 1,
  borderRadius: 6,
  paddingHorizontal: 12,
  paddingVertical: 6,
  width: 80,
  textAlign: "center",
  fontSize: 15,
},
inputSuffix: {
  fontSize: 14,
},
radioRow: {
  flexDirection: "row",
  alignItems: "center",
  gap: 10,
  paddingVertical: 6,
},
radioOuter: {
  width: 20,
  height: 20,
  borderRadius: 10,
  borderWidth: 2,
  alignItems: "center",
  justifyContent: "center",
},
radioInner: {
  width: 10,
  height: 10,
  borderRadius: 5,
},
radioLabel: {
  fontSize: 14,
},
```

- [ ] **Step 6: Commit in mobile repo**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app
git add translations/ app/analysis/new.tsx
git commit -m "feat: add advanced settings UI to mobile app analysis form"
```

---

## Task 12: Final verification

- [ ] **Step 1: Run full backend test suite with coverage**

```bash
docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"
```

Expected: ALL PASS, 100% coverage.

- [ ] **Step 2: Verify web app builds**

```bash
docker exec wildfire-ui npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Manual smoke test**

Open the web app, go to Analysis page:
1. Verify ROI-only checkbox still works
2. Click "Advanced Settings" toggle — verify it expands
3. Move cloud threshold slider — verify value updates
4. Change days before/after — verify integer-only input
5. Select different mosaic strategies — verify radio buttons work
6. Run an analysis — verify no errors
7. Check browser network tab — verify all new query params are sent

- [ ] **Step 4: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: final cleanup for advanced settings feature"
```
