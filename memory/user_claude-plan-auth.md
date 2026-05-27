---
name: claude-plan-auth
description: Tom uses his personal Claude Pro/Max subscription for Claude integrations; he does not pay for or use Anthropic API keys.
metadata:
  type: user
---

Tom does not use Anthropic API keys. He authenticates against Claude using his personal Claude Pro/Max subscription. Any integration that calls the Claude API on his behalf (GitHub Actions, MCP servers, CI tools, scripts) must use the OAuth-based subscription token (`CLAUDE_CODE_OAUTH_TOKEN`, generated locally via `claude setup-token`), never `ANTHROPIC_API_KEY`.

Apply this whenever proposing or configuring any tool, workflow, or repo secret that authenticates against Claude. Default to `claude_code_oauth_token` in `anthropics/claude-code-action` and to OAuth/subscription flows in any future Claude integration. Do not suggest "add an API key" as the default option; mention it only as an alternative if the user asks.
