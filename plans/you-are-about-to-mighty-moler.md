# Operator-Pattern Agent Orchestration Plan — Matrix Quote App

## Context

This project is an internal Streamlit tool (`matrix_quote_app`) that trains
12 per-operation Gradient Boosting Regressor (GBR) models on historical
automation-project hour data and produces per-operation predictions with
P10/P50/P90 quantile intervals, rolled up into 9 Sales buckets. The
business logic is tightly coupled across a small set of files:

- `core/config.py` defines the operation TARGETS, SALES_BUCKETS,
  SALES_BUCKET_MAP, QUOTE_NUM_FEATURES, QUOTE_CAT_FEATURES, and
  REQUIRED_TRAINING_COLS. Nearly every other module imports from here.
- `core/schemas.py` defines the Pydantic `QuoteInput` contract with
  **40 fields** (1 optional `project_id` + 6 categorical + 33 numeric).
  This schema is the input boundary between the UI and the prediction
  library.
- `core/features.py` engineers derived indices
  (`stations_robot_index`, `mech_complexity_index`,
  `controls_complexity_index`, `physical_scale_index`) and converts
  yes/no flags to 0/1.
- `core/models.py` trains a 3-model bundle per target (main GBR + q10
  + q90) using `n_estimators=300, max_depth=5, learning_rate=0.1`.
  Supports two bundle shapes: legacy `{pipeline, q10, q90}` and CQR
  `{preprocessor, model_mid, model_lo, model_hi, qhat, alpha, meta}`.
- `service/predict_lib.py` orchestrates per-operation inference and
  bucket rollup; computes `rel_width` and maps it to a confidence label
  (high <0.3, medium <0.6, else low).
- `quote_app.py` is a **1282-line** Streamlit monolith (not 959 as
  stated in the brief) with 7 pages dispatched through a single
  `PAGE_DISPATCH` dict, coordinated via `st.session_state` keys
  (`models_ready`, `active_page`, `quoted_hours_by_bucket`).

The orchestration system below is designed around these concrete
touch-points, not a generic ML project template.

---

## 1. CLAUDE.md

**Location:** project root (`CLAUDE.md`), but `.gitignore`-excluded per
user instruction in §7.

**Target length:** ~220–260 lines.

### Included sections

1. **Project purpose.** One paragraph: "Internal Streamlit tool that
   trains per-operation GBR models (12 targets) and produces
   P10/P50/P90 quote estimates with 9 Sales bucket rollups."

2. **The 12 operations and sales-bucket mapping.** Copied verbatim from
   `core/config.py:5-49` (TARGETS and SALES_BUCKET_MAP), rendered as a
   table. Every agent is required to consult this before touching
   anything that mentions "operation" or "bucket".

   | Operation prefix | Bucket  | Operations in bucket        |
   |------------------|---------|-----------------------------|
   | me10, me15, me230| ME      | 3                           |
   | ee20             | EE      | 1                           |
   | rb30             | Robot   | 1                           |
   | cp50             | Controls| 1                           |
   | bld100, shp150   | Build   | 2                           |
   | inst160          | Install | 1                           |
   | trv180           | Travel  | 1                           |
   | doc190           | Docs    | 1                           |
   | pm200            | PM      | 1                           |

3. **QuoteInput field contract.** Full list of the 40 fields with
   types and defaults taken from `core/schemas.py:9-53`. Flagged rule:
   any addition or rename of a QuoteInput field must propagate to
   `QUOTE_NUM_FEATURES` / `QUOTE_CAT_FEATURES` in `core/config.py`
   **and** to the Streamlit form inputs in `render_single_quote`
   (`quote_app.py:611-868`). Orchestrator cannot close a schema-change
   task until all three are aligned.

4. **GBR training pattern.** Documented from `core/models.py:70-100`:
   - `GradientBoostingRegressor(n_estimators=300, max_depth=5,
     learning_rate=0.1, random_state=42)` for the main model
   - Two quantile models with `loss="quantile"`, `alpha=0.1` and
     `alpha=0.9`, trained on the same preprocessed features
   - `train_test_split(test_size=0.25, random_state=42)`
   - Categorical pipeline: `SimpleImputer(most_frequent) →
     OneHotEncoder(handle_unknown="ignore")`
   - Numeric pipeline: `SimpleImputer(median)`
   - `ColumnTransformer(remainder="drop")`
   - Bundle layout: `{"pipeline", "q10", "q90"}`
   - Per-target artifact path: `models/{target}_v1.joblib`

5. **Quantile confidence interval methodology.** Documented from
   `service/predict_lib.py:35-52` and `core/models.py:141`:
   - `std ≈ (p90 - p10) / 2.56` (assumes approximate normality)
   - `rel_width = (p90 - p10) / max(|p50|, 1e-6)`
   - Label thresholds: `<0.3 → high`, `<0.6 → medium`, `else → low`
   - These thresholds are **governance constants**: changing them
     requires Schema & Config Specialist review (affects user-facing
     confidence ratings).

6. **Data flow.** Narrative + ASCII diagram tracing:
   - Excel upload in `render_admin` (quote_app.py:1122-1266) →
   - `engineer_features_for_training` (core/features.py:94-143) →
   - filter `include_in_training` + `dataset_role=="actuals"` →
   - append + dedup on `project_id` (last-write-wins:
     quote_app.py:1197-1201) →
   - write `data/master/projects_master.parquet` →
   - loop `train_one_op` over TARGETS →
   - write `models/{target}_v1.joblib` + `models/metrics_summary.csv`
     →
   - UI-side: `QuoteInput` → `_quote_to_df` → `prepare_quote_features`
     → per-target `load_model` + `predict_with_interval` → bucket
     rollup.

7. **Conventions observed in the code** (all agents must honor):
   - Path constants declared at top of `quote_app.py:36-38`
     (`MASTER_DATA_PATH`, `UPLOADS_LOG_PATH`, `METRICS_PATH`). Never
     hardcode these anywhere else.
   - `_BOOL_STR_COLS` in `core/features.py:10-18` is the canonical
     set of columns requiring yes/no→0/1 coercion.
   - Feature importances read from `bundle["meta"]["feature_importances"]`
     first, then fall back to raw model attribute
     (`quote_app.py:484-513`). Both bundle shapes must continue to work.
   - Metrics columns written to `metrics_summary.csv`: `target,
     version, rows, mae, r2, model_path` (see
     `core/models.py:102-109`). Downstream readers
     (`quote_app.py:221-230`) depend on `mae` and `r2` columns.
   - `project_id` is the dedup key. Last-write-wins (`keep="last"`).

---

## 2. Agent Roster (10 agents)

Model tier conventions:
- **Haiku 4.5** — deterministic read-only checks and templated writes.
- **Sonnet 4.6** — most design/coding work.
- **Opus 4.7** — high-risk structural changes with cross-cutting impact.

### Tier 1 — Data Integrity

#### a. Data Quality Auditor (Haiku 4.5)

- **File scope (read-only):**
  - `data/master/projects_master.parquet`
  - `data/master/uploads_log.csv`
  - `core/config.py` (REQUIRED_TRAINING_COLS + TARGETS + feature lists)
- **Permission mode:** `read-only`. No write tools.
- **Why Haiku:** Deterministic column presence + null-rate checks,
  no open-ended reasoning.
- **Hooks:** None on itself. Triggered by pre-training hook (see §6).
- **Structured output contract:**
  ```json
  {
    "status": "PASS" | "WARN" | "BLOCK",
    "rows_total": int,
    "required_cols_missing": [str],
    "null_rate_per_feature": {feature: float},
    "operations_with_data": [target],
    "operations_insufficient": [{"target": str, "rows": int}],
    "implausible_hours_flags": [{"target": str, "row_count": int,
                                 "reason": str}],
    "categorical_consistency": {
        "industry_segment_uniques": int,
        "system_category_uniques": int
    },
    "block_reason": str | null
  }
  ```
- **BLOCK conditions:**
  - Any `REQUIRED_TRAINING_COLS` column missing
  - <5 rows with `target > 0` for **every** target (aligns with
    `core/features.py:196` minimum)
  - Master Parquet not readable
- **Implausible hours check:** For each target, flag rows with
  `actual_hours > 10000` or `< 0`. Per-operation thresholds live in the
  `matrix-data-contract` skill and can be overridden.
- **Invoked by orchestrator:** First on any task whose free-text
  matches `/(train|retrain|upload|data|master|parquet)/i`.

#### b. Config Drift Detector (Haiku 4.5)

- **File scope (read-only):**
  - `core/config.py`
  - `data/master/projects_master.parquet`
- **Permission mode:** `read-only`.
- **Why Haiku:** Simple set diff + coverage arithmetic.
- **Hooks:** Registered as the pre-training hook in §6.
- **Structured output contract:**
  ```json
  {
    "status": "PASS" | "WARN" | "BLOCK",
    "coverage_pct": {feature: float},
    "null_rate_per_feature": {feature: float},
    "missing_in_data_but_defined_in_config": [str],
    "present_in_data_but_absent_from_config": [str],
    "targets_defined_vs_present": {
        "defined": int, "present": int,
        "absent": [target]
    }
  }
  ```
- **BLOCK condition:** Any column in `REQUIRED_TRAINING_COLS` is
  absent from the master Parquet.
- **Invoked by orchestrator:** Second on any training task; also
  pre-flight for Schema & Config Specialist and ML Specialist.

#### c. Schema & Config Specialist (Sonnet 4.6)

- **File scope (write, acceptEdits):**
  - `core/config.py`
  - `core/schemas.py`
- **File scope (deny):** Everything else. Cannot touch `core/features.py`,
  `core/models.py`, `service/predict_lib.py`, or `quote_app.py` —
  downstream changes are the responsibility of ML and UI Specialists.
- **Why Sonnet:** Decisions about feature list additions / target
  renames require reasoning about downstream `SALES_BUCKET_MAP`
  consistency, `QuoteInput` field types, and default values.
- **Hooks:** Post-edit triggers Documentation Agent (see §6).
- **Structured output contract:**
  ```json
  {
    "files_changed": [path],
    "fields_added": [{"name": str, "type": str, "default": any,
                      "target_file": path}],
    "fields_renamed": [{"old": str, "new": str}],
    "fields_removed": [str],
    "targets_changed": {"added": [str], "removed": [str]},
    "sales_bucket_map_changes": [{"op": str, "old_bucket": str,
                                   "new_bucket": str}],
    "downstream_files_requiring_update": [
      "core/features.py",
      "service/predict_lib.py",
      "quote_app.py::render_single_quote",
      "quote_app.py::render_batch_quotes"
    ]
  }
  ```
- **Invoked by orchestrator:** When task mentions schema, feature list,
  target, sales bucket, or `QuoteInput`. Always pre-checked by Config
  Drift Detector.

### Tier 2 — ML

#### d. ML Specialist (Sonnet 4.6)

- **File scope (write, acceptEdits):**
  - `core/models.py`
  - `core/features.py`
- **File scope (deny):** `core/config.py` (goes to Schema Specialist),
  `core/schemas.py`, `quote_app.py`, `service/predict_lib.py` read-only
  for context only.
- **Why Sonnet:** GBR tuning, quantile regression improvements (CQR
  bundle support already exists at `core/models.py:131-140`),
  cross-validation design, and index feature engineering all require
  ML reasoning.
- **Hooks:** Triggered by post-edit hook on `core/models.py` or
  `core/features.py` → queues Documentation Agent.
- **Structured output contract:**
  ```json
  {
    "files_modified": [path],
    "bundle_shape": "legacy" | "cqr" | "both",
    "metrics_delta": {
      "mae_before": float | null,
      "mae_after": float | null,
      "r2_before": float | null,
      "r2_after": float | null,
      "per_target": [{"target": str,
                       "mae_before": float, "mae_after": float,
                       "r2_before": float, "r2_after": float}]
    },
    "caveats": [str],
    "retraining_required": bool,
    "training_data_required": str
  }
  ```
- **Caveats must include** any of: "changed bundle shape — UI
  `load_model` path must verify both shapes still work", "modified
  `_compute_indices_inplace` — all historical predictions now
  inconsistent until retrain", "changed train/test split seed —
  deterministic test set shift".
- **Invoked by orchestrator:** Tasks matching
  `/(tune|quantile|CQR|cross[- ]?validation|feature engineering|GBR)/i`.

#### e. Model Diagnostics Agent (Haiku 4.5)

- **File scope (read-only):**
  - `models/metrics_summary.csv`
  - `models/*.joblib`
  - `data/master/projects_master.parquet` (for feature importance
    computation only)
- **Permission mode:** `read-only`.
- **Why Haiku:** Structured threshold checks, no open design work.
- **Hooks:** None on itself; invoked post-ML-Specialist-edits.
- **Structured output contract:**
  ```json
  {
    "operations": {
      target: {
        "r2": float, "mae": float, "rows": int,
        "status": "green" | "yellow" | "red",
        "reason": str | null
      }
    },
    "wide_interval_targets": [{"target": str, "median_rel_width":
                                float}],
    "importance_drift": [{"target": str, "top3_features": [str]}],
    "baseline_comparison": {"present": bool, "baseline_path": str,
                             "drops": [{"target": str,
                                        "r2_before": float,
                                        "r2_after": float}]}
  }
  ```
- **Thresholds** (encoded in `matrix-ml-conventions` skill):
  - `green`: r2 ≥ 0.5, median rel_width < 0.3
  - `yellow`: 0.2 ≤ r2 < 0.5 or rel_width 0.3–0.6
  - `red`: r2 < 0.2 or rel_width ≥ 0.6 or rows < 10
- **Baseline storage:** `models/metrics_summary.baseline.csv` (not yet
  present; ML Specialist will create on first retrain).
- **Invoked by orchestrator:** Always after ML Specialist; on-demand
  when task mentions performance, regression, or drift.

### Tier 3 — Presentation

#### f. UI Specialist (Sonnet 4.6)

- **File scope (write, acceptEdits):**
  - `quote_app.py`
  - `service/predict_lib.py`
- **File scope (deny):** All of `core/`.
- **Why Sonnet:** Streamlit session_state coupling
  (`st.session_state["models_ready"]`, `active_page`,
  `quoted_hours_by_bucket`) and the 7-page `PAGE_DISPATCH` table
  demand careful reasoning but not the structural depth of Opus.
- **Hooks:** Post-edit queues Documentation Agent if any public
  function signature in `service/predict_lib.py` changes (detected via
  AST diff).
- **Structured output contract:**
  ```json
  {
    "tabs_modified": [str],
    "pages_touched": ["Single Quote" | "Batch Quotes" | "Overview" |
                      "Data Explorer" | "Model Performance" |
                      "Drivers & Similar" | "Upload & Train"],
    "session_state_keys_touched": [str],
    "session_state_keys_added": [str],
    "predict_lib_signatures_changed": [str],
    "extraction_candidates": [{"tab": str, "line_range": str,
                                "reason": str}]
  }
  ```
- **Hard rules:**
  - `st.session_state["models_ready"]` and `active_page` semantics
    must be preserved exactly (read sites: `quote_app.py:107-120, 192,
    204, 621, 1058`).
  - Path constants `MASTER_DATA_PATH`, `UPLOADS_LOG_PATH`,
    `METRICS_PATH` stay top-of-file.
  - Any new field collected in `render_single_quote` must match an
    existing field in `QuoteInput` or coordinate with Schema
    Specialist.
- **Invoked by orchestrator:** UI/display/tab tasks; batch prediction
  output formatting.

#### g. Refactor Specialist (Opus 4.7)

- **File scope (write, acceptEdits):**
  - `quote_app.py`
  - `service/predict_lib.py`
  - `ui/` (new directory, created by the agent)
  - `ui/helpers.py` (new)
- **File scope (deny):** All of `core/`.
- **Mandate:** Modularize `quote_app.py` (**1282 lines** — corrected
  from the 959 figure in the brief) into:
  ```
  ui/
    __init__.py
    single_quote.py      (~260 lines from quote_app.py:611-868 +
                          render helper at 871-1047)
    batch_quotes.py      (~72 lines from 1049-1119)
    overview.py          (~86 lines from 211-294)
    data_explorer.py     (~91 lines from 297-385)
    model_perf.py        (~57 lines from 388-442)
    drivers_similar.py   (~166 lines from 445-608)
    admin.py             (~145 lines from 1122-1266)
    helpers.py           (_load_master, _get_dropdown_options,
                          _load_metrics, _reset_app_state,
                          _log_upload, path constants)
  ```
- **Why Opus:** The 1282-line monolith entangles `st.session_state`
  reads and writes across eight `render_*` functions and one shared
  `_render_quote_results` helper. Splitting these without breaking the
  session-state contract is structurally risky; Opus justified.
- **Permission mode:** `acceptEdits` on `quote_app.py`,
  `service/predict_lib.py`, and new `ui/**`. Deny on `core/**`.
- **Hooks:** Must present every proposed file split to UI Specialist
  for approval before writing. Enforced via an `UserPromptSubmit`-style
  orchestrator checkpoint (not a Claude Code file hook).
- **Structured output contract:**
  ```json
  {
    "modules_created": [path],
    "functions_moved": [{"from": "quote_app.py::render_overview",
                          "to": "ui/overview.py::render"}],
    "session_state_keys_read_by_module": {module: [key]},
    "session_state_keys_written_by_module": {module: [key]},
    "tests_added": [path],
    "pre_refactor_line_count": 1282,
    "post_refactor_line_count": int,
    "risks": [str]
  }
  ```
- **Invoked by orchestrator:** Only on explicit refactor / modularize /
  split-file requests. Never in routine edits.

### Tier 4 — Cross-Cutting

#### h. Performance Agent (Sonnet 4.6)

- **File scope (read-only):**
  - `core/models.py`
  - `service/predict_lib.py`
- **Permission mode:** `read-only` on files; `Bash` allowed only for
  `python -c`, `python -m cProfile`, `time`, and benchmark scripts
  under an ephemeral `bench/` path. Cannot run anything that writes to
  `data/master/` or `models/`.
- **Why Sonnet:** Profiling trace interpretation + refactor proposals.
- **Known bottlenecks it will surface** (inferred from reading the
  code — not pre-written solutions):
  - `load_model(target)` is called once per target inside the
    `for target in TARGETS` loop of **both** `predict_quote`
    (`service/predict_lib.py:68-72`) and `predict_quotes_df`
    (`service/predict_lib.py:136-140`). Every single-quote request
    reads 12 `.joblib` files from disk. No caching.
  - `train_one_op` runs serially in `render_admin`
    (`quote_app.py:1210-1218`); 12 GBR fits ≈ linear wall time and
    could be parallelized via `joblib.Parallel(n_jobs=-1)`.
  - `prepare_quote_features` is called per quote with only a 1-row
    frame; cheap but `_compute_indices_inplace` does 11 column
    coercions on every call.
- **Structured output contract:**
  ```json
  {
    "bottlenecks": [
      {"location": "file:func:line", "measured_ms": float,
       "proposed_fix": str, "estimated_saving_ms": float,
       "risk": "low" | "medium" | "high"}
    ],
    "profiling_method": str,
    "recommendation_priority": ["hot", "warm", "cold"]
  }
  ```
- **Does not implement changes.** Every proposed fix returns to the
  orchestrator, which routes to ML Specialist (for `core/models.py`)
  or UI Specialist (for `service/predict_lib.py`).
- **Invoked by orchestrator:** Tasks matching
  `/(slow|performance|speed|cache|parallel|profil)/i`.

#### i. Documentation Agent (Haiku 4.5)

- **File scope (read-only):** all production files.
- **File scope (write, acceptEdits):**
  - `README.md`
  - Docstrings **within** existing `core/`, `service/`, and
    `quote_app.py` (edits must be confined to
    `"""docstring"""`-bounded regions, enforced via a
    pre-write validator in the skill).
- **Why Haiku:** Text generation from structured inputs.
- **Hooks:** Registered as post-write hook on any file in `core/` (see
  §6).
- **Structured output contract:**
  ```json
  {
    "files_touched": [path],
    "readme_sections_updated": [str],
    "data_requirements_table_regenerated": bool,
    "data_dictionary_path": "docs/data_dictionary.md" | null,
    "docstrings_added": int,
    "docstrings_updated": int
  }
  ```
- **Auto-generated artifacts:**
  - README data-requirements table is rebuilt from
    `REQUIRED_TRAINING_COLS`.
  - A data dictionary stub (optional, orchestrator-gated) built from
    `QUOTE_NUM_FEATURES` + `QUOTE_CAT_FEATURES`.
- **Invoked by orchestrator:** Final step, always, on any
  production-file-touching task.

#### j. Test Writer (Sonnet 4.6)

- **File scope (write, acceptEdits):** `tests/**` only. Creates the
  directory if missing.
- **File scope (deny):** All production files (read-only).
- **Why Sonnet:** Test design requires understanding of the code under
  test (preprocessor fixtures, `QuoteInput` factory, mocked `.joblib`
  bundles).
- **Initial test targets:**
  - `tests/test_config.py` — asserts 12 TARGETS, 9 SALES_BUCKETS, 12
    entries in SALES_BUCKET_MAP, all targets covered by the map.
  - `tests/test_features.py` — `engineer_features_for_training` with
    yes/no casting, `dataset_role` filtering, index computation
    correctness, log-cost fallback.
  - `tests/test_models.py` — `train_one_op` on a synthetic 50-row
    DataFrame, checks bundle keys, `predict_with_interval` on both
    legacy and CQR bundles.
  - `tests/test_predict_lib.py` — `predict_quote` smoke test with
    mocked `load_model`, bucket rollup correctness per
    `SALES_BUCKET_MAP`, `_compute_confidence` thresholds at boundary
    values.
- **Structured output contract:**
  ```json
  {
    "tests_added": [path],
    "pass_count": int,
    "fail_count": int,
    "skipped": int,
    "coverage_pct": {module: float},
    "missing_coverage": [{"file": path, "function": str}]
  }
  ```
- **Invoked by orchestrator:** Final step, always, on tasks that touch
  `core/**` or `service/**`. Runs in parallel with Documentation Agent.

---

## 3. Dispatch Order and Dependencies

### Dependency graph

```
           (any training-touching task)
                    |
                    v
        ┌──────────────────────┐
        │ Data Quality Auditor │  ─┐
        └──────────────────────┘   │  BLOCK → halt
                    |              │
                    v              │
        ┌──────────────────────┐   │
        │ Config Drift Detect  │  ─┘
        └──────────────────────┘
                    |
         ┌──────────┼──────────┐
         v          v          v
    Schema &    ML Spec    UI Spec
    Config Sp.     |          |
         |         v          |
         |    Model Diagn.    |
         |         |          |
         └─────┬───┴────┬─────┘
               v        v
         Refactor Specialist (only if explicit)
               |
               v
        Performance Agent (on-demand)
               |
               v
        ┌──────┴───────┐
        v              v
  Documentation   Test Writer     (parallel, always last)
```

### Rules

1. **Halt conditions.** A `BLOCK` status from Data Quality Auditor or
   Config Drift Detector halts the pipeline. Schema Specialist and ML
   Specialist are not invoked. Orchestrator reports the BLOCK reason to
   the user and exits.

2. **Parallelism.** Within a single task:
   - Data Quality Auditor and Config Drift Detector run in
     parallel (they have disjoint outputs and no dependencies on each
     other).
   - Schema Specialist, UI Specialist, and ML Specialist can run in
     parallel **only if** the task explicitly declares disjoint edits
     (orchestrator infers from the task description; ambiguous tasks
     default to serial).
   - Documentation Agent and Test Writer always run in parallel at the
     end.

3. **Sequential dependencies.**
   - Schema Specialist → ML Specialist (Schema output becomes
     ML input via structured handoff; see §4).
   - ML Specialist → Model Diagnostics Agent (diagnostics needs fresh
     metrics).
   - ML Specialist → UI Specialist (only when prediction interface
     changes; otherwise they can parallelize).
   - Refactor Specialist → UI Specialist (approval checkpoint before
     refactor writes).
   - Performance Agent proposals → ML or UI Specialist (explicit
     orchestrator approval required before implementation).

4. **Early-exit fast paths.**
   - Pure documentation request: skip directly to Documentation Agent.
   - Pure test-adding request: skip directly to Test Writer.
   - UI-only task not touching `QuoteInput`: skip Data Quality Auditor
     + Config Drift Detector (they're about training data integrity,
     not UI).

---

## 4. `/orchestrate` Slash Command

**Location:** `.claude/commands/orchestrate.md`.

### Invocation

```
/orchestrate <free-text task description>
```

### Logic

1. **Task classification.** The command file contains a first-pass
   classifier prompt that tags the task with zero or more of: `data`,
   `schema`, `ml`, `ui`, `refactor`, `perf`, `docs`, `tests`. The
   classifier uses keyword matching plus a narrow LLM judgment in
   ambiguous cases.

2. **Agent selection.** Based on tags:

   | Tag      | Agents invoked                                    |
   |----------|---------------------------------------------------|
   | data     | Data Quality Auditor, Config Drift Detector        |
   | schema   | Schema & Config Specialist (+ data tag)            |
   | ml       | ML Specialist, Model Diagnostics (+ data tag)      |
   | ui       | UI Specialist                                      |
   | refactor | Refactor Specialist (+ ui)                         |
   | perf     | Performance Agent                                  |
   | docs     | Documentation Agent (always runs at end anyway)    |
   | tests    | Test Writer (always runs at end anyway)            |

3. **Handoff protocol** — structured JSON passed between agents:

   **Schema → ML handoff.** The Schema Specialist's
   `fields_added` and `fields_renamed` arrays are injected into the ML
   Specialist's prompt as:
   ```
   NEW/RENAMED FIELDS TO INTEGRATE:
     - custom_pct: float=0 (added; must be added to num_features list,
                           handled in _compute_indices_inplace if
                           derived)
   ```
   The ML Specialist echoes back which it has integrated.

   **ML → UI handoff.** The ML Specialist's
   `predict_lib_signatures_changed` field (or any update to
   `predict_with_interval` return contract) becomes the UI Specialist's
   prompt:
   ```
   PREDICTION INTERFACE CHANGED:
     - predict_with_interval now returns 5-tuple including bundle_meta
     - callers in service/predict_lib.py:68-140 must be updated
   ```
   The UI Specialist updates `service/predict_lib.py` and flags any
   user-visible changes in `quote_app.py`.

   **UI → Refactor handoff (pre-approval).** Refactor Specialist
   submits its planned module layout to UI Specialist, which returns:
   ```json
   {"approved": bool, "objections": [str],
    "required_preserved_symbols": [str]}
   ```

4. **Final report structure.** The slash command prints a single
   Markdown report:

   ```markdown
   # Orchestration Report

   Task: <original task>
   Agents invoked: <list>
   Duration: <wall time>

   ## Files changed per agent
   - Data Quality Auditor: (none, read-only)
   - Schema Specialist: core/config.py (+2 lines),
                         core/schemas.py (+1 field)
   - ML Specialist: core/models.py (modified predict_with_interval)
   - UI Specialist: service/predict_lib.py, quote_app.py

   ## Test results
   - 47 passed, 0 failed
   - Coverage: core/models.py 82%, core/features.py 91%

   ## Diagnostics
   - (Model Diagnostics output or "not run")

   ## Downstream follow-ups flagged
   - [ ] `models/` artifacts stale — retrain required
   - [ ] README data-requirements table will need a new row for X
   - [ ] Performance Agent identified `load_model` hot path but no
         fix was approved this run
   ```

---

## 5. Skills, Plugins, and Nested Tooling

### Skills (domain knowledge preloaded via subagent frontmatter)

| Skill name                 | Content                                                                                                                                                  | Agents using it                                                 |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| `matrix-quote-schema`      | Full `QuoteInput` contract (40 fields, types, defaults), `TARGETS`, `SALES_BUCKETS`, `SALES_BUCKET_MAP`, `QUOTE_NUM_FEATURES`, `QUOTE_CAT_FEATURES`.    | Schema & Config Specialist, ML Specialist, UI Specialist, Test Writer |
| `matrix-ml-conventions`    | GBR hyperparameters (`n_estimators=300, max_depth=5, lr=0.1, seed=42`), quantile alphas (0.1, 0.9), `std=(p90-p10)/2.56`, bundle shapes (legacy + CQR), diagnostic thresholds. | ML Specialist, Model Diagnostics Agent, Performance Agent       |
| `matrix-data-contract`     | `REQUIRED_TRAINING_COLS`, Parquet layout, upload log schema, implausible-hours thresholds per operation, `dataset_role="actuals"` filter rule.            | Data Quality Auditor, Config Drift Detector, Documentation Agent |
| `matrix-streamlit-patterns`| Session-state keys in use (`models_ready`, `active_page`, `quoted_hours_by_bucket`), `PAGE_DISPATCH` convention, `inject_css`, sidebar nav pattern.       | UI Specialist, Refactor Specialist                               |
| `matrix-testing-layout`    | `tests/` layout, pytest conventions, synthetic-data fixture patterns, coverage targets per module (core ≥85%, service ≥80%).                              | Test Writer                                                      |

### Plugins (packaging proposals)

1. **`matrix-data-integrity` plugin.** Bundles Data Quality Auditor,
   Config Drift Detector, and the `matrix-data-contract` skill. Reason
   for packaging: this tier is project-agnostic enough to be reused
   on a future related project with similar training-data upload
   patterns.

2. **`matrix-ml-core` plugin.** Bundles Schema & Config Specialist, ML
   Specialist, Model Diagnostics Agent, and the `matrix-ml-conventions`
   + `matrix-quote-schema` skills. This is the ML kernel of the
   orchestration system and could plug into other quote-style apps.

3. **UI/Refactor, Performance, Docs, Tests stay local** to this
   repository — too project-specific (Streamlit + 1282-line file
   layout) or too general (tests/docs) to warrant plugin packaging.

### Nested tooling / MCP

| Agent                  | External tool / MCP dependency                                    | Blocking if unavailable? |
|------------------------|-------------------------------------------------------------------|--------------------------|
| Data Quality Auditor   | None (pandas + pyarrow already in `requirements.txt`).             | No                       |
| Config Drift Detector  | None.                                                              | No                       |
| Schema Specialist      | None.                                                              | No                       |
| ML Specialist          | Optional: full retrain via Bash (`python -c "from core.models import train_one_op..."`). Requires master Parquet present. | No; flagged as caveat    |
| Model Diagnostics      | None.                                                              | No                       |
| UI Specialist          | Optional: `streamlit run quote_app.py --server.headless=true` for smoke testing via the Claude Preview MCP or `mcp__Claude_Preview__preview_start`. | No; degraded validation  |
| Refactor Specialist    | Same as UI Specialist + Bash for `python -c "import ui.<module>"` import-smoke after each split. | No; degraded validation  |
| Performance Agent      | **Bash required** for `cProfile`, `time`, `python -m timeit`. No external MCP. | Yes — agent cannot operate without Bash permission |
| Documentation Agent    | None.                                                              | No                       |
| Test Writer            | **Bash required** for `pytest -q` and `pytest --cov`. `pytest` and `pytest-cov` must be added to `requirements.txt` (currently absent). | Yes — agent will flag missing deps as first output and request user approval to add |

---

## 6. Hooks

All hooks configured in `.claude/settings.local.json` (or
`settings.json`). Exact schema depends on the Claude Code hooks spec;
below are the logical hooks.

1. **Pre-training data validation hook (`PreToolUse` on Bash/Edit).**
   Trigger: any tool call whose payload contains
   `train_one_op(` or edits to `core/models.py::train_one_op`.
   Action: runs Config Drift Detector; blocks the action if status is
   BLOCK, emitting the BLOCK reason to the model.

2. **Post-write documentation sync (`PostToolUse` on Write/Edit).**
   Trigger: any successful Edit/Write where the target matches
   `core/**/*.py`. Action: enqueues Documentation Agent via a
   background agent call. Does not block the triggering turn.

3. **Destructive-path guard (`PreToolUse` on Bash).**
   Trigger: Bash commands matching
   `/(rm|del|move|mv|rmdir)\s.*(data/master|models)/` (regex,
   Windows-aware for `del`, `move`). Action: requires explicit user
   confirmation before allowing the command. The Data Quality Auditor
   and Config Drift Detector are read-only so this only affects ML,
   UI, Refactor, Performance, and ad-hoc user Bash usage.

4. **Schema-change propagation nudge (`PostToolUse` on Edit).**
   Trigger: any edit to `core/config.py` or `core/schemas.py`. Action:
   emits a system-reminder to the model listing the downstream sites
   (`QuoteInput`→`_quote_to_df`→`render_single_quote` form inputs→
   `QUOTE_NUM_FEATURES`→`REQUIRED_TRAINING_COLS`) so follow-up edits
   are not forgotten.

5. **Test-suite freshness hook (`Stop` event).**
   Trigger: orchestrator Stop event. Action: if any production file
   under `core/` or `service/` was modified in the turn and Test
   Writer was not invoked, appends a warning to the final report.

---

## 7. Git Worktrees and `.gitignore`

### Worktree proposal (task-based, 3 worktrees)

Because most real tasks in this project cross module boundaries (e.g.,
"add a new feature" touches config, schemas, features, models,
predict_lib, and the UI), module-based worktrees would fight the grain
of the work. Task-based worktrees align with how the orchestration
system groups agents.

| Worktree                        | Branch pattern          | Purpose                                                                                                                      |
|---------------------------------|-------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `../matrix-quote-app--ml/`      | `ml/*`                  | Model tuning, feature engineering, quantile work, retrains. Touches `core/features.py`, `core/models.py`, `core/config.py`.   |
| `../matrix-quote-app--ui/`      | `ui/*` and `refactor/*` | UI tab work, Streamlit changes, and the big `quote_app.py` → `ui/` modularization. Isolates session-state experiments from ML branches. |
| `../matrix-quote-app--ops/`     | `ops/*`, `docs/*`, `test/*` | Documentation, test additions, data-integrity audits, and hot ops work. Low-blast-radius stuff runs here.               |

Using the `EnterWorktree` tool, these would be created on demand — no
permanent worktrees required. The Refactor Specialist's long-running
modularization should live in the `ui/` worktree for the duration of
the split.

### `.gitignore` additions

Per user instruction, add:

```
# Local Claude Code development workflow — never committed
CLAUDE.md
.claude/
```

Existing `.gitignore` (referenced in README.md:75) already excludes
`data/master/`, `models/`, `__pycache__/`. The two new lines above
complete the exclusion. **Caveat:** committing CLAUDE.md is the more
common convention since it propagates project conventions to
teammates; the user's instruction overrides.

---

## 8. Gaps and Risks

1. **`quote_app.py` session-state coupling.**
   `st.session_state["models_ready"]` is read at
   `quote_app.py:192, 204, 621, 1058` and written at
   `quote_app.py:107-115, 158, 1224`. `active_page` is read at
   `quote_app.py:192, 1281` and written at `:199`. A Refactor
   Specialist that splits `quote_app.py` into `ui/*.py` modules must
   either (a) keep all session-state mutations in a single
   `ui/session.py` module, or (b) expose a typed `AppState` wrapper.
   Either way, the Opus tier is justified, and the UI Specialist's
   pre-approval checkpoint is essential.

2. **Scope overlap between UI Specialist and Refactor Specialist.**
   Both can write to `quote_app.py` and `service/predict_lib.py`. If
   both are invoked in parallel on the same branch they will collide.
   **Mitigation:** orchestrator treats them as mutually exclusive —
   Refactor Specialist claims exclusive access to these files for the
   duration of its task. UI Specialist tasks are deferred until
   Refactor merges.

3. **Schema Specialist cannot complete alone.**
   A new field added to `QuoteInput` requires downstream changes to:
   - `QUOTE_NUM_FEATURES` or `QUOTE_CAT_FEATURES` in `core/config.py`
     (in scope).
   - `prepare_quote_features` and `_BOOL_STR_COLS` in
     `core/features.py` (out of scope — goes to ML Specialist).
   - `render_single_quote` form input (out of scope — UI Specialist).

   The orchestrator must treat Schema Specialist output as a **ticket
   generator** that fans out into parallel ML and UI tasks. This is
   modeled in the handoff protocol (§4) but is an inherent coupling
   risk.

4. **ML Specialist metrics-delta is often unknowable at edit time.**
   Changing hyperparameters in `train_one_op` does not produce a
   metrics delta unless a retrain is run. The contract allows
   `null` values with `retraining_required: true`, but this means the
   orchestrator cannot always present real before/after numbers in its
   final report.

5. **Performance Agent's hot-path is structurally protected.**
   The redundant `load_model` calls in `service/predict_lib.py:68-72`
   and `:136-140` look like an obvious fix (`functools.lru_cache`),
   but `.joblib` files change on retrain. The cache must be keyed on
   the file's mtime or invalidated from `render_admin` after training.
   Any Performance Agent proposal here must address cache invalidation
   explicitly or it will introduce a stale-model bug.

6. **`_compute_confidence` thresholds are user-visible governance.**
   The `<0.3`/`<0.6`/`else` thresholds in
   `service/predict_lib.py:45-50` determine whether users see "high",
   "medium", or "low" confidence on their quotes. Any agent proposing
   to change these must route through Schema & Config Specialist (not
   ML Specialist) because the change is a governance policy change,
   not a model change. Tool scopes as written allow either to edit
   this — the CLAUDE.md convention section must call this out.

7. **Bundle-shape fallback is fragile.**
   `predict_with_interval` (`core/models.py:113-142`) supports two
   bundle shapes. Feature-importance extraction in
   `quote_app.py:484-513` also handles both. ML Specialist changes to
   training output (e.g., switching everything to CQR) must keep the
   legacy reader path working or every field that reads a pre-switch
   `.joblib` will break silently. Test Writer must cover both shapes.

8. **`REQUIRED_TRAINING_COLS` is under-specified.**
   The list (`core/config.py:100-109`) requires only `me10_actual_hours`
   among the 12 targets. A dataset with all 12 columns present but
   all non-me10 columns all-null will pass Config Drift Detector and
   train only one model. The Data Quality Auditor catches this via the
   `operations_insufficient` field, but the orchestrator must honor
   that signal as at-least-WARN.

9. **Documentation Agent docstring scope is hard to police.**
   Haiku writing docstrings inside existing files risks accidentally
   rewriting adjacent code. **Mitigation:** the
   `matrix-documentation-patterns` skill includes a pre-write
   validator (regex: every proposed Edit must have
   `old_string` fully contained within `"""..."""` or `# ...` lines).

10. **Test Writer's dependency on missing packages.**
    `pytest` and `pytest-cov` are not in `requirements.txt`. Test
    Writer's first action on a fresh environment is to propose adding
    them to a dev-dependencies section, which is scoped to
    `requirements.txt` — currently outside its allowlist. Resolution:
    Test Writer is granted write access to a new
    `requirements-dev.txt` file (not `requirements.txt`).

---

## Summary Table

| # | Agent Name               | Tier | Model       | File Scope                                                            | Dispatch Position                       | Shared Skills                                              |
|---|--------------------------|------|-------------|-----------------------------------------------------------------------|-----------------------------------------|------------------------------------------------------------|
| 1 | Data Quality Auditor     | 1    | Haiku 4.5   | RO: `data/master/**`, `core/config.py`                                 | 1st (any training task)                  | `matrix-data-contract`                                     |
| 2 | Config Drift Detector    | 1    | Haiku 4.5   | RO: `core/config.py`, `data/master/**`                                 | 1st, parallel with #1                    | `matrix-data-contract`                                     |
| 3 | Schema & Config Specialist | 1  | Sonnet 4.6  | W: `core/config.py`, `core/schemas.py`                                 | After #1/#2 PASS; before #4, #6          | `matrix-quote-schema`                                      |
| 4 | ML Specialist            | 2    | Sonnet 4.6  | W: `core/models.py`, `core/features.py`                                | After #3 (if schema changed)             | `matrix-ml-conventions`, `matrix-quote-schema`             |
| 5 | Model Diagnostics Agent  | 2    | Haiku 4.5   | RO: `models/**`, `data/master/**`                                      | After #4                                 | `matrix-ml-conventions`                                    |
| 6 | UI Specialist            | 3    | Sonnet 4.6  | W: `quote_app.py`, `service/predict_lib.py`                            | After #4 (if prediction iface changed); else parallel with #4 | `matrix-streamlit-patterns`, `matrix-quote-schema` |
| 7 | Refactor Specialist      | 3    | Opus 4.7    | W: `quote_app.py`, `service/predict_lib.py`, new `ui/**`               | Explicit invocation only; blocks #6      | `matrix-streamlit-patterns`                                |
| 8 | Performance Agent        | 4    | Sonnet 4.6  | RO: `core/models.py`, `service/predict_lib.py`; Bash for profiling     | On demand; proposals routed to #4 or #6  | `matrix-ml-conventions`                                    |
| 9 | Documentation Agent      | 4    | Haiku 4.5   | W: `README.md`, docstrings in any prod file                            | Always last (parallel with #10)          | `matrix-data-contract`                                     |
| 10| Test Writer              | 4    | Sonnet 4.6  | W: `tests/**`, `requirements-dev.txt`                                  | Always last (parallel with #9)           | `matrix-testing-layout`, `matrix-quote-schema`             |

---

## Verification section (how to test after build-out)

Once the orchestration system is implemented (not this task):

1. **Dry-run a training task.** `/orchestrate retrain all models after
   dropping the changeover_time_min feature`. Confirm: Data Quality
   Auditor + Config Drift Detector run first, Schema Specialist edits
   `core/config.py` + `core/schemas.py`, ML Specialist updates
   `core/features.py` references, Model Diagnostics runs post-train,
   Documentation + Test Writer run last.

2. **Dry-run a UI-only task.** `/orchestrate add a footer to the
   Single Quote page showing the model version`. Confirm: data-tier
   agents are **not** invoked; UI Specialist runs alone; Documentation
   Agent updates docstrings if it added a helper.

3. **Dry-run a BLOCK scenario.** Rename `me10_actual_hours` in the
   master Parquet to `me10_hours`, then invoke `/orchestrate retune
   me10 model`. Confirm: Config Drift Detector returns BLOCK, the
   pipeline halts, no downstream agents run, user gets a clear error.

4. **Destructive-path hook test.** In the main conversation, attempt
   `rm -rf data/master/`. Confirm: hook intercepts, user-confirmation
   prompt appears.

5. **Refactor dry-run.** `/orchestrate split quote_app.py into a ui/
   directory`. Confirm: Refactor Specialist proposes module layout,
   UI Specialist approves, files are created, `streamlit run
   quote_app.py` still launches, all 7 pages still render, all 3
   `st.session_state` keys still work.
