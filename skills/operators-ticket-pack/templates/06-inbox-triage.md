# Ticket 06 - The Inbox Triage Ticket

**Use case:** Categorize a batch of emails into urgent / this-week / archive with a one-line reason per email.

## Bracket list

Collect these from the operator in one batch before filling:

- `[EMAIL EXPORT FILE OR FOLDER]` - path to the email export (e.g. `./inbox-export.mbox`, `./emails.csv`, `./emails/`)

The operator must also resolve two ambiguities before the ticket is paste-ready:

1. **Email export format** - MBOX, CSV, JSON, IMAP dump? The PDF does not specify; the downstream agent needs to know.
2. **"Urgent in 24h"** - 24h from email receipt time, or 24h from now? Pick one. "From now" is the simpler default for a batch triage.

## Template (verbatim from DOO MADE)

```
GOAL: Triage the emails in [EMAIL EXPORT FILE OR
FOLDER] into three categories: urgent, this-week,
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

## Plain-English proof gate

Done = every email in the input has exactly one row in `triage.csv`, every category is valid (urgent / this-week / archive), and every `one_line_reason` is at least 5 words long.

## Why it works (from DOO MADE)

- The minimum word count on the reason field forces the cook to think about each email instead of plating "looks important" for every row.
- The boundary against marking automated emails as urgent prevents the most common false-positive pattern.
- The default-to-this-week fallback guarantees forward progress without overcommitting to "urgent".

## Filled example - 200 emails, MBOX export

```
GOAL: Triage the emails in ./inbox-export.mbox into three categories: urgent, this-week,
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
