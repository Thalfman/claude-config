# Ticket 05 - The Invoice Extractor

**Use case:** Pull line items from PDF invoices into a CSV, with a checksum validator that catches extraction errors.

## Bracket list

Collect these from the operator in one batch before filling:

- `[FOLDER PATH]` - the folder containing the invoice PDFs (e.g. `./invoices/2026-q1/`)
- `[N]` - the number of invoices to process (or the total count in the folder)

## Template (verbatim from DOO MADE)

```
GOAL: Extract every line item from the PDF
invoices in [FOLDER PATH] into invoices.csv.

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
   - Every invoice in [FOLDER PATH] has at least
     one row in the output.

3. THE BOUNDARY
   - Do not modify the source PDFs.
   - Do not skip invoices because they look hard.
     Mark them for review instead.

4. THE BUDGET
   - Stop after [N] invoices have been processed.

5. THE FALLBACK
   - If line totals do not match the document total,
     mark the invoice_id in REVIEW_NEEDED.csv and
     move to the next one.
   - If an invoice cannot be parsed at all, log the
     filename and error to PARSE_ERRORS.md and
     continue.
```

## Plain-English proof gate

Done = every invoice in `[FOLDER PATH]` has at least one row in `invoices.csv`, the CSV parses cleanly, and for each invoice the `line_total` values sum to the `document_total`.

## Why it works (from DOO MADE)

- The checksum proof gate (line items sum to document total) is deterministic and catches extraction errors instantly.
- The boundary against skipping invoices forces every input to be accounted for, either in the CSV or the review pile.
- The fallback splits failures into "needs review" vs. "could not parse" - different problems for the operator to handle.

## Filled example - 47 supplier invoices

```
GOAL: Extract every line item from the PDF
invoices in ./invoices/2026-q1/ into invoices.csv.

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
   - Every invoice in ./invoices/2026-q1/ has at least
     one row in the output.

3. THE BOUNDARY
   - Do not modify the source PDFs.
   - Do not skip invoices because they look hard.
     Mark them for review instead.

4. THE BUDGET
   - Stop after 47 invoices have been processed.

5. THE FALLBACK
   - If line totals do not match the document total,
     mark the invoice_id in REVIEW_NEEDED.csv and
     move to the next one.
   - If an invoice cannot be parsed at all, log the
     filename and error to PARSE_ERRORS.md and
     continue.
```
