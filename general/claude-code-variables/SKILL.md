---
name: claude-code-variables
description: Master reference of EVERY knob Claude Code reads — remote feature flags (GrowthBook tengu_* / Statsig gates / experiment features), environment variables, settings.json keys, and telemetry event names — for the installed CLI binary, with code default vs the value actually served, per-item summaries, and an APPEND-ONLY ledger. Self-updating — a SessionStart hook rescans when the binary version changes, appends new items as `new` (uninvestigated), moves vanished items to the deprecated list, and tells the operator what to investigate. Load when a question involves what a flag / env var / setting does, whether a behaviour is remote-controlled, how to override it, what changed between CLI versions, or when the hook reports pending items.
---

# claude-code-variables — the master map of Claude Code's knobs

## What lives here
| path | what | edit? |
|---|---|---|
| `reference/INDEX.md` | counts per kind/status, binary version, pending count | generated |
| `reference/flags.md` | remote flags: code default, **served value now** (growthbook / statsig / experiment), summary, versions seen | generated |
| `reference/env-vars.md` | environment variables: how read (typed table vs `process.env`), sites, summary | generated |
| `reference/settings.md` | settings.json keys: the binary's own schema description where it has one, else the agent summary | generated |
| `reference/events.md` | `tengu_*` telemetry EVENT names — not flags; listed so nobody mistakes them for flags | generated |
| `reference/deprecated.md` | items a previous binary read that the current one does not (kept forever) | generated |
| `reference/served-only.md` | flag names served by Anthropic that this build never reads (other versions) | generated |
| `reference/NOTICE.md` | the pending-investigation queue with snippets | generated |
| `data/inventory.jsonl` | **append-only ledger**: added / deprecated / restored / default_changed / value_changed / investigated / scan | append via ccv.py only |
| `data/state.json` | materialised view (rebuilt by ccv.py from scans + ledger) | never by hand |
| `scripts/ccv.py` | the scanner / ledger / generator (also drives the `claude-code-experiments` skill) | code |

Hand-written background (method, verified deep-dives on compaction/memory/resume, env↔flag layering):
`.claude/claude_research_analysis/04-feature-investigations/CLAUDE_CODE_REMOTE_FLAGS_2.1.296.md` and `CLAUDE_CODE_ENV_VARS_2.1.296.md`;
memories [[claude-code-remote-flags-map]], [[claude-code-env-vars-map]], [[feedback-idle-compaction-off]].

## How the knobs layer (verified pattern, read in the binary)
```
env var (shell / settings "env" block)  →  settings.json key  →  remote flag (served; cached in .claude.json)  →  code default
   checked first, always wins                 e.g. idleCompaction          tengu_* via k("name", default)         when nothing is served
```
`DISABLE_GROWTHBOOK=1` drops every remote value (all flags fall to code defaults — untested side effects). `DISABLE_COMPACT`
kills manual /compact too. Settings keys the code reads AFTER a flag still override it (`idleCompaction`, `autoCompactEnabled`,
`precomputeCompactionEnabled`).

## Self-update contract
- **Trigger:** `.claude/hooks/claude-code-variables-watch.py` on `SessionStart` runs `ccv.py check` (fast). It compares the installed
  binary's version (package.json beside it, else the `VERSION:"…"` literal) with `state.last_scanned_version`.
- **Binary changed →** `ccv.py update` is launched in the background (~1 min): rescans flags / env / settings / events, diffs against
  the state, appends `added` events (status `new`, or `auto` for telemetry events and settings that carry schema text), `deprecated`
  events for items no longer read (moved to `reference/deprecated.md`), `restored` when one comes back, `default_changed` when a code
  default moved; regenerates every reference file and the experiments skill. The hook announces the change.
- **Every session:** the `.claude.json` flag cache is diffed inline → `value_changed` ledger rows + the served column, and experiment
  starts/ends/variation changes go to the experiments skill.
- **Operator notice:** whenever `new` items exist the hook injects
  `[claude-code-variables] N item(s) await investigation …`. The agent must then: load this skill, read `reference/NOTICE.md`,
  investigate each item (snippet first; `python3 - <<EOF` over the binary for more context), record it, and tell the operator in one
  short list what appeared and what it does.
- **Record an investigation** (the only way `new` becomes `investigated`):
  ```
  python3 .claude/skills/claude-code-variables/scripts/ccv.py mark <NAME> --kind <flag|env|setting> \
      --category <compaction-context|memory-autoresume|model-effort-thinking|tools-permissions|mcp|ui-tui|telemetry-surveys|bridge-remote-control|auth-billing-limits|plugins-skills|agents-subagents-workflows|performance-caching|rollout-killswitch|networking-api|session-host-internal|other> \
      --summary "<≤25 words, from code you read>" --confidence <high|med|low> [--by operator|agent]
  ```
- Other commands: `ccv.py status` (counts + pending), `ccv.py update` (force a full rescan now), `ccv.py regen` (rebuild reference files),
  `ccv.py check --no-spawn` (dry hook path). Log: `/tmp/claude-code-variables.log`. Env overrides: `CCV_BINARY`, `CCV_CONFIG_JSON`.

## Rules
1. The ledger is append-only: never edit or delete lines in `data/inventory.jsonl`; corrections are new `investigated` rows (`mark` again).
2. Never hand-edit `reference/*.md` or `data/state.json` — they are regenerated. Put prose in the research docs or memories instead.
3. A summary must come from code you read (snippet or binary), never from the name alone; say "unclear" + low confidence otherwise
   ([[feedback-stop-dont-thrash]], [[feedback-subagent-claims-are-unverified]]). Reader-pass rows from 2026-10-12 are marked as such in
   `investigated_by`; re-`mark` any you verify by hand.
4. Deprecated ≠ deleted: items stay listed with their last summary and the version that dropped them.
5. Scanning rules of thumb: the per-name regex pass over the 200 MB binary is too slow (7+ min) — ccv.py uses single-pass scans; never
   `pkill -f` a pattern that appears in your own command line (it kills your shell).

## Quick answers this skill gives
- "Is X remote-controlled?" → `reference/flags.md` row (served column) or `served-only.md`; absence everywhere = not a flag in this build.
- "How do I turn X off locally?" → the env var row (env wins), else the settings row, else there is no local override.
- "What changed in the new CLI?" → `grep '"event": "added"\|"deprecated"' data/inventory.jsonl | tail`, or the INDEX counts + NOTICE.md.
- "Which experiments touch X?" → load `claude-code-experiments`.

## Changelog tracking + library candidates (2026-10-20, operator)
The public changelog (`https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`; the installed package ships none) names
new variables/flags/settings as they ship and describes behaviour the binary scan can only hint at. It is tracked beside the scan:
| path | what | edit? |
|---|---|---|
| `data/changelog.md` | raw cached changelog (last fetch) | generated |
| `data/changelog.jsonl` | **append-only**: `changelog_entry` (version, bullet, linked inventory items, keyword tags) / `changelog_triaged` | append via ccv.py only |
| `data/changelog-state.json` | per-version bullets + triaged flag | never by hand |
| `reference/changelog.md` | UNTRIAGED section (tagged bullets, linked `kind:name` items) + the newest 40 versions in full | generated |
| `library/CANDIDATES.md` | **hand-curated**: Claude Code changes the nexus-cortex harness should adopt / mirror / decline, with the harness analog, proposal and status | the agent writes rows |
- **Refresh:** `ccv.py check` (the SessionStart hook) spawns `ccv.py changelog` in the background when the cache is older than 24 h or the
  binary changed; `ccv.py update` refreshes it too. Manual: `ccv.py changelog` (network) or `ccv.py changelog --file <path>`. ~5 s for 424 versions.
- **Operator notice:** the hook says `N Claude Code changelog version(s) untriaged for library candidates`. The agent then: reads
  `reference/changelog.md` UNTRIAGED (tagged bullets first; `Fixed …` lines rarely matter), adds rows to `library/CANDIDATES.md` for anything
  the harness should answer (what it is · harness analog or gap with a file pointer to VERIFY · proposal · status), and records the pass:
  `python3 .claude/skills/claude-code-variables/scripts/ccv.py changelog-triaged <version> [<version> …]` (`--before <ver> --by baseline`
  marks pre-ledger history as not-to-be-triaged; done once for everything below 2.1.290).
- **Rules:** rows cite the bullet's version; a harness pointer is a lead to verify, never a fact ([[feedback-subagent-claims-are-unverified]]);
  an accepted candidate gets a def-… backlog row / Rxx line and the status here moves with it; declined rows keep their reason.
- Seeded 2026-10-20 with C01–C21 from 2.1.290 → 2.1.304 (system-prompt-in-transcript, bash changed-files capture, compaction tool roster,
  per-agent effort/compaction window, Read allow_large, 529/usage-limit retry levers, fail-closed hooks, tool-description byte budgets, …).
