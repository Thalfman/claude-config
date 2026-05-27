# Ticket 07 - The Content Repurposer

**Use case:** Turn one source asset into three distinct content formats with format validation.

## Bracket list

Collect these from the operator in one batch before filling:

- `[SOURCE FILE]` - path to the source asset (e.g. `./blog/2026-05-ticket-pack.md`, `./transcripts/keynote.txt`)

## Template (verbatim from DOO MADE)

```
GOAL: Take the source asset at [SOURCE FILE]
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

## Plain-English proof gate

Done = a JSON file that parses cleanly, with a 5-7 tweet thread (each tweet under 280 chars), a 150-250 word LinkedIn post, and a 1-2 sentence pull-quote.

## Why it works (from DOO MADE)

- The JSON structure with hard length validators makes the proof gate deterministic.
- The boundary against inventing statistics is the most important rule for repurposing, because hallucinated stats destroy trust faster than any other error.
- The "talk to one person" rule keeps the output in operator voice instead of LinkedIn-influencer voice.

## Filled example - blog post to multi-format

```
GOAL: Take the source asset at ./blog/2026-05-ticket-pack.md
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
