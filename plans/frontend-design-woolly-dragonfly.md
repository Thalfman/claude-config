# Design Critique — Matrix Quote Web Frontend

> Scope: Full visual-design review of the React frontend (`frontend/src/`) as merged on 2026-04-17 via PR #4. Not an implementation plan — this is a report.

## Context

The redesign shipped 7 plans: design-tokens-only Tailwind config, editorial typography (Barlow Condensed display + Inter + JetBrains Mono), a `[data-theme="dark"]` overlay, dark-mode PDF polish, and cleanup of legacy `brand/navy/steel/accent` aliases (commits `cb14d31`, `40e886e`). Goal of this critique: surface what's working, what's inconsistent, and what to tighten before the next functional slice (batch quotes, admin wiring) lands.

Files read for this critique (live code, not design drafts):
- [frontend/tailwind.config.js](frontend/tailwind.config.js)
- [frontend/src/styles/globals.css](frontend/src/styles/globals.css)
- [frontend/src/components/Layout.tsx](frontend/src/components/Layout.tsx)
- [frontend/src/components/PageHeader.tsx](frontend/src/components/PageHeader.tsx)
- [frontend/src/pages/SingleQuote.tsx](frontend/src/pages/SingleQuote.tsx)
- [frontend/src/pages/single-quote/QuoteForm.tsx](frontend/src/pages/single-quote/QuoteForm.tsx)
- [frontend/src/pages/single-quote/HeroEstimate.tsx](frontend/src/pages/single-quote/HeroEstimate.tsx)
- [frontend/src/pages/single-quote/ResultTabs.tsx](frontend/src/pages/single-quote/ResultTabs.tsx)
- [frontend/src/pages/single-quote/tabs/EstimateTab.tsx](frontend/src/pages/single-quote/tabs/EstimateTab.tsx)

---

## Overall Impression

The frontend reads as **clean, editorial, and confidently minimal** — a rare look for an internal B2B quoting tool. Barlow Condensed display headings paired with tabular-num monospace estimates give the numbers the weight they deserve; the navy (`ink #0D1B2A`) + paper (`#F6F4EF`) + amber (`#F2B61F`) + teal (`#1F8FA6`) palette reads as grown-up industrial, not SaaS-generic. The sidebar + breadcrumb strip + sticky result aside is a solid information-architecture choice for a long-form estimator.

The biggest opportunity isn't visual — the design system has a **pair of token bugs** (one dead gradient, one large family of dead dark-mode utilities) that will silently drift the UI away from its own tokens as new code is added. Fixing these is the highest-leverage polish in the codebase.

---

## Usability

| # | Finding | Severity | Recommendation |
|---|---------|----------|----------------|
| U1 | [QuoteForm.tsx](frontend/src/pages/single-quote/QuoteForm.tsx) has **6 numbered sections and ~25 fields** above the submit button. Section 05's `<details>` "Advanced indices" and Section 06's single cost field tack on extra scroll depth before the CTA. | 🟡 Moderate | Consider: collapse Sections 04–06 into a single "Product & complexity" tab; or move the submit button to a sticky footer that travels with the scrolled page (currently only the result aside is sticky). |
| U2 | The "Populate with last quote" affordance ([QuoteForm.tsx:41-48](frontend/src/pages/single-quote/QuoteForm.tsx:41)) is a small teal underline text-button floated top-right of the form. It's the single most useful shortcut on the page and it's invisible. | 🟡 Moderate | Promote it: pill with icon, next to a "Reset" button at the top of the form — or a "Last quote" chip in the PageHeader chips slot when `sessionStorage` has a payload. |
| U3 | The `prompt()` calls in [SingleQuote.tsx:105, :107, :138](frontend/src/pages/SingleQuote.tsx:105) are native browser dialogs used to collect **scenario name, project name, and PDF project name**. These block the thread, can't be branded, and don't persist focus/scroll position. | 🔴 Critical | Replace with an in-app modal/drawer primitive. This is the single most jarring UX seam right now — the rest of the app is polished, then `alert()`-era dialogs appear. |
| U4 | On `/` the result panel empty state ([ResultPanel.tsx](frontend/src/pages/single-quote/ResultPanel.tsx)) and the "models not trained" empty state ([SingleQuote.tsx:76-80](frontend/src/pages/SingleQuote.tsx:76)) both render as plain text cards with no icon or illustration. | 🟢 Minor | Add a small geometric eyebrow mark or an icon set for empty states so the page doesn't feel like "nothing happened yet." |
| U5 | The "compare to your quoted hours" toggle ([QuoteForm.tsx:314-321](frontend/src/pages/single-quote/QuoteForm.tsx:314)) is a plain underlined text button tucked between the last section and the submit row. Users won't find it. | 🟢 Minor | Integrate as an optional collapsible section with a real step badge (e.g., "07 · Actual vs. estimated") or move behind a settings-style toggle inside Section 02. |
| U6 | `useHotkey` binds both `Meta+Enter` and `Ctrl+Enter` ([SingleQuote.tsx:62-63](frontend/src/pages/SingleQuote.tsx:62)) but the hint text only renders at `md:` and above ([QuoteForm.tsx:359-368](frontend/src/pages/single-quote/QuoteForm.tsx:359)). Desktop-only hint is fine, but the hint never mentions `Cmd` for macOS users. | 🟢 Minor | Detect platform or show "⌘/Ctrl + Enter" in the kbd hint. |

---

## Visual Hierarchy

**What draws the eye first:** On `/`, the display-hero page title "Single Quote" (text-4xl Barlow Condensed, 600 weight) is rightly the first thing, followed by the sticky **HeroEstimate** numeric (56px tabular-nums in the result aside). This is correct — the estimated hours *are* the product.

**Reading flow:**
- Sidebar: Logo → section labels → nav items → model status. Clean top-to-bottom.
- Main: Breadcrumb → PageHeader → 2-column split (form left / result right). The 3fr/2fr grid gives the form visual priority before results exist, which is correct for a *pre-estimate* state — and the sticky aside keeps results present once generated.

**Emphasis issues:**
- **Step badges `01`–`06`** ([Section.tsx](frontend/src/components/Section.tsx), rendered in [QuoteForm.tsx:51, :113, :145, :178, :249, :308](frontend/src/pages/single-quote/QuoteForm.tsx:51)) use `text-[11px]` monospace in a 24-px pill. They're quiet enough that the *title* carries the section — which is fine — but six identical badges give the form a flat rhythm. No section feels more important than another.
- **Tab underline** ([ResultTabs.tsx:49](frontend/src/pages/single-quote/ResultTabs.tsx:49)) uses `border-teal` for the active tab. Good — teal reads as the interactive/accent color throughout the app. But the scenario count badge ([line 57](frontend/src/pages/single-quote/ResultTabs.tsx:57)) is also `bg-teal text-white` — two teal signals in the same header row. Consider using `bg-amber` or `bg-tealSoft` for the count badge to reduce redundancy.
- **Confidence dots** in [HeroEstimate.tsx:43-53](frontend/src/pages/single-quote/HeroEstimate.tsx:43) are 6px (`w-1.5 h-1.5`) — so small they read as decoration, not a visualization. At typical viewing distance the filled vs. empty dots are hard to count.

**Whitespace:** Generous on section outers (`mb-8`), snug within (`gap-3`/`gap-4`). PageHeader's `pb-6 mb-8` gives pages a clear masthead beat. Good.

---

## Consistency

| Element | Issue | File:line | Recommendation |
|---------|-------|-----------|----------------|
| **Undefined color token** `navy-900` | Gradient on HeroEstimate references `navy-900/[0.03]` but the Tailwind config only defines `ink` — this produces **zero CSS output**, so the card has no gradient at all. | [HeroEstimate.tsx:31](frontend/src/pages/single-quote/HeroEstimate.tsx:31) vs. [tailwind.config.js:7](frontend/tailwind.config.js:7) | Change to `from-ink/[0.03]` (the intended token) or drop the gradient. |
| **Dead `dark:*-dark` utilities** | `darkMode: "class"` in config ([tailwind.config.js:2](frontend/tailwind.config.js:2)) triggers on the `.dark` class, but `ThemeToggle` sets `data-theme="dark"` on `<html>`. AND the referenced colors (`ink-dark`, `muted-dark`, `border-dark`, `bg-dark`) are not defined. These utilities emit no CSS in either case. | Widespread — sample in [EstimateTab.tsx:33, :36, :46](frontend/src/pages/single-quote/tabs/EstimateTab.tsx:33), [ResultTabs.tsx:36](frontend/src/pages/single-quote/ResultTabs.tsx:36), [QuoteForm.tsx:355, :359, :361, :365](frontend/src/pages/single-quote/QuoteForm.tsx:355) | Decide one path: either (a) switch Tailwind `darkMode` to `["selector", '[data-theme="dark"]']` and add the `-dark` tokens to the palette, or (b) remove all `dark:*-dark` utilities — dark mode already works entirely via the `dark-mode.css` overlay remapping existing tokens. Option (b) is simpler and matches the "design-tokens-only" intent; option (a) gives component authors more control. Don't leave it half-wired. |
| **Two conflicting dark-mode mechanisms** | The app uses `[data-theme="dark"]` CSS variable overlay (`dark-mode.css`) **and** attempts `dark:` utilities. Future contributors will write `dark:` variants that silently no-op. | Whole codebase | Document the chosen approach in [frontend/CLAUDE.md](frontend/CLAUDE.md) or a design-system README. Whichever option from the row above is picked, lint for the other. |
| **Spacing scale drift** | Gaps across similar layouts vary: `gap-3`, `gap-4`, `gap-6`, `space-y-1.5`, `space-y-2`, `space-y-2.5`, `space-y-3`, `space-y-4` all appear on the Single Quote page alone. | [QuoteForm.tsx](frontend/src/pages/single-quote/QuoteForm.tsx), [ResultPanel.tsx](frontend/src/pages/single-quote/ResultPanel.tsx), tabs/ | Collapse to 3 step sizes (tight = `gap-2`, default = `gap-4`, section = `gap-8`). Treat anything else as a smell. |
| **Button styles are ad-hoc** | There is no `<Button>` primitive. The submit button at [QuoteForm.tsx:342-348](frontend/src/pages/single-quote/QuoteForm.tsx:342) inlines a 9-class string; "Populate with last quote", "Reset form", and "Hide/Optional: compare" all use different text-button treatments. | Form and result panel | Add `Button` (variants: primary=teal, secondary=outline, ghost=text). Each ad-hoc variant is another token-drift surface. |
| **`hairline` class vs. `border-line`** | Both do the same thing (#E5E1D8 border). `hairline` is a custom class, `border-line` is a Tailwind utility. They coexist — `hairline` in [PageHeader.tsx:26](frontend/src/components/PageHeader.tsx:26), `border-line` and its alias `border-border` elsewhere. | Widespread | Pick one. The Tailwind utility wins for grep-ability and no CSS-authoring cost. |
| **Eyebrow color drift** | PageHeader eyebrow is `text-teal` ([PageHeader.tsx:28](frontend/src/components/PageHeader.tsx:28)). HeroEstimate eyebrow is `text-muted` ([HeroEstimate.tsx:32](frontend/src/pages/single-quote/HeroEstimate.tsx:32)). Admin login eyebrow is `muted` too ([AdminLogin.tsx](frontend/src/pages/AdminLogin.tsx)). | Page vs. card vs. form | Decide semantic: eyebrows at the *page* level = teal accent; eyebrows on *cards within* = muted. Both are defensible — just document it. Currently the asymmetry reads as oversight. |

---

## Accessibility

| Check | Finding | Status |
|-------|---------|--------|
| **Color contrast — body text** | `text-ink` (#0D1B2A) on `bg-paper` (#F6F4EF) ≈ 15.4:1. | 🟢 Pass (AAA) |
| **Color contrast — muted text** | `text-muted` (#5A6573) on `bg-surface` (#FFFFFF) ≈ 5.3:1. | 🟢 Pass (AA) |
| **Color contrast — muted text on paper** | `text-muted` (#5A6573) on `bg-paper` (#F6F4EF) ≈ 4.9:1. | 🟢 Pass (AA) |
| **Color contrast — teal button text** | `text-white` on `bg-teal` (#1F8FA6) ≈ 3.5:1. | 🟡 Fails AA for normal text (<4.5:1); passes AA for large text. Submit button uses `text-sm` (14px) which is borderline. |
| **Color contrast — success/danger text** | `text-success` (#2F8F6F) on `bg-surface` ≈ 3.3:1. | 🟡 Fails AA for normal text. Used as body in model-status pill ([Layout.tsx:110](frontend/src/components/Layout.tsx:110)) and PageHeader chips. |
| **Text size** | Multiple labels and eyebrows at `text-[10px]` and `text-[11px]` — below the conventional 12px minimum. Examples: sidebar group labels ([Layout.tsx:75](frontend/src/components/Layout.tsx:75)), model-status eyebrow ([Layout.tsx:97](frontend/src/components/Layout.tsx:97)), PageHeader eyebrow ([PageHeader.tsx:28](frontend/src/components/PageHeader.tsx:28)), tab badge ([ResultTabs.tsx:57](frontend/src/pages/single-quote/ResultTabs.tsx:57)), kbd hints ([QuoteForm.tsx:361, :365](frontend/src/pages/single-quote/QuoteForm.tsx:361)). | 🟡 Readable for sighted power users at typical viewing distance, but risky for anyone zoomed out or with mild low vision. Consider 11px minimum for eyebrows; 12px for any value/content. |
| **Touch targets** | Tab buttons `py-2.5` + `px-3 sm:px-4` ≈ 36px tall. Submit button `py-2.5 px-6` ≈ 40px. Sidebar nav items `py-2 px-3` ≈ 32px. | 🟡 Sidebar links are below the 44×44 Apple/WCAG AAA recommendation, though this is a desktop-sidebar context. |
| **Focus ring** | Global `:focus-visible { outline: 2px solid #1F8FA6; outline-offset: 2px }` in [globals.css:10-14](frontend/src/styles/globals.css:10). | 🟢 Clear and consistent. Good. |
| **Form labels** | `Field` wraps `<label>` around label text + child input. Because the input is passed as `children`, it's inside the `<label>`, so implicit association works — but only one input per Field. | 🟢 Pass (implicit). Would fail if a Field ever contained two inputs. |
| **Switch is a checkbox, labeled "Switch"** | The Switch component ([Switch.tsx](frontend/src/components/Switch.tsx)) is a styled checkbox with no toggle affordance — no thumb, no track. Used 7 times in [QuoteForm.tsx](frontend/src/pages/single-quote/QuoteForm.tsx) for project flags. | 🟡 Functionally a checkbox — which is fine semantically. But calling the component "Switch" invites future contributors to use it as a visual switch without redesigning. |
| **Animated "ping" on model-status dot** | [Layout.tsx:100-102](frontend/src/components/Layout.tsx:100) — indefinite `animate-ping`. | 🟡 Can distract; no `motion-reduce:` variant. ResultSkeleton correctly uses `motion-safe:animate-pulse`; adopt the same pattern here. |
| **`aria-hidden` on decorative progress bars** | [EstimateTab.tsx:43](frontend/src/pages/single-quote/tabs/EstimateTab.tsx:43) and similar. | 🟢 Good. |

---

## What Works Well

- **Typography pairing is genuinely distinctive.** Barlow Condensed display + Inter body + JetBrains Mono for tabular numbers is a thoughtful choice for an estimator; the large display number on the HeroEstimate is the right editorial centerpiece and better-looking than the typical "KPI card" pattern.
- **The sidebar is clean and restrained.** `bg-ink` with white text, `border-l-2 border-amber` on the active link, and the model-status indicator at the bottom of the rail — no clutter, no bucket icons, no nested collapsibles. This is a rare sidebar that knows what it is.
- **The page frame is confident.** Breadcrumb strip + PageHeader + max-width 1400px container feels editorial rather than dashboard-y. The `pb-6 mb-8 border-b hairline` on PageHeader is a tiny detail that gives every page the same masthead beat.
- **Density system is an honest mechanism.** CSS custom properties `--density-y` / `--density-x` with `.density-compact` / `.density-comfy` modifier classes is a much better design than a wrapping theme provider. It will age well.
- **PDF template matches the web aesthetic.** System-font-only, exact hex values, amber + navy stripes on cover — the exported PDF is recognizably the same brand as the web app. Few internal tools achieve this.
- **Progressive disclosure via `<details>` for advanced indices** ([QuoteForm.tsx:277-305](frontend/src/pages/single-quote/QuoteForm.tsx:277)) is the right choice and uses the native element rather than re-implementing.
- **Sticky result aside.** `lg:sticky lg:top-6 self-start` ([SingleQuote.tsx:178](frontend/src/pages/SingleQuote.tsx:178)) is exactly right for a long form.

---

## Priority Recommendations

1. **Fix the two token bugs first.** They're cheap and they're undermining the design-tokens-only promise.
   - `from-navy-900/[0.03]` → `from-ink/[0.03]` in [HeroEstimate.tsx:31](frontend/src/pages/single-quote/HeroEstimate.tsx:31).
   - Decide the dark-mode mechanism and enforce it — either add the `-dark` tokens + switch Tailwind selector to `[data-theme="dark"]`, OR strip every `dark:*-dark` utility (recommended; the CSS overlay already does the work). A simple `grep` of `dark:` in `frontend/src` returns the worklist.

2. **Replace `prompt()` dialogs.** Build one modal primitive; wire it to "Save scenario", "Export PDF", and any future name/note entries. This is the single highest-impact polish in the app today — it flips the most broken-looking interaction into something the rest of the UI deserves.

3. **Add a `Button` primitive with three variants** (primary/teal, secondary/outline, ghost/text). Migrate the submit button, the reset-form link, the populate-last-quote link, and the "Optional: compare" toggle. This is the second-biggest consistency lever after the dark-mode cleanup.

4. **Tighten form hierarchy on Single Quote.** 6 numbered sections is a lot of visual noise for what's functionally 4 groups (Classification, Scale, Controls, Product & complexity) + 1 leaf (Cost) + 1 advanced toggle. Either merge down, or let some sections collapse by default. Promote "Populate with last quote" while you're in there.

5. **Accessibility sweep on small text.** Audit every `text-[10px]` and `text-[11px]` use — keep them for true eyebrows only, lift labels and any content to 12px minimum. Add `motion-reduce:` variant to the `animate-ping` model-status dot.

6. **Document the design system.** A short [frontend/DESIGN.md](frontend/DESIGN.md) covering: (a) the token list and what each semantic name is for, (b) the dark-mode mechanism and how to test it, (c) the spacing/density scales, (d) when to use eyebrow-teal vs. eyebrow-muted. Right now the system is mostly in people's heads.

---

## Verification

This is a critique, not an implementation — nothing to verify programmatically. If items are acted on, verify each by:

- **Token bugs:** `grep -rn "navy-900" frontend/src` should return nothing; `grep -rn "dark:.*-dark" frontend/src` should match the chosen convention.
- **Dialog replacement:** walk Single Quote → Estimate hours → Save scenario / Export PDF → confirm in-app modal, ESC to dismiss, focus returns to triggering button.
- **Button primitive:** start dev server, visit `/`, inspect element on each button, confirm all now render the shared component (check className contains a shared `btn-` fragment or React devtools shows `<Button>`).
- **Accessibility:** run [axe DevTools](https://www.deque.com/axe/devtools/) on `/`, `/batch`, `/quotes`, `/performance`, `/insights`, `/admin`; confirm contrast and text-size violations drop to zero.
- **Design-system doc:** new contributors should be able to answer "how do I add a new status color?" and "how do I style a new page" from the doc alone.
