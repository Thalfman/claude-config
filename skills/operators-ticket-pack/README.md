# Operator's Ticket Pack - Claude skill

A Claude skill that helps operators construct paste-ready, five-part tickets for delegating one job at a time to AI agents (Claude Code, Codex, bash loop). Eight verbatim templates spanning coding and ops tasks.

## What this is

The skill detects which of 8 ticket types fits the operator's task, collects the bracketed inputs (paths, commands, percentages, file locations) in one batch, fills the chosen template verbatim, and hands back a paste-ready prompt. The proof gate is restated in plain English so the operator can sanity-check before pasting.

The skill produces text. It does **not** execute the filled ticket - that is the downstream agent's job.

## Install

Drop this folder into your Claude skills directory:

```
~/.claude/skills/operators-ticket-pack/
```

Restart your Claude session. The skill triggers on phrases like:

- "Write me a ticket to migrate from `requests` to `httpx`"
- "Help me delegate inbox triage to Claude Code"
- "Give me a five-part ticket for X"
- "What is a proof gate?"

## The 8 tickets

| # | Ticket | Use case |
|---|--------|----------|
| 01 | Migration | Move from one library/framework to another |
| 02 | Bug Hunt | Get failing tests in a directory passing |
| 03 | Coverage Climber | Raise coverage on a module to a target % |
| 04 | Refactor | Merge functions with >=70% structural overlap |
| 05 | Invoice Extractor | PDF invoices to CSV with checksum proof |
| 06 | Inbox Triage | Emails to urgent / this-week / archive |
| 07 | Content Repurposer | Source asset to tweet + LinkedIn + pull-quote (JSON) |
| 08 | Lead Qualifier | Score inbound leads against a rubric |

## Credit

This skill is a packaging of:

> **The Operator's Ticket Pack - DOO MADE**
> Volume 01 - The Ticket Series - Updated May 2026

Companion read to the **Ralph Wiggum Loop** video on **DOO MADE**.
Built for operators using Claude Code, Codex, or the bash loop.

All eight templates are reproduced verbatim. The skill adds a decision layer (which ticket fits this task?) and a bracket-collection workflow. It does **not** alter the PROOF, BOUNDARY, BUDGET, or FALLBACK wording - that text is load-bearing.

## Scope

- v1: faithful to the 8 PDF tickets. Custom tickets are out of scope.
- Local-only distribution.
- No code, no build, no tests, no external dependencies.

## What this skill is NOT

- A ticket *runner*. It produces prompt text; it does not execute the filled ticket.
- An open-ended prompt generator. The 8 tickets are the 8 tickets.
- A replacement for the PDF. The PDF carries the author's full reasoning and "why it works" prose; this skill carries the operational shape.
