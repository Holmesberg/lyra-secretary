# OpenClaw + Claude Subscription — 2026-04-29 Findings

**Trigger:** operator asked whether OpenClaw could be powered by their Claude subscription instead of paid API credits.
**Short answer:** No, not anymore. Anthropic blocked third-party agent harnesses from Pro/Max subscription quota on **April 4, 2026** — about three weeks before this conversation.
**Status:** documented for future reference. OpenClaw container updated 2026.4.5 → 2026.4.26 in the same session.

---

## The hard truth

What's allowed on Pro/Max subscription billing as of 2026-04:
- claude.ai (web/desktop/mobile)
- Claude Code CLI
- Claude Cowork

What now requires a separate `ANTHROPIC_API_KEY` with paid credits:
- **OpenClaw, Cursor, Cline, custom Agent SDK builds — every other external tool.**

The CLIProxyAPI bridge that used to forward subscription session tokens to Anthropic's edge as if they were API requests is **deprecated** as of April 4. OpenClaw still ships placeholder env vars (`CLAUDE_AI_SESSION_KEY`, `CLAUDE_WEB_COOKIE`, `CLAUDE_WEB_SESSION_KEY`) for backward compat with installs that pre-date the cutoff, but those auth paths return 401 from Anthropic now.

The Claude Agent SDK **explicitly requires API key authentication** and prohibits subscription billing. There's an open Github issue (`anthropics/claude-agent-sdk-python#559`) requesting Max-plan support, with no roadmap commitment.

## What the operator's container actually has

Inspected `openclaw-openclaw-gateway-1`:
```
ANTHROPIC_API_KEY:        set (108 chars, sk-ant-...)
CLAUDE_AI_SESSION_KEY:    empty
CLAUDE_WEB_COOKIE:        empty
CLAUDE_WEB_SESSION_KEY:   empty
```

The API key is wired in — whether it has credits attached is something only the operator can verify at console.anthropic.com. If it was set up earlier and never topped up, it's a dead key.

## What we updated 2026-04-29

`docker pull ghcr.io/openclaw/openclaw:latest` jumped the running container from **2026.4.5** → **2026.4.26** (21-day window of releases). New since the last update:

- **DeepSeek V4 Flash + V4 Pro** added to the bundled catalog. V4 Flash is the **new onboarding default** — the timing strongly suggests this was the OpenClaw team's response to the Anthropic subscription cutoff: ship a cheaper default. DeepSeek V4 Flash is ~$0.14/M tokens vs Sonnet 4.5's ~$3/M (20× cheaper) on roughly comparable reasoning quality per public benchmarks.
- **Google Meet plugin** as bundled participant — personal Google auth, paired-node Chrome support, attendance/artifact exports.
- **TTS expansion** — chat-scoped auto-TTS, new providers (Azure Speech, ElevenLabs v3, Inworld, Volcengine, Xiaomi, Local CLI).
- **Claude importer** — preview/apply Claude Code + Claude Desktop instructions, MCP servers, skills, command prompts. One-time migration tool, useful for the operator if they want to bring in the Claude Code skills they already have.
- **Plugin registry hardening** — cold persisted registry, faster startup, deterministic provider discovery.
- Reliability fixes across agents, memory, cron, gateway startup.

## Operator's options going forward (no API credits)

| Option | Cost | Reasoning quality | Effort |
|---|---|---|---|
| **Ollama (local)** | Free | Weaker than Sonnet but acceptable for tool-orchestration. Lyra already runs `qwen2.5:3b` for its LLM-enrichment path per `CLAUDE.md`; could bump to `qwen2.5:14b` or `llama3.3:70b` if the operator's GPU has VRAM | ~5 min config swap |
| **DeepSeek V4 Pro/Flash** | ~$0.14/M tokens | New default in 2026.4.26; close to Sonnet on benchmarks | API key + $5 top-up |
| **Anthropic API top-up** | ~$3/M Sonnet input | Best reasoning, key already set | Top up at console.anthropic.com |

## Operator decision (deferred)

Operator was hoping for the subscription path; on hearing it was closed, did not immediately commit to one of the alternatives. Documenting for later when the decision is made — most likely path given the current "no credits" stance is **Ollama with whichever local model fits the GPU**, since Lyra's stack is already wired to use it.

## Sources

- [Using Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan)
- [I have a paid Claude subscription. Why pay separately for the API?](https://support.claude.com/en/articles/9876003)
- [Anthropic OpenClaw ban: third-party harnesses blocked from subscriptions](https://www.mindstudio.ai/blog/anthropic-openclaw-ban-third-party-harnesses-claude-subscriptions)
- [OpenClaw + Claude Code Costs 2026 (after subscription cutoff)](https://www.shareuhack.com/en/posts/openclaw-claude-code-oauth-cost)
- [Agent SDK should support Max plan billing — open issue](https://github.com/anthropics/claude-agent-sdk-python/issues/559)
