# ROI-Only Checkbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `roi_only` parameter configurable from the analysis UI via a checkbox (checked by default), passing it through the API to the processor.

**Architecture:** Add `roi_only` BooleanField to AnalysisRun model, accept it as a query param in the analyze view, pass it to `process_fire_assessment()`. UI gets a checkbox below the form row (Option A layout). All 3 platforms (web, mobile, electron) updated.

**Tech Stack:** Django, React 19, React Native (Expo), Bootstrap 5

---

## File Structure

### Backend
- Modify: `api/wildfire_assessment/models.py:138` — add `roi_only` field after `status`
- Modify: `api/wildfire_assessment/svc/processor.py:33-69` — accept `roi_only` param
- Modify: `api/wildfire_assessment/views.py:193-226` — read `roi_only` query param, pass to processor and save_analysis_run
- Modify: `api/wildfire_assessment/svc/area_of_interest.py:77-118` — accept and persist `roi_only`
- Create: `api/wildfire_assessment/migrations/0030_analysisrun_roi_only.py` — via makemigrations
- Modify: `api/wildfire_assessment/tests/test_services.py` — test processor with roi_only
- Modify: `api/wildfire_assessment/tests/test_apis.py` — test view passes roi_only

### Web App
- Modify: `ui/src/features/analysis/AnalysisPage.js` — add roiOnly state + checkbox + send in query
- Modify: `ui/src/translations/en.json` — add translation keys
- Modify: `ui/src/translations/pt-BR.json` — add translation keys
- Modify: `ui/src/translations/fr.json` — add translation keys
- Modify: `ui/src/translations/es-ES.json` — add translation keys

### Electron App
- Modify: `wildfire-assessment-electron/src/features/analysis/AnalysisPage.js` — same as web
- Modify: `wildfire-assessment-electron/src/translations/en.json` — add translation keys
- Modify: `wildfire-assessment-electron/src/translations/pt-BR.json` — add translation keys
- Modify: `wildfire-assessment-electron/src/translations/fr.json` — add translation keys
- Modify: `wildfire-assessment-electron/src/translations/es-ES.json` — add translation keys

### Mobile App
- Modify: `wildfire-assessment-app/app/analysis/new.tsx` — add roiOnly state + switch
- Modify: `wildfire-assessment-app/app/(tabs)/analysis.tsx` — add roiOnly state + switch
- Modify: `wildfire-assessment-app/services/api.ts:172-191` — accept roiOnly param
- Modify: `wildfire-assessment-app/translations/en.json` — add translation keys
- Modify: `wildfire-assessment-app/translations/pt-BR.json` — add translation keys
- Modify: `wildfire-assessment-app/translations/fr.json` — add translation keys
- Modify: `wildfire-assessment-app/translations/es-ES.json` — add translation keys

---

### Task 1: Backend — Add `roi_only` to model and processor

**Files:**
- Modify: `api/wildfire_assessment/models.py:138`
- Modify: `api/wildfire_assessment/svc/processor.py:33-69`
- Modify: `api/wildfire_assessment/svc/area_of_interest.py:77-118`
- Test: `api/wildfire_assessment/tests/test_services.py`

- [ ] **Step 1: Add `roi_only` field to AnalysisRun model**

In `api/wildfire_assessment/models.py`, after line 138 (`default="completed"`), add:

```python
    roi_only = models.BooleanField(default=True)
```

- [ ] **Step 2: Update `process_fire_assessment` to accept `roi_only` param**

In `api/wildfire_assessment/svc/processor.py`, change the function signature from:

```python
def process_fire_assessment(
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
) -> dict:
```

to:

```python
def process_fire_assessment(
    pre_fire_date: str,
    post_fire_date: str,
    polygon_path: str,
    roi_only: bool = True,
) -> dict:
```

And change line 69 from `roi_only=True` to `roi_only=roi_only`.

- [ ] **Step 3: Update `save_analysis_run` to accept and persist `roi_only`**

In `api/wildfire_assessment/svc/area_of_interest.py`, change `save_analysis_run` signature:

```python
def save_analysis_run(user, area, pre_fire_date, post_fire_date, assessment_result, roi_only=True):
```

And add `roi_only=roi_only` to the `AnalysisRun.objects.create()` call at line 108.

- [ ] **Step 4: Write tests for processor with roi_only**

In `api/wildfire_assessment/tests/test_services.py`, add a test in `ProcessorTests` after the existing `test_process_fire_assessment_uses_visual_urls_when_available` test. **Match the existing decorator order** (os.unlink outermost, then PostFireAssessment, then download, then secret):

```python
@patch("wildfire_assessment.svc.processor.os.unlink")
@patch("wildfire_assessment.svc.processor.PostFireAssessment")
@patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
@patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
def test_process_fire_assessment_passes_roi_only_false(
    self, mock_secret, mock_download, mock_assessment, mock_unlink
):
    mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
    mock_download.return_value = '{"type": "Polygon"}'
    assessment_instance = MagicMock()
    assessment_instance.run.return_value = {
        "visual": {
            "RGB_PRE_FIRE_VISUAL": {"url": "http://example.com/pre.jpg"},
            "RGB_POST_FIRE_VISUAL": {"url": "http://example.com/post.jpg"},
            "DNDVI_VISUAL": {"url": "http://example.com/dndvi.jpg"},
            "DNBR_VISUAL": {"url": "http://example.com/dnbr.jpg"},
            "RBR_VISUAL": {"url": "http://example.com/rbr.jpg"},
        },
        "statistics": {
            "DNBR_AREA_STATISTICS": {"url": "http://example.com/stats.json"}
        },
    }
    mock_assessment.return_value = assessment_instance

    processor.process_fire_assessment(
        pre_fire_date=self.pre_fire_date,
        post_fire_date=self.post_fire_date,
        polygon_path=self.polygon_path,
        roi_only=False,
    )

    call_kwargs = mock_assessment.call_args.kwargs
    self.assertFalse(call_kwargs["roi_only"])
```

Also add tests for `save_analysis_run` in the **`AreaOfInterestServiceTests` class** (after the existing `test_save_analysis_run_*` tests, around line 1459+):

```python
def test_save_analysis_run_persists_roi_only_false(self):
    result = {"severity_map": "{}"}
    run = aoi_service.save_analysis_run(
        self.user, self.area, "2023-01-01", "2023-02-01", result, roi_only=False
    )
    self.assertFalse(run.roi_only)

def test_save_analysis_run_defaults_roi_only_true(self):
    result = {"severity_map": "{}"}
    run = aoi_service.save_analysis_run(
        self.user, self.area, "2023-01-01", "2023-02-01", result
    )
    self.assertTrue(run.roi_only)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"`
Expected: All tests pass, 100% coverage maintained.

- [ ] **Step 6: Generate migration**

Run: `docker exec wildfire-api python manage.py makemigrations wildfire_assessment`
Expected: Creates `0030_analysisrun_roi_only.py`

- [ ] **Step 7: Commit**

```bash
git add api/wildfire_assessment/models.py api/wildfire_assessment/svc/processor.py api/wildfire_assessment/svc/area_of_interest.py api/wildfire_assessment/migrations/0030_analysisrun_roi_only.py api/wildfire_assessment/tests/
git commit -m "feat: make roi_only configurable in model and processor"
```

---

### Task 2: Backend — Wire `roi_only` through the analyze view

**Files:**
- Modify: `api/wildfire_assessment/views.py:193-226`
- Test: `api/wildfire_assessment/tests/test_apis.py`

- [ ] **Step 1: Add `roi_only` to `@extend_schema` parameters and read it in the view**

In `api/wildfire_assessment/views.py`, add a new `OpenApiParameter` to the `@extend_schema` `parameters` list (after the `post_fire_date` parameter, around line 190):

```python
OpenApiParameter(
    name="roi_only",
    description="Clip results to Region of Interest only (default: true)",
    type=OpenApiTypes.BOOL,
    required=False,
),
```

Then in the `analyze` method (line 202-203), after reading `post_fire_date`, add:

```python
roi_only = request.query_params.get("roi_only", "true").lower() != "false"
```

Then pass it to `process_fire_assessment` at line 205:

```python
assessment_result = process_fire_assessment(
    pre_fire_date=pre_fire_date,
    post_fire_date=post_fire_date,
    polygon_path=instance.polygon_path,
    roi_only=roi_only,
)
```

And pass it to `save_analysis_run` at line 211:

```python
analysis_run = save_analysis_run(
    user=request.user,
    area=instance,
    pre_fire_date=pre_fire_date,
    post_fire_date=post_fire_date,
    assessment_result=assessment_result,
    roi_only=roi_only,
)
```

- [ ] **Step 2: Update existing analyze test to verify roi_only is passed**

In `api/wildfire_assessment/tests/test_apis.py`, update `test_analyze_calls_processor_with_expected_arguments` (line 119) to also assert roi_only:

After line 139 (`self.assertEqual(kwargs["polygon_path"], self.reserve.polygon_path)`), add:

```python
self.assertTrue(kwargs["roi_only"])
```

- [ ] **Step 3: Add test for roi_only=false in query params**

Add a new test after `test_analyze_calls_processor_with_expected_arguments`:

```python
@patch("wildfire_assessment.views.process_scientific_deliverable.delay")
@patch("wildfire_assessment.views.process_fire_assessment")
def test_analyze_passes_roi_only_false(self, mock_process, mock_scientific):
    UserCountry.objects.create(user=self.user, country=self.country)
    self.client.force_authenticate(user=self.user)
    query = urlencode(
        {
            "pre_fire_date": "2023-01-01",
            "post_fire_date": "2023-01-15",
            "roi_only": "false",
        }
    )
    url = reverse("areaofinterest-analyze", args=[self.reserve.id])
    mock_process.return_value = {"s3_urls": {}, "analysis_results": {}}
    self.client.post(f"{url}?{query}")
    kwargs = mock_process.call_args.kwargs
    self.assertFalse(kwargs["roi_only"])
```

- [ ] **Step 4: Run tests**

Run: `docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"`
Expected: All tests pass, 100% coverage.

- [ ] **Step 5: Commit**

```bash
git add api/wildfire_assessment/views.py api/wildfire_assessment/tests/
git commit -m "feat: wire roi_only query param through analyze endpoint"
```

---

### Task 3: Web App — Add ROI-only checkbox to analysis form

**Files:**
- Modify: `ui/src/features/analysis/AnalysisPage.js`
- Modify: `ui/src/translations/en.json`
- Modify: `ui/src/translations/pt-BR.json`
- Modify: `ui/src/translations/fr.json`
- Modify: `ui/src/translations/es-ES.json`

- [ ] **Step 1: Add translation keys to all 4 language files**

Add after the `"app.deliverableError"` key (line 92) in each file to keep deliverable keys grouped:

**en.json:**
```json
"app.roiOnly": "Clip results to Region of Interest only",
"app.roiOnlyHint": "When unchecked, analysis covers the full satellite image extent",
```

**pt-BR.json:**
```json
"app.roiOnly": "Recortar resultados apenas para a Região de Interesse",
"app.roiOnlyHint": "Quando desmarcado, a análise cobre a extensão completa da imagem de satélite",
```

**fr.json:**
```json
"app.roiOnly": "Limiter les résultats à la Région d'Intérêt uniquement",
"app.roiOnlyHint": "Si décoché, l'analyse couvre l'étendue complète de l'image satellite",
```

**es-ES.json:**
```json
"app.roiOnly": "Recortar resultados solo a la Región de Interés",
"app.roiOnlyHint": "Cuando está desmarcado, el análisis cubre toda la extensión de la imagen satelital",
```

- [ ] **Step 2: Add `roiOnly` state to AnalysisPage.js**

In `ui/src/features/analysis/AnalysisPage.js`, after line 22 (`const [analysisStep, setAnalysisStep] = useState(0);`), add:

```javascript
const [roiOnly, setRoiOnly] = useState(true);
```

- [ ] **Step 3: Add checkbox UI below the form row**

In `AnalysisPage.js`, after the closing `</div>` of the `row g-3` div (line 523), and before the closing `</form>` tag, add:

```jsx
<div className="mt-3 pt-3 border-top">
  <div className="form-check">
    <input
      className="form-check-input"
      type="checkbox"
      id="roiOnly"
      checked={roiOnly}
      onChange={(e) => setRoiOnly(e.target.checked)}
    />
    <label className="form-check-label" htmlFor="roiOnly">
      {t("app.roiOnly")}
    </label>
    <div className="form-text">{t("app.roiOnlyHint")}</div>
  </div>
</div>
```

- [ ] **Step 4: Send `roi_only` in the analyze request**

In `AnalysisPage.js`, in `handleSubmit` (around line 385), update the queryParams to include roi_only:

```javascript
const queryParams = new URLSearchParams({
  pre_fire_date: preFireDate,
  post_fire_date: postFireDate,
  roi_only: String(roiOnly),
});
```

- [ ] **Step 5: Verify in browser**

Open the web app, navigate to Analysis page. Confirm:
- Checkbox appears below the form controls with a top border separator
- Checkbox is checked by default
- Unchecking sends `roi_only=false` in the request (check network tab)

- [ ] **Step 6: Commit**

```bash
git add ui/src/features/analysis/AnalysisPage.js ui/src/translations/
git commit -m "feat: add ROI-only checkbox to web app analysis form"
```

---

### Task 4: Electron App — Add ROI-only checkbox (mirror web app)

**Files:**
- Modify: `wildfire-assessment-electron/src/features/analysis/AnalysisPage.js`
- Modify: `wildfire-assessment-electron/src/translations/en.json`
- Modify: `wildfire-assessment-electron/src/translations/pt-BR.json`
- Modify: `wildfire-assessment-electron/src/translations/fr.json`
- Modify: `wildfire-assessment-electron/src/translations/es-ES.json`

- [ ] **Step 1: Add same translation keys to all 4 electron translation files**

Same keys as Task 3 Step 1, added to the electron app translation files.

- [ ] **Step 2: Apply same AnalysisPage.js changes as web app**

The electron app's `AnalysisPage.js` mirrors the web app. Apply the exact same 3 changes:
1. Add `const [roiOnly, setRoiOnly] = useState(true);` state
2. Add checkbox HTML below the form row
3. Add `roi_only: String(roiOnly)` to queryParams in handleSubmit

- [ ] **Step 3: Commit**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-electron
git add src/features/analysis/AnalysisPage.js src/translations/
git commit -m "feat: add ROI-only checkbox to electron app analysis form"
```

---

### Task 5: Mobile App — Add ROI-only switch

**Files:**
- Modify: `wildfire-assessment-app/services/api.ts:172-191`
- Modify: `wildfire-assessment-app/app/analysis/new.tsx`
- Modify: `wildfire-assessment-app/app/(tabs)/analysis.tsx`
- Modify: `wildfire-assessment-app/translations/en.json`
- Modify: `wildfire-assessment-app/translations/pt-BR.json`
- Modify: `wildfire-assessment-app/translations/fr.json`
- Modify: `wildfire-assessment-app/translations/es-ES.json`

- [ ] **Step 1: Add translation keys to all 4 mobile translation files**

Same keys as Task 3 Step 1 (use the `app.roiOnly` and `app.roiOnlyHint` keys).

- [ ] **Step 2: Update `api.ts` to accept `roiOnly` param**

In `wildfire-assessment-app/services/api.ts`, update `runAnalysis`:

```typescript
async runAnalysis(
  areaId: number,
  preFireDate: string,
  postFireDate: string,
  roiOnly: boolean = true,
  signal?: AbortSignal
): Promise<any> {
  const qs = new URLSearchParams({
    pre_fire_date: preFireDate,
    post_fire_date: postFireDate,
    roi_only: String(roiOnly),
  });
  const res = await this.authorizedFetch(
    `${API_URL}/area_of_interest/${areaId}/analyze/?${qs}`,
    { method: "POST", signal }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw errorData;
  }
  return res.json();
}
```

- [ ] **Step 3: Update `app/analysis/new.tsx` — add state + Switch + pass to API**

Add state near other state declarations:
```typescript
const [roiOnly, setRoiOnly] = useState(true);
```

Add a Switch component after `AnalysisDatePicker` (after line 318) and before the Run button:
```tsx
<View style={[styles.checkboxRow, { borderTopColor: theme.border }]}>
  <View style={styles.checkboxTextContainer}>
    <Text style={[styles.checkboxLabel, { color: theme.text }]}>
      {t("app.roiOnly")}
    </Text>
    <Text style={[styles.checkboxHint, { color: theme.textSecondary }]}>
      {t("app.roiOnlyHint")}
    </Text>
  </View>
  <Switch
    value={roiOnly}
    onValueChange={setRoiOnly}
    trackColor={{ false: theme.border, true: theme.primary }}
  />
</View>
```

Update the `handleSubmit` call (line 120-123):
```typescript
const result = await apiClient.runAnalysis(
  selectedAreaId,
  preFireDate,
  postFireDate,
  roiOnly,
  abortRef.current.signal
);
```

Add `roiOnly` to the `useCallback` dependency array (line 146).

Add styles:
```typescript
checkboxRow: {
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "space-between",
  marginTop: 12,
  paddingTop: 12,
  borderTopWidth: 1,
},
checkboxTextContainer: {
  flex: 1,
  marginRight: 12,
},
checkboxLabel: {
  fontSize: 14,
  fontWeight: "500",
},
checkboxHint: {
  fontSize: 12,
  marginTop: 2,
},
```

- [ ] **Step 4: Update `app/(tabs)/analysis.tsx` — same changes as new.tsx**

Apply all 4 changes to the tabs version:
1. Add `const [roiOnly, setRoiOnly] = useState(true);` state
2. Add Switch UI component after `AnalysisDatePicker` and before the Run button
3. Update `apiClient.runAnalysis` call to pass `roiOnly` before `abortRef.current.signal`
4. Add `roiOnly` to the `useCallback` dependency array
5. Add the `checkboxRow`, `checkboxTextContainer`, `checkboxLabel`, `checkboxHint` styles

- [ ] **Step 5: Commit**

```bash
cd /Users/diogo/github-archive/repos/Brazil-Flying-Labs/wildfire-assessment-app
git add services/api.ts app/analysis/new.tsx "app/(tabs)/analysis.tsx" translations/
git commit -m "feat: add ROI-only switch to mobile app analysis form"
```

---

### Task 6: Run full test suite and verify coverage

- [ ] **Step 1: Run full backend test suite with coverage**

Run: `docker exec wildfire-api bash -c "coverage run --source=wildfire_assessment manage.py test && coverage report"`
Expected: All tests pass, 100% coverage.

- [ ] **Step 2: Run migration**

Run: `docker exec wildfire-api python manage.py migrate`
Expected: Migration 0030 applies successfully.

- [ ] **Step 3: Final commit if any fixes needed**

If any test failures or coverage gaps were found, fix and commit.
