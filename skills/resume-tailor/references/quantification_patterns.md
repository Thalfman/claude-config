# Quantification Patterns

Numbers turn vague claims into evidence. But a number you don't have is a fabrication. **Only quantify when the master resume contains the metric, or when the user explicitly confirms it.**

## Why quantify

| Without numbers | With numbers |
|---|---|
| "Improved system performance" | "Reduced p99 latency from 450ms to 280ms (38%) on the checkout API" |
| "Led a small team" | "Led a 5-engineer team across 3 time zones" |
| "Grew the user base" | "Grew MAUs from 12K to 38K (3.2×) in 9 months" |
| "Reduced costs" | "Cut AWS spend by $14K/month (22%) by rightsizing EC2 and consolidating Redis" |

A bullet with one good number beats three bullets without.

## What to quantify

### Scope (size of the thing you worked on)
- Team size: "5-engineer team", "team of 12 across 3 PMs and 2 designers"
- Codebase: "120K-line monorepo", "8-service backend"
- Users: "8M MAU", "320K registered users", "24 enterprise accounts"
- Revenue: "$12M ARR product line", "$2M annual budget"
- Volume: "2M API requests/day", "180K orders/month"
- Geography: "operations in 14 countries"

### Outcome (impact of what you did)
- Performance: "−38% p99 latency", "+2.4× throughput", "−72% error rate"
- Cost: "−$14K/month AWS spend", "−$280K annual contract"
- Quality: "−65% production incidents", "+18 percentage-point test coverage"
- Growth: "+3.2× MAU", "+22% conversion", "+$1.8M new ARR"
- Time: "shipped in 6 weeks vs 12-week estimate", "cut deploy time from 45 min to 8 min"
- Adoption: "82% of eligible users in 4 months", "rolled out to all 14 regions"

### Effort (your contribution at scale)
- "Reviewed 40+ PRs/week"
- "Mentored 4 junior engineers (2 promoted within 18 months — only quantify if true)"
- "Authored 3 RFCs adopted org-wide"
- "Presented to 200-person engineering all-hands"

## CAR / STAR structure

Both are scaffolds for "I did something that mattered". CAR is tighter, STAR has more setup.

**CAR — Challenge, Action, Result**
> "Backend service hit 8s p99 under load (Challenge). Profiled and rewrote the hot path with batched queries and a Redis read-through cache (Action). Drove p99 to 240ms; service handles 5× the prior peak (Result)."

**STAR — Situation, Task, Action, Result**
> "After we 4×'d traffic in 2023 (Situation), the checkout API became our top SEV-2 source (Task). I led a 3-engineer fire team, rewrote the hot path, and added a Redis cache (Action). p99 dropped 38%, SEV-2 incidents on checkout went to zero (Result)."

In a resume bullet, compress to **Action + Result** (the others are context for an interview):

> "Cut checkout API p99 latency 38% under 4× load by rewriting the hot path and adding Redis read-through cache."

## Sentence shapes

These all preserve "verb + object + measurable outcome" structure.

- `[Verb] [thing] [by metric] [via mechanism]`
  > Reduced AWS spend by $14K/month by rightsizing EC2 and consolidating Redis
- `[Verb] [thing] [from X to Y] [in Z time]`
  > Drove p99 latency from 450ms to 280ms in 8 weeks
- `[Verb] [thing], [resulting in metric]`
  > Migrated 8 services to gRPC, cutting cross-service call latency 4×
- `[Verb] [thing] [for scope], [metric outcome]`
  > Designed onboarding flow for 320K users; +18% activation, +9% Day-7 retention

## When you don't have numbers

Don't fabricate. You have three honest moves:

1. **Switch to scope.** "Improved performance for the checkout flow" → "Improved performance for the checkout flow used by 8M MAU" (if scope number is in the master).
2. **Use qualitative outcome.** "Improved performance, eliminated weekly latency-related on-call pages." Less impressive than a number, but real and specific.
3. **Drop the bullet.** If a bullet has no metric, no scope, and no qualitative outcome, it may not be earning its space.

## Number formatting

| Rule | Example |
|---|---|
| Use digits for numbers ≥ 10 | "12 services", "8 engineers" |
| Use digits for numbers with units | "5×", "8K MAU", "$2M" |
| Spell out single-digit counts in prose only | "five-person team" in prose; "5-person team" in a bullet |
| Use SI prefixes for large numbers | "8M" not "8,000,000"; "120K" not "120,000" |
| Be precise where it helps | "38% reduction" beats "around 40%" |
| Round to 2 sig figs unless precision matters | "$14K/month" not "$13,872/month" — unless the exact number is the point |
| Currency symbol before, no spaces | "$2M ARR" not "2M $" |
| Time direction explicit | "from 450ms to 280ms" or "−38%" — never just "280ms" without a baseline |

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| "Improved performance significantly" | Either provide a number from the master, or drop "significantly" — it's filler |
| "Massively reduced costs" | Same. Quantify or drop the qualifier |
| "Several engineers" | If you have a number, use it. If not, "a small team" / "the team" |
| "Approximately 50%" | If approximate, the metric is probably weak. Either get the number or change the bullet to qualitative |
| Padding precision: "23.7% improvement in throughput on Tuesdays" | Suspicious-precise. Use "≈25%" or just "25%" |
| Reusing the same number across many bullets | Probably a guess being amortized. Each metric should be unique evidence |
