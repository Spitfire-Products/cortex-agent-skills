---
name: grounded-research
description: Active-discovery + map-before-assert research discipline. Invoke BEFORE answering any cross-cutting "who calls X / which path / how does this flow" question, before fixing or deploying against an assumed code path, or whenever tempted to state a conclusion from a narrow grep. Enforces: map the full surface (Explore agent / exhaustive multi-form search) first, cite file:line or label "unverified", never build on an ungrounded premise.
metadata:
  version: "1.0"
  source: omniclaude-v4/training_docs/ACTIVE_DISCOVERY_GROUNDED_RESEARCH_METHODOLOGY.md
---

# Grounded Research — Map Before Assert

Ground every claim in code you have actually read. A confident-but-wrong conclusion is
the most expensive kind, because the next steps get built on it.

## 🗺️ Map Before Assert (the core rule)

A single narrow `grep` answers "does this string appear here?" — NOT "who calls X?",
"which path does Y?", or "how does this flow end-to-end?". Treating a scoped match as a
system-wide truth produces misleading claims.

1. **Recognize a cross-cutting question.** Any "who calls / what uses / which path / how
   does it flow" spanning multiple files, modules, or layers (browser↔server,
   snake_case↔camelCase, TS↔Rust, two SpacetimeDB modules) is a MAPPING task, not a grep.

2. **Map the full surface before concluding.** Default to an **Explore agent** — it reads
   excerpts across many files and returns the conclusion without burning your context. If
   searching directly, cover EVERY name form and surface:
   ```bash
   # WRONG — scoped, single-form → "X is the only caller" (misleading)
   grep -rn "system_create_server_from_template" modules/database-ai/
   # RIGHT — every form, whole repo
   grep -rniE "system_create_server_from_template|systemCreateServerFromTemplate|createServerFromTemplate" \
     --include="*.ts" --include="*.tsx" --include="*.rs" .
   ```

3. **Label confidence on every claim.** "verified at `file:line`" vs "assumption — not
   checked." If you cannot cite it, you have not grounded it. Never present an inference
   as fact.

4. **Do not build on an unverified premise.** Do NOT edit, fix, or deploy against a path
   until the map confirms it is the right target. Mapping AFTER coding means you may have
   fixed the wrong thing.

## Active Discovery (before/during/after)

- **Before implementing:** search for existing patterns; check for an existing **skill**
  or doc that already covers it (read it FIRST — don't re-derive). Find integration points.
- **During:** validate against architecture/PRD; test integration with real components.
- **After:** run the real test suite; verify alignment; document discoveries (update the
  relevant skill/doc — make it the source of truth, not a one-off memory).

## What NOT to do

- ❌ Assert "who calls / which path / how it flows" from a partial grep — map first.
- ❌ Build/edit/deploy against a premise you haven't grounded.
- ❌ Skip the existing skill/research doc — they hold the map you're about to re-derive.
- ❌ Use mocks where real API calls + data would reveal the truth.
- ❌ Present an unverified inference without the "assumption" label.

## Real failure this prevents (this codebase)

A snake_case-only, single-directory grep concluded "the cortex is the only caller of
`system_create_server_from_template`." The real map (one Explore agent) showed TWO swarm
provisioning paths — a **browser path** (`NpcWindow.tsx` → `createUserServer` +
`createRoom`) and a **headless path** (`provision_swarm_chat` → that reducer). The browser
path never touches the reducer, so it was invisible to the narrow grep; the conclusion was
confidently stated and wrong. One Explore agent up front would have produced the correct
map immediately. (Operator: "you keep doing this. you are guessing… it is costing us accuracy.")
