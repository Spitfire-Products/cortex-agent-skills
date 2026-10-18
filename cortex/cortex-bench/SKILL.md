---
name: cortex-bench
description: Multi-model parallel benchmark methodology for finding harness deficiencies and driving autoresearch-style recursive self-improvement of the CORTEX harness itself. Cross-provider comparison with ground-truth control. EVERY run must produce a deficiency ledger; experiments are git-worktree-isolated; visual/TUI output is evaluated via tmux capture; NEVER use model='auto' routing when benchmarking models.
triggers:
  - benchmark
  - multi-model
  - cross-provider
  - harness audit
  - recursive improvement
  - recursive self-improvement
  - auto-research
  - autoresearch
  - compare models
  - ground truth
  - cortex bench
  - parallel benchmark
  - find harness bugs
  - git worktree
  - tmux capture
  - tui evaluation
  - frontend design
---

# Cortex-Bench — Multi-Model Benchmark Methodology

> **SURFACE**: benchmarking the **nexus-cortex harness** (omniclaude-v4 — skill:
> `nexus-cortex-harness`). NOT the Nexus Terminal CORTEX browser agent. Full map:
> `docs/SURFACES.md`.

Cross-provider benchmark technique for auditing the CORTEX harness and driving recursive iterative self-improvement. The core insight: **many apparent "model quality gaps" between providers are harness-side bugs, not model-side**. Only a side-by-side comparison catches them.

Proven to surface 7+ classes of harness bugs (R18a/b/c, R19a-d, R20a/b/c, R27, R28a-f, R29a) — see `omniclaude-v4-harness-deficiencies` memory for the full trail.

> ## ⚑ THREE NON-NEGOTIABLE OPERATING RULES (read before any benchmark)
>
> 1. **Every benchmark must produce a DEFICIENCY LEDGER, not a pass/fail.** Any agent benchmarking in the omniclaude-v4 CORTEX harness runs tasks *in order to find and fix what's wrong with the harness*. The deliverable of every run is a structured list of (a) harness deficiencies found + their fix, (b) model-disposition gaps to address via prompts/tool-defs/system-msgs, and (c) what was verified clean. A run that ends "all arms agree, looks good" is a wasted run — the task wasn't hard enough or wasn't real-work. Mine every run for deltas.
>
> 2. **NEVER use `model='auto'` / the model router when benchmarking models.** Benchmarking *measures a specific model*, so you must PIN it (`cortex -m <model>` / `Task model='<exact-id>'`). `'auto'` routes to a possibly-different model per task type, silently swapping the variable you're measuring and destroying the comparison. Worse, the router *learns from these runs* (`MODEL_ROUTER_RECORD`), so an auto-routed benchmark poisons the matrix with mislabeled data. The router is for production dispatch; the bench is for controlled measurement. Keep them apart.
>
> 3. **The eval is sacred — never game it.** The ground-truth control + the verifiable task is the fixed measuring stick (the `prepare.py` of this system). You may change the *harness*; you may never weaken the *check* to make a model/harness "pass." If a fix only passes by relaxing the verification, it's not a fix.

## The Core Methodology

```
Same exact prompt
    ├── Arm 1: CORTEX via model A (e.g., deepseek-v4-pro, Chat Completions API)
    ├── Arm 2: CORTEX via model B (e.g., claude-sonnet-4-6, Messages API)
    ├── Arm 3: CORTEX via model C (e.g., gemini-2.5-flash, GenerateContent API)
    ├── Arm 4+: More models covering more adapter paths
    └── Control: Claude Code native sub-agent (Opus) — the ground-truth reference

                   ↓

  Compare all arms side-by-side across:
    - Correctness vs control
    - Tool call counts (thrashing?)
    - Empty/dropped content
    - Duplicate blocks
    - 400 errors in server logs
    - Cache hit rates
    - Latency and cost

                   ↓

  Discrepancies → harness bugs OR model disposition differences
  Harness bugs → fix → harness improves → re-benchmark
  Model differences → document → improve prompts/tool defs/system msgs
```

## Cardinal Rules (learned the hard way)

1. **n ≥ 2, different tasks.** One task agreeing three ways is a false positive. Run at least two different tasks in fresh sessions.
2. **Ground-truth against the real artifact, not an agent.** The parallel sub-agent is a reference that fails differently, not an oracle. The only truth is direct shell/grep/python on actual files. **Existence/resolution claims need a behavioral probe**: an agent asserting "X is registered / X resolves / the alias works" must demonstrate it (run the lookup, hit the endpoint) — in a live audit, 2 of 6 agents asserted a nonexistent alias from a comment they'd read, and only the probe refuted it (which then exposed a real bug).
3. **Fresh server + fresh session per model probe.** `--new` on every prompt; restart the server between models. Prompt cache and debug logs bleed across models.
4. **Discard confounded runs.** After every run: `grep -nE "429|capacity|exhausted|rate.?limit|overloaded|quota" /tmp/omniclaude-server.log`. If it hits, the model was throttled, not benchmarked. Throw it away.
5. **Real work surface, not toy prompts.** The task must (a) move the harness/platform forward AND (b) have an independently verifiable answer. "Count imports in file X" is verifiable but worthless; "refactor module Z" is real but unverifiable. Find tasks that are BOTH.
6. **Pin the model — never `auto`.** See operating rule #2. When the variable under test IS the model, routing must be off and the model explicit. Auto-routing during a model benchmark is a methodology error that also corrupts the router matrix.
7. **Output is a deficiency ledger.** See operating rule #1. End every run by writing the findings to `.cortex/bench/<round>-<tag>.md` AND appending durable harness deficiencies to the `omniclaude-v4-harness-deficiencies` memory. No ledger → the run didn't happen.

## Server Setup for Benchmarking

```bash
# Kill old server (match REAL argv — "node dist/index.js" not the full path)
pkill -9 -f "node dist/index.js" 2>/dev/null; sleep 2
ps -eo pid,args | grep "[d]ist/index.js" && echo "ZOMBIE — kill -9" || echo "clean"

# Start stateless (CRITICAL — persistent mode leaks context across probes)
cd $WORKSPACE/omniclaude-v4/packages/server && \
  DEBUG=true \
  MENTORSHIP_ENABLED=false \
  ENABLE_SERVER_SIDE_TOOLS=true \
  XAI_API_MODE=messages \
  CORTEX_MODE=stateless \
  setsid nohup node dist/index.js > /tmp/omniclaude-server.log 2>&1 < /dev/null &

# Poll for boot (~20s cold, not 5s)
for i in $(seq 1 30); do sleep 2; curl -sf http://localhost:4000/health >/dev/null && break; done

# Verify isolation: two identical probes must give DIFFERENT conversationId, SAME inputTokens
curl -s http://localhost:4000/v1/messages -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-pro","messages":[{"role":"user","content":"say hi"}],"max_tokens":50}' | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('metadata',{}).get('conversationId','MISSING')[:8])"
```

## The Prompt Template

Craft a task that is:
- **Deterministic**: file contents, code patterns, counts — anything verifiable
- **Multi-step**: forces 3-15 tool calls (exercises tool loop, budget signals, error recovery)
- **Specific**: asks for exact line numbers, code quotes, structured output

Counter-examples (don't use): web content (varies by time), creative writing (no ground truth), single-file reads (too simple, bypasses loop).

## Running the Benchmark (Parallel Dispatch)

From within a Claude Code session, dispatch ALL arms in ONE message for true parallelism:

```
Task sub-agent 1: model=deepseek-v4-flash, prompt="[TASK TEXT]"
Task sub-agent 2: model=deepseek-v4-pro, prompt="[TASK TEXT]"  
Task sub-agent 3: model=claude-sonnet-4-6, prompt="[TASK TEXT]"
Task sub-agent 4: model=gemini-2.5-flash, prompt="[TASK TEXT]"
```

Or via the cortex CLI + Task agents mixed:
```bash
# In one bash call, launch cortex + Claude Code sub-agent concurrently:
cortex --new --quiet -m deepseek-v4-pro "[TASK]" &
# + Task agent with Opus as control
```

## Sub-agent Orchestration: isolation vs throughput (learned live, 2026-08-05)

Dispatching N agents at once raises the question this skill left implicit: **do they
share a working tree, or get isolated ones?** Both are right — for different task
shapes. Choosing wrong costs either wall-clock or a phantom bug hunt.

| | **Worktree isolation** (`isolation: "worktree"`) | **Disjoint file sets** (shared tree) |
|---|---|---|
| Mechanism | Each agent gets its own checkout off the same `.git` | All agents edit the live tree; each is *told* which files it owns |
| Enforcement | Structural — collisions impossible | By instruction only — nothing prevents an overlap |
| Agent can build/test itself | **No** — a fresh worktree has no `node_modules` (gitignored) until you install there | Yes (deps already present) |
| Cost | N× dependency install on a monorepo; disk; time | Main tree holds unverified code mid-flight |
| Use when | Agents edit **existing shared** files · large change · agent must self-verify | **New-file / additive** work · low collision surface · env can't afford N installs |

**The phantom-error trap.** A shared-tree agent that runs a *whole-project* typecheck
will observe peers' half-written files and report errors that are not its own. In a
live run the RelayExecutor agent reported a TS error in `ConnectionsPage.tsx` — a file
it never touched — because a concurrent agent was mid-write; that cost a real
debugging detour. **Rule: a shared-tree agent verifies ONLY its own files (or not at
all); the orchestrator owns whole-project verification.** Worktrees make this
structurally impossible — that's their value beyond collision safety.

**Central verification pattern (resource-constrained boxes).** Agents write; the
orchestrator compiles, tests, and ships — ONE build at a time. `main` stays at a
known-good checkpoint until each piece is proven, and you never hang a small box with
N concurrent builds. Trade-off: verification serializes through the orchestrator. Want
parallel self-verification? Pay for worktrees + installs. Don't pretend it's free.

**Trust on-disk state, not the agent's report.** An agent killed mid-flight (session
restart, timeout) may have *fully landed* its work with no report, or landed half of
it. Check the files before re-dispatching — blind re-runs duplicate work or clobber
good output. Corollary: when no report arrives, the BUILD is the verification, not the
missing summary.

**Let agents refute your assumptions.** Brief them to VERIFY identifiers against the
registry instead of accepting yours. In a live ontology build two of the tool IDs I
asserted (`searchTools`, `skills`) were wrong; the agent grepped the real registry and
returned `cortex_search_tools` / `cortex_skill`. An agent told to "use these names"
would have shipped the bug. This is Cardinal Rule 2 (behavioral probe) applied to
delegation.

## The Comparison Table (copy this format)

| Metric | Arm A (model) | Arm B (model) | Arm C (model) | Control (Opus) | Verdict |
|--------|---------------|---------------|---------------|----------------|---------|
| Turns | | | | | |
| Tool calls | | | | | |
| Tool pattern | | | | | |
| File path | | | | | |
| Key answer 1 | | | | | |
| Key answer 2 | | | | | |
| Code blocks correct? | | | | | |
| Empty/dropped content? | | | | | |
| Errors? | | | | | |
| Duration | | | | | |

## Bug Patterns — What Each Discrepancy Means

| Symptom | Likely Harness Bug | Class |
|---------|-------------------|-------|
| Empty content / no text | Empty-response not retried (R18b), responses adapter wrong id field (R18c) | Adapter |
| Duplicate tool_use blocks | Streaming accumulator no dedup (R18a) | Streaming |
| 400 error in server log | Wrong param name for provider (R19/O-series), id prefix mismatch (R19e) | Adapter/Config |
| 404 on Responses path | Doubled endpoint (R27#1) | Routing |
| Model returns tool_use only, no text | Loop exits on tool-use-no-text (R29a) | Loop control |
| Model thrashing (15+ calls) | Wrong working directory (R44 ESM bug), budget signals too weak | Infrastructure |
| Cache hit rate flat ~0.5% | System prompt in moving user slot instead of stable system field (R28a-f) | Caching |
| Cross-turn model switch 400s | Cross-provider response_id leak (R20a) | State |
| All o-series models 400 | Missing max_completion_tokens param (R19) | Model card |
| Gemini multi-turn 400 | thoughtSignature stripped in canonical conversion (R19c/d) | Adapter |

## Performance Benchmarking Addendum

When comparing cost/latency (not just correctness), capture these fields from every `/v1/messages` response:

| Field | Why |
|-------|-----|
| `usage.inputTokens` | System message + history overhead |
| `usage.outputTokens` | Response size |
| `usage.cacheReadTokens` / `usage.cacheCreationTokens` | Cache effectiveness |
| `metadata.toolCallIterations` | Round-trips |
| Wall-clock (time the curl) | Latency |

**Caveats:**
- `usage.cost_in_usd_ticks` only exists on XAI Responses API path — don't compare cost from paths that don't emit it
- `usage.outputTokens` under-reported for Gemini and XAI Messages
- Fresh-session floor ≈ 16k input tokens (system messages + tool schemas)

## Recursive Auto-Research Self-Improvement (autoresearch-style)

The harness is now mature enough to **research and improve its own library, autonomously and recursively** — the same pattern as karpathy/autoresearch (an agent mutates code, runs a fixed eval, keeps-or-discards, repeats, indefinitely). Here the "model being trained" is **the CORTEX harness itself**, and the eval is this benchmark methodology.

### The autoresearch mapping (internalize this)

| autoresearch | this harness |
|---|---|
| `train.py` — the mutable code the agent edits | the harness source in `packages/` (NOT a single file → use git-worktree isolation, below) |
| `prepare.py` — fixed, read-only eval (the ground truth metric) | the cortex-bench task + ground-truth control. **Never modify the check to pass** (operating rule #3) |
| `program.md` — human-tuned instructions ("a super lightweight skill") | **THIS skill** + the system messages. The human iterates HERE; the agent iterates on the code |
| `val_bpb` — one comparable metric | the per-run score: correctness-vs-control + deficiency count + the perf fields (input/output tokens, cache hit rate, tool iterations, latency) |
| `results.tsv` — append-only experiment ledger | `.cortex/bench/<round>-<tag>.md` + the `omniclaude-v4-harness-deficiencies` memory + `router-matrix.jsonl` |
| keep/discard via `git reset` | merge the worktree if the re-bench improves + no regression; else drop the worktree |
| **simplicity criterion** | a harness fix that *deletes* code/complexity and still holds the benchmark is a top-tier win. Weigh complexity cost vs. improvement; reject ugly hacks for tiny gains |
| **NEVER STOP** (run until interrupted) | run round after round; do not pause to ask "should I continue?" — escalate task difficulty and keep mining (consistent with the operator's `execute, don't defer` rule) |

### The loop

```
0. SETUP: pick a round tag (e.g. r55-loopfix). Create an isolated worktree (below).
1. RUN BENCHMARK (multi-model, same task, models PINNED — no 'auto')
       ↓
2. COMPARE vs control → MINE the deficiency ledger (operating rule #1)
       ↓
3. CLASSIFY each finding:
   ├── Harness bug → FIX in the worktree (ONE coherent fix; scope-isolation prevents creep)
   ├── Model disposition difference → improve prompts / tool-defs / system msgs
   └── Genuine model error → log it; nothing to fix in the harness
       ↓
4. REBUILD (npm run build) + RE-RUN the SAME benchmark in the worktree
       ↓
5. DECIDE: improved AND no regression on prior rounds' tasks?
   ├── yes → merge worktree → main; append the deficiency + fix to the memory ledger
   └── no  → drop the worktree (cheap discard); log "discard" + why
       ↓
6. Pick the NEXT task (harder, exercises newly-fixed paths) → goto 1.  Until interrupted.
```

The harness converges: each round fixes bugs that masked real model differences, making the next round's comparisons cleaner. Eventually the only remaining discrepancies are genuine model-capability differences (addressed via prompting, not code).

### Git-worktree schema — use the native `WorkspaceManager` tool (this already exists)

autoresearch isolates by editing one file; we isolate by **one git worktree per experiment** — required here because (a) the harness is a whole monorepo, not one file, (b) **two agents share this working tree** (Claude Code + the CORTEX agent), so an in-place experimental edit corrupts the other's state, and (c) a failed experiment must be discardable in one command.

**Do NOT hand-roll raw `git worktree` — the harness ships the `WorkspaceManager` tool for exactly this** (the agent-team-workspace system, built 2026-02-13; there is even a "Git Worktree" *dispatch mode* = `WorkspaceManager` + team dispatch where each parallel agent gets its own worktree). Native CORTEX agents call the tool; it wraps the git mechanics:

| `WorkspaceManager` action | what it runs | returns |
|---|---|---|
| `create` | `git worktree add /tmp/workspace-{uuid} -b {branch} {baseBranch}` | `{ worktreePath, branch, baseBranch, repoPath }` |
| `status` | `git worktree list --porcelain` | `{ worktreeCount, worktrees: [{path,head,branch}] }` |
| `diff` | `git diff {baseBranch} -- .` | `{ changedFiles, fileCount, diffLines, diff }` |
| `cleanup` | remove the worktree | — |
| `clone` | `git clone --depth 50` external repo (+ optional worktree) | `{ cloneDir, worktreePath, branch, repo }` |

Experiment loop with the tool:
1. `WorkspaceManager create` (branch `cortex-exp/<round>`) → isolated `worktreePath`.
2. **build INSIDE that worktree** (`cd <worktreePath>/omniclaude-v4 && npm install && npm run build`) — each worktree is its own checkout with its own `dist/`; never share `dist/`.
3. run the experiment server on a **non-default port** (4100, 4101, …) so it doesn't collide with the operator's live :4000.
4. bench against the experiment port, mine deficiencies, apply **one** coherent fix, rebuild, re-bench. Use `WorkspaceManager diff` to review the experiment's full change set before deciding.
5. **KEEP** (improved + no regression) → merge the branch to main, then `WorkspaceManager cleanup`. **DISCARD** → `WorkspaceManager cleanup` + delete the branch (cheap revert — the autoresearch keep/discard step).

Rules: **one fix per worktree** (scope-isolation = autoresearch's single-file constraint); parallel experiments = multiple worktrees on different ports; the keep/discard decision is the only thing that touches `main`.

*(Direct shell equivalents, if you're driving without the tool — e.g. a Claude Code session: `git worktree add -b cortex-exp/<round> /tmp/cortex-exp-<round> <base>` → build → bench on :4100 → `git merge --no-ff` or `git worktree remove --force` + `git branch -D`.)*

### The deficiency backlog — auto-add via the `ResearchBacklog` tool

The deficiency ledger (operating rule #1) is now a **tracked, triaged task lifecycle**, not just prose. Every deficiency found → `ResearchBacklog` tool, `action:add` (auto-triages + computes priority on add). The harness identifies its own weaknesses, prioritizes them, and works the highest-priority one next.

- **Triage / priority** = `(severityWeight × impact × confidence) ÷ effort`. Low-confidence "deficiencies" (could be model noise) sink automatically — the triage-layer overfitting guard.
- **Lifecycle**: `open → triaged → in_progress → fixed → verified → closed` (+ `wont_fix`, `regressed`). `action:next` returns the top-priority open item — the recursion's "what to fix next."
- **OVERFITTING GUARD in the status model**: `action:fixed` = passes the task that *surfaced* it; `action:verified` = ALSO holds on **held-out** tasks. **Never `verified` without held-out confirmation** — `fixed` is not done.
- Store: `.cortex/research-backlog.jsonl` (append-only, two-agent safe). The matrix (`router-matrix.jsonl`) holds the *scores*; the backlog holds the *work items*; they share `harnessRef`/`taskFingerprint` provenance.
- **View + drive it from the CLI (nexus-cortex 4.46+):** `cortex autoresearch backlog list / show <id> / next` to see the pool; `resolve <id> [--wont-fix|--close|--fixed]` for the PM keep/discard. `--repo <path>`/`CORTEX_ROOT` targets a specific pool. This is the same JSONL the `ResearchBacklog` tool writes — just a human/CLI surface over it.
- **Work-swarm mode (divide-and-conquer):** when many INDEPENDENT deficiencies should be worked in parallel by different workers (vs `loop`'s competitive same-goal arms), `cortex autoresearch backlog claim-next --owner <id>` gives each worker a DIFFERENT item under a TTL lease (no double-claim); `release [id] [--expired]` frees leases. The per-item `resolve` is the merge. Don't route a divide-and-conquer job through the competitive `loop` gate.

### Overfitting guards (the recursion's immune system)

Recursive self-improvement's failure mode is **gaming the eval** — the harness tuned to pass the benchmark tasks rather than genuinely improving. Guards, layered:
1. **Held-out split.** Mark validation runs `CORTEX_BENCH_HOLDOUT=true` (→ `split:'holdout'` on matrix records). **Keep/discard uses `train`; verification uses `holdout`.** A fix tuned against task T is only `verified` when it improves *other* tasks it never saw.
2. **`fixed` ≠ `verified`.** The backlog enforces it structurally — no held-out pass, no verification.
3. **Confidence-weighted triage.** Noise-suspect findings are deprioritized, not chased.
4. **n ≥ 2 + significance.** LLM benchmarks are noisy; a single-run delta is often noise. Never "keep" on a delta within run-to-run variance (cardinal rule #1).
5. **Rotate the task pool.** Don't re-use the same handful of tasks every round; a fixed eval set invites overfitting. Real-work-surface tasks (cardinal rule #5) + rotation keep the eval honest.
6. **Regression scan across a broad set**, not just the target task — a "fix" that helps T while quietly hurting U is a discard.

### External / official benchmarks (SWE-bench etc.) — same pipeline, different source

The pipeline is **benchmark-source-agnostic**: `BenchmarkRecord.benchmarkSource` (env `CORTEX_BENCH_SOURCE`, default `cortex-bench`) lets official benchmarks feed the SAME matrix + backlog. An external runner (e.g. SWE-bench) records under `benchmarkSource:'swebench'`, the instance id as `taskFingerprint`, and pass/score from *its* grader — then auto-adds deficiencies for instances the harness fails. So SWE-bench / aider-polyglot / terminal-bench become additional ground-truth lenses pinpointing harness weaknesses, scored on the same axes, gated by the same overfitting/held-out discipline. (External runs are *excellent* held-out sets — the harness was never tuned against them.)

### North-star: a public verifiable record (SpacetimeDB)

The three local append-only stores — `router-matrix.jsonl` (scores), `research-backlog.jsonl` (work items), and `experiments.jsonl` (keep/discard decisions) — are **deliberately shaped to map onto STDB tables**: each is an append-only event stream keyed by `(taskFingerprint, modelId, harnessRef)` / `deficiency id` / `experimentTag`. Promoting them to a SpacetimeDB module would give a **public, verifiable, tamper-evident record** of the harness's self-improvement — every score, deficiency, and keep/discard decision auditable with commit provenance. (That module lives on the nexus/DBAI side, not in omniclaude-v4; the JSONL schemas here are the local mirror that ports up.)

### The decision layer is BUILT — call it, don't hand-judge keep/discard

As of 2026-06-07 the keep/discard decision is a **statistically-gated, reproducible** pipeline in `@nexus-cortex/core` (commits `ab9eb0b37`·`f7fc7e5c2`·`ec0f47551`·`825ada395`·`adb927987`). Do NOT eyeball "score went up → keep" — that overfits a recursive loop. Use:
- **`evaluateAutoResearchExperiment(matrix, ledger, input)`** — runs regressionScan → opens the ledger record → the Monte-Carlo gate → writes the audited verdict to `.cortex/experiments.jsonl`. `input = {experimentTag, baseRef, candidateRef, branch, deficiencyId?, benchmarkSource?, modelId?, nFamilyExperiments?, gate?, epsilon?}`. A 'keep' that introduced collateral regressions is flagged in the recorded reason.
- **`verifyOnHoldout(matrix, input)`** — the mandatory 2nd gate on `split='holdout'`; a candidate merges ONLY if kept-on-train AND verified-on-holdout (`fixed` ≠ `verified`; null = no held-out evidence = not mergeable).
- The gate = bootstrap CI (keep iff CI excludes 0) + permutation p-value + **N-aware FWER** (pass `nFamilyExperiments` = swarm width so the keep bar tightens with parallelism). Seeded RNG → **reproducible verdicts** (same records + seed = same p/CI), which is what makes the future STDB record publicly verifiable. Pure stats also exported: `decideExperiment`, `bootstrapCI`, `permutationPValue`, `sidakThreshold`, `mcFwerThreshold`.
- Optional **Thompson-sampling router** (`MODEL_ROUTER_EXPLORATION=true`) for explore/exploit so the matrix doesn't lock onto early winners. Off by default.

**Producing REAL scored records — `cortex autoresearch bench` (the grader).** The orchestrator's auto-record (`MODEL_ROUTER_RECORD`) writes only a liveness STUB (`qualitativeScore = hasText ? 75 : 0`) — useless for keep/discard (base ≈ candidate → always discard). To get real signal, run a graded task set:
```
cortex autoresearch bench --task-set <file|dir of *.json> --experiment-tag <id> \
  --runs 2 --split train|holdout [--harness-ref <sha>] [--model <id>]
```
Task = `{id, prompt, verifier, taskType?}`; verifier ∈ `exact|regex|contains|llm-judge`. **Prefer `contains` (partial credit → continuous score) or graded rubrics** over binary exact/regex — the bootstrap/permutation gate separates arms far better on continuous scores. Sample: `.cortex/bench/tasks/sample-tasks.json`. Run it in the base build and the candidate build (different `--harness-ref`/worktree), then `cortex autoresearch evaluate`. Keep holdout task FILES out of any fixing agent's context (overfitting guard).

**The one-shot runner — `cortex autoresearch experiment` (v4.7.0).** Does the whole single-experiment loop in one call (build+serve both arms → bench train+holdout → gate → `verifyOnHoldout` → teardown), so you don't orchestrate `bench`×2 + `evaluate` by hand:
```
cortex autoresearch experiment --experiment-tag <id> \
  --candidate-dir <worktree-with-fix> --base-dir <prebuilt base> \
  --task-set <train.json> [--holdout-set <holdout.json>] \
  --model <id> --runs 3 --n-family <swarm-width> --cortex-dir <per-exp dir> --json
```
`--json` → `{verdict, holdoutVerdict, regressedTasks, mergeEligible, benchSummaries, cortexDir, jsonlPaths}`. Owns the "two builds not one relabel" correctness (each arm served from its OWN built code; refuses `baseRef===candidateRef`). `--cortex-dir` is the per-experiment **artifact** (all 3 `.cortex/*.jsonl`). `mergeEligible` = keep ∧ fwerAdjusted ∧ holdout-keep (FALSE without holdout). Validated live end-to-end (both a real **discard** and a real **keep** with `mergeEligible:true`).

**The multi-arm campaign runner — `cortex autoresearch loop --width N` (4.45+).** The swarm-width family is now AUTOMATED: `loop --width N` fans each round into N parallel Fixer arms (own worktree + own model each, pool via `--arm-models`/`--providers`, `--missing-provider-key-policy` for unfunded arms), passes `--n-family <width>` to every arm's experiment so the FWER bar is honest, records per-arm `fixer:<model>` strategy labels into the matrix, and merges only the best gate-accepted (and judge-approved, if required) arm. This IS the N-of-this-experiment machinery — don't hand-orchestrate N `experiment` calls when a width'd loop round does it with correct family statistics.

### Hard-won benchmarking gotchas (from the first live runs, 2026-06-08)
- **Server returns `model` as an OBJECT** `{id, provider}`, not a string — any recorder must extract `.id` (fixed in serverRunner/estimateCost, `a4097aaf8`).
- **`PROJECT_PATH`, not `PROJECT_ROOT`**, controls the orchestrator's project context (system messages, CORTEX.md, agents) — set it when spawning a harness for a specific checkout (fixed in startServer, `3f549daa5`).
- **System-message resolution is project → global → builtin.** A candidate that edits a **built-in/`dist`** system message is **shadowed by `~/.cortex` (global)** and has NO effect. To change harness behavior, override at the **PROJECT** level (`<dir>/.cortex/system-messages/` or `<dir>/.cortex/CORTEX.md`) — that wins over global. (System-message injection itself WORKS — confirmed ~72K chars incl. CORTEX.md reach the model.)
- **Markers/format tokens are an UNRELIABLE signal** — low-compliance models (e.g. deepseek-v4-flash) ignore a format rule buried in a 72K system prompt even when it's present. For a measurable base-vs-candidate signal, use a **high-compliance model** (e.g. `claude-haiku-4-5`) and a **strong directive** (e.g. "respond only with JSON `{\"answer\":…}`") with a verifier that checks it. That's what produced the clean keep proof.

### Model-selection discipline while benchmarking (no-xAI cost constraint)
Default sub-agent model is **deepseek** (`DEFAULT_SUBAGENT_MODEL=deepseek-v4-flash`; `recommend()` fallback is deepseek too — no grok/sonnet defaults). The auto-router (Thompson exploration) honors `MODEL_ROUTER_EXCLUDE` (default `grok*`, a prefix wildcard) so it can NEVER auto-route a sub-agent to an xAI model. This is a guardrail on *automatic* picks only — an **explicit** model choice (driver `DEFAULT_MODEL_ID`, `/model`, an agent profile's pinned model, or the Task tool's `model` param) is always honored, including xAI/expensive-Claude. When benchmarking specific models, name them explicitly and never rely on `'auto'` (per the deficiency-first rule above).

### Composing skills inside the loop
- **The FIX step can be a `best-of-n` tournament.** A high-value deficiency justifies N competing fixes instead of one: one worktree per entrant, distinct strategy/model/temperature per arm (pass `strategy`/`temperature` on the Task dispatch — recorded into the matrix), criteria frozen before launch, one central judge. The re-bench IS the tournament's acceptance check.
- **The VERIFY step is `verify-work`.** Before a keep decision, run its refute-don't-confirm checklist on the candidate: independent verifier that never saw the fix reasoning, evidence-based per-claim verdicts, blast-radius scan. The statistical gate (`evaluate`) and the structural verifier catch different failure modes — use both.
- **The document skills (`docx`/`xlsx`/`pptx`/`pdf-documents`) are ready-made bench-task surfaces.** "Produce a workbook with these computed columns / a deck with these sections" is real work with a deterministic verifier (re-open the file, assert contents) — exactly the real-work-surface + independently-verifiable pair that cardinal rule #5 demands, and a graded `contains`/`numeric` task-set can check the extracted content.

## Visual / TUI Evaluation via tmux (for CLI/TUI frontend-design benchmarks)

Most benchmarks compare JSON from `/v1/messages` — but that **cannot see what a human sees**. When the thing under test is *rendered output* — markdown formatting (tables, code fences, lists), the Ink TUI's layout, colors, alignment, spinners, wrapping, the thinking/tool-call panes — you must evaluate the **actual terminal render**, not the raw model text. A model can emit perfect markdown that the TUI then mangles; only a capture shows it.

**Use the native `TmuxSession` tool** (proven method — same one used during the earlier active-improvement rounds; it wraps `TmuxCapture.ts`/`TmuxManager.ts`, stores metadata in `.cortex/tmux-sessions/`, binary via `TMUX_BIN`). The tool exposes **create → send commands → capture output → list → kill**. The agentic flow:

1. `TmuxSession create` — a persistent session sized like a real terminal (e.g. 200×50; also test 80×24 — different widths expose different wrapping/overflow bugs).
2. `TmuxSession send` → `cd $WORKSPACE/omniclaude-v4 && neoncortex` (Ink UI; or `cortex-cli`). Wait for boot.
3. `TmuxSession send` → the prompt that exercises the rendering under test (e.g. *"Show a markdown table of the 5 cheapest models with a fenced code example"*). Wait for the stream to finish.
4. `TmuxSession capture` — **this captured pane IS the metric.** It's the human-visible truth; the raw model text is NOT (a model can emit perfect markdown the TUI then mangles — only the capture shows it).
5. Evaluate the capture for **frontend-design deficiencies**, treating the render as a real UI surface (hierarchy, alignment, contrast, density — not just "did text appear"):
   - markdown table aligned / borders intact? code fence syntax-highlighted vs. raw backticks?
   - wrapping at the pane width, or overflow / truncation?
   - colors readable, spacing/padding sane, no doubled/garbled lines?
   - thinking & tool-call panes legible and not stealing the answer's space?
6. Fix the renderer (`packages/tui/src/ink-ui/...`), rebuild, **re-capture, diff before/after** — same keep/discard discipline as the code loop. `TmuxSession kill` when done.

*(Direct shell equivalent without the tool: `tmux new-session -d -s T -x 200 -y 50` → `tmux send-keys -t T '…' Enter` → `tmux capture-pane -p -e -t T > render.txt` (`-e` keeps ANSI color) → inspect → `tmux kill-session -t T`.)*

## Quick-Start (copy-paste into a session)

```
I need a multi-model benchmark. Pick a specific task:

TASK: "In omniclaude-v4, find [specific file/function]. Report: (a) path,
(b) complete implementation, (c) [specific detail], (d) [edge case behavior].
Be precise, cite line numbers."

Dispatch arms:
- Arm A: model=deepseek-v4-pro, same prompt
- Arm B: model=claude-sonnet-4-6, same prompt  
- Arm C: model=claude-haiku-4-5, same prompt
- Control: I (Opus) will answer directly

Then compare all 4 answers side-by-side and report discrepancies.
```

## Location Reference

- Server: `$WORKSPACE/omniclaude-v4/packages/server/dist/index.js`
- Server log: `/tmp/omniclaude-server.log`
- Bench results / deficiency ledgers: `$WORKSPACE/omniclaude-v4/.cortex/bench/`
- Routing matrix (the metric store): `$WORKSPACE/omniclaude-v4/.cortex/router-matrix.jsonl`
- **Cortex skill (load it — full tool/subsystem reference incl. `TmuxSession`, `WorkspaceManager`):** `.agents/skills/cortex/SKILL.md`
- **Worktree/team proven pattern:** `WorkspaceManagerTool` (core: `tools/definitions/`, executor: `executors/.../execution/`) + memory `agent-team-workspace`
- **TUI capture proven pattern:** `TmuxSession` tool, `TmuxCapture.ts` / `TmuxManager.ts`, sessions in `.cortex/tmux-sessions/`
- Harness deficiency trail (the running ledger): `.claude/projects/-home-runner-workspace/memory/omniclaude-v4-harness-deficiencies.md`
- Auto-research source/inspiration: `github.com/karpathy/autoresearch` — `program.md` is the "lightweight skill" analog of THIS file; `prepare.py` (fixed eval) ≙ our ground-truth control; `train.py` (mutable) ≙ the harness code (worktree-isolated).

## DELTA 2026-07-28 — env-flag benchmarking, zombie definitive check, receipt promotion

**Scope reminder (operator-ratified):** this skill is a GUIDE for driving nexus-cortex
as a headless subagent — pin model, run task, report. The heavy machinery (worktrees,
autoresearch gates, ledger ceremony) is for deliberate harness-improvement rounds,
not every run.

- **Env-flag arms MUST verify the flag reached the server** — the definitive check is
  `tr '\0' '\n' < /proc/<serverpid>/environ | grep <FLAG>`, run AFTER identifying the
  pid that actually owns :4000. A 2026-07-28 A/B lost THREE arms to a stale flagless
  server: even the bracketed full-path pkill (`node [p]ackages/server/dist/index.js`)
  misses relative-argv instances (`node dist/index.js`, CLI-spawned with cwd inside
  packages/server). Kill by PID after `ps -eo pid,args | grep "[d]ist/index.js"`,
  never trust the pattern alone.
- **`cortex --env KEY=VALUE` delivery to an auto-spawned server is UNVERIFIED** (first
  probe was confounded by the zombie above). Until verified with a clean /proc check,
  launch flagged servers manually.
- **Render-path questions: test the adapter IN-PROCESS before server A/Bs.** Import the
  built adapter from `packages/core/dist/adapters/`, feed it the REAL session records +
  a real modelConfig, inspect output. Minutes vs hours; separates "code wrong" from
  "env/plumbing wrong". A disposable `console.error` sed-patched into dist (rebuilt
  clean after) resolves the remaining live-path questions.
- **Recall probes need discriminators.** Facts derivable from visible prompts
  invalidate a recall probe (the model re-derives). Use exact-string forms only the
  hidden channel contains (stored `yellowsix` vs re-derivable `yellow6`) + a
  tag-visibility question as the mechanism check.
- **Model cards can silently reroute your test path**: both deepseek v4 cards are
  HYBRID (`reasoning.supported: true`) — a branch keyed on "non-reasoning model"
  never fires for them. Read the card (`packages/core/src/models/cards/...`) before
  designing a branch-coverage A/B. Related provider fact — CORRECTED 2026-09-01 (operator caught the stale claim; verified by
  live recall probe): DeepSeek's reasoning replay is MODE-SPLIT. NO-tools multi-turn: prior
  `reasoning_content` is ignored as context (the original finding — true only there). WITH the
  `tools` param (the agentic path): prior reasoning_content MUST be passed back (400 on omission)
  and the model GENUINELY CONDITIONS on it — a seeded string present only in a prior turn's
  reasoning_content was recalled verbatim inside a tool chain. So DeepSeek-in-agentic-mode is an
  INTERLEAVED thinker within a task (like the Anthropic dialect); the amnesia is only across user
  turns. Implications: reasoning rides in context every call (input grows with it — cache-read
  makes it affordable); loops are reinforced by the accumulated REASONING trail, not just content
  (strengthens the mentor-as-decorrelator case); replaying its own reasoning there is
  in-distribution, coherence-preserving. Docs: api-docs.deepseek.com/guides/thinking_mode. STYLE ALSO CORRECTED (trajectory-measured, chess-best-move 41 blocks): DeepSeek's per-turn reasoning is INCREMENTAL delta-continuation on its readable trail (0 task-restatements in 38 blocks; openings cite prior conclusions), median ~540 tok/interval with escalation spikes on hard branches — the same economy as Claude interleaved at moderate effort. The 'verbose amnesiac re-deriver' lore is dead on both axes for the tools path.
- **Publishing results:** promotion to the public proofs is SELECTIVE — one command,
  `npx tsx scripts/canon/canon-receipt.ts <ledger.md> --claim "..."` (secret-scan
  refusal, append-only, auto-indexes `nexus-canon-store/receipts/`). Future CLI face:
  `cortex autoresearch bench --public-benchmark`. Routine runs stay local ledgers.

## ⚑ QUEUED EXPERIMENT (operator 2026-08-13): tool-profile A/B — see memory `detllm-twil-candidates`
Hypothesis: tool-surface size × model capability interact (frontier models gain from lean/bash-only —
mini-SWE-agent precedent, ~16K fresh-session floor is mostly tool defs; small models lose — schemas
scaffold their action space; webgpu-2B control-trio precedent). Build `CORTEX_TOOL_PROFILE=full|lean|
bash-only` + trimmed sys-prompt, then matrix 3 profiles × 3-4 pinned models via `autoresearch
experiment`. If confirmed: tool profile becomes a per-model-card property + router dimension. Strong
candidate for the FIRST autonomous MCP campaign.

## DELTA 2026-08-22 — 🔴 D61: steering layers are PART OF THE INSTRUMENT

Operator hypothesis VERIFIED from canon transcripts: ShellTool's dedicated-tool
redirect guard (bare `cat`→"Use the Read tool instead", flag-free `grep`→Grep,
`sed -i`→Edit, literal `echo > f`→Write — ERRORS, not executions) was ACTIVE in
every P-series door bench, because `CORTEX_TOOL_ANCHOR` is first-turn-only and
the session reverts to the full profile (where all redirects fire) right after
the anchor framed the model bash-native. 218 blocks + 12 permission denials in
92 recorded sessions, top offenders = bench cells. Bias direction: door arms
were taxed MORE and still won → door-vs-full verdicts are CONSERVATIVE-safe;
per-cell token/latency numbers include redirect retry cycles; door-VARIANT
comparisons (bash-edit vs bash-plus) carry unmodeled noise.

RULES (standing):
1. Every cell RECORDS the steering state (`CORTEX_TOOL_REDIRECTS`, profile,
   anchor) as instrument parameters — like temperature (D20) and mode (D28).
2. Door / bash-framed cells run `CORTEX_TOOL_REDIRECTS=off` (lever shipped
   2026-08-22, changeset heredoc-bash-permissions) unless steering is the
   thing under test.
3. Heredoc-heavy tasks: the permissions whitelist is heredoc-aware as of the
   same changeset (stdin-only heredocs whitelisted; writes → graylist).
   Benches on OLDER harness versions re-inherit the old `/[<>]/` ejection —
   pin the harness version in the cell record.
4. Guidance built for weaker models becomes measurement sabotage once models
   outgrow it — when a capability assumption changes, re-audit every layer
   that encodes it.

## DELTA 2026-08-29 — the two dominant TB2 deficiencies now have env-gated fixes (ship dark)

The A′ distiller quantified the top fail classes (retry_loop×24, wrong_artifact×12); both landed as env-gated
fixes in the published harness (nexus-cortex 4.86.0), OFF by default, each validated to FIRE end-to-end via a
LIVE SEEDED test (the operator vetoed synthetic tests — "previous synthetic tests have not been very good"):

- **retry_loop → AskForAdvice v2 forced tool_choice** (`CORTEX_MENTOR_FORCE=true` + `MENTORSHIP_ENABLED=true`,
  helper=deepseek-v4-pro): on high-confidence thrash (`resolveThrashState`), forces the apprentice to consult a
  stronger mentor for one turn. FIVE DeepSeek wiring bugs found+fixed by SEEDED-thrash validation (seed
  DecisionStore `{"success":false}`×6 + `CORTEX_THRASH_MIN_TURNS=1`, drive a failing bash task, watch DEBUG) —
  see cortex-tool-development §DELTA + harbor-bench §DELTA(b).
- **wrong_artifact → EndTurn Stage-4 requirements verifier** (`CORTEX_ENDTURN_GATE=true` +
  `CORTEX_ENDTURN_REQUIREMENTS=true`): the mandatory-finish gate rejects a finish whose requirements attestation is
  empty/malformed/unverified, forcing the model to re-read the task and attest each stated requirement with proof.
  Validated by driving a task-shaped mutating turn with the gate armed (Stage-4 rejected 3× → model re-attested →
  passed → clean finish).

🔴 TWO STANDING METHODOLOGY LESSONS from this arc:
1. **"gated-off + green tsc ≠ working."** A dormant, compile-clean mechanism can be fully broken (v2 had 5 hidden
   wiring bugs) OR already complete (EndTurn had 0) — ONLY a live seeded run distinguishes them. Never trust a
   ship-dark feature, or bench it, until a seeded trigger proves it fires. Ground-truth beats inference (§Cardinal 2).
2. **A prior matrix with the lever OFF IS the control.** When measuring a new lever whose baseline you already ran
   (e.g. the A′/TB2 matrix ran both levers off), the efficacy bench is TREATMENT-vs-known-control (single-arm),
   not a fresh 2-arm spend. Don't re-measure a control you already have banked with the same harness+task+model.

## DELTA 2026-09-05 — Local harness as a BUDGET-OFFLOAD subagent + config-mirroring (validated live: flash-vs-pro build A/B)

Operator framing: driving REAL work through the local `cortex` harness (DeepSeek models) draws **ZERO from the Anthropic
weekly cap** AND doubles as a live capability test (Cardinal Rule #5 — real-work surface). Use it for extraction/build/analysis
delegations you'd otherwise spend sonnet/opus on; keep the Anthropic tier only for the hardest judge/synthesis leg. This IS the
cortex-bench "drive a model as a subagent" pattern with a cost motive — a DELTA, not a new skill. Validated 2026-09-05: flash vs
pro each built a real CF-worker durability fix (def-2332d425c8), orchestrator-verified `tsc`-clean; both correct.

Five reusable techniques this run added (not previously in this skill):

1. **Prove the path before trusting it.** `cortex --new --quiet -m deepseek-v4-flash "reply with TOKEN"` → expect the exact token.
   The CLI auto-spawns a server on :4000 in the CWD (dies on repl crash — re-runnable). ai-proxy up = 405 on a bare GET.

2. **Config-mirroring — make local == a DEPLOYED/bench config.** To reproduce the harbor bench's exact behavior locally, assemble
   its COMMON + adapter levers into an env file and `source` it before launch (env-OVERRIDE — do NOT mutate the 56KB
   `.env.example` lever ledger; alt path = edit `.env.example` then delete `.env` so it regens on boot). Source of the COMMON =
   harbor-bench `verify-armer.sh` (the `COMMON=` line) + the adapter's `env[...]` sets (`nexus_cortex_agent.py`). Key reson levers:
   `CORTEX_ENDTURN_RESOLVER=true CORTEX_ENDTURN_GATE=true CORTEX_ENDTURN_REQUIREMENTS=true MENTORSHIP_ENABLED=true
   MENTORSHIP_HELPER_MODEL=deepseek-v4-pro CORTEX_LIFT_PLAN=true CORTEX_TOOL_ANCHOR=bash-edit MAX_TOOL_ITERATIONS=1000
   TOOL_BUDGET_SOFT=400 CORTEX_TURN_DEADLINE_MS=<0.9×budget_ms> …` (full guard set in the reson-config). Echo a `config:` line at
   launch to PROVE the vars are live. 🔴 The local server runs DEFAULT config unless you do this — never conflate a default-config
   local run with bench behavior.

3. **Crash-surviving setup (workspace, NOT /tmp).** A repl crash wipes `/tmp` — it ate a run's scratchpad + the running task once.
   Put the runner + config + task brief + isolated arm copies + logs under the WORKSPACE (`$WORKSPACE/.bench/local-ab/`).
   The running process still dies on crash, but the SETUP survives → relaunch is one command, not a rebuild, and the log persists
   so you can read how far it got.

4. **Light isolation for a single-file build task.** Full worktree + `npm install` is overkill when the task edits ONE file. Instead:
   copy just the target dir (minus `node_modules`) per arm (`rsync -a --exclude node_modules`), and for the orchestrator's own
   verification `ln -s <real>/node_modules node_modules` then `npx tsc --noEmit`. Cheaper; still real typecheck.

5. **Runner-script shape (`run-arm.sh <arm> <model>`).** `set -uo pipefail`; pre-create the log (`: > "$LOG"`); `pkill -f
   "packages/server/dist/index.js" || true; sleep 2` (fresh server, correct CWD — the CLI reuses a live :4000 server with the WRONG
   cwd, so restart between arms); `cd` the isolated arm; source secrets + config; `export DEBUG=true`; `timeout 620 cortex --new
   --quiet -m "$MODEL" "$(cat task.txt)" >> "$LOG" 2>&1`; then append `WALL=`, `grep -c "wall-clock deadline reached"`, and
   `index_ts_lines`/`FIX_NOTES` status. Run arms SEQUENTIALLY (server-CWD collision forbids same-server parallel).

Deficiency datapoints from the live run (feed the ledger): (a) **deepseek-v4-pro fetch-failed 1 of 2 runs** (flash 0/1) — pro-path
transport wobble; discard-and-rerun the confounded fetch-fail. (b) Harness agents **could not run their own `tsc`** (git/npm in the
nested monorepo copy timed out) → they fell back to inspection; the orchestrator must do the authoritative typecheck.

## DELTA 2026-09-06 — local-server config verification + the stale-server-reuse trap
Verifying the LOCAL cortex server's effective config (e.g. confirming a .env / .env.example change took):
- **The config dashboard is `GET http://localhost:4000/health/config`** — JSON `{generatedAt, groups:[{group, levers:[{key,what,codeDefault,effective,source,active}]}]}`. Extract a lever: iterate `groups[].levers[]`. NOT :4001 (that port isn't the server). A lever absent from `groups[]` means it's not in effectiveConfig's REPORTED set (a display gap) — check the server's `/proc/<pid>/environ` for ground truth, not just the dashboard.
- **🔴 `cortex --new` REUSES a live :4000 server — it does NOT respawn.** So editing config/dist/.env and "restarting" via the CLI hits the STALE server (loads old config/dist). To actually pick up a change: `kill -9 <serverpid>` FIRST (get pid via `pgrep -f "[p]ackages/server/dist/index.js"`), confirm `:4000` free, THEN start. This caused hours of "the change isn't taking" confusion 2026-09-06. Check the server's `etime` — if it predates your edit, it's stale.
- **pkill self-match (exit 144):** `pkill -f "packages/server/dist/index.js"` matches your OWN bash command line. Use the bracket trick: `pkill -f "[p]ackages/server/dist/index.js"`.
- **🔴 .env config loading — REBUILT 2026-09-06 (old `.env.example`-copy model is DEAD; full map: [[nexus-cortex-config-architecture]]):** `omniclaude-v4/.env` is now the MASTER (tracked, colorized, the lever ledger); its GENERATED mirror `.env.defaults` (committed, `scripts/sync-env-defaults.mjs`) is READ LIVE as the lowest default layer — NOT copied. `bootstrapEnv` seeds a KEYS-ONLY `~/.cortex/.env`, runs a one-time migration, and loads `.env.defaults` LAST (lowest). Precedence: user `~/.cortex/.env` > real env > `.env.defaults` > `DEFAULT_SETTINGS` floor. To run reson locally: nothing to do — the master (`packageRoot/.env`) already carries it and loads above the mirror; a clean box gets reson straight from `.env.defaults`. `/health/config` reflects it (levers show `source=env` because `.env.defaults` loads into process.env).
- **Reliable per-run bench config = env-override** (export levers before launch) — deterministic, wins over `.env.defaults` (first-wins: a value already in process.env is never overwritten by a base file). This is WHY the harbor-bench adapter's env-var A/B still works untouched. A LOCAL-only personal setting that must not ship goes in the `# LOCAL-ONLY` section of the master `.env` (stripped from the mirror) or `omniclaude-v4/.env.local` (gitignored, highest precedence).

## DELTA 2026-09-23 — comparator discipline
Before quoting any public leaderboard number as a target: fetch the board's own data source (Terminal-Bench 4.0: the Harbor Hub leaderboard-read
function; AA: its methodology page names the harness), record agent + harness + repeats + date beside the number, and never carry a 2.x
attribution onto a 4.0 number. The 09-23 correction: AA's V4.1 Flash 26.8 = mini-swe-agent, not Terminus 2; no Terminus 2 rows on the 4.0 board.
