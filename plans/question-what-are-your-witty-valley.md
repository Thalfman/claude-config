# Matrix Quote Web Demo — Improvement Plan (rev 5, locked)

## Context

Two apps on one demo. Both use **the exact same implementation** — same code path, same gradient-boosting model architecture, same default hyperparameters, same Pyodide pipeline, same UI component. The only difference is the data each side's models were trained on. The Real side overfits because n=24 is small, and **that overfit is the pitch point** — it shows what the engine looks like with limited data, while the Synthetic side shows what it looks like at scale.

All decisions confirmed:

- Drivers: **Top 3 rolled up** across the whole quote.
- Confidence wording: **High confidence / Moderate confidence / Lower confidence.**
- Supporting matches: **Both sides** — Real shows "Most similar past projects," Synthetic shows "Most similar training rows."
- Overfit framing: **Let the confidence chips speak for themselves.** No callout banner. Cross-side compare button stays deferred to a later PR.

---

# PART 1 — Summary for review

## The architectural change in one sentence

**Train a second set of 12 gradient-boosting models on the 24 real projects using the EXACT same `train_one_op` pipeline (no hyperparameter changes), ship both sets, parameterize Pyodide to load whichever set the active tab needs, and wire both Quote tabs to one shared `QuoteResultPanel` that surfaces estimate, likely range, top 3 drivers, per-category confidence, and the closest 3 past projects (or training rows on the Synthetic side).**

## What we're changing

| Area | Today | After |
|---|---|---|
| **Models shipped** | 12 GBR joblibs trained on 500 synthetic rows | 24 GBR joblibs — same 12 targets × 2 datasets: `models_real/*.joblib` (n=24, overfits, lower confidence) and `models_synthetic/*.joblib` (n=500, higher confidence) |
| **Training script** | One pipeline, synthetic only | Two passes through the **identical** `train_one_op` call with default hyperparameters — once with the real CSV, once with the synthetic CSV |
| **Pyodide client** | Loads one fixed model set | Lazy-loads either set (`dataset: "real" \| "synthetic"`); caches both |
| **Real Quote** | Find-Similar only, no estimate | Full ML prediction via real-trained models. Same UI as Synthetic. |
| **Synthetic Quote** | Prediction with inert Drivers/Neighbors tabs | Full ML prediction with drivers populated (rolled-up top 3) and per-category confidence |
| **Result panel** | Two different components | One shared `QuoteResultPanel` for both sides |
| **Supporting matches** | Real shows match cards, Synthetic shows nothing | Both sides show top-3 closest past projects / training rows beneath the headline estimate |
| **Customer-facing copy** | Mix of ML jargon and plain English | 100% business language — no ML terms in the UI |
| **Home page** | Three cards (Real Quote, Synthetic Quote, Real Insights) | Two cards (Real Data, Synthetic Data) each surfacing the three sub-tabs as chips |
| **Data disclosure** | None | Small "What this is trained on" popover on each Quote / Compare / Insights page |

## Translation table (the vocabulary rule)

Every term on the left appears in code or training metadata. The customer sees only the right-hand version.

| In code / model artifacts | In the UI |
|---|---|
| P50 | Estimated hours |
| P10–P90 band | Likely range |
| R² ≥ 0.70 | High confidence |
| R² 0.50–0.70 | Moderate confidence |
| R² < 0.50 | Lower confidence |
| MAE | (not surfaced — rolls into the confidence label) |
| Feature importances | What drives this estimate |
| Top-k nearest neighbors (Real) | Most similar past projects |
| Top-k nearest neighbors (Synthetic) | Most similar training rows |
| Gradient boosting / quantile regression | "the prediction engine" or "the model" |
| Synthetic data | Generated training data / training pool |
| Real data / historical book | Your historical projects / today's book |
| Pyodide / scikit-learn / WebAssembly | Runs in your browser — no servers |
| Per-target / per-operation | Per work category (Mech, Elec, Robot, Controls, Build, Ship, Install, Travel, Docs, PM) |

## n=24 — the overfit IS the demo

Training gradient boosting with default hyperparameters on 24 real projects will overfit. **That is intentional and required.** Do not tune `n_estimators`, `max_depth`, `learning_rate`, or any other knob to soften it. The whole point of the Real-vs-Synthetic comparison is that:

- The Real tab's per-category R² values come back low → the UI maps them to "Lower confidence" chips visible across the breakdown.
- The Real tab's "Most similar past projects" card will show 3 real projects whose actuals are very close to the prediction, making it visible to the buyer that the model has essentially memorized those examples.
- The Synthetic tab's confidence skews "Moderate" or "High" because the larger pool produces more stable models.
- The buyer compares the two tabs side-by-side (mentally, by switching) and concludes: "today's data is limited, the engine is honest about its limits, more data would help."

## Recommended bundle — one PR, ~14–18 hours

Five commits in one PR:

1. **`feat(demo): train a real-data GBR bundle alongside synthetic`** — `scripts/generate_demo_assets.py` trains both datasets through the identical `train_one_op` call; outputs `demo_assets/models_real/` and `demo_assets/models_synthetic/`. `scripts/build_demo_static.py` copies both to `frontend/public/demo-assets/` and emits `model_metrics_real.json` + `model_metrics_synthetic.json`.
2. **`feat(pyodide): lazy-load models by dataset`** — `pyodideClient.ts` accepts `dataset: "real" | "synthetic"`, loads each set on first use, caches both. Exposes `getFeatureImportances(dataset)` alongside `predictQuote(input, dataset)`.
3. **`feat(quote): unified QuoteResultPanel with drivers, per-category confidence, supporting matches`** — new shared component consumed by both Quote tabs. Same shape on both sides; only the supporting-matches label differs.
4. **`feat(real-quote): run ML prediction via Pyodide on real-trained models`** — rewires `ComparisonQuote.tsx` from Find-Similar to full ML prediction. Deletes `CompareFindSimilarTab.tsx`. Updates `MachineLearningQuoteTool.tsx` to use the same shared panel.
5. **`style(demo): two-card home, business-language sweep, "what this is trained on" disclosure`** — copy and small-component polish; string-only changes plus `DataProvenanceNote`.

## What we're NOT doing

- **Not adding a backend.** Runs in browser, period.
- **Not changing model hyperparameters for either pipeline.** Both use the existing defaults from `train_one_op`. The user explicitly said: do not change the implementation.
- **Not adding any callout banner about overfitting** on the Real side. The confidence chips and the side-by-side comparison speak for themselves.
- **Not exposing ML jargon anywhere in customer-facing strings.** Code can use technical terms internally; the UI cannot.
- **Not redesigning Compare or Insights tabs.** They're already parallel after PR #8.
- **Not adding new top-level routes.**
- **Not shipping a marketing footer destination yet** (blocks on CTA URL/email).
- **Not shipping the cross-side compare button in this PR.** Deferred to a follow-up.
- **Not editing `core/models.py`.** Default hyperparameters means the existing `train_one_op(df, target, models_dir, version)` signature is sufficient — no new kwargs needed.

---

# PART 2 — Implementation appendix (executor reference)

## Architecture overview

```
                           ┌────────────────────────┐
                           │   QuoteResultPanel     │
                           │   - hero estimate      │
                           │   - likely range       │
                           │   - top 3 drivers      │
                           │   - confidence chip    │
                           │   - per-category break │
                           │   - supporting matches │
                           └─────────▲──────────────┘
                                     │
                           UnifiedQuoteResult
                                     │
                           ┌─────────┴──────────┐
                           │   toUnifiedResult  │  one adapter,
                           │  (prediction +     │  same shape on both sides
                           │   importances +    │
                           │   metrics +        │
                           │   supportingPool + │
                           │   supportLabel)    │
                           └─────────▲──────────┘
                                     │
              ┌──────────────────────┴──────────────────────┐
              │                                             │
  ┌───────────┴───────────┐                     ┌───────────┴───────────┐
  │ ComparisonQuote.tsx   │                     │ MachineLearningQuote  │
  │                       │                     │ Tool.tsx              │
  │  predictQuote(input,  │                     │  predictQuote(input,  │
  │    "real")            │                     │    "synthetic")       │
  │  getFeatureImportance │                     │  getFeatureImportance │
  │    ("real")           │                     │    ("synthetic")      │
  │  supportingPool=real  │                     │  supportingPool=syn   │
  │  supportLabel="Most   │                     │  supportLabel="Most   │
  │  similar past         │                     │  similar training     │
  │  projects"            │                     │  rows"                │
  └───────────────────────┘                     └───────────────────────┘
                                     │
                           ┌─────────┴──────────┐
                           │  pyodideClient.ts  │
                           │  loads models by   │
                           │  dataset, caches   │
                           │  both              │
                           └─────────▲──────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
  demo-assets/models_real/*.joblib     demo-assets/models_synthetic/*.joblib
  demo-assets/model_metrics_real.json  demo-assets/model_metrics_synthetic.json
                     │                               │
        12 models · default hyperparams   12 models · default hyperparams
        trained on 24 real rows           trained on 500 synthetic rows
                  ↓                                ↓
        will overfit (intentional)       reasonable generalization
        → low R² → "Lower confidence"    → moderate/high R² → mixed confidence
```

## Commit 1 — Train both bundles, identical pipeline

**File to modify:** `scripts/generate_demo_assets.py` — replace the body so it reads from both CSVs and trains both bundles through the SAME `train_one_op` call with no hyperparameter override.

```python
# scripts/generate_demo_assets.py (rewritten body)
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "demo_assets"

REAL_CSV      = DEMO_ROOT / "data/real/projects_real.csv"
SYNTHETIC_CSV = DEMO_ROOT / "data/synthetic/projects_synthetic.csv"

MODELS_REAL      = DEMO_ROOT / "models_real"
MODELS_SYNTHETIC = DEMO_ROOT / "models_synthetic"

def train_bundle(df: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    """Train 12 GBR models with default hyperparameters; write joblibs + metrics."""
    sys.path.insert(0, str(REPO_ROOT))
    from core.config import TARGETS
    from core.models import train_one_op
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for target in TARGETS:
        # NOTE: identical call on both sides. No hyperparameter override.
        result = train_one_op(df, target, models_dir=str(out_dir), version="v1")
        if result:
            rows.append(result)
            print(f"  trained {target}")
        else:
            print(f"  skipped {target} (not enough data)")
    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "metrics_summary.csv", index=False)
    return summary

def main():
    real_df = pd.read_csv(REAL_CSV)
    syn_df  = pd.read_csv(SYNTHETIC_CSV)
    print(f"Training real pipeline (n={len(real_df)})...")
    train_bundle(real_df, MODELS_REAL)
    print(f"Training synthetic pipeline (n={len(syn_df)})...")
    train_bundle(syn_df, MODELS_SYNTHETIC)
    # Existing helpers (write_metrics_history, calibration parquet) — preserve, dispatching
    # by which bundle directory they should target. Default keep them in MODELS_SYNTHETIC
    # for backwards compatibility unless we want them on both sides.

if __name__ == "__main__":
    main()
```

Notes:
- The identical `train_one_op(df, target, models_dir, version)` call IS the implementation lock. Any change to that call would violate the user's "stop changing it" rule.
- The existing `build_master(n=300)` helper can be deleted — it builds synthetic data in-process; we now read the committed CSV instead. (Or leave it as a fallback for someone running locally without the CSV.)
- Existing `write_metrics_history()` and `calibration.parquet` writes — preserve them on the synthetic side only for now; the real side's metrics are noisy enough that a metrics-history chart would be misleading and is not required for this PR.

**Then update:** `scripts/build_demo_static.py` — copy both new model dirs to `frontend/public/demo-assets/`, and emit per-bundle metrics JSON:

```python
# After the existing copy step, replace the single-models block with:
import csv, json, shutil

for src_name in ("models_real", "models_synthetic"):
    src = DEMO_ROOT / src_name
    dst = OUT_DIR / "demo-assets" / src_name
    shutil.copytree(src, dst, dirs_exist_ok=True)
    rows = []
    with (src / "metrics_summary.csv").open() as f:
        for r in csv.DictReader(f):
            rows.append({
                "target": r["target"],
                "rows":   int(r["rows"]),
                "mae":    round(float(r["mae"]), 2),
                "r2":     round(float(r["r2"]), 3),
            })
    suffix = src_name.split("_", 1)[1]   # "real" or "synthetic"
    (OUT_DIR / "demo-assets" / f"model_metrics_{suffix}.json").write_text(
        json.dumps({"models": rows}, indent=2))
```

**Cleanup:** old `demo_assets/models/*` and `frontend/public/demo-assets/models/*` paths become redundant after both new dirs exist. Delete in this commit; update any code that referenced the old path.

**Verification:**
```bash
python scripts/generate_demo_assets.py    # exit 0; 12 joblibs + csv in each dir
python scripts/build_demo_static.py       # both dirs copied + 2 metrics JSONs emitted
ls demo_assets/models_real        # me10..pm200_*.joblib + metrics_summary.csv
ls demo_assets/models_synthetic   # same 12 + metrics
ls frontend/public/demo-assets/   # ...models_real/, models_synthetic/, model_metrics_real.json, model_metrics_synthetic.json
```

The real-side metrics will look bad (low R²). That's expected and required — leave as-is.

## Commit 2 — Parameterize Pyodide client by dataset

**File to modify:** `frontend/src/demo/pyodideClient.ts`.

Current API (approximate): `predictQuote(input)`, `subscribe()`, `ensurePyodideReady()`. Models loaded at warmup from a fixed URL.

Target API:

```ts
export type Dataset = "real" | "synthetic";

export function subscribe(cb: (s: Stage) => void): () => void;       // unchanged
export function ensurePyodideReady(): Promise<void>;                 // unchanged

/** Lazy-load a specific dataset's models into the running pyodide runtime.
 *  Caches per dataset — second call is a no-op. */
export function ensureModelsReady(dataset: Dataset): Promise<void>;

/** Predict against a specific dataset's models. Throws if dataset's models not loaded
 *  (caller must `ensureModelsReady(dataset)` first). */
export function predictQuote(input: QuoteInput, dataset: Dataset): Promise<Prediction>;

/** Returns { targetName: [[encodedFeatureName, importance], ...top 5] }
 *  for the given dataset. Cached after first call. */
export function getFeatureImportances(
  dataset: Dataset,
): Promise<Record<string, Array<[string, number]>>>;
```

**Implementation sketch** — keep two parallel module dicts in the pyodide runtime:

```python
# Stringified inside pyodideClient.ts
import joblib, json, urllib.request, io
LOADED: dict[str, dict[str, object]] = {"real": {}, "synthetic": {}}
IMPORTANCES_CACHE: dict[str, dict[str, list]] = {}

def load_bundle(dataset: str, urls: dict[str, str]) -> None:
    # urls = {"me10_actual_hours": "demo-assets/models_real/me10_actual_hours_v1.joblib", ...}
    if LOADED[dataset]:
        return  # already loaded
    for tgt, url in urls.items():
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        LOADED[dataset][tgt] = joblib.load(io.BytesIO(data))

def predict(dataset: str, input_payload: str) -> str:
    import pandas as pd
    payload = json.loads(input_payload)
    df = pd.DataFrame([payload])
    out = {}
    for tgt, pipeline in LOADED[dataset].items():
        # Pipelines have main + p10 + p90 (existing pattern in service/predict_lib.py)
        p50 = float(pipeline["main"].predict(df)[0])
        p10 = float(pipeline["p10"].predict(df)[0])
        p90 = float(pipeline["p90"].predict(df)[0])
        out[tgt] = {"p10": p10, "p50": p50, "p90": p90}
    return json.dumps(out)

def collect_importances(dataset: str) -> str:
    if dataset in IMPORTANCES_CACHE:
        return json.dumps(IMPORTANCES_CACHE[dataset])
    out = {}
    for tgt, pipeline in LOADED[dataset].items():
        # Walk the pipeline to find the GBR + preprocessor — depends on
        # how core/models.py constructs them. Verify by reading core/models.py
        # before committing this code.
        pre = pipeline["main"].named_steps.get("preprocessor")
        gbr = pipeline["main"].named_steps.get("regressor")
        if pre is None or gbr is None:
            continue
        names = list(pre.get_feature_names_out())
        imps  = list(gbr.feature_importances_)
        out[tgt] = sorted(zip(names, imps), key=lambda p: -p[1])[:5]
    IMPORTANCES_CACHE[dataset] = out
    return json.dumps(out)
```

(Adapt step names to whatever `core/models.py:train_one_op` actually produces. Read that file before writing the Python.)

**Stage labels surfaced to the UI:**
- "Warming up the engine" (Pyodide bootstrap)
- "Loading prediction libraries" (sklearn + pandas + joblib)
- "Loading real-data models" (when ensureModelsReady("real") fires)
- "Loading synthetic-data models" (when ensureModelsReady("synthetic") fires)
- "Ready"

The PyodideLoader UI already supports a stage strip — extend `STAGE_ORDER` accordingly.

**Verification:**
- `/ml/quote` → only synthetic models load.
- Navigate to `/compare/quote` → real models load (no synthetic reload).
- Both predictions return reasonable shapes; per-target keys match.

## Commit 3 — Unified `QuoteResultPanel` + adapter

**New files:**

```
frontend/src/demo/quoteResult.ts
frontend/src/demo/quoteAdapter.ts
frontend/src/demo/featureLabels.ts
frontend/src/demo/categoryLabels.ts
frontend/src/demo/modelMetrics.ts
frontend/src/lib/projectHours.ts
frontend/src/components/quote/QuoteResultPanel.tsx
frontend/src/components/quote/QuoteResultPanel.test.tsx
```

**`quoteResult.ts`** — the contract:

```ts
export interface UnifiedQuoteResult {
  estimateHours: number;
  likelyRangeLow: number;
  likelyRangeHigh: number;
  overallConfidence: "high" | "moderate" | "lower";
  perCategory: Array<{
    label: string;
    estimateHours: number;
    rangeLow: number;
    rangeHigh: number;
    confidence: "high" | "moderate" | "lower";
  }>;
  topDrivers: Array<{
    label: string;
    direction: "increases" | "decreases";
    magnitude: "strong" | "moderate" | "minor";
  }>;
  supportingMatches: {
    label: string;        // "Most similar past projects" or "Most similar training rows"
    items: Array<{
      projectId: string;
      projectName: string;
      actualHours: number;
      similarity: number;  // 0..1
    }>;
  };
}
```

**`quoteAdapter.ts`** — single function used by both sides:

```ts
import { QuoteInput } from "@/api/types";
import { ProjectRecord, computeFeatureStats } from "@/demo/realProjects";
import { nearestK } from "@/lib/nearestNeighbor";
import { sumActualHours } from "@/lib/projectHours";
import { CATEGORY_LABEL } from "@/demo/categoryLabels";
import { humanFeatureLabel } from "@/demo/featureLabels";
import { UnifiedQuoteResult } from "./quoteResult";
import type { ModelMetric } from "./modelMetrics";

export interface AdapterArgs {
  input: QuoteInput;
  prediction: Record<string, { p10: number; p50: number; p90: number }>;
  importances: Record<string, Array<[string, number]>>;
  metrics: Record<string, ModelMetric>;
  supportingPool: ProjectRecord[];
  supportingLabel: string;        // "Most similar past projects" | "Most similar training rows"
}

export function toUnifiedResult(args: AdapterArgs): UnifiedQuoteResult {
  const targets     = Object.keys(args.prediction);
  const perCategory = targets.map((t) => ({
    label:         CATEGORY_LABEL[t] ?? t,
    estimateHours: args.prediction[t].p50,
    rangeLow:      args.prediction[t].p10,
    rangeHigh:     args.prediction[t].p90,
    confidence:    r2ToConfidence(args.metrics[t]?.r2 ?? 0),
  }));
  const estimateHours   = perCategory.reduce((s, c) => s + c.estimateHours, 0);
  const likelyRangeLow  = Math.max(0, perCategory.reduce((s, c) => s + c.rangeLow, 0));
  const likelyRangeHigh = perCategory.reduce((s, c) => s + c.rangeHigh, 0);
  const topDrivers      = rollUpDrivers(args.prediction, args.importances, args.input);
  const overallConfidence = rollUpConfidence(perCategory);

  const stats = computeFeatureStats(args.supportingPool);
  const supportingItems = nearestK(args.input, args.supportingPool, stats, 3).map((m) => ({
    projectId:   m.record.project_id ?? "",
    projectName: m.record.project_name ?? "",
    actualHours: sumActualHours(m.record),
    similarity:  1 / (1 + m.distance),
  }));

  return {
    estimateHours, likelyRangeLow, likelyRangeHigh, overallConfidence,
    perCategory, topDrivers,
    supportingMatches: { label: args.supportingLabel, items: supportingItems },
  };
}

function r2ToConfidence(r2: number): "high" | "moderate" | "lower" {
  if (r2 >= 0.70) return "high";
  if (r2 >= 0.50) return "moderate";
  return "lower";
}

function rollUpDrivers(prediction, importances, input) {
  const totalEstimate = Object.values(prediction).reduce((s, p) => s + p.p50, 0);
  // 1) For each target's importances, weight each entry by (target.p50 / totalEstimate)
  // 2) Group by raw feature name; sum weights
  // 3) Take top 3
  // 4) Translate name → business label, infer direction from input vs typical
  // 5) Magnitude: > 0.15 strong, > 0.08 moderate, else minor
  const accum: Map<string, number> = new Map();
  for (const [tgt, pairs] of Object.entries(importances)) {
    const w = (prediction[tgt]?.p50 ?? 0) / Math.max(1, totalEstimate);
    for (const [name, imp] of pairs) {
      accum.set(name, (accum.get(name) ?? 0) + imp * w);
    }
  }
  const sorted = [...accum.entries()].sort((a, b) => b[1] - a[1]);
  return sorted.slice(0, 3).map(([rawName, weight]) => {
    const { label, direction } = humanFeatureLabel(rawName, input);
    return {
      label,
      direction,
      magnitude: (weight > 0.15 ? "strong" : weight > 0.08 ? "moderate" : "minor") as
                 "strong" | "moderate" | "minor",
    };
  });
}

function rollUpConfidence(perCategory): "high" | "moderate" | "lower" {
  const total = perCategory.reduce((s, c) => s + c.estimateHours, 0);
  if (total === 0) return "lower";
  const score = perCategory.reduce((s, c) => {
    const w = c.estimateHours / total;
    return s + w * (c.confidence === "high" ? 1 : c.confidence === "moderate" ? 0.5 : 0);
  }, 0);
  if (score >= 0.70) return "high";
  if (score >= 0.40) return "moderate";
  return "lower";
}
```

**`featureLabels.ts`** (skeleton — fill all 33 numeric + 6 categorical):

```ts
const NUM_LABELS: Record<string, string> = {
  station_count:      "Number of stations",
  robot_count:        "Number of robots",
  servo_axes:         "Servo axes",
  conveyor_total_ft:  "Conveyor length",
  fence_perimeter_ft: "Safety fencing",
  // ... all 33 numeric features
};
const CAT_LABELS: Record<string, string> = {
  industry_segment: "Industry",
  system_category:  "System category",
  automation_level: "Automation level",
  plc_family:       "PLC family",
  hmi_family:       "HMI family",
  vision_type:      "Vision system",
};
export function humanFeatureLabel(rawName: string, input: Record<string, unknown>) {
  if (NUM_LABELS[rawName]) {
    return { label: NUM_LABELS[rawName], direction: "increases" as const };
  }
  // One-hot encoded names look like "industry_segment_Aerospace" — split on "_"
  for (const field of Object.keys(CAT_LABELS)) {
    if (rawName.startsWith(field + "_")) {
      const value = rawName.slice(field.length + 1);
      return { label: `${CAT_LABELS[field]}: ${value}`, direction: "increases" as const };
    }
  }
  return { label: rawName, direction: "increases" as const };
}
```

(Direction is `"increases"` for all v1 — true direction would require partial-dependence evaluation; not worth the complexity for demo copy. If buyer feedback demands true direction in v2, we can add it.)

**`categoryLabels.ts`:**

```ts
export const CATEGORY_LABEL: Record<string, string> = {
  me10_actual_hours:    "Mechanical Engineering — primary",
  me15_actual_hours:    "Mechanical Engineering — detailing",
  me230_actual_hours:   "Mechanical Engineering — fixtures",
  ee20_actual_hours:    "Electrical Engineering",
  rb30_actual_hours:    "Robotics",
  cp50_actual_hours:    "Controls & PLC",
  bld100_actual_hours:  "Build & assembly",
  shp150_actual_hours:  "Shipping & QC",
  inst160_actual_hours: "Installation",
  trv180_actual_hours:  "Travel",
  doc190_actual_hours:  "Documentation",
  pm200_actual_hours:   "Project management",
};
```

**`modelMetrics.ts`:**

```ts
import { useQuery } from "@tanstack/react-query";
import { DEMO_ASSETS } from "@/lib/demoMode";

export type ModelMetric = { target: string; rows: number; mae: number; r2: number };

export function useModelMetrics(dataset: "real" | "synthetic") {
  return useQuery<{ models: ModelMetric[] }>({
    queryKey: ["demo", "modelMetrics", dataset],
    queryFn: async () => {
      const res = await fetch(`${DEMO_ASSETS}/model_metrics_${dataset}.json`);
      if (!res.ok) throw new Error(`model_metrics_${dataset}.json ${res.status}`);
      return res.json();
    },
    staleTime: Infinity,
  });
}
```

**`projectHours.ts`:**

```ts
import { ProjectRecord } from "@/demo/realProjects";
const ACTUAL_FIELDS = [
  "me10_actual_hours","me15_actual_hours","me230_actual_hours","ee20_actual_hours",
  "rb30_actual_hours","cp50_actual_hours","bld100_actual_hours","shp150_actual_hours",
  "inst160_actual_hours","trv180_actual_hours","doc190_actual_hours","pm200_actual_hours",
] as const;
export function sumActualHours(r: ProjectRecord): number {
  return ACTUAL_FIELDS.reduce((s, f) => s + Number(r[f] ?? 0), 0);
}
```

**`QuoteResultPanel.tsx`:**

```tsx
import { TrendingUp, TrendingDown } from "lucide-react";
import { UnifiedQuoteResult } from "@/demo/quoteResult";

const CONFIDENCE_LABEL = {
  high:     "High confidence",
  moderate: "Moderate confidence",
  lower:    "Lower confidence",
};
const CONFIDENCE_TONE = {
  high:     "bg-tealSoft text-tealDark",
  moderate: "bg-amberSoft text-ink",
  lower:    "bg-amber/10 text-danger",
};
const CONFIDENCE_SHORT = { high: "H", moderate: "M", lower: "L" };
const MAGNITUDE_LABEL = {
  strong:   "Strong driver",
  moderate: "Moderate driver",
  minor:    "Minor driver",
};
const fmtHrs = (n: number) => Math.round(n).toLocaleString();

export function QuoteResultPanel({ result }: { result: UnifiedQuoteResult }) {
  return (
    <div className="space-y-6" id="quote-results">
      {/* Hero estimate */}
      <div className="card p-6">
        <div className="flex items-baseline justify-between">
          <span className="eyebrow text-[10px] text-muted">Estimated hours</span>
          <span className={`text-[10px] eyebrow px-2 py-0.5 rounded-sm ${CONFIDENCE_TONE[result.overallConfidence]}`}>
            {CONFIDENCE_LABEL[result.overallConfidence]}
          </span>
        </div>
        <div className="display-hero text-4xl text-ink tnum mt-2">{fmtHrs(result.estimateHours)} hrs</div>
        <div className="text-sm text-muted mt-1">
          Likely range {fmtHrs(result.likelyRangeLow)}–{fmtHrs(result.likelyRangeHigh)} hrs
        </div>
      </div>

      {/* Drivers */}
      <div className="card p-5">
        <div className="eyebrow text-[10px] text-muted mb-3">What drives this estimate</div>
        <ul className="space-y-2">
          {result.topDrivers.map((d, i) => (
            <li key={i} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2 text-ink">
                {d.direction === "increases"
                  ? <TrendingUp size={14} className="text-amber" aria-hidden="true" />
                  : <TrendingDown size={14} className="text-teal" aria-hidden="true" />}
                {d.label}
              </span>
              <span className="text-[11px] eyebrow text-muted">{MAGNITUDE_LABEL[d.magnitude]}</span>
            </li>
          ))}
          {result.topDrivers.length === 0 && (
            <li className="text-sm text-muted">No clear drivers — inputs are similar to typical projects.</li>
          )}
        </ul>
      </div>

      {/* Per-category */}
      <div className="card p-5">
        <div className="eyebrow text-[10px] text-muted mb-3">Hours by work category</div>
        <div className="space-y-1.5">
          {result.perCategory.map((c) => (
            <div key={c.label} className="grid grid-cols-12 gap-2 items-baseline text-sm">
              <span className="col-span-6 text-ink truncate">{c.label}</span>
              <span className="col-span-2 text-ink tnum text-right">{fmtHrs(c.estimateHours)} hrs</span>
              <span className="col-span-3 text-[11px] text-muted tnum text-right">
                {fmtHrs(c.rangeLow)}–{fmtHrs(c.rangeHigh)}
              </span>
              <span className={`col-span-1 text-[10px] eyebrow text-center rounded-sm ${CONFIDENCE_TONE[c.confidence]}`}
                title={CONFIDENCE_LABEL[c.confidence]}>
                {CONFIDENCE_SHORT[c.confidence]}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Supporting matches — both sides */}
      <div className="card p-5">
        <div className="eyebrow text-[10px] text-muted mb-3">{result.supportingMatches.label}</div>
        <div className="space-y-2">
          {result.supportingMatches.items.map((m) => (
            <div key={m.projectId} className="flex items-baseline justify-between gap-3 text-sm">
              <span className="min-w-0 truncate text-ink">{m.projectName}</span>
              <span className="text-[11px] text-muted mono shrink-0">
                {fmtHrs(m.actualHours)} hrs · {(m.similarity * 100).toFixed(0)}% match
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Tests** for the panel: `QuoteResultPanel.test.tsx` — render with a fixture result, assert hero number, drivers list, per-category H/M/L chips, supporting label and items. Snapshot-style assertions on a fixture covering "high" vs "lower" overall confidence.

**Tests** for the adapter: `quoteAdapter.test.ts` — fixture with predefined prediction + importances + metrics + a small pool; assert estimate sum, range, confidence buckets, top-3 drivers, supporting items.

## Commit 4 — Wire both Quote pages to the shared panel

**`pages/demo/compare/ComparisonQuote.tsx`** — full rewrite of the body. Mirror the structure of `MachineLearningQuoteTool.tsx`, swapping which dataset's models are loaded:

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { PageHeader } from "@/components/PageHeader";
import { PyodideLoader } from "@/components/PyodideLoader";
import { ensurePyodideReady, ensureModelsReady, predictQuote,
         getFeatureImportances, subscribe } from "@/demo/pyodideClient";
import { useRealProjects } from "@/demo/realProjects";
import { useModelMetrics } from "@/demo/modelMetrics";
import { useHotkey } from "@/lib/useHotkey";
import { QuoteForm } from "@/pages/single-quote/QuoteForm";
import { QuoteResultPanel } from "@/components/quote/QuoteResultPanel";
import { toUnifiedResult } from "@/demo/quoteAdapter";
import { UnifiedQuoteResult } from "@/demo/quoteResult";
import { DataProvenanceNote } from "@/components/DataProvenanceNote";
import { quoteFormDefaults, quoteFormSchema, transformToQuoteInput,
         QuoteFormValues } from "@/pages/single-quote/schema";

export function ComparisonQuote() {
  const { data: pool } = useRealProjects();
  const { data: metricsData } = useModelMetrics("real");
  const metricsByTarget = useMemo(
    () => Object.fromEntries((metricsData?.models ?? []).map((m) => [m.target, m])),
    [metricsData],
  );

  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UnifiedQuoteResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  const form = useForm<QuoteFormValues>({
    resolver: zodResolver(quoteFormSchema),
    defaultValues: quoteFormDefaults,
    mode: "onBlur",
  });

  useEffect(() => {
    const unsub = subscribe((s) => {
      if (s.stage === "error") setError(s.message);
    });
    ensurePyodideReady()
      .then(() => ensureModelsReady("real"))
      .then(() => setReady(true))
      .catch((e) => setError(String(e)));
    return unsub;
  }, []);

  useHotkey({ key: "Enter", meta: true }, () => formRef.current?.requestSubmit());
  useHotkey({ key: "Enter", ctrl: true }, () => formRef.current?.requestSubmit());

  const handleSubmit = async () => {
    if (!ready || !pool) return;
    setSubmitting(true);
    try {
      const input = transformToQuoteInput(form.getValues());
      const [prediction, importances] = await Promise.all([
        predictQuote(input, "real"),
        getFeatureImportances("real"),
      ]);
      setResult(toUnifiedResult({
        input, prediction, importances,
        metrics:         metricsByTarget,
        supportingPool:  pool,
        supportingLabel: "Most similar past projects",
      }));
      requestAnimationFrame(() => {
        document.getElementById("quote-results")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Estimate failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Real Data · Quote"
        title="Real Data Quote"
        description="Estimate hours for a new project using your twenty-four real historical projects. Runs in your browser — no servers."
      />
      <DataProvenanceNote variant="real" />

      {/* Loader strip + form/result columns — mirror MachineLearningQuoteTool layout */}
      <PyodideLoader />
      <div className="grid gap-6 lg:grid-cols-2 mt-6">
        <div>
          <QuoteForm ref={formRef} form={form} onSubmit={handleSubmit}
                     submitting={submitting} ready={ready} error={error} />
        </div>
        <div>
          {result && <QuoteResultPanel result={result} />}
        </div>
      </div>
    </>
  );
}
```

**`pages/demo/MachineLearningQuoteTool.tsx`** — symmetric rewrite of the result handling. Replace lines around 96 (`setResult({ prediction, drivers: null, neighbors: null })` and the existing `<ResultPanel>`) with:

```tsx
const { data: pool } = useSyntheticPool();
const { data: metricsData } = useModelMetrics("synthetic");
const metricsByTarget = useMemo(
  () => Object.fromEntries((metricsData?.models ?? []).map((m) => [m.target, m])),
  [metricsData],
);
// ... in handleSubmit:
const [prediction, importances] = await Promise.all([
  predictQuote(input, "synthetic"),
  getFeatureImportances("synthetic"),
]);
setResult(toUnifiedResult({
  input, prediction, importances,
  metrics:         metricsByTarget,
  supportingPool:  pool ?? [],
  supportingLabel: "Most similar training rows",
}));
// ... in JSX, replace <ResultPanel ... /> with:
{result && <QuoteResultPanel result={result} />}
```

Eyebrow update (handled in this commit, not Commit 5, since the file is touched here):
- `MachineLearningQuoteTool.tsx:119` → `eyebrow="Synthetic Data · Quote"`
- Description → `"Estimate hours with a likely range and what's driving each number — runs in your browser."`

**Delete** `frontend/src/demo/CompareFindSimilarTab.tsx` and its test (verify nothing else imports it via `grep -nr "CompareFindSimilarTab" frontend/src`). The Real-Quote logic is now consolidated in `ComparisonQuote.tsx`.

**Pyodide warmup state:** the existing module-level "subscribe / ready" model needs to handle two possible "ready" states (real-loaded, synthetic-loaded). Easiest: scope `ready` per dataset in the page component using `ensureModelsReady(dataset)` instead of a single global `ready`. The existing `subscribe()` API can stay for stage-progress UI without per-dataset gating.

## Commit 5 — Polish bundle

**a) Two-card home** — `frontend/src/pages/demo/DemoHome.tsx`. Replace `ToolCard` with `SectionCard` (defined inline in the file). Two cards, each with the count chip + 3 tab chips. Copy:

| | Real Data card | Synthetic Data card |
|---|---|---|
| Eyebrow | "Real Data" | "Synthetic Data" |
| Title | "Today's book" | "At scale" |
| Description | "Twenty-four of your real, billed projects. Quote a new project and the engine estimates hours from your history — with a likely range and the factors driving the estimate." | "Five hundred generated training projects — what the engine could do once you've collected more data. Same quote experience, same outputs." |
| Count chip | `manifest.real_count` projects | `manifest.synthetic_count` training rows |
| Tabs | `/compare/quote`, `/compare/compare`, `/compare/insights` → "Quote", "Compare", "Business Insights" | `/ml/quote`, `/ml/compare`, `/ml/insights` → same labels |

(Full `SectionCard` skeleton: see Commit 1.6 in rev 3 of this file. Same component.)

**b) Business-language sweep** — `grep -nrE "P10|P50|P90|R²|MAE|gradient boost|synthetic data|Pyodide|feature import|Machine Learning · Client" frontend/src --include="*.tsx" --include="*.ts" | grep -v test | grep -v ".d.ts"`. For each hit in customer-facing strings, apply the Translation Table from Part 1.

Most likely hits (verify each before editing):
- `MachineLearningQuoteTool.tsx` — eyebrow + description (handled in Commit 4)
- `pages/demo/DemoHome.tsx` — already replaced in (a)
- `pages/demo/business/BusinessInsightsView.tsx` — datasetLabel prop values
- `pages/demo/ml/MachineLearningInsights.tsx` — eyebrow / description
- `pages/demo/business/ComparisonInsights.tsx` — eyebrow / description
- `components/PyodideLoader.tsx` — stage labels
- `pages/single-quote/ResultPanel.tsx` — only if it's imported by anything still customer-facing (after this PR, the demo doesn't use it; the parent app still does — so DON'T edit if it's shared with parent app)

**c) `DataProvenanceNote` component** — same skeleton as previous revisions, business-language copy:

```ts
const COPY: Record<Variant, { eyebrow: string; body: string }> = {
  real: {
    eyebrow: "What this is trained on",
    body:
      "Twenty-four of your real, completed projects. The prediction engine learned from these specific examples. " +
      "With this much data the engine is most reliable when your new project looks like past ones; " +
      "for less-common projects, expect lower confidence ratings — that's the engine being honest about its limits.",
  },
  synthetic: {
    eyebrow: "What this is trained on",
    body:
      "Five hundred generated training projects, designed to give the engine wide coverage. " +
      "This is what the engine would look like once you've collected enough real projects of your own — " +
      "wider coverage, tighter likely ranges, more consistent confidence ratings across work categories.",
  },
};
```

Mount sites (one line each, just under each `<PageHeader>`):
- `pages/demo/compare/ComparisonQuote.tsx` (already added in Commit 4) → `variant="real"`
- `pages/demo/compare/ComparisonCompare.tsx` → `variant="real"`
- `pages/demo/business/ComparisonInsights.tsx` → `variant="real"`
- `pages/demo/MachineLearningQuoteTool.tsx` (Commit 4) → `variant="synthetic"`
- `pages/demo/ml/MachineLearningCompare.tsx` → `variant="synthetic"`
- `pages/demo/ml/MachineLearningInsights.tsx` → `variant="synthetic"`

**d) Test updates:**
- `DemoHome.test.tsx` — switch from "3 cards" to "2 cards each with chip strip."
- `DemoLayout.test.tsx` — verify nothing changes; sidebar labels are already correct from PR #8.
- Delete `CompareFindSimilarTab.test.tsx` (file deleted in Commit 4).
- New: `QuoteResultPanel.test.tsx`, `quoteAdapter.test.ts`, `DataProvenanceNote.test.tsx`, `useModelMetrics.test.ts`.
- Update any test that asserted on the old "Machine Learning · Client-side" eyebrow or old "P50" string.

## Verification

```bash
cd "C:/Users/thalf/OneDrive/Documents/Matrix/matrix-quote-web-demo"
python scripts/generate_demo_assets.py
python scripts/build_demo_static.py
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

Targets: 363+ tests pass (some need updates), no lint/type errors, build succeeds.

Manual walk:

| Check | Expected |
|---|---|
| `/` | Two cards: "Today's book" / "At scale". Chip strip with three tabs each. Cards stack at 480 px. |
| `/compare/quote` | Form, submit, hero estimate + likely range + confidence chip + drivers + per-category breakdown + "Most similar past projects" list. The per-category H/M/L chips skew **toward L (lower)** — this is the overfit signature and is required. |
| `/ml/quote` | Same panel shape. Per-category chips skew **toward M and H** (synthetic models generalize better). "Most similar training rows" list at the bottom. |
| Same inputs on both tabs | The buyer can mentally compare: Real estimate may be tight to a memorized example (high variance), Synthetic estimate drawn from a wider pool (more stable). Confidence labels reflect the difference. |
| Search any rendered page for ML jargon: "P50", "R²", "MAE", "Gradient", "Pyodide", "Feature importance", lowercase "synthetic" used as jargon | No results. |
| "What this is trained on" popover | Opens on all six pages with variant-correct, business-language copy. |
| Load `/compare/quote` first | PyodideLoader stages show "Loading real-data models" only. Hitting `/ml/quote` after triggers a separate "Loading synthetic-data models" — no full reload. |

## File-modification map

| Commit | Files modified | Files added | Files deleted |
|---|---|---|---|
| 1. Train both bundles | `scripts/generate_demo_assets.py`, `scripts/build_demo_static.py` | `demo_assets/models_real/{12 joblibs, metrics_summary.csv}` (LFS), `demo_assets/models_synthetic/{12 joblibs, metrics_summary.csv}` (LFS), `frontend/public/demo-assets/models_real/`, `frontend/public/demo-assets/models_synthetic/`, `frontend/public/demo-assets/model_metrics_real.json`, `frontend/public/demo-assets/model_metrics_synthetic.json` | `demo_assets/models/*` (replaced) |
| 2. Pyodide param | `demo/pyodideClient.ts` | (types inline) | — |
| 3. Shared panel + adapter | — | `demo/quoteResult.ts`, `demo/quoteAdapter.ts`, `demo/quoteAdapter.test.ts`, `demo/featureLabels.ts`, `demo/categoryLabels.ts`, `demo/modelMetrics.ts`, `lib/projectHours.ts`, `components/quote/QuoteResultPanel.tsx`, `components/quote/QuoteResultPanel.test.tsx` | — |
| 4. Wire both Quote pages | `pages/demo/compare/ComparisonQuote.tsx`, `pages/demo/MachineLearningQuoteTool.tsx` | — | `frontend/src/demo/CompareFindSimilarTab.tsx`, `frontend/src/demo/CompareFindSimilarTab.test.tsx` (verify imports first) |
| 5. Polish | `pages/demo/DemoHome.tsx`, `pages/demo/DemoHome.test.tsx`, ~6 mount sites for `DataProvenanceNote`, ~5 page files for language sweep | `components/DataProvenanceNote.tsx`, `components/DataProvenanceNote.test.tsx` | — |

Approximate diff size: ~10 new source files, ~12 edited source files, 12 new joblib artifacts (LFS, ~30 MB total), ~1,800 LoC added net.

## Known risks & mitigations

1. **`core/models.py:train_one_op` step names may not match what the Pyodide importance-extraction code assumes.** Pre-flight: read `core/models.py` before writing the `collect_importances` Python in Commit 2. Adapt step names accordingly. No `core/` edit needed.
2. **n=24 will produce unstable train/test R² values per target.** Some targets may even produce a `train_one_op` skip if the holdout has no variance. Acceptable — the metrics CSV will show `null` or low R² and the UI will map those to "Lower confidence" honestly.
3. **Git LFS payload increases ~30 MB.** Doubling joblib count. Acceptable but flagged.
4. **Pyodide loading two model sets ≈ 60 MB heap.** Within browser limits; monitor in dev. If memory pressure shows up, add a "switch dataset" path that unloads the previous set — not needed in v1.
5. **Feature-importance direction is `"increases"` for all v1 drivers.** True direction would require partial-dependence; out of scope for v1. Acceptable for demo copy.
6. **The shared `ResultPanel` from `pages/single-quote/ResultPanel`** is still used by the parent app's flows. Don't edit it. The new `components/quote/QuoteResultPanel` is demo-only; the two coexist.

## Tier 2 — explicitly deferred

Will be addressed in a follow-up PR after Tier 1 stabilizes:

- **Cross-side compare button** ("Compare against the other side") — most-asked feature once both sides produce comparable outputs.
- **Responsive KPI grid** on Insights pages.
- **URL-persisted filter state** on Insights and Compare.
- **Footer CTA** — blocks on user-supplied destination.
