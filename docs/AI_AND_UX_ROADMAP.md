# AI & UX Roadmap — SecuriSphere

Last updated: July 2026

Prioritized features to make the SOC workflow easier and more distinctive for portfolio/pilot demos.

## Implementing now (this release)

| Priority | Feature | Why |
|----------|---------|-----|
| P0 | **AI Security Assistant** (local + optional LLM) | Context-aware chat from alert/offense/event data; works without API keys |
| P0 | **Smart Investigation Copilot** | One-click “Ask AI” from alert pane + auto investigation summary |
| P0 | **Natural language → SIEM query** | Unique differentiator; lowers search learning curve |
| P1 | **Command palette (⌘K / Ctrl+K)** | Fast navigation and common actions for power users |
| P1 | **Onboarding checklist** | Guides first-time users: host → simulation → triage |
| P1 | **Contextual help tooltips** | Lightweight hints on hosts, simulation, alerts |
| P1 | **Offense AI brief** | Plain-English offense narrative for analysts |

## Later (post-pilot)

| Feature | Notes |
|---------|-------|
| RAG over full event corpus | Needs vector store + scale tuning |
| Autonomous response playbooks | Requires approval workflows and action audit |
| LLM-generated correlation rules | Higher risk; needs guardrails |
| Voice / mobile assistant | Separate UX surface |
| Multi-language NL search | Extend pattern library per locale |
| SSO-aware assistant memory | Blocked on identity provider work |

## Design principles

1. **Local-first** — rule-based intelligence and templates work offline; LLM is optional enrichment.
2. **Context from DB** — assistant reads real alert/offense/host data, not hallucinated incidents.
3. **Analyst in control** — suggestions only; no autonomous containment or rule changes.
4. **Minimal scope** — reuse FastAPI routers, React Query, Tailwind, existing panel patterns.

## Env toggles

| Variable | Default | Purpose |
|----------|---------|---------|
| `AI_ASSISTANT_ENABLED` | `true` | Master switch for assistant endpoints |
| `AI_PROVIDER` | `local` | `local`, `openai`, or `anthropic` |
| `OPENAI_API_KEY` | empty | Optional richer chat + NL search |
| `ANTHROPIC_API_KEY` | empty | Alternative LLM provider |
