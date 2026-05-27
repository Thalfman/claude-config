# Glossary

| Term | Meaning |
|------|---------|
| **Ticket** | A five-part task definition (Order, Proof, Boundary, Budget, Fallback) for one AI agent job. |
| **The Order** | Goal + acceptance criteria. What "done" looks like in plain language. |
| **The Proof** | Deterministic test that decides done - exit code, checksum, format check, grep result. |
| **The Boundary** | Explicit "do not" list. Blocks the most common reward-hacks for this task. |
| **The Budget** | Hard stop in turns AND minutes (or counts, for data-shaped tickets). Whichever hits first. |
| **The Fallback** | Graceful exit when blocked. Write a diagnostic artifact and stop, instead of looping. |
| **Proof gate** | The load-bearing acceptance condition in the Proof block. The one that separates ship from garbage. |
| **The Cook** | Informal term for the executing agent (Claude Code, Codex, whichever model runs the ticket). |
| **Reward-hacking** | Passing the letter of a rule while violating its intent. Example: deleting a failing test so the suite "passes". |
| **One ticket = one job** | A ticket addresses exactly one outcome. Two outcomes means two tickets. |
| **Pragma syntax** | Bracketed placeholders in tickets - `[LIKE THIS]` - that the operator fills before pasting. |
| **Bash loop** | A bash-shell-driven agent loop. One of the runtimes these tickets target. |
| **/goal in Codex** | Codex's command for handing a ticket to its agent runtime. |
| **PDF default** | The budget value specified by DOO MADE for each ticket. Used when the operator does not override. |

## The operator's standard (from page 07)

> Better proof gates beat better cooks every time.

If you remember nothing else:
1. Your ticket is more important than which AI you pick.
2. The proof gate decides whether you ship work or garbage.
3. One ticket = one job. Bake the budget into the ticket itself.

## Source

Terms drawn from DOO MADE - The Operator's Ticket Pack (May 2026), pages 02 and 07. "The Cook" and "reward-hacking" are vocabulary the PDF uses to describe failure modes; they are repeated here for the skill's own use.
