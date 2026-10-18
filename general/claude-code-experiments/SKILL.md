---
name: claude-code-experiments
description: Active, past and candidate A/B experiments that Anthropic runs on this Claude Code install (GrowthBook experiment enrollments cached in .claude.json — experimentId, variationId, the feature flags and values each one drives), cross-linked to the claude-code-variables skill so you can see which knobs an experiment changes. Self-updating — the same SessionStart hook diffs the enrollment cache every session (start / end / variation change → append-only ledger) and the binary scan refreshes the candidate list. Load when behaviour changed without a version bump, when a flag's served value looks like a treatment arm, or to answer "what experiments am I in?".
---

# claude-code-experiments

## Files
| path | what | edit? |
|---|---|---|
| `reference/experiments.md` | **Active** (enrolled now), **Past** (seen before, gone now), **Candidates** (flags the binary reads with nothing served yet) | generated |
| `data/experiments.jsonl` | append-only ledger: `experiment_started` / `experiment_changed` / `experiment_ended` / `experiment_resumed`, with source (`live` or the `.claude.json.backup.*` it was seeded from) | append via ccv.py only |
| `data/state.json` | materialised view | never by hand |

Generated and updated by `.claude/skills/claude-code-variables/scripts/ccv.py` (shared scanner) via the SessionStart hook
`.claude/hooks/claude-code-variables-watch.py`. Force a refresh: `python3 .claude/skills/claude-code-variables/scripts/ccv.py update`.

## What an experiment IS here (and what cannot be known)
- Enrollment arrives in Claude Code's remote-eval payload and is cached as `cachedExperimentData` in `.claude.json`:
  `{ <feature flag>: { experimentId, variationId, value } }`. `variationId` 0 is normally control; ≥1 a treatment arm. The served
  `value` is what the flag returns while enrolled, so an experiment shows up in the variables skill as a flag whose served column says
  `(experiment: <id>)`.
- **Active** = in the cache at the last check. **Past** = recorded earlier (live or from the config backups) and absent now.
- **Candidates** = flags this binary reads for which nothing is served. That is the only forward-looking signal: experiments are NOT
  enumerable from the binary (no list of experiment ids ships in it), so "future" can only mean "the code is ready, nothing is served
  yet". Treat the candidate list as leads.
- Exposure logging: the binary records `growthbook_experiment` exposure events (experimentId, variationId) when an enrolled flag is read.

## Known enrollments at seed time (2026-10-12, CLI 2.1.296) — see reference/experiments.md for the live list
`precomputed-compaction-v7` (treatment: `tengu_sepia_moth`=true + `tengu_amber_moleskin` buffer-fraction table → compaction summary
precomputed when within 6% of the threshold on 1M windows; settings `precomputeCompactionEnabled` overrides), `ultrareview_cli_nudges`,
`tengu_read_dedup_killswitch`, `cai_giggly_dream` ($250 cloud-credit promo), `tengu_plank_river_frost`, `tengu_amber_prism`, and controls
`tengu_flint_harbor`, `tengu_mcp_subagent_prompt-public`, `cc-grace-launch-1`.

## Rules
1. Ledger is append-only; reference files are generated — never hand-edit either.
2. When the hook reports `experiments changed`, read `reference/experiments.md`, then the affected flags in
   `claude-code-variables/reference/flags.md`, and tell the operator in one line per experiment what behaviour it moves.
3. An experiment that changes something the operator has ruled on (compaction, checkpoints, memory) is a finding to report immediately,
   not a curiosity — cf. [[feedback-idle-compaction-off]] (idle compaction arrived as a remote rollout, not an experiment, with no local notice).
