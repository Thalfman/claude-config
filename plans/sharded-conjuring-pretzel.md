# RFQ Input Normalization (Mocked Generation)

## Context

Today the intake → generate flow is shape-only: `IntakeForm` POSTs the file to `/api/upload` (validation only, no extraction), then POSTs metadata to `/api/generate`, which calls `buildMockOutput` and ignores any RFQ content. The review page renders the mock from sessionStorage.

To unblock real generation in a later phase without lighting up OpenAI yet, we need a normalization layer: a single `NormalizedRfqInput` produced from either pasted text or an uploaded `.txt` / `.md` / `.docx` / text-extractable `.pdf`, with hard size/char limits and clear UI feedback when extraction is partial or impossible (notably scanned PDFs). Generation stays mocked.

## Decisions (locked from clarifications)

- Intake UI: **tabbed toggle** — `Upload` and `Paste` tabs, exactly one source.
- Char limit behavior: **hard reject** when extracted text > `MAX_RFQ_CHARS`. No silent truncation.
- `MAX_RFQ_CHARS` default: **50000** (env-overridable, parsed with the same hardened pattern as `MAX_UPLOAD_MB`).
- PDF library: **`unpdf`**. DOCX: **`mammoth`**. TXT/MD: native `text/...` decode. No OCR. No images. No `.msg`.

## Architecture

```
IntakeForm (Upload | Paste tabs)
    │
    ├─ Upload tab → POST /api/upload (multipart) ──► returns NormalizedRfqInput
    │
    └─ Paste tab → POST /api/normalize (json text) ──► returns NormalizedRfqInput
                                                        │
                                                        ▼
       sessionStorage.setItem('rfqInput:{requestId}', NormalizedRfqInput)
                                                        │
                                                        ▼
   POST /api/generate { requestId, rfqText, source, fileName?, …form fields }
                          │
                          ▼
                 parseGenerateRequest → buildMockOutput (still mock; reads metadata only)
                          │
                          ▼
       sessionStorage.setItem('rfq:{requestId}', RfqOutput) → /review/{requestId}
```

Key shift: `/api/upload` becomes the extractor and returns the normalized payload directly. Paste path uses a sibling `/api/normalize` endpoint that runs the same length/empty checks. Both produce the **same** `NormalizedRfqInput` shape, so the form has one downstream codepath.

## Data shape

`rfq-sow-app/lib/schema.ts` — add:

```ts
export const RFQ_SOURCES = ["paste", "txt", "md", "docx", "pdf"] as const;
export type RfqSource = (typeof RFQ_SOURCES)[number];

export interface NormalizedRfqInput {
  requestId: string;          // reuses upload-route id format
  source: RfqSource;
  fileName: string | null;    // null for paste
  contentType: string | null; // null for paste
  size: number;               // bytes for files; UTF-8 byte length for paste
  rfqText: string;            // extracted/normalized text
  charCount: number;          // rfqText.length
  warnings: string[];         // human-readable extraction warnings
}
```

Add `rfqText`, `source` (optional) to `GenerateRequest`. They are passed through to `buildMockOutput` but **not consumed yet** — generation stays mocked. Adding them now keeps the wire contract stable when real generation lights up.

## Files

### New

- `rfq-sow-app/lib/limits.ts` — central `parsePositiveIntEnv(name, default, max?)` (extracted from existing `parseMaxUploadMb` so both `MAX_UPLOAD_MB` and `MAX_RFQ_CHARS` share the hardened parser). Export `getMaxUploadMb()`, `getMaxRfqChars()`, and `MAX_RFQ_CHARS_DEFAULT = 50000`.
- `rfq-sow-app/lib/extract.ts` — pure async functions:
  - `extractFromTxt(buf: ArrayBuffer): Promise<{ text: string; warnings: string[] }>` (utf-8, BOM strip, CRLF→LF)
  - `extractFromMd(buf): …` — same as txt, no markdown stripping (preserve formatting; downstream model handles it)
  - `extractFromDocx(buf)` — `mammoth.extractRawText`; warnings flow from mammoth `messages`
  - `extractFromPdf(buf)` — `unpdf.extractText`; if joined text trims to empty, throw a `PdfTextlessError` so the route can return the manual-paste message
  - `normalizeWhitespace(s)` — collapse runs of blank lines to ≤2, trim trailing space per line
- `rfq-sow-app/app/api/normalize/route.ts` — POST JSON `{ text: string }`. Trim, run length checks, build `NormalizedRfqInput` with `source: "paste"`. Reuses helpers from `extract.ts` and `limits.ts`.

### Modified

- `rfq-sow-app/app/api/upload/route.ts` — after the existing MIME/size guards, branch on detected type, call the matching `extract*` function, normalize, run length checks, build `NormalizedRfqInput`. Keep `requestId` generation as-is. Remove the mock `pathname` field from the response (callers don't use it; the new shape is the contract). Map `PdfTextlessError` → 422 with body `{ error, code: "PDF_NO_TEXT", message: "This PDF has no extractable text. Please paste the RFQ content using the Paste tab." }`. Empty-after-trim from any source → 422 `EMPTY_INPUT`.
- `rfq-sow-app/lib/validation.ts` —
  - Add `parseNormalizeRequest(body)` and an `isNormalizedRfqInput()` guard (mirrors `isRfqOutput` style; uses `RFQ_SOURCES` enum, `hasOnlyKeys`, `additionalProperties`-strict).
  - Extend `parseGenerateRequest` to accept optional `rfqText: string` (≤ `getMaxRfqChars()`) and optional `source: RfqSource`. Both stay optional so the existing mock path keeps working.
- `rfq-sow-app/app/api/generate/route.ts` — pass `rfqText`/`source` through to `buildMockOutput` (signature change only; body still hard-coded). No OpenAI call. Acceptance criterion "No OpenAI calls happen" stays trivially satisfied.
- `rfq-sow-app/components/IntakeForm.tsx` —
  - Replace single file input with `<TabGroup>`-style toggle: `Upload` (current `<input type="file">`) and `Paste` (new `<textarea>` + live char count vs `MAX_RFQ_CHARS`).
  - On submit:
    1. If Upload tab: POST file to `/api/upload` → `NormalizedRfqInput`.
    2. If Paste tab: POST `{ text }` to `/api/normalize` → `NormalizedRfqInput`.
    3. Render any `warnings` in a non-blocking yellow notice strip above the form (already styled siblings exist for ErrorBox).
    4. POST `/api/generate` with `requestId`, `rfqText`, `source`, `fileName`, plus existing form fields.
    5. Persist `RfqOutput` to sessionStorage and navigate to `/review/{requestId}` (unchanged).
  - Disable submit while empty: Upload tab requires a file; Paste tab requires non-whitespace text.

### Dependencies

`pnpm add unpdf mammoth` inside `rfq-sow-app/`. Both are pure-JS, ESM-friendly, and compatible with Next.js 16 + Turbopack root config that's already in `next.config.ts`.

## Reused existing utilities

- `parseMaxUploadMb` pattern in `app/api/upload/route.ts:13-20` → extract into `lib/limits.ts` and reuse for `MAX_RFQ_CHARS`.
- `requestId` generation pattern in `app/api/upload/route.ts` → keep, share between both routes.
- `hasOnlyKeys`, `isString`, `isStringArray`, enum-narrowing pattern in `lib/validation.ts:11-100` → reuse for `isNormalizedRfqInput` and the new `parseNormalizeRequest`.
- `OUTPUT_MODES` and the existing `parseGenerateRequest` envelope → extend, do not rewrite.
- `ErrorBox` component already used in `IntakeForm.tsx:163` → reuse for fatal errors; add a sibling `WarningBox` (small new component) for the soft `warnings[]` list.

## Acceptance criteria mapping

| Criterion | How met |
|---|---|
| Pasted text works | `/api/normalize` happy path; Paste tab in form |
| TXT works | `extractFromTxt` in upload route |
| MD works | `extractFromMd` |
| DOCX works | `extractFromDocx` via mammoth |
| Text-based PDF works | `extractFromPdf` via unpdf |
| Scanned/unreadable PDF fails gracefully | `PdfTextlessError` → 422 `PDF_NO_TEXT` with paste-instead message rendered in `IntakeForm` |
| Mock output still renders | `buildMockOutput` body unchanged; only signature widens |
| No OpenAI calls happen | No client added; `generate/route.ts` keeps the same mock path |
| Reject unsupported file types | Existing MIME/ext allowlist in upload route stays the gate |
| Reject empty input | Post-extract trim check in upload + normalize routes → 422 `EMPTY_INPUT` |
| Enforce `MAX_UPLOAD_MB` | Existing header + size guards retained |
| Enforce `MAX_RFQ_CHARS` | Hard reject on `rfqText.length > getMaxRfqChars()` in both routes → 422 `RFQ_TOO_LONG` |
| Show extraction warnings | `WarningBox` rendered above form when `NormalizedRfqInput.warnings.length > 0` |

## Verification

1. `pnpm install` then `pnpm typecheck` and `pnpm build` from `rfq-sow-app/` — both must pass cleanly with the widened types.
2. `pnpm dev` and exercise the full matrix from the browser:
   - Paste tab: ~200-char paste → 200 OK, mock renders.
   - Paste tab: 60_000-char paste → 422 `RFQ_TOO_LONG`, error visible.
   - Paste tab: empty / whitespace → 422 `EMPTY_INPUT`.
   - Upload tab: a `.txt` (sample short RFQ) → mock renders.
   - Upload tab: a `.md` → mock renders.
   - Upload tab: a real `.docx` → mock renders; mammoth warnings (if any) shown in `WarningBox`.
   - Upload tab: a born-digital `.pdf` (e.g. an exported text PDF) → mock renders.
   - Upload tab: a scanned `.pdf` (e.g. image-only) → 422 `PDF_NO_TEXT` with the manual-paste message.
   - Upload tab: `.png` → 415 from existing allowlist.
   - Upload tab: file > `MAX_UPLOAD_MB` → 413.
3. Network tab: confirm exactly two requests per submit (`/api/upload` or `/api/normalize`, then `/api/generate`). No `api.openai.com` requests in any case.
4. Type-guard sanity: `curl -X POST /api/normalize -d '{"text":""}' -H 'content-type: application/json'` returns 422; same with junk JSON returns 400.
5. Re-run codex review on the resulting PR (per memory `feedback_codex_review_loop.md`) until clean.

## Out of scope (per requirements)

OCR, image inputs, `.msg` parsing, server-side persistence, database, OpenAI integration. Do not add any of these.
