# Ticket 08 - The Lead Qualifier

**Use case:** Score a batch of inbound leads on fit using your own criteria, output a ranked CSV.

## Bracket list

Collect these from the operator in one batch before filling:

- `[LEADS FILE]` - path to the leads input (e.g. `./leads/2026-q1-inbound.csv`)
- `[CRITERIA FILE]` - path to the scoring rubric (e.g. `./criteria/icp-v3.md`)

## Template (verbatim from DOO MADE)

```
GOAL: Score the inbound leads in [LEADS FILE]
against the criteria in [CRITERIA FILE] and
produce a ranked output.

1. THE ORDER
   - Read [CRITERIA FILE] in full. This is your
     scoring rubric.
   - For each lead in [LEADS FILE], assign a fit
     score from 1 to 10 based strictly on the rubric.
   - Output ranked_leads.csv sorted by score
     descending. Columns: lead_id, name, company,
     score, one_line_reason.

2. THE PROOF
   - Every lead in the input has exactly one row in
     the output.
   - Every score is an integer between 1 and 10.
   - Every reason references at least one criterion
     from [CRITERIA FILE].
   - The output is sorted by score descending.

3. THE BOUNDARY
   - Do not contact any lead.
   - Do not add criteria not in [CRITERIA FILE].
   - Do not default to a middle score (5 or 6) when
     uncertain. Pick a clear high or low and explain
     why.

4. THE BUDGET
   - Stop after all leads scored OR after 200 leads,
     whichever hits first.

5. THE FALLBACK
   - If a lead is missing data needed to score, mark
     them with score 0 and note "insufficient data:
     [FIELD]" in the reason.
```

## Plain-English proof gate

Done = every lead has exactly one row in `ranked_leads.csv`, every score is an integer 1-10, every reason cites at least one criterion from `[CRITERIA FILE]`, and the CSV is sorted descending by score.

## Why it works (from DOO MADE)

- The "every reason references a criterion" rule forces the cook to actually use the rubric instead of vibing.
- The boundary against middle-scoring blocks the most common laziness pattern: everyone gets a 6.
- The score 0 fallback separates "low fit" from "missing data" - different problems for the operator.

## Filled example - 50 inbound leads against ICP rubric

```
GOAL: Score the inbound leads in ./leads/2026-q1-inbound.csv
against the criteria in ./criteria/icp-v3.md and
produce a ranked output.

1. THE ORDER
   - Read ./criteria/icp-v3.md in full. This is your
     scoring rubric.
   - For each lead in ./leads/2026-q1-inbound.csv, assign a fit
     score from 1 to 10 based strictly on the rubric.
   - Output ranked_leads.csv sorted by score
     descending. Columns: lead_id, name, company,
     score, one_line_reason.

2. THE PROOF
   - Every lead in the input has exactly one row in
     the output.
   - Every score is an integer between 1 and 10.
   - Every reason references at least one criterion
     from ./criteria/icp-v3.md.
   - The output is sorted by score descending.

3. THE BOUNDARY
   - Do not contact any lead.
   - Do not add criteria not in ./criteria/icp-v3.md.
   - Do not default to a middle score (5 or 6) when
     uncertain. Pick a clear high or low and explain
     why.

4. THE BUDGET
   - Stop after all leads scored OR after 200 leads,
     whichever hits first.

5. THE FALLBACK
   - If a lead is missing data needed to score, mark
     them with score 0 and note "insufficient data:
     [FIELD]" in the reason.
```
