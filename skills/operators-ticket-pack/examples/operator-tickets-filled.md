# Worked examples - operator tickets (05-08)

A second filled example per operator ticket. The first example for each ticket lives inline in `templates/0X-name.md`; this file adds another scenario for reference.

---

## 05 Invoice Extractor - 12 vendor receipts from 2026

```
GOAL: Extract every line item from the PDF
invoices in ./vendor-receipts/2026/ into invoices.csv.

1. THE ORDER
   - For each invoice, extract every line item into
     a row.
   - Each row contains: invoice_id,
     line_item_description, quantity, unit_price,
     line_total, document_total.
   - One CSV file at the end, all invoices combined.

2. THE PROOF
   - For every invoice, the sum of its line_total
     values matches the document_total on the
     invoice.
   - The CSV parses cleanly with no malformed rows.
   - Every invoice in ./vendor-receipts/2026/ has at least
     one row in the output.

3. THE BOUNDARY
   - Do not modify the source PDFs.
   - Do not skip invoices because they look hard.
     Mark them for review instead.

4. THE BUDGET
   - Stop after 12 invoices have been processed.

5. THE FALLBACK
   - If line totals do not match the document total,
     mark the invoice_id in REVIEW_NEEDED.csv and
     move to the next one.
   - If an invoice cannot be parsed at all, log the
     filename and error to PARSE_ERRORS.md and
     continue.
```

**Plain-English proof gate:** Done = every invoice in `./vendor-receipts/2026/` has at least one row in `invoices.csv`, each invoice's `line_total` values sum to its `document_total`, and the CSV is well-formed.

**Note:** Receipts (gas stations, taxis, restaurants) often have tax or tip rows that are NOT line items. The checksum will fail if those rows are missed. The operator should clarify whether tax / tip rows count as line items in this batch before pasting.

---

## 06 Inbox Triage - 200 emails, Gmail JSON export

```
GOAL: Triage the emails in ./gmail-export.json into three categories: urgent, this-week,
archive.

1. THE ORDER
   - For each email, output one row in triage.csv
     with: email_id, subject, sender, category,
     one_line_reason.
   - Categories: urgent (action needed in 24h),
     this-week (action within 7 days),
     archive (no action needed).

2. THE PROOF
   - Every email in the input has exactly one row
     in triage.csv.
   - Every row has a valid category.
   - Every one_line_reason is at least 5 words long.

3. THE BOUNDARY
   - Do not delete or modify any emails in the
     source.
   - Do not reply to any email.
   - Do not categorize automated emails as urgent
     unless they explicitly require human response.

4. THE BUDGET
   - Stop after all emails processed OR after 200
     emails, whichever hits first.

5. THE FALLBACK
   - If an email has no clear category, mark it as
     this-week with "unclear, needs human review"
     in the reason.
```

**Plain-English proof gate:** Done = every email in `./gmail-export.json` has exactly one row in `triage.csv`, every category is valid, and every reason is at least 5 words.

**Operator's call:** "Urgent in 24h" - 24h from receipt or from now? "From now" is the simpler default for a backlog triage; "from receipt" is the right call for a real-time sweep. Pick one and state it.

---

## 07 Content Repurposer - keynote transcript to multi-format

```
GOAL: Take the source asset at ./transcripts/keynote-2026.txt
and produce a tweet thread, a LinkedIn post, and
a newsletter pull-quote.

1. THE ORDER
   - Read the source asset in full.
   - Identify the ONE strongest insight.
   - Produce: (a) a 5-7 tweet thread,
     (b) a single LinkedIn post 150-250 words,
     (c) a newsletter pull-quote 1-2 sentences.
   - Output as one JSON file:
     { "tweet_thread": [...],
       "linkedin_post": "...",
       "newsletter_pullquote": "..." }.

2. THE PROOF
   - The output JSON parses cleanly.
   - tweet_thread has 5-7 entries, each under 280
     characters.
   - linkedin_post is 150-250 words.
   - newsletter_pullquote is 1-2 sentences.

3. THE BOUNDARY
   - Do not use hashtags in the tweet thread.
   - Do not use em-dashes anywhere.
   - Do not invent statistics or quotes not present
     in the source.
   - Do not write in lecturer voice. Talk to one
     person.

4. THE BUDGET
   - Stop after 10 turns.

5. THE FALLBACK
   - If you cannot meet word or character counts on
     any field, output what you have and note the
     gap in REPURPOSE_NOTES.md.
```

**Plain-English proof gate:** Done = a JSON file that parses cleanly, with a 5-7 tweet thread (each tweet under 280 chars), a 150-250 word LinkedIn post, and a 1-2 sentence pull-quote.

**Note:** Long transcripts often contain throwaway statistics the speaker quoted from elsewhere. Those count as "present in the source" by the letter of the boundary but are still risky to repeat without re-verification. Flag this trade-off to the operator alongside the handoff.

---

## 08 Lead Qualifier - 200 inbound PLG signups against ICP-v4

```
GOAL: Score the inbound leads in ./leads/plg-signups-may.csv
against the criteria in ./criteria/icp-v4.md and
produce a ranked output.

1. THE ORDER
   - Read ./criteria/icp-v4.md in full. This is your
     scoring rubric.
   - For each lead in ./leads/plg-signups-may.csv, assign a fit
     score from 1 to 10 based strictly on the rubric.
   - Output ranked_leads.csv sorted by score
     descending. Columns: lead_id, name, company,
     score, one_line_reason.

2. THE PROOF
   - Every lead in the input has exactly one row in
     the output.
   - Every score is an integer between 1 and 10.
   - Every reason references at least one criterion
     from ./criteria/icp-v4.md.
   - The output is sorted by score descending.

3. THE BOUNDARY
   - Do not contact any lead.
   - Do not add criteria not in ./criteria/icp-v4.md.
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

**Plain-English proof gate:** Done = every lead has exactly one row, every score is an integer 1-10, every reason cites at least one criterion from `icp-v4.md`, and the CSV is sorted descending by score.

**Note:** PLG signups often have sparse company data (free-email signups, missing employee count). Expect a meaningful number of score-0 rows in the fallback - that is the signal, not the failure.
