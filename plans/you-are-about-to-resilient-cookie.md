# Matrix Quote Web — Full-Stack Migration Plan

## Context

`matrix-quote-web/` is a fresh Git repo seeded with the ML core from the existing Streamlit app at `../matrix_quote_app/` (note the underscore; the task brief's path `../matrix-quote-app/` was a typo). Only `core/` (`config.py`, `schemas.py`, `features.py`, `models.py`), `service/predict_lib.py`, and `requirements.txt` have been copied. The Streamlit-specific `core/ui.py` was intentionally left behind.

The migration goal is to expose the existing per-operation GBR quoting engine through a professional, public-facing web application: a polished customer-facing estimator (Single Quote, Batch Quotes, Model Performance) plus a password-protected admin console (Upload & Train, Data Explorer, Drivers & Similar, Overview). The `core/` and `service/` modules are treated as a **vendored, read-only library** — the backend wraps them without modification so improvements in the Streamlit reference repo can still be pulled in by a straight file copy.

Success criteria: (1) a customer can estimate hours for a new project through a branded web form, (2) an admin can upload an Excel file and retrain all 12 operation models without SSH, (3) the deployment survives redeploys without losing the master Parquet or model artifacts, and (4) `core/`/`service/` remain byte-for-byte portable between the Streamlit repo and the web repo.

---

## 1. Architecture Overview

### 1a. Backend framework — **FastAPI**

FastAPI is the obvious fit because `core/schemas.py` already defines `QuoteInput`, `OpPrediction`, `SalesBucketPrediction`, and `QuotePrediction` as Pydantic v2 models. FastAPI consumes those types directly as request and response models, so the existing schema code doubles as the API contract — no duplication, no translation layer. Starlette's `UploadFile` handles the xlsx/csv streams that `train_one_op()` and `predict_quotes_df()` need, and the automatic OpenAPI docs at `/docs` become a free admin/debugging surface.

Concretely, the following existing callables become routes:

| Existing callable | Location | Route |
|---|---|---|
| `predict_quote(q: QuoteInput) -> QuotePrediction` | `service/predict_lib.py:55` | `POST /api/quote/single` |
| `predict_quotes_df(df_in: pd.DataFrame) -> pd.DataFrame` | `service/predict_lib.py:125` | `POST /api/quote/batch` |
| `train_one_op(df_master, target, models_dir, version)` | `core/models.py:47` | `POST /api/admin/train` (loops all 12 targets) |
| `load_model(target, version, models_dir)` | `core/models.py:145` | used internally by predict + `GET /api/admin/model/{op}/importances` |
| `engineer_features_for_training(df_raw)` | `core/features.py:94` | used internally by `/api/admin/train` |
| `prepare_quote_features(df_quote)` | `core/features.py:146` | used internally by `/api/quote/batch` |

Route signature summary (full table in the Summary Tables section):

```
POST /api/quote/single      body: QuoteInput                          -> QuotePrediction
POST /api/quote/batch       multipart: file (csv|xlsx), sheet?        -> FileResponse(text/csv)
GET  /api/metrics                                                      -> MetricsSummary
GET  /api/health                                                       -> HealthResponse
GET  /api/catalog/dropdowns                                            -> DropdownOptions
POST /api/admin/login       body: {password}                          -> {token}
POST /api/admin/train       multipart: file (xlsx), sheet             -> TrainResponse
GET  /api/admin/dataset     query: industry_segment?, system_category? -> DatasetPage
GET  /api/admin/drivers/{op}                                           -> DriversResponse
POST /api/admin/similar     body: SimilarRequest                       -> SimilarResponse
GET  /api/admin/overview                                               -> OverviewResponse
POST /api/admin/reset                                                  -> {ok: true}
```

Python 3.11 for runtime parity with the Streamlit repo (matches its devcontainer). `uvicorn` for dev, `gunicorn -k uvicorn.workers.UvicornWorker` for prod.

### 1b. Frontend framework — **Vite + React 18 + TypeScript**

Next.js is overkill here. There is no SEO need (admin is gated, customer side is a calculator), no server-rendered marketing pages, and no incremental-static-regeneration story that matters. A Vite SPA gets us:

- Single static bundle, deploys to any static host or behind FastAPI itself.
- Sub-second dev HMR, which matters given how many form fields the Single Quote page has (31 numeric + 6 categorical).
- Avoids the friction of matching Next.js's file-upload handling (multipart streams are simpler in a plain fetch/axios path than in Next route handlers, and `train_one_op` calls need multi-second requests that Next server functions deliberately constrain).

Primary libraries:

- **React Router v6** — routes listed under §3.
- **TanStack Query (React Query) v5** — server-state for `/api/metrics`, `/api/admin/overview`, dataset paging, catalog dropdowns. Caches the expensive `/api/admin/dataset` reads.
- **React Hook Form + Zod** — the Single Quote form has ~37 fields; React Hook Form keeps re-renders minimal and Zod mirrors the `QuoteInput` schema so client validation matches server validation.
- **TanStack Table v8** — Data Explorer, Batch Quotes results, Model Performance, Similar Projects.
- **Recharts** — feature-importance horizontal bars, MAE/R² comparisons, robot_count-vs-hours scatter, Model-vs-Quoted grouped bars. (Recharts handles the five chart types in the Streamlit app without needing a second library.)
- **Tailwind CSS v3 + shadcn/ui primitives** — the visual direction in §3 is built on these.
- **axios** — one wrapper that injects the admin bearer token when present.

### 1c. Deployment target — **Railway, single-service with persistent volume**

Railway is chosen over Render, Fly, and Vercel for three reasons specific to this app:

1. **Persistent disk is native.** Railway Volumes attach to the container at a mount path and survive redeploys. The Streamlit app writes `data/master/projects_master.parquet`, `data/master/uploads_log.csv`, and `models/*.joblib` to local paths defined as `MASTER_DATA_PATH`, `UPLOADS_LOG_PATH`, `METRICS_PATH` in `quote_app.py:36-38`. Mounting a 1 GB volume at `/data` and pointing those paths to it preserves the existing file-based workflow with zero code changes to `core/models.py`.
2. **No serverless time limit.** Training all 12 models on a realistic dataset (hundreds of rows × 3 × `GradientBoostingRegressor(n_estimators=300, max_depth=5)` per op = 36 GBRs per train call) can exceed 10 s easily. Vercel's 10 s (Hobby) / 60 s (Pro) ceiling would force a job-queue redesign; Railway containers have no such ceiling.
3. **Single-service topology.** FastAPI serves both the API and the built Vite bundle from `StaticFiles`. No CORS, no domain juggling, no split deploy. The frontend builds to `frontend/dist/` and FastAPI mounts it at `/` with an API prefix of `/api`.

S3 and Supabase Storage were considered and rejected at this scale. The master Parquet is megabytes, not gigabytes; the 12 model bundles combined are tens of MB. Remote object storage adds latency on every `load_model()` call (12 loads per `/api/quote/single`) and forces cache invalidation logic after retraining. A mounted volume is simpler and faster. If the dataset grows past volume-reasonable size (>10 GB) or a multi-instance deploy becomes necessary, migration to S3 with a local LRU cache is straightforward — but that is a YAGNI problem for later.

Env vars for deployment:
- `ADMIN_PASSWORD` — required, no default.
- `ADMIN_JWT_SECRET` — required, 32+ random bytes.
- `DATA_DIR` — defaults to `./` locally, `/data` on Railway.
- `PORT` — Railway injects.

### 1d. Monorepo layout

```
matrix-quote-web/
├── core/                           # vendored from matrix_quote_app, DO NOT EDIT
│   ├── config.py
│   ├── schemas.py
│   ├── features.py
│   └── models.py
├── service/                        # vendored from matrix_quote_app, DO NOT EDIT
│   └── predict_lib.py
├── backend/                        # new — FastAPI wrapper
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, static mount, router include
│   │   ├── deps.py                 # settings, path helpers, admin auth dep
│   │   ├── paths.py                # MASTER_DATA_PATH, METRICS_PATH, UPLOADS_LOG_PATH from DATA_DIR
│   │   ├── routes/
│   │   │   ├── quote.py            # /api/quote/single, /api/quote/batch
│   │   │   ├── metrics.py          # /api/metrics, /api/health, /api/catalog/dropdowns
│   │   │   └── admin.py            # /api/admin/* (login, train, dataset, drivers, similar, overview, reset)
│   │   ├── schemas_api.py          # API-layer extensions (TrainResponse, DatasetPage, etc.) — QuoteInput re-exported from core
│   │   └── storage.py              # read_master(), write_master(), read_metrics(), log_upload(), reset_all()
│   └── pyproject.toml              # backend-only deps (FastAPI, uvicorn, python-multipart, python-jose, pydantic-settings)
├── frontend/                       # new — Vite SPA
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                 # BrowserRouter + layout
│   │   ├── api/                    # axios client + typed hooks
│   │   ├── components/             # shared UI (Button, Card, Input, Table, Chip, PageHeader, Section, Kpi, ResultHero, EmptyState)
│   │   ├── pages/
│   │   │   ├── SingleQuote.tsx
│   │   │   ├── BatchQuotes.tsx
│   │   │   ├── ModelPerformance.tsx
│   │   │   ├── AdminLogin.tsx
│   │   │   ├── AdminLayout.tsx     # wraps admin pages, checks token
│   │   │   ├── UploadTrain.tsx
│   │   │   ├── DataExplorer.tsx
│   │   │   ├── Drivers.tsx
│   │   │   └── Overview.tsx
│   │   ├── types/                  # generated from OpenAPI via openapi-typescript
│   │   └── styles/                 # Tailwind entry + tokens
│   ├── index.html
│   ├── vite.config.ts              # proxies /api to :8000 in dev
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── tests/                          # pytest + httpx, see §4f
│   ├── conftest.py
│   ├── test_quote_routes.py
│   ├── test_admin_routes.py
│   ├── test_storage.py
│   └── fixtures/                   # tiny xlsx and trained-model fixtures
├── data/                           # gitignored; mirrors Streamlit layout
│   └── master/                     # projects_master.parquet, uploads_log.csv
├── models/                         # gitignored; *.joblib + metrics_summary.csv
├── .github/workflows/ci.yml        # lint + test
├── Dockerfile                      # multi-stage: build frontend, install backend, copy both
├── railway.json                    # Railway config (build + start + volume)
├── requirements.txt                # production pin (extends backend/pyproject)
├── .gitignore
├── .dockerignore
├── .env.example
└── README.md                       # deployment + local dev instructions
```

Rationale: `core/` and `service/` stay at the repo root so the vendoring stays identical to `matrix_quote_app/`. Backend code that *wraps* them lives in `backend/app/` to make the guard hook (see §6) trivial — "anything under `core/` or `service/` is off-limits except through explicit approval."

---

## 2. Backend Plan

All routes live under `/api`. Pydantic models used directly from `core/schemas.py` are re-exported in `backend/app/schemas_api.py` alongside new response types listed below. The admin bearer token is obtained from `POST /api/admin/login` and required (via `Depends(require_admin)`) on every `/api/admin/*` route.

### 2a. Single quote prediction — `POST /api/quote/single`

- **Purpose:** Wrap `predict_quote()` from `service/predict_lib.py:55`.
- **Auth:** Public (no token).
- **Request body:** `QuoteInput` from `core/schemas.py:9`. Exactly the 6 categorical + 31 numeric fields the Streamlit form collects (see `quote_app.py:826-866` for the construction call). `project_id` is optional. Defaults match `QuoteInput` defaults so any unset numeric field becomes `0` and flags become `0`/`1` as declared.
- **Response body:** `QuotePrediction` from `core/schemas.py:77`. Includes `ops: Dict[str, OpPrediction]` keyed by `me10`..`pm200`, `total_p50/p10/p90`, and `sales_buckets: Dict[str, SalesBucketPrediction]` keyed by the 9 entries in `SALES_BUCKETS`.
- **Implementation notes:** If no models are trained, `predict_quote()` returns an empty `ops` dict and zero totals. The route should detect that (by checking `len(ops) == 0`) and return HTTP 409 with `{"detail": "Models are not trained. Please upload a dataset and train first."}` so the frontend can render the equivalent of the Streamlit "Models are not trained" empty state (`quote_app.py:628`).

### 2b. Batch quote prediction — `POST /api/quote/batch`

- **Purpose:** Wrap `predict_quotes_df()` from `service/predict_lib.py:125`.
- **Auth:** Public.
- **Request:** `multipart/form-data` with `file` (required) and optional `sheet` (string, used only for xlsx). Mirrors `quote_app.py:1077-1093`.
- **Response:** `text/csv` via `StreamingResponse`. Filename defaults to `quote_predictions.csv` matching `quote_app.py:1117`.
- **Implementation notes:**
  - Parse xlsx with `pd.ExcelFile(uploaded.file)` using the given sheet; CSV is `pd.read_csv(uploaded.file)`.
  - Before calling `predict_quotes_df`, check the required columns as in `quote_app.py:1098-1103`: `set(QUOTE_NUM_FEATURES + QUOTE_CAT_FEATURES)` must be a subset of the uploaded columns. Missing columns → HTTP 400 with `{"detail": "Missing required columns: [...]"}`.
  - Reject files over 10 MB to prevent accidental DoS (`UploadFile.file.seek(0, 2)` check).
  - No JSON preview is returned; the frontend's preview table is built from the first 50 rows the user sees locally in the file-reader component before upload.

### 2c. Model training — `POST /api/admin/train`

- **Purpose:** Replicate the full "Merge into master & train models" button behavior from `quote_app.py:1152-1244`. This single route calls `train_one_op()` for each of the 12 targets.
- **Auth:** Admin.
- **Request:** `multipart/form-data` with `file` (xlsx, required) and `sheet` (required — we surface sheet selection in the UI first via a tiny `POST /api/admin/train/preview` that returns sheet names, or we accept the first sheet by default; see §3 Upload & Train UX).
- **Response:**
  ```
  TrainResponse {
    rows_raw: int,
    rows_train: int,
    rows_master_total: int,
    metrics: List[MetricRow],      # one row per trained op: {target, version, rows, mae, r2, model_path}
    trained_targets: List[str],
    skipped_targets: List[str],    # targets with <5 rows, matching core/models.py:61 behavior
    models_ready: bool
  }
  ```
- **Implementation flow (lifted from `quote_app.py:1155-1244`):**
  1. Parse xlsx → `df_raw`.
  2. Validate `REQUIRED_TRAINING_COLS` from `core/config.py:100`.
  3. `df_train = engineer_features_for_training(df_raw)` — `core/features.py:94`.
  4. Filter to rows with at least one non-zero `*_actual_hours` value (replicates `quote_app.py:1163-1169`).
  5. Merge into master: read existing `MASTER_DATA_PATH` parquet if present, concat, dedupe by `project_id` keeping last (`quote_app.py:1197-1203`), write back.
  6. Log to `UPLOADS_LOG_PATH` via `storage.log_upload(rows_raw, rows_train, rows_master_total)`.
  7. Iterate `TARGETS` from `core/config.py:5` calling `train_one_op(df_master_new, target, models_dir=models_dir(), version="v1")`.
  8. Aggregate returned metric dicts into a DataFrame, write to `METRICS_PATH`.
  9. Return `TrainResponse`.
- **Concurrency:** Wrap the whole flow in an asyncio lock so two admins uploading at once don't corrupt the master parquet. The lock is process-local; for multi-worker gunicorn use a file lock on `DATA_DIR/.train.lock` via `filelock`.

### 2d. Model metrics — `GET /api/metrics`

- **Purpose:** Replicate Model Performance page data source (`quote_app.py:388-442`).
- **Auth:** Public (customer-facing "Model Performance" page). This is a deliberate product decision — showing MAE and R² signals model quality to customers and builds trust.
- **Response:**
  ```
  MetricsSummary {
    models_ready: bool,
    metrics: List[MetricRow]      # direct pass-through of models/metrics_summary.csv
  }
  ```
- **Implementation:** `storage.read_metrics()` reads `METRICS_PATH`; returns empty list and `models_ready=false` when the file is absent.

**Related route — `GET /api/admin/drivers/{op}`** returns feature importances for a single op (see §2f) and is admin-only because it exposes internal feature weights.

### 2e. Data explorer — `GET /api/admin/dataset`

- **Purpose:** Replicate the filter + paged-table behavior in `quote_app.py:297-385`.
- **Auth:** Admin.
- **Query params:**
  - `industry_segment: List[str] | None` — repeated param or CSV.
  - `system_category: List[str] | None`.
  - `limit: int = 50`, `offset: int = 0`.
  - `op: str | None` — if provided, includes that op's column in the response plus `robot_count` pairs for the scatter plot.
- **Response:**
  ```
  DatasetPage {
    total: int,
    filtered_total: int,
    columns: List[str],
    rows: List[Dict[str, Any]],                  # JSON-safe records
    facets: {
      industry_segment: List[str],
      system_category: List[str],
      ops_with_data: List[str]
    },
    scatter: List[{project_id, robot_count, hours}] | None   # only when op is given
  }
  ```
- **Implementation:** Reads `MASTER_DATA_PATH` via `storage.read_master()` (uses pandas `read_parquet`), applies `.isin()` filters, slices `[offset:offset+limit]`. `NaN` → `None` for JSON safety (use `df.replace({np.nan: None}).to_dict(orient='records')`).

### 2f. Drivers and similar projects

Two routes, both admin-only because the endpoint exposes training-internal data.

**`GET /api/admin/drivers/{op}`**
- Loads bundle via `load_model(op, version='v1')` from `core/models.py:145`.
- Derives feature importances with the exact logic in `quote_app.py:485-513`:
  1. Prefer `bundle['meta']['feature_importances']` if present (CQR bundle shape).
  2. Else extract from `pipeline.named_steps['model'].feature_importances_` (legacy shape).
  3. Try `preprocessor.get_feature_names_out()` to label features; fall back to `f_{i}`.
- Response:
  ```
  DriversResponse {
    op: str,
    has_model: bool,
    features: List[{feature: str, importance: float}],  # sorted desc, all features
    nonzero_count: int
  }
  ```

**`POST /api/admin/similar`**
- Request:
  ```
  SimilarRequest {
    industry_segment: str | None,
    system_category: str | None,
    min_robots: int = 0,
    max_robots: int = 10,
    limit: int = 50
  }
  ```
- Response:
  ```
  SimilarResponse {
    count: int,
    rows: List[Dict[str, Any]]    # same projection as quote_app.py:589-608
  }
  ```
- Implementation mirrors `quote_app.py:578-608`: filter the master parquet, return a projection of `project_id, industry_segment, system_category, robot_count, stations_count` plus the first available target column.

### 2g. Dataset health / overview — `GET /api/admin/overview`

- **Purpose:** Replicate `quote_app.py:211-294`.
- **Auth:** Admin.
- **Response:**
  ```
  OverviewResponse {
    n_projects: int,
    n_ops_modeled: int,                # metrics_df['target'].nunique()
    avg_mae: float | None,
    avg_r2: float | None,
    models_ready: bool,
    recent_uploads: List[UploadLogRow],   # tail(10) from uploads_log.csv
    metrics: List[MetricRow]
  }
  ```

### 2h. Admin authentication

Single static password, shared bearer JWT, 12-hour expiry. Rationale: this app has a tiny admin population (the internal team), no self-serve accounts, no privilege tiers. A proper IdP would be over-engineered.

Mechanism:

1. Operator sets `ADMIN_PASSWORD` and `ADMIN_JWT_SECRET` in Railway env vars.
2. `POST /api/admin/login` body `{password: str}`:
   - Compare using `hmac.compare_digest(ADMIN_PASSWORD, password)` to avoid timing attacks.
   - Rate-limit to 10 attempts per IP per 10 minutes via `slowapi`.
   - On success: sign a JWT with `python-jose` containing `{sub: "admin", exp: now+12h}`. Return `{token, expires_at}`.
3. `backend/app/deps.py::require_admin(Authorization: str = Header(...))` verifies the JWT and raises 401 on failure. Every `/api/admin/*` route depends on it.
4. Frontend stores the token in `sessionStorage` (not `localStorage` — dies with the tab, acceptable for internal admin use), attaches it to axios via an interceptor, and clears it on 401.

Explicitly not in scope: password reset, rotation UX, multi-admin accounts, audit logs. If the admin surface ever opens up to more users or contains anything customer-sensitive, swap this out for an IdP (Clerk/Auth0/WorkOS) — the swap is a local change to `require_admin` and the login page.

**One public/admin split risk:** `GET /api/metrics` is public, but `GET /api/admin/drivers/*` is admin-only even though both derive from the same model artifacts. This is intentional — aggregate accuracy numbers are fine to show customers, per-feature importance (which reveals internal estimation logic) is not.

---

## 3. Frontend Plan

### Visual design direction

**Palette.** A professional industrial-automation tool should read as *precise* and *trustworthy*, not flashy. Going with a **light-default** theme because customers don't want to stare at a dark form while entering 37 values; dark mode is a nice-to-have toggle.

- Background: `#F8F8F6` (warm off-white) / `#0F1013` in dark.
- Surface: `#FFFFFF` / `#17181C`.
- Ink: `#0F1013` / `#F2F2F3`.
- Muted text: `#5A5D66` / `#A0A0A8`.
- Border: `#E5E5E2` / `#26272D`.
- **Accent primary — `#F5A524` (amber)** — the Streamlit app already leans on this for bars and "Recommended" values (see `_altair_theme` in `quote_app.py:86`). It signals industrial/engineering without being as clichéd as safety-yellow or hi-vis orange, and it has enough contrast against both light and dark surfaces.
- Accent secondary — `#60A5FA` (blue) for "Your quote / comparison" elements.
- Semantic — `#22C55E` success, `#EAB308` warning, `#EF4444` danger.

**Typography.** `IBM Plex Sans` for UI (matches the Streamlit app's Altair labels, self-hosted via `fontsource`). `IBM Plex Mono` for numbers, metrics, and the table body. Display sizes: 13/14/16/20/28/40. Weight: 400 body, 500 headings and KPI labels, never 700.

**Layout.** 1200 px content max, 24 px grid, Tailwind's default spacing scale. Section headers use the Streamlit pattern of a numbered step chip (`01`, `02`) next to a title — preserved because it gave the Streamlit app a calm, checklist-like feel that fits a quoting workflow. The Single Quote page mirrors the 6-section layout from `quote_app.py:634-800` so users comfortable with the Streamlit version find themselves.

**Navigation.** Left rail at ≥1024 px (Estimate / Analyze / Admin groups like `quote_app.py:179-183`), top bar on mobile. A persistent "Model status" chip in the rail — green "Ready" / amber "Not trained" — is polled from `/api/metrics` every 60 s.

### Public (customer-facing) routes

**`/` — Single Quote**

The hero surface. Six sections matching `quote_app.py:634-800`:

1. **Project classification** — three `<Select>`s (industry segment, system category, automation level) populated from `GET /api/catalog/dropdowns` which returns unique values from the master parquet plus static fallbacks. Four checkbox toggles: Includes controls, Includes robotics, Retrofit, Duplicate.
2. **Physical scale** — 9 numeric inputs in a 3-column grid. Inline unit labels (`ft`, `count`).
3. **Controls & automation** — plc_family, hmi_family, vision_type as free-text with autocomplete-from-dataset (populated from catalog); panel/drive/servo/pneumatic/vision counts.
4. **Product & process** — 3 sliders (familiarity, rigidity, uncertainty), 3 checkboxes, a numeric (changeover time), a second slider (bulk rigidity).
5. **Complexity & indices** — two 1–5 sliders, a 0–100 custom_pct slider, four derived-index inputs hidden behind an "Advanced" disclosure (matches Streamlit's optional style).
6. **Cost** — single input for `estimated_materials_cost`, which the frontend log-transforms (`Math.log1p`) before packing into `QuoteInput.log_quoted_materials_cost` — same convention as `quote_app.py:824`.

Below the form: a collapsible "Compare to your quoted hours" block with 9 number inputs (one per sales bucket), replicating `quote_app.py:803-815`.

**CTA** — large primary `Estimate hours` button. On submit, posts to `/api/quote/single`. While loading: disabled state + shimmer on the results hero.

**Results area** — uses a hero card (big amber `P50 total hours`, unit "hours", meta chips for "Your quote", "Delta", "Status"), then a tabbed `<Tabs>` with two panes:

- *Sales view*: the 9-row sales-bucket table (Role / Recommended P50 / Range P10–P90 / Confidence / Quoted / Delta / Status when compare-mode is on) + a grouped bar chart (Recharts `<BarChart>` with `xOffset` behavior) showing Recommended vs Quoted per bucket. Exactly mirrors `quote_app.py:954-1027`.
- *Operations view*: the 12-row per-op table (Operation / P10 / P50 / P90 / Std / Rel width / Confidence) from `quote_app.py:1031-1046`.

UX notes specific to the quoting context:
- Confidence is rendered as a colored dot + label, not just text — `high`=green, `medium`=amber, `low`=red.
- All hours use `Intl.NumberFormat("en-US", {maximumFractionDigits: 1})` so "1,234.5" reads correctly.
- Submitting with invalid inputs shows a single summary error at top (`"Please complete: stations_count, plc_family"`) and scrolls to the first field — customers hate hunting for red highlights across a long form.
- After a successful estimate, the form state persists (no reset), so users can tweak one field and re-estimate. A small "Reset form" link sits next to the Estimate button.
- Print stylesheet so the results block prints cleanly to a single page — useful in internal review meetings.

**`/batch` — Batch Quotes**

- Section 01: File input (`.csv`, `.xlsx`). After selection, for xlsx we parse sheet names client-side using `xlsx`/`exceljs` to offer a `<Select>` of sheets before upload — this matches `quote_app.py:1089-1092` and prevents a round-trip.
- Section 02: In-browser preview of first 20 rows via TanStack Table. Detects missing required columns (`QUOTE_NUM_FEATURES + QUOTE_CAT_FEATURES`) and shows an inline error banner before the user clicks Upload, again saving a round-trip.
- Section 03 (post-response): paginated preview of predictions + a `Download CSV` button that saves the blob returned by `/api/quote/batch`.
- Progress indicator during upload: indeterminate bar, with a warning that batches over 500 rows may take several seconds.

**`/performance` — Model Performance**

- KPI row: Operations modeled (X / 12), Average MAE, Average R², Sample count.
- MAE bar chart (Recharts) and R² bar chart side by side, sorted descending by the metric value. Mirrors `quote_app.py:413-442`.
- Per-op metrics table below (target, rows, mae, r2, version).
- Empty state when `models_ready = false`: "Models have not been trained yet. Please check back later." — no admin links from the public page.

### Protected (admin) routes

**`/admin/login`**

Single centered card: password field, `Sign in` button, subtle error banner on wrong password. On success, redirects to `/admin` (Overview).

**`/admin` — Overview**

- KPI grid (projects in master, operations modeled, average MAE, average R²) same shape as `quote_app.py:250-275`.
- Recent uploads table (last 10 from uploads_log.csv).
- Per-op metrics table.
- Two quick-action buttons: "Upload & Train" and "Reset app state" (the latter with a destructive-confirm dialog that matches `quote_app.py:1260-1266`).

**`/admin/train` — Upload & Train**

- Drag-and-drop xlsx upload. Client-side parses sheet names for selection.
- Preview first 10 rows in TanStack Table.
- Validates `REQUIRED_TRAINING_COLS` client-side before enabling the Train button.
- Train button: posts to `/api/admin/train` with a progress/spinner overlay. On success: a metrics table (from the `TrainResponse`), a "Download metrics_summary.csv" button, a toast "Master updated, 12 models trained".
- Because training can take 30-120 s, the frontend shows a rotating status message ("Validating", "Merging master", "Training me10...", etc.) driven by a response stream if we implement SSE, or by a fallback "This can take up to 2 minutes" helper if we don't. Default implementation: plain POST with overlay, SSE is a §8 follow-up.

**`/admin/data` — Data Explorer**

- Filters: multi-selects for industry_segment and system_category populated from `facets` in the response.
- Server-side paginated TanStack Table (50 rows per page) calling `/api/admin/dataset`.
- Below the table: an operation selector + two Recharts views — bar chart of hours by project_id, scatter of robot_count vs hours. Driven by the `scatter` field in the dataset response.

**`/admin/drivers` — Drivers & Similar**

- Two-column layout mirroring `quote_app.py:464-608`.
- Left column: op selector (only operations with a trained model), horizontal bar chart of top 15 feature importances via `/api/admin/drivers/{op}`.
- Right column: similar-projects finder form (industry, system, min/max robots) + result table from `/api/admin/similar`.

### Cross-cutting UX

- Every page has a `<PageHeader>` component with eyebrow / title / description / right-side chips — matches the Streamlit `page_header()` helper (`quote_app.py:240-248`) semantically.
- Empty states use a dedicated `<EmptyState>` component with a calm icon and a subheading that tells the user what action unblocks the page.
- Toasts via `sonner` for success/error notifications.
- Keyboard: `Cmd+Enter`/`Ctrl+Enter` anywhere on Single Quote submits the estimate.
- Accessibility: all form fields have explicit labels, error text gets `aria-describedby`, charts expose a text-table fallback via shadcn `<VisuallyHidden>` summary.

---

## 4. Agent Roster

All agents are defined in `.claude/agents/*.md`. File-scope restrictions are enforced by a PreToolUse hook in `.claude/settings.json` that checks the agent's declared `cwd_scope` and rejects `Edit`/`Write`/`MultiEdit` calls outside it.

### 4a. Backend Specialist (`backend-specialist`)

- **File scope:** `backend/**`, `core/**` *(read-only)*, `service/**` *(read-only)*, `tests/**` *(write through handoff to Test Writer, not directly)*. Writes to `backend/`, reads from `core/` and `service/`. **Never touches `frontend/`.**
- **Model tier:** Sonnet 4.6. Justification: FastAPI route work and pandas glue is bread-and-butter for a mid-tier model; saves budget for the UI/UX work that genuinely benefits from Opus.
- **Permission mode:** `acceptEdits` on backend files; Bash limited to `pytest`, `uv`, `pip`, and `uvicorn` dev-server commands.
- **Output contract:** Every change includes: (a) a code diff under `backend/`, (b) an updated or new test in `tests/`, (c) an updated OpenAPI-derived types file for the frontend (runs `npm run gen:api` in frontend), (d) a short changelog entry in the PR body.
- **Pre-loaded skills:** `superpowers:test-driven-development`, `superpowers:verification-before-completion`.

### 4b. Frontend Specialist (`frontend-specialist`)

- **File scope:** `frontend/**`. **Never touches `backend/`, `core/`, `service/`.**
- **Model tier:** Sonnet 4.6. Justification: same reasoning — CRUD-style component wiring doesn't need Opus.
- **Permission mode:** `acceptEdits` on frontend files; Bash limited to `npm`, `pnpm`, `node`, and `vite` commands.
- **Output contract:** Each change ships: (a) a component or page diff, (b) a typed hook under `src/api/` if a new endpoint is consumed, (c) a visual check via `webapp-testing` skill that the page renders without console errors.
- **Pre-loaded skills:** `superpowers:test-driven-development` (for React Testing Library), `98669c11ca63:webapp-testing`.

### 4c. UI/UX Specialist (`ui-ux-specialist`)

- **File scope:** `frontend/src/components/**`, `frontend/src/styles/**`, `frontend/src/pages/SingleQuote.tsx`, `frontend/src/pages/BatchQuotes.tsx`, `frontend/src/pages/ModelPerformance.tsx`, `frontend/tailwind.config.ts`, `frontend/index.html`. Explicitly **does NOT** touch admin pages or `src/api/` or any business logic.
- **Model tier:** Opus 4.7. Justification: visual polish and layout judgement — where customer trust is built — is exactly where the stronger model earns its keep.
- **Permission mode:** `acceptEdits` on the listed paths.
- **Output contract:** (a) Component diff, (b) before/after screenshot via `webapp-testing`, (c) notes on the design-token changes and why. Must preserve the dark/light token contract defined in `src/styles/tokens.css`.
- **Pre-loaded skills:** `98669c11ca63:frontend-design`, `design:design-critique`, `design:accessibility-review`, `98669c11ca63:webapp-testing`.

### 4d. Auth & Admin Specialist (`auth-admin-specialist`)

- **File scope:** `backend/app/routes/admin.py`, `backend/app/deps.py` (auth dep only), `frontend/src/pages/AdminLogin.tsx`, `frontend/src/pages/AdminLayout.tsx`, `frontend/src/api/auth.ts`, and admin pages under `frontend/src/pages/Admin*`.
- **Model tier:** Sonnet 4.6. Justification: the auth is deliberately small (static password + JWT); the risk is mis-configuration rather than novel design.
- **Permission mode:** `acceptEdits` on listed paths. Bash limited to `pytest tests/test_admin_routes.py`.
- **Output contract:** (a) Code diff, (b) a test verifying 401 on missing/expired tokens, (c) a `.env.example` update if new env vars are introduced, (d) explicit callout if the change affects the rate limit or token expiry.
- **Pre-loaded skills:** `superpowers:test-driven-development`, `engineering:code-review`.

### 4e. Storage Specialist (`storage-specialist`)

- **File scope:** `backend/app/storage.py`, `backend/app/paths.py`. Must understand the Streamlit conventions: `MASTER_DATA_PATH=<DATA_DIR>/data/master/projects_master.parquet`, `UPLOADS_LOG_PATH=<DATA_DIR>/data/master/uploads_log.csv`, `METRICS_PATH=<DATA_DIR>/models/metrics_summary.csv`, and `models/*.joblib` under `<DATA_DIR>/models/`. Has read access to `core/models.py:145` (`load_model`) to know the file-naming scheme.
- **Model tier:** Sonnet 4.6.
- **Permission mode:** `acceptEdits` on listed paths.
- **Output contract:** (a) Code diff, (b) a test using `tmp_path` fixture that exercises round-trip read/write/reset behavior, (c) documentation note on the expected on-disk layout.
- **Pre-loaded skills:** `superpowers:test-driven-development`.

### 4f. Test Writer (`test-writer`)

- **File scope:** `tests/**` (write). **Read-only** on everything else (`backend/**`, `frontend/**`, `core/**`, `service/**`).
- **Model tier:** Sonnet 4.6.
- **Permission mode:** `acceptEdits` only inside `tests/`. Bash limited to `pytest`, `npm test`, `vitest`.
- **Output contract:** For each route or component, produces (a) a happy-path test, (b) an auth-failure test where relevant, (c) an edge-case test (empty master, missing model, malformed upload). Uses `httpx.AsyncClient` for FastAPI, Vitest + React Testing Library for the frontend.
- **Pre-loaded skills:** `engineering:testing-strategy`, `superpowers:test-driven-development`.

### 4g. Documentation Agent (`documentation-agent`)

- **File scope:** `README.md`, `backend/app/**/*.py` (docstrings only — enforced by a hook that rejects functional-body diffs from this agent), `.env.example`, `docs/**`.
- **Model tier:** Sonnet 4.6.
- **Permission mode:** `acceptEdits` on the listed paths.
- **Dispatch position:** **Last.** Runs after every other agent completes a feature, synchronizes docs, regenerates the `docs/api.md` from the OpenAPI schema.
- **Output contract:** (a) README delta, (b) updated API route table (if routes changed), (c) updated `.env.example` (if env vars changed).
- **Pre-loaded skills:** `engineering:documentation`, `anthropic-skills:doc-coauthoring`.

---

## 5. `/orchestrate` Slash Command

`.claude/commands/orchestrate.md` implements a dispatcher that reads the user's intent and fans out to the right agents in the right order. Because `core/` and `service/` are vendored from the Streamlit repo, changes originating there cascade across both the backend (new request/response fields) and the frontend (new form inputs, new result fields). The orchestrator handles that explicitly.

Phases:

**Phase 1 — Classify.** Parse the request for layer hints: "API"/"route"/"endpoint" → backend; "form"/"page"/"style" → frontend; "auth"/"admin login" → auth; "storage"/"parquet"/"joblib" → storage; "schema"/"QuoteInput field" → core-change (special path).

**Phase 2 — Core-change branch.** If the user's request *requires* editing `core/` or `service/` (e.g., adding a new `QuoteInput` field), the orchestrator:
1. Stops and surfaces a prompt: "This change edits the vendored `core/` code. The upstream Streamlit repo should be updated first so the vendor stays in sync. Proceed anyway with a local-only edit? [y/N]"
2. On `y`, dispatches the Backend Specialist with an explicit override flag that the guard hook recognizes (`CC_ALLOW_CORE_EDIT=1`), then dispatches Frontend Specialist to add the corresponding form field, then Test Writer, then Documentation.
3. On `N`, aborts and instructs the user to apply the change to `matrix_quote_app/` first, then copy `core/` + `service/` over with a git-friendly sync script (`scripts/sync_from_streamlit.sh`).

**Phase 3 — Standard dispatch.** For non-core changes:
1. Dispatch the most-specific agent(s): Backend/Frontend/UI-UX/Auth/Storage, in parallel when independent.
2. After every dispatch returns, dispatch Test Writer with a summary of changed files.
3. After tests pass, dispatch Documentation Agent.
4. Present a unified PR description drawn from each agent's changelog entry.

**Phase 4 — Verification gate.** Before marking complete, run:
- `pytest` and `npm test` (via Test Writer's handoff).
- `npm run build` in `frontend/` to ensure the bundle compiles.
- A boot-check: start `uvicorn`, hit `/api/health`, confirm 200.
- If deployed: Railway logs scanned for startup errors.

**Cross-layer propagation rule.** Any agent that changes a Pydantic request or response body in `backend/app/schemas_api.py` automatically triggers a follow-up Frontend Specialist dispatch to regenerate `src/types/api.ts` via `npm run gen:api` and update any affected page. The orchestrator blocks completion until the frontend types compile.

---

## 6. Hooks

Configured in `.claude/settings.json`. Three categories:

### 6a. Vendored-code guard (PreToolUse)

```
Event: PreToolUse
Matcher: tool in {Edit, Write, MultiEdit, NotebookEdit}
Script: .claude/hooks/guard_vendored.sh
```

The script inspects `$CLAUDE_FILE_PATHS`. If any path matches `^core/` or `^service/`, it rejects unless the environment variable `CC_ALLOW_CORE_EDIT=1` is set (which only the orchestrator's explicit core-change branch sets). Applies to every agent, including the Backend Specialist — an agent wanting to edit `core/` must go through `/orchestrate` with the explicit approval prompt.

Exit code 2 with a message: `"Refusing to edit vendored module ${path}. These files are synced from ../matrix_quote_app. Run /orchestrate and confirm the core-change branch, or sync from the source repo via scripts/sync_from_streamlit.sh."`

### 6b. Docs-sync trigger (PostToolUse)

```
Event: PostToolUse
Matcher: tool in {Edit, Write, MultiEdit} AND path matches backend/app/routes/**
Script: .claude/hooks/trigger_docs.sh
```

Appends a note to a session-scoped file `.claude/state/pending_docs.txt` listing the changed route module. The `/orchestrate` command reads this list at completion time and dispatches the Documentation Agent with those files as context. (We don't dispatch the agent *during* a tool call — that would fight the current agent's control flow.)

### 6c. Pre-commit lint (PreToolUse on Bash git commit / on Stop)

Two shell hooks:
- `ruff check backend/ tests/` and `ruff format --check backend/ tests/`
- `cd frontend && npm run lint && npm run typecheck`

Bound to the Stop event so the final output of each agent's run is linted, plus a `commit-msg` git hook for ergonomics if the user runs git manually outside Claude. Failures block the commit with the exact ruff/eslint output.

### 6d. Session bootstrap (UserPromptSubmit)

Minor: on every new session, a small hook prints a one-liner reminder if `data/master/` or `models/` is empty, hinting that Single Quote and Batch Quotes will return 409 until training happens. Skips silently otherwise.

---

## 7. `.gitignore`

Additions on top of the usual Python + Node.js ignores:

```
# Claude Code local state — never commit agent definitions, skills, or settings
CLAUDE.md
.claude/

# Runtime data (mirrors matrix_quote_app/.gitignore)
data/master/
models/
!models/.gitkeep

# Environment
.env
.env.local
.env.*.local

# Build outputs
frontend/dist/
frontend/node_modules/
frontend/.vite/

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/

# Editor / OS
.DS_Store
Thumbs.db
.vscode/
.idea/

# Coverage
.coverage
coverage/
htmlcov/

# Logs
*.log
```

Critical notes:
- `CLAUDE.md` and `.claude/` must not leak. Per-developer agent tweaks, skills, and local hook configuration stay on each machine.
- `data/master/` and `models/` are gitignored; the deployment relies on the Railway Volume, not git.
- `models/.gitkeep` is kept so a fresh clone has the directory structure the app expects. Same for `data/master/.gitkeep`.
- `.env.example` **is** committed. `.env` is not.

---

## 8. Gaps and Risks

**R1 — Persistent storage for models and master parquet.**
Cloud containers are ephemeral. If we don't attach a persistent volume, every redeploy wipes `data/master/` and `models/`, forcing a re-train from the operator's local Excel file. Mitigation: Railway Volume mounted at `/data` as described in §1c. Fallback plan: if Railway's volume pricing becomes a concern, move to Supabase Storage with a small local read-through cache, accepting ~100-200 ms overhead per `load_model()` call. Documented as "Plan B" in the README.

**R2 — Serverless execution limits (Vercel).**
Explicitly called out in the brief. Vercel's Hobby 10 s / Pro 60 s function limit makes `/api/admin/train` non-viable there — training 12 GBRs sequentially can take minutes on a modest dataset. Railway and Render have no such ceiling. Chose Railway (§1c). If the frontend later moves to Vercel (pure static), the API must still be hosted on Railway/Render/Fly.

**R3 — `QuoteInput` representation.**
The Streamlit form uses `number_input` (integers with steps), `checkbox` (booleans), `slider` (1-5 scales, 0-100 percent), and `selectbox` (categorical with dataset-backed options). Mapping to the web form:
- Booleans (`has_controls`, `has_robotics`, `duplicate`, `Retrofit`, `is_product_deformable`, `is_bulk_product`, `has_tricky_packaging`) — rendered as `<Switch>` in the form, serialized as `0` or `1` in the `QuoteInput` payload (the Pydantic schema declares them as `int`, not `bool`, which is a historical quirk of the Streamlit-era code; we preserve it to avoid editing `core/schemas.py`).
- Sliders (`product_familiarity_score`, `product_rigidity`, `bulk_rigidity_score`, `process_uncertainty_score`, `complexity_score_1_5`) — all 1-5 integer sliders, rendered as `<Slider min={1} max={5} step={1}>` with numeric label.
- `custom_pct` — 0-100 slider with a `%` suffix.
- Derived indices (`stations_robot_index`, `mech_complexity_index`, `controls_complexity_index`, `physical_scale_index`) — these are *computed* from other fields in `core/features.py::_compute_indices_inplace` (lines 58-91). Exposing them as user inputs was a Streamlit-era escape hatch. The web form hides them under an Advanced disclosure and leaves them as `0` by default; `prepare_quote_features` will recompute them server-side regardless. Mitigation for user confusion: tooltip says "Auto-computed unless overridden."
- `log_quoted_materials_cost` — computed from the user's "Estimated materials cost" via `Math.log1p` on the client, matching `quote_app.py:824`. The raw dollar input is the only field the customer sees.

Risk: if a future `QuoteInput` field is added, the Pydantic default must be sensible (the current schema's `0`/`3` defaults assume "if unspecified, use a neutral baseline") — the Documentation Agent's checklist includes updating both the frontend form and the server-side schema docstring.

**R4 — Admin auth for a customer-facing app.**
Static password + JWT is simple but blunt:
- *Shared password* means any departure on the admin team forces a rotation.
- *No audit trail* — we don't know who retrained the model at 3am.
- *No MFA.*
- *Single failure surface* — if `ADMIN_PASSWORD` leaks, any attacker can wipe the master parquet via `/api/admin/reset`.

Mitigations in this plan:
- Rate-limit login (10/10m per IP).
- 12-hour token expiry.
- `ADMIN_JWT_SECRET` rotation invalidates all live sessions.
- `/api/admin/reset` returns a confirmation token that must be echoed in a second call within 30 s — i.e., destructive actions require two round-trips.

Escalation path (out of scope for v1 but documented): swap `require_admin` for a Clerk/Auth0/WorkOS check when admin headcount grows past 3 or when external auditors ask for an access log.

**R5 — Training runtime vs. HTTP timeout.**
Nginx/Railway's edge proxy kills requests at ~300 s by default. A 12-model train on a large dataset could brush that. Mitigation: set gunicorn worker timeout to 600 s and run training synchronously for v1. If training exceeds 5 minutes in practice, introduce a job queue (RQ + Redis, or arq) and swap the route to "enqueue + poll status". Flag this as the main follow-up on the §5 verification gate.

**R6 — Concurrent admin uploads corrupting the master parquet.**
Two admins training at once would race-read-then-race-write the parquet. Mitigation: file lock via `filelock` on `DATA_DIR/.train.lock`. Acceptable for a small team; documented in the Storage Specialist's contract.

**R7 — OpenAPI drift between backend and frontend types.**
`frontend/src/types/api.ts` is generated from the FastAPI OpenAPI schema via `openapi-typescript`. If a developer edits `schemas_api.py` without regenerating, the frontend compiles against stale types. Mitigation: a CI check that fails if `git diff --quiet src/types/api.ts` fails after `npm run gen:api`.

**R8 — Client-side xlsx parsing for batch uploads.**
We propose parsing sheet names client-side with `xlsx`/`exceljs` to avoid a round-trip. But pulling ~150 KB of JS just for that is a non-trivial bundle cost. Alternative: a tiny `POST /api/quote/batch/preview` that returns sheet names (+ column list) for xlsx uploads. Decision: start with the API preview approach; it's simpler, matches `/api/admin/train/preview`, and keeps the batch path as a single small POST + the main POST. The client-side parser is an optimization deferred to §8 follow-up.

**R9 — Reading metrics_summary.csv format changes.**
`core/models.py:102-110` writes `target, version, rows, mae, r2, model_path`. The Streamlit `quote_app.py:228` tolerates missing `r2`. The web backend's `MetricRow` schema should mark `r2` as `Optional[float]` to survive older metrics files produced by earlier Streamlit runs. Called out here so the Backend Specialist defines the type correctly the first time.

---

## Summary Tables

### Table 1: API Routes

| Route | Method | Auth Required | Calls | Request Shape | Response Shape |
|---|---|---|---|---|---|
| `/api/health` | GET | No | — | — | `{status: "ok", models_ready: bool}` |
| `/api/metrics` | GET | No | `storage.read_metrics()` | — | `MetricsSummary {models_ready, metrics[]}` |
| `/api/catalog/dropdowns` | GET | No | `storage.read_master()` | — | `DropdownOptions {industry_segment[], system_category[], automation_level[], plc_family[], hmi_family[], vision_type[]}` |
| `/api/quote/single` | POST | No | `service.predict_lib.predict_quote` | `QuoteInput` (core/schemas.py:9) | `QuotePrediction` (core/schemas.py:77) |
| `/api/quote/batch/preview` | POST | No | pandas xlsx parse | multipart: `file` | `{sheets[], columns_per_sheet{}}` |
| `/api/quote/batch` | POST | No | `service.predict_lib.predict_quotes_df` | multipart: `file`, `sheet?` | `text/csv` stream |
| `/api/admin/login` | POST | No | password compare + JWT sign | `{password: str}` | `{token: str, expires_at: datetime}` |
| `/api/admin/train/preview` | POST | Yes | pandas xlsx parse | multipart: `file` | `{sheets[], columns_per_sheet{}}` |
| `/api/admin/train` | POST | Yes | `core.features.engineer_features_for_training`, `core.models.train_one_op` (×12) | multipart: `file`, `sheet` | `TrainResponse {rows_raw, rows_train, rows_master_total, metrics[], trained_targets[], skipped_targets[], models_ready}` |
| `/api/admin/dataset` | GET | Yes | `storage.read_master()` + pandas filter/slice | query: `industry_segment[]?, system_category[]?, op?, limit=50, offset=0` | `DatasetPage {total, filtered_total, columns[], rows[], facets{}, scatter?[]}` |
| `/api/admin/drivers/{op}` | GET | Yes | `core.models.load_model` + feature-importance extraction | path: `op` | `DriversResponse {op, has_model, features[], nonzero_count}` |
| `/api/admin/similar` | POST | Yes | `storage.read_master()` + pandas filter | `SimilarRequest {industry_segment?, system_category?, min_robots, max_robots, limit}` | `SimilarResponse {count, rows[]}` |
| `/api/admin/overview` | GET | Yes | `storage.read_master()`, `read_metrics()`, `read_uploads_log()` | — | `OverviewResponse {n_projects, n_ops_modeled, avg_mae?, avg_r2?, models_ready, recent_uploads[], metrics[]}` |
| `/api/admin/reset/prepare` | POST | Yes | — | — | `{confirm_token, expires_at}` |
| `/api/admin/reset` | POST | Yes | `storage.reset_all()` | `{confirm_token}` | `{ok: true}` |

### Table 2: Agent Roster

| Agent Name | Model | File Scope | Dispatch Position | Shared Skills |
|---|---|---|---|---|
| `backend-specialist` | Sonnet 4.6 | `backend/**` (write), `core/**` + `service/**` (read) | First for API/route tasks | `superpowers:test-driven-development`, `superpowers:verification-before-completion` |
| `frontend-specialist` | Sonnet 4.6 | `frontend/**` | First for functional frontend tasks; after backend for cross-layer tasks | `superpowers:test-driven-development`, `98669c11ca63:webapp-testing` |
| `ui-ux-specialist` | Opus 4.7 | `frontend/src/components/**`, `frontend/src/styles/**`, customer-facing pages, Tailwind config | After frontend-specialist for visual polish passes | `98669c11ca63:frontend-design`, `design:design-critique`, `design:accessibility-review`, `98669c11ca63:webapp-testing` |
| `auth-admin-specialist` | Sonnet 4.6 | `backend/app/routes/admin.py`, `backend/app/deps.py` (auth dep), frontend admin login + layout + admin API client | First for auth/admin-flow tasks | `superpowers:test-driven-development`, `engineering:code-review` |
| `storage-specialist` | Sonnet 4.6 | `backend/app/storage.py`, `backend/app/paths.py` | First for parquet/model-artifact/FS tasks | `superpowers:test-driven-development` |
| `test-writer` | Sonnet 4.6 | `tests/**` (write); everything else read-only | After every production-code change | `engineering:testing-strategy`, `superpowers:test-driven-development` |
| `documentation-agent` | Sonnet 4.6 | `README.md`, `backend/app/**` (docstrings only), `.env.example`, `docs/**` | **Last** — after every other agent completes | `engineering:documentation`, `anthropic-skills:doc-coauthoring` |
