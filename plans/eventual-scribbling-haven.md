# Plan: Upgrade rfq-sow-app to Demo-Only Showcase

## Context

The repo already contains `rfq-sow-app/` — a Next.js App Router scaffold that is *functionally* demo-only today: `/api/generate` returns a hardcoded mock, `lib/openai.ts` is a stub returning `{ ready: false }`, and no OpenAI / Vercel Blob / DB packages are installed in `package.json`. The schema in `lib/schema.ts` already matches the demo spec character-for-character (including `ROM_DISCLAIMER` and `MAX_RFQ_CHARS = 60_000`).

What is **missing** to satisfy `rfq_sow_app_demo_only_no_api_showcase_plan.md`:

- A demo scenario selector with five canned RFQs that vary the mocked output.
- The mock generator has no scenario / project-type variation — every RFQ produces the same controls-upgrade content.
- No download buttons for Markdown / JSON / Reviewed-Example exports (though `lib/markdown.ts` exists).
- No `localStorage` draft recovery on the review page.
- No visible Demo Mode badge or top-of-page disclaimer.
- No `docs/` folder with demo script + future-integration notes.
- Reviewed-example Markdown format is not yet implemented.

User confirmed three things:
1. **Upgrade `rfq-sow-app` in place** — no rename, no fork.
2. **Keep PDF/DOCX/TXT/MD upload working** — the existing `mammoth` + `unpdf` extraction is a feature, not a deviation worth downgrading.
3. **Keep `/api/generate`, `/api/upload`, `/api/save-reviewed`** — they call no external services and the abstraction is already in place.

The plan therefore extends the existing app rather than rewriting it. Spec deviations (real PDF/DOCX extraction; server routes) are documented in the README, not removed.

## Approach

Add scenarios + downloads + draft recovery + polish on top of the existing scaffold. Move mock generation out of the route handler into `lib/mockGenerate.ts` so it varies by `scenarioId`, `projectType`, `outputMode`, and `materialsCost`. Wire scenario selection through `IntakeForm`. Add three new components (`DemoBadge`, `DisclaimerBox`, `DownloadButton`), one new lib (`lib/demoScenarios.ts`, `lib/localStorage.ts`, `lib/downloads.ts`), and three docs.

## Files

### New files

- `rfq-sow-app/lib/demoScenarios.ts` — exports `DEMO_SCENARIOS: DemoScenario[]` with five entries (`simple-cell`, `controls-upgrade`, `robot-integration`, `ambiguous-rfq`, `conveyor-handling`). Each has `id`, `label`, `projectType`, `sampleRfqText` (~600–1200 chars), and a `mockProfile` flag (`clear` | `complex` | `ambiguous`) consumed by `mockGenerate.ts`.
- `rfq-sow-app/lib/mockGenerate.ts` — exports `buildMockOutput(req: GenerateRequest): RfqOutput`. Migrate the existing `buildMockOutput` from `app/api/generate/route.ts` and add scenario-aware branching: `ambiguous` profile → more `missing_information`, more `priority: "high"` questions, `confidence: "low"`, conservative SOW; `complex` profile → more `risk_flags` and `ask_to: "engineering"` questions; `clear` profile → fewer unknowns. Vary `scope_summary` + `known_requirements` per `projectType`. Always include `ROM_DISCLAIMER`.
- `rfq-sow-app/lib/localStorage.ts` — exports `saveDraft(requestId, output, reviewerNotes)`, `loadDraft(requestId)`, `clearDraft(requestId)`. Namespaced as `rfq-draft:${requestId}`. Browser-only guard with `typeof window !== 'undefined'`.
- `rfq-sow-app/lib/downloads.ts` — exports `downloadText(filename, content, mime)`. Creates a Blob, anchors it, revokes the object URL.
- `rfq-sow-app/components/DemoBadge.tsx` — small server component, "Demo Mode · mocked output · no external APIs".
- `rfq-sow-app/components/DisclaimerBox.tsx` — server component, internal-use + mocked-output + ROM-not-a-quote text.
- `rfq-sow-app/components/DownloadButton.tsx` — client component that takes `{ filename, getContent, mime, label }` and calls `downloadText` on click.
- `rfq-sow-app/docs/demo-script.md` — 5-minute walkthrough.
- `rfq-sow-app/docs/future-openai-integration.md` — where the OpenAI Responses API will plug in (`/api/generate` swap-in for `buildMockOutput`).
- `rfq-sow-app/docs/future-vector-store-setup.md` — KB ingestion plan and what *not* to upload.

### Modified files

- `rfq-sow-app/lib/schema.ts` — add `scenarioId?: string` to `GenerateRequest`. Add `DEMO_SCENARIO_IDS` const tuple for validator. Keep everything else.
- `rfq-sow-app/lib/validation.ts` — pass-through `scenarioId` in `parseGenerateRequest`; reject unknown ids.
- `rfq-sow-app/lib/markdown.ts` — add `buildReviewedExampleMarkdown(output, reviewerNotes)` matching the spec template (Tags / Original RFQ Summary / AI Draft Issue / Manager Correction / Approved Language / Lesson) with the "Demo export only" footer.
- `rfq-sow-app/app/api/generate/route.ts` — delete the inline `buildMockOutput` and `emptyDraftSow`; import from `lib/mockGenerate.ts`. Pass `scenarioId` through.
- `rfq-sow-app/components/IntakeForm.tsx` — add a "Demo scenario" card above the RFQ input card: `<select>` over `DEMO_SCENARIOS` + a "Load sample RFQ" button that sets `pasteText`, `projectName`, `customerName`, `projectType`. Send `scenarioId` in the `/api/generate` payload.
- `rfq-sow-app/components/ReviewEditor.tsx` — add a sticky toolbar (or inline buttons) for: Copy Summary / Copy Clarifying Questions / Copy Draft SOW (use existing `CopyButton`); Download Markdown / Download JSON / Download Reviewed Example (use new `DownloadButton`); Save Draft Locally / Load Draft / Clear Draft.
- `rfq-sow-app/app/layout.tsx` — render `<DemoBadge />` in the top bar; render `<DisclaimerBox />` near the page footer or top.
- `rfq-sow-app/app/page.tsx` — keep intake form; surface `DisclaimerBox` once.
- `rfq-sow-app/.env.example` — add `NEXT_PUBLIC_APP_MODE=demo`; comment-out OpenAI/Blob vars with a note that they belong to the future-integration phase.
- `rfq-sow-app/README.md` — reframe top section as "demo-only, no external APIs"; document the spec deviations explicitly (server routes used; PDF/DOCX extraction is real); link to `docs/demo-script.md` and the two future-integration docs.

### Reused (do not touch unless necessary)

- `lib/markdown.ts` — already converts `RfqOutput` → Markdown; only add the reviewed-example builder.
- `lib/extract.ts` — keep PDF/DOCX/TXT/MD extraction.
- `lib/blob.ts` — already a mock with null URLs; leave it.
- `components/CopyButton.tsx`, `components/SectionEditor.tsx`, `components/ClarifyingQuestionsEditor.tsx`, `components/FileUpload.tsx`, `components/ErrorBox.tsx`, `components/LoadingState.tsx` — reuse as-is.
- `app/api/upload/route.ts` — keep; the file collision guard and size limits are already correct.
- `app/api/save-reviewed/route.ts` — keep as a no-op stub.

## Verification

End-to-end manual demo flow (must all pass):

1. `cd rfq-sow-app && npm run dev` → http://localhost:3000 loads with the Demo Mode badge visible and disclaimer text rendered.
2. Select **Ambiguous RFQ** scenario → click *Load sample RFQ* → paste box populates, project name/customer/type prefill.
3. Click *Generate* → review page renders. Verify the output has noticeably *more* `missing_information` and `priority: "high"` clarifying questions than the **Simple Automation Cell** scenario (run that as a contrast).
4. Switch to **Robot Integration** → confirm `risk_flags` count increases and at least one question has `ask_to: "engineering"`.
5. Edit a SOW assumption → click *Save Draft Locally* → reload the page → click *Load Draft* → edit persists.
6. Click *Download Markdown* → file opens with all sections + ROM disclaimer.
7. Click *Download JSON* → `JSON.parse` succeeds; matches `RFQ_OUTPUT_JSON_SCHEMA` shape.
8. Click *Download Reviewed Example* → Markdown contains `demo_source: yes`, the "Demo export only" footer, and the six headed sections.
9. Upload a `.pdf` and a `.docx` from the project root or any sample file → extraction completes; generated output uses extracted text length in `model_notes`.
10. `npm run build` succeeds; `npm run typecheck` (or `tsc --noEmit`) clean.
11. Search for forbidden strings — `rg -n 'openai\\.' rfq-sow-app/app rfq-sow-app/components rfq-sow-app/lib --type=ts` returns only `lib/openai.ts` (the stub) and the README/docs. No active OpenAI client code path.
12. README's "Spec deviations" section calls out (a) server routes retained, (b) real PDF/DOCX extraction retained, with rationale.
