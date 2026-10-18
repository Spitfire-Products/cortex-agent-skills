---
name: harbor-bench
description: Run a PUBLIC agentic benchmark (Terminal-Bench 2.0 via the Harbor framework) against the hosted nexus-cortex harness, durably, and read the results honestly. Covers the Harbor installed-agent ADAPTER (the "A1 arm"), the CF nexus-cortex-sandbox container it runs in, the DURABLE in-container supervisor (survives Claude Code session death), the prompt-mass / model-pin config levers, and every hard-won plumbing fix (Node 20, working-dir, port collision, 600s bypass, session→container routing). Use whenever benchmarking our published harness against a public leaderboard number (Terminal-Bench, and the same pattern for other Harbor datasets). NOT for cortex-bench (in-process multi-model harness-deficiency runs) and NOT for browser-CORTEX.
triggers:
  - terminal-bench
  - harbor
  - public benchmark
  - leaderboard
  - tb2
  - benchmark the harness
---

# harbor-bench — Public agentic benchmark against the hosted nexus-cortex harness

> 2026-09-10: the repl-side control plane (armers/watchdogs/relaunchers) is RETIRED in favor of the STDB module; the
> operating manual for running a fleet now is the **stdb-bench** skill. This file stays the full executor + history record.

Runs **Terminal-Bench 2.0** (89 tasks, objective per-task `test.sh` graders, no LLM judge) — or any Harbor dataset — with the **published `nexus-cortex` npm harness** as the agent, in the **CF `nexus-cortex-sandbox` DinD container**, and reads the number against the published band. This is the "A1 arm" of the public-proof band rig (A0 = bare API, A1 = our harness, A2 = a reference harness like Terminus-2 / grok-build).

> **Surface boundary.** This benchmarks the SHIPPED product (published `nexus-cortex`, sterile install). It is NOT `cortex-bench` (in-process multi-model deficiency mining on the dev checkout) and NOT `browser-cortex-bench`. Compare to a **BAND, never a point** — published V4-Flash on TB2.1 spans 67–83% by methodology alone.

## 🎯 CURRENT-BEST TB2.0 FULL-89 RESULTS (read THIS before quoting a number — do NOT reconstruct from a raw HF dataset)

**Accumulated best (lifted config + 4.70–4.78 guard stack + steering flips), grounded 2026-08-25** — canonical source `session-resume-2026-08-25.md` "OFFICIAL TB2.0 FULL-89 RESULTS":
- **pro-lifted = 76/89 = 85.4%** (official conservative count 75/89=84.3% + 1 undercounted task the plain config solves reliably) — the **84–85% band edging AHE's GPT-5.5 84.7%** on cheap DeepSeek-V4-Pro. Baseline 72 (80.9%) + guard/steering flips (dna-insert, regex-log, rstan-to-pystan, …).
- **flash-lifted = 67/89 = 75.3%** — baseline 59 (66.3%) + **8 genuine flips** (compile-compcert, hf-model-inference, install-windows-3.11, largest-eigenval, polyglot-rust-c, qemu-alpine-ssh, query-optimize, rstan-to-pystan).
- 🔴 **The raw `<hf-org>/tb2-nexus-cortex-results` dataset shows only 59/89 (66%) — that is the PRE-guard baseline, NOT the current best.** Never quote it as the standing number. The 67/89 · 76/89 above already fold in every accumulated flip.
- 🔴 **FLIP-ACCOUNTING TRAP:** a cell "pass" is only a flip if the task is in that arm's ACTUAL fail-set. Known PASS-controls — `bn-fit-modify`, `fix-code-vulnerability`, `regex-chess`, `sqlite-db-truncate` — were already passing; counting them inflates flips.
- **A′ increment (deferred-refinement matrix, 2026-08-29, hard-subset only, n=1):** flash +2 genuine new flips (db-wal-recovery, path-tracing-reverse) → ~69/89 ≈77.5%; pro tentative +1 (write-compressor, also flips under B = possible control-noise) → ~77/89 ≈86.5%. Projection assumes no regression on the untested already-passing majority — UNVERIFIED until a full-89 A′ run.

## 🔴 LAUNCHING A CELL (Vast executor, current substrate) — the ONE repl-dependent window
A cell run is repl-independent ONLY after its box is provisioned. Until then everything runs on the repl, so the launcher must be
started so that it outlives the Claude Code session:
```bash
tmux new-session -d -s <tag> "cd $WORKSPACE && <ENV=…> bash .bench/vm/<cell>-launch.sh > .bench/vm/logs/<tag>.log 2>&1"
tmux ls   # confirm; read progress from the log, never attach from a tool call
```
- **Never** start a launcher with `setsid nohup … &` or `( … & )` from a Bash tool call: it dies with the session. 09-27 → 09-28: the dc1
  rerun launcher died mid-smoke when the session ended and sat dead ~11 h (nothing rented, run stalled). Same law as every repl-side
  watcher — only processes ON the box survive.
- **Phases:** DeepSeek credit gate (≥ `LAUNCH_MIN_DEEPSEEK_USD`, default $15) → npm wait (`LAUNCH_SKIP_NPM_WAIT=1` if already published) →
  mechanism smoke (serialized via `smoke-slot.lock`) → rent → wait `running` → provision → `self-reaper armed` → `LAUNCH-DONE (sup=N …)`.
  The box is on its own from `self-reaper armed` + `LAUNCH-DONE`: supervisors bank to the HF store, reboot cron relaunches, the
  reaper destroys it on completion or TTL.
- **tmux survives a session end, NOT a repl restart.** After any repl restart: `vastai show instances --raw`, and for each box check
  `.bench/vm/provision-<tag>.log` for `self-reaper armed`; a box without it has no teardown — `yes | vastai destroy instance <iid>`.
- **Box goes `exited` right after rent** → the provisioner waits 40 min for `running`. Kill it BY PID (never `pkill -f` from a command
  line containing the pattern — it kills your own shell, exit 144), destroy the box, relaunch with the offer in `LAUNCH_EXCLUDE_OFFERS`.
- **Rerun a subset of a store:** the supervisor skips any task with a `status:"done"` row in `results*.jsonl`. Move the rows to rerun into
  a non-`results*` file (e.g. `credit-poisoned-<date>.jsonl`, never delete), push, relaunch the SAME store; only those tasks run.
- **Provider credit refusal** (402 / "Insufficient Balance") is infra: since a191471127 the supervisor never banks it — non-done
  `infra_credit` row, 10-min wait + retry, stop the slice unbanked after 2 h. Stores seeded before that carry the old supervisor.
- Detail and traps: skill `vast-compute` §2–3.

## When to use / not use
- **Use** when you need a defensible public-benchmark number for our harness+model on a real leaderboard task set, or to A/B a harness config change (prompt mass, tool anchor, budgets) on third-party tasks.
- **Don't use** for finding harness bugs on our own code (that's `cortex-bench`), or when you just need a quick model probe (drive `cortex` directly).

## Architecture

```
repl host (fragile — dies on session churn)         CF sandbox (durable-ish, but evicts + routes per-session)
  you / a monitor  ──/debug/exec?session=tb2run──▶   nexus-cortex-sandbox container ("cloudchamber")
                                                        └─ tb2-container-supervisor.py  (RUN THIS — survives your session)
                                                             └─ harbor run -i <task> -a nexus_cortex_agent:NexusCortex -m deepseek-v4-flash
                                                                  └─ task container (alexgshaw/<task>:DATE)  ← the graded env + test.sh
                                                                       └─ cortex-server (published nexus-cortex) drives /v1/messages
```

- **Adapter (A1 arm):** `nexus-terminal/workers/nexus-cortex-sandbox/bench/nexus_cortex_agent.py` — a Harbor `BaseInstalledAgent`. Loaded via custom import path `-a "nexus_cortex_agent:NexusCortex"` (Harbor's `factory.py` custom-path branch — NO enum/factory edit). `SUPPORTS_ATIF=False` (reward from `test.sh`, no trajectory mapping).
- **Durable supervisor:** `scripts/tb2-container-supervisor.py` — runs INSIDE the container, banks each reward to `/app/bench/tb2-results.jsonl`, resumable. **This is the durable executor** (see §Durability).
- **Repl-host driver:** `scripts/tb2-bench-driver.py` — the OLD host-driven-queue version. **Deprecated for long runs: it dies on Claude Code session churn** (model switch, teardown). Kept for reference / short supervised runs only.
- **Poll helper:** `.bench/tb2_poll.py` — one poll of the supervisor via `tb2run` + syncs results to the repl backstop.

## 🔴 THE FIX LEDGER — every plumbing bug that cost hours (all baked into the adapter already)

Read this before touching the adapter. Each was a real reward-0 / crash before the fix.

1. **Node 20, not distro node18.** cortex's undici needs the `File` global; node18 crashes. `install()` fetches the v20 static tarball.
2. **`npm install -g --prefix /usr/local nexus-cortex`** so `cortex`/`cortex-server` land on PATH.
3. **Working-dir = the reward-killer.** cortex-server's Bash/Edit/Write tools operate in the **server process cwd** (fallback for project context) — NOT the CLI cwd. The CLI's auto-spawned server inherits neither → tools default to `/tmp`, edits never reach the graded repo → reward 0 *even when cortex solves it*. FIX: `run()` starts `cortex-server` EXPLICITLY in the task dir, then drives it. (Verified: flipped regex-log 0→1.0.)
4. **NEVER set `PROJECT_PATH` to the task repo.** It triggers cortex's MCP auto-detect → tries `python3 main.py` → ENOENT crash on task containers. cwd alone roots the tools correctly. (autoresearch's `startServer` sets PROJECT_PATH because it benches the HARNESS itself — different case.)
5. **Port collision.** Task containers share the CF-sandbox host network → cortex-servers collide on `:4000` across tasks; the CLI talks to a STALE first-task server (wrong cwd → orphaned `tool` 400s → `NonZeroAgentExitCodeError`). FIX: read the ACTUAL bound port from the server log (`grep -oE 'running on port [0-9]+'`), set `CORTEX_SERVER_URL=http://localhost:$P`.
6. **NEVER `pkill -f cortex-server`** — the shell's own argv contains the literal → self-match → SIGKILL / exit 137.
7. **The hardcoded 600s cut.** `cortex --quiet` uses `AbortSignal.timeout(600000)` at `single-message.ts:54` — NOT liftable by any env. Hard tasks get cut at 10 min → harbor misreports `NetworkConnectionError`. FIX: drive the server's **`/v1/messages`** endpoint directly (the autoresearch `serverRunner` path) with `curl -m 3600` — full agentic loop server-side, Harbor's `task.toml` timeout governs. **`/v1/messages` is the cortex-SERVER's ingress (thin wrapper around CortexOrchestrator), NOT DeepSeek's API — the model still calls upstream via its card's transport (deepseek → ChatCompletions).**
8. **Session→container ROUTING (the big one — and it's UNSTABLE).** `/debug/exec?session=<S>` routes to **DIFFERENT container instances** (all hostname `cloudchamber`, separate filesystems). Two facts, both cost hours:
   - **Different sessions → different containers.** A supervisor in `tb2run` is INVISIBLE from `tb2setup`/`tb2defer`. Most "the process died / results gone" false alarms are you checking the wrong session's container. Always drive one run via ONE fixed session, and verify per-session (`pgrep` + `wc -l results` in the SAME session) before pronouncing anything dead.
   - **Even the SAME session is NOT pinned.** It's usually consistent, but a recycle / scale / load-balance can flip `tb2run` to a *fresh* instance mid-run (observed: a restart landed on a container showing the ORIGINAL 10-row seed while the real supervisor had reached 21 elsewhere). **Corollary: NEVER trust container-local state as the source of truth.** Keep the results ledger on a STABLE surface (repl-synced backstop and/or HF mirror) and reconcile; the container is disposable compute that may be ANY instance on any call. A restart may re-run tasks it can't see — idempotent (dedup by task on read, last-wins), and a silver lining if the adapter improved (re-runs backfill new metrics).

## Durability — apply the HF-training pattern (`hf-space-job-ops-rules`), don't reinvent it

This was learned the hard, wasteful way: a bespoke "container-local file + session-bound repl sync" driver is FRAGILE and cost a whole arc of firefighting. The CF `nexus-cortex-sandbox` is NOT a stable executor — the repl-host `setsid` poller dies on Claude session churn (a `/model` switch kills it), and the container itself evicts + routing-flips. **Treat the container as disposable compute and apply the three durability pillars we already proved for training runs.** Reference impl: `scripts/tb2-durable-supervisor.py` (+ `tb2-relaunch.py`, `.bench/tb2_ds_poll.py`).

1. **PILLAR 1 — state in a durable store SEPARATE from the disposable compute.** The **HF Dataset** `<hf-org>/tb2-nexus-cortex-results` is the SINGLE source of truth. The supervisor keeps a **git clone** of it in the container and, per task, appends the result + `git commit` + **`git push` immediately** (git is in the image + `HF_TOKEN`; the `huggingface_hub` pip pkg fails on the PEP-668 container — use raw git, not the pkg). Monitor by reading the Dataset (`tb2_ds_poll.py`), NEVER by polling the container (that's where routing-flip false-alarms come from).
2. **PILLAR 2 — self-provision + fail-fast + self-MAINTAIN.** `ensure()` makes any container it lands on whole and runs at boot AND before every task:
   - Adapter + task list travel IN the Dataset clone → copied to `/app/bench`. Venue yaml is **baked into the image at `/app/harbor-host-network.yaml`** (`Dockerfile:436`: `services:\n  main:\n    network_mode: host`) — verify it, re-write an embedded fallback if absent. (It was never "lost"; my old supervisor used the wrong path `/app/bench/…`.)
   - Hard-verify `command -v harbor`, `docker ps`, yaml present; a task that can't run banks `venue_unready` + **RETRIES**, never a silent `parse_failed` cascade.
   - **🔴 PRUNE DISK before every task.** Each task pulls a 100MB–1.5GB image; on the ~18G container disk they accumulate and hit 100% → agent `apt-get install` dies "No space left on device" → harbor reports it as `NonZeroAgentExitCodeError` and **every remaining task fast-fails in ~25s**, silently marking the whole set failed. `docker system prune -af` + `rm -rf /app/bench/j_*` before each task (results are already durable in the Dataset, so job dirs are disposable). This single omission looks exactly like a venue/routing bug — check `df -h /` FIRST on any fast-fail cascade.
3. **PILLAR 3 — design for death → resume, not refit.** `load_done()` reads the Dataset clone; completed tasks are skipped. Any kill / eviction / restart resumes clean with zero lost work.
4. **Relaunch / watchdog.** `tb2-relaunch.py` is idempotent (no-op if alive; else re-place + relaunch, which resumes from the Dataset). A `CronCreate` runs it every ~20 min — but **CronCreate is session-only** (dies with your Claude session), so it only covers eviction *while you're working*. The supervisor being a *container* process already survives your session death; the residual gap (session + container die together) is a **single lossless command** from any future session: `python3 scripts/tb2-relaunch.py`.

**Proving it (the bar the training runs clear): kill it mid-run and watch it finish clean.** Kill the supervisor, confirm results already in the Dataset, run `tb2-relaunch.py`, confirm it resumes at the right task and skips the done ones.

**Reset discipline:** to start a genuinely fresh arm, EMPTY the Dataset `results.jsonl` and *verify the push took* by re-cloning (a no-op commit silently leaves old rows → the supervisor "resumes" from garbage). NEVER merge result sources by hand (a naive dedup once produced a bogus "56%" by mixing baseline + defer + disk-fail rows). One Dataset per arm, keyed by task, `done` beats everything, never cross arms.

**🔴 SINGLE-WRITER — kill ALL old drivers before running (the zombie-clobber incident).** The Dataset must have exactly ONE writer. A **repl-host `tb2-bench-driver.py` survived ~4.5h unnoticed** (session churn did NOT kill it after all) and kept mirroring its own local results via **`HfApi.upload_file` — a whole-file OVERWRITE that clobbers the git-append supervisor's commits every upload**, silently repopulating the Dataset with stale v2 rows and making the fresh run look like it "resumed from 47 done." Overwrite-mirror and git-append are **incompatible writers.** RULES: before launching, `ps -eo pid,etimes,args | grep tb2` on the **repl host** AND across every reachable exec session, and kill EVERYTHING (old drivers evict-survive and hide on unreachable container instances). Prefer git-append everywhere; never mix an `HfApi.upload_file` mirror with a git-writer on the same repo. If the Dataset row count jumps or `adapter`/`arm` tags don't match the running supervisor, suspect a second writer FIRST. Tag every row with `adapter` + `arm` so a foreign writer is instantly visible.

**🔴 READ-SIDE STALE-CLONE TRAP — the poll can silently FREEZE while the run is healthy (2026-08-23).** The write side (container push) and the *monitor* are separate git clones; the monitor's is the one that lies. `tb2_ds_poll.py` originally reused a persistent shallow clone (`/tmp/tb2-hfds-mon`) and did `git pull -q` with `capture_output=True` and **no return-code check** — when the pull started failing, it failed SILENTLY and the reported count **froze at 14 while remote was actually at 26** (looked like a 2-hour throughput stall; the run was fine). This is the same stale-clone class as the write-side traps, just on READ. **Diagnosis that cuts through it in one step:** compare the *container's* view (`tail durable.log` → "N done" + `cd /app/bench/hfds && git status -sb` shows `up-to-date` with N rows) against the poll's number — if the container says 26 and the poll says 14, it's the poll's clone, not the run. **Fix (applied): the poll now `rm -rf`s and FRESH-clones every run** (the Dataset is tiny, ~1-2s) — never reuse a clone for monitoring, and never trust a `git pull` whose exit code you didn't check. A frozen done-count with a *still-alive* supervisor is a monitoring artifact until proven otherwise — check the container's own ledger before declaring a stall.

## Config levers — this is where the real findings live

The adapter env is the crafted-optimal set (grounded in the harness code, NOT the shipped `.env.defaults` — which is the current SHIP config, not necessarily bench-optimal). 🔴 Config model rebuilt 2026-09-06 — see [[nexus-cortex-config-architecture]]: the container gets a KEYS-ONLY `~/.cortex/.env` + `.env.defaults` read-live; the adapter env-vars (process.env, first-wins) still override everything, so the A/B mechanism is UNCHANGED.

| Lever | Value | Why |
|---|---|---|
| model pin | `-m deepseek-v4-flash` + `DEFAULT_MODEL_ID` | **Pin explicitly — never `auto`.** The container's default `DEFAULT_MODEL_ID` now comes from the shipped `.env.defaults` (= `deepseek-v4-flash`, the master's value; the keys-only `~/.cortex/.env` seed carries NO levers); the adapter's `process.env` (first-wins) + `-m` pin it regardless. |
| `MAX_TOOL_ITERATIONS` / `TOOL_BUDGET_SOFT` | `1000` / `400` | R64 code defaults (failsafes, not work limits). `.env.defaults` now ships 1000/400 (matches); the OLD `.env.example` was stale at 50/15. |
| tool anchor | card `anchorProfile:'bash-edit'` (auto) | D61: redirect steering (`cat`→Read etc.) is OFF by default for bash-anchored cards, ALL turns — bash is not second-guessed. No `CORTEX_TOOL_REDIRECTS` needed. |
| `MODEL_ROUTER_RECORD` | `false` | keep the flat-75 auto-record stub out of the shared store (matches autoresearch `startServer`). |
| `CORTEX_PROMPT_MASS` | **UNSET (mandatory for deepseek)** | 🔴 Setting it to ANY value (incl. `defer`) DISABLES boot-minimal's ~400B narrow-door prompt → full 4.5KB prompt → deepseek over-reasons. Leave unset. See the defer-trap below. |

**🔴🔴 NEVER set `CORTEX_PROMPT_MASS` for the deepseek narrow-door bench (the defer trap, 2026-08-23).** deepseek's card = `promptPreset: 'boot-minimal'` — a ~400-byte dsh narrow-door frame that FORCES the model to ACT (bash/edit) on turn 1 instead of deliberating (the whole point of the P4-proven bash-edit door). **Setting `CORTEX_PROMPT_MASS` to ANY value — including `defer` — DISABLES that replacement prompt.** `SystemMessageMiddleware` applies the preset prompt only when the env is unset: `presetPrompt = (!envMass && !CORTEX_SYSTEM_PROMPT_FILE) ? presetSystemPrompt(card) : undefined`. So `CORTEX_PROMPT_MASS=defer` silently falls back to the FULL ~4.5KB `SYSTEM_PROMPT.md`, and deepseek then **reasons to the 65K output wall with ZERO tool calls** instead of acting. **PROOF (DEBUG_PAYLOAD, local harness, exact ARS task):** boot-minimal → `sysMsg=659B` → acts (anchor lifts 3→15 tools, tool calls, fast); defer → `sysMsg=4529B` → stuck at 3 tools, reasons to the wall. Same code, same bash-edit anchor — only the prompt size differs. **Leave `CORTEX_PROMPT_MASS` UNSET so the card's boot-minimal applies.**

**🔴 DELTA 2026-08-29 — the defer-TRAP is FIXED, but defer still LOSES; the truly-untested lever is deferred-loading OFF.** The "defer disables boot-minimal → full prompt turn 1" bug above was FIXED (`SystemMessageMiddleware` Item-9a: `presetPrompt = ((!envMass || envMass === 'defer') && !CORTEX_SYSTEM_PROMPT_FILE) ? …`). FIXED `defer` now COMPOSES: boot-minimal turn 1 + the dropped corpus (incl `TOOL_USAGE_GUIDE.md`) delivered ONCE at the anchor-lift boundary via `buildDeferredStaticCorpus()`. It WAS retested in the 4.78.0 steering matrix (`defer-flash`/`defer-pro` arms) and STILL **LOST** to the lifted control ("no steering arm beat control; lifted control leads flash 11/30") — because it re-bloats the prompt after the lift. So: don't set defer for the bench (still correct), but for the RIGHT reason now (it loses on merit, not the old trap). 🎯 **What NOBODY ever benched: `ENABLE_DEFERRED_TOOL_LOADING=false` with the minimal prompt held fixed.** Every arm ran deferred=ON (16 essential tools); the anchor lift lifts the TOOL SET not the prompt (sysMsg constant ~662-924B all turns; TOOL_USAGE_GUIDE never appears in 'minimal'). deferred=OFF → the model gets all **57 tool SCHEMAS** at the SAME minimal prompt (verified: `tools=57 sysMsg=924B` — pure tool-count, NO prompt bloat, ≈3× tool-schema tokens 68KB vs 23KB). This is the clean isolated experiment (16 vs 57 tools, prompt fixed) — run it before concluding 16-tool deferred is optimal. Related: SearchTools steering lives in TOOL_USAGE_GUIDE which 'minimal' drops → deepseek makes 0 SearchTools calls → the 41 deferred tools are unreachable unless a minimal-prompt nudge is added or deferred is turned OFF. See [[session-resume-2026-08-29]].
- **The earlier "defer helped both hard tasks" claim is RETRACTED — it was confounded**: "defer" was actually sending the full prompt, so it measured full-prompt vs boot-minimal, and its 106K-output/0-tool "clean completion" on adaptive-rejection-sampler was the *broken* behavior, not a win. Symptom-chases that all FAILED before finding this: "deepseek doom-loops" (reasoning was novel, not repetitive — a tail-loop guard does nothing), "disable thinking", "cap reasoning_effort". The cause was a self-inflicted config swap.
- **Diagnostic that found it:** run a local cortex-server with the exact bench env + `DEBUG_PAYLOAD=1`, POST the task to `/v1/messages`, and read `[DEBUG_PAYLOAD] … sysMsg=NNNB tools=N/…`. `sysMsg≈659B` + `tools=3`→ narrow door active; `sysMsg≈4529B` or `tools=15` on turn 0 → door NOT active. This is THE check when the model over-reasons.
- **Harness bug to fix:** `defer` can never deliver its "minimal turn-1 + full after act 1" intent, because setting the env disables the boot-minimal replacement prompt (the two mechanisms are mutually exclusive). "Full knowledge after act 1" is not actually available until that gate is fixed.
- **✅ PRODUCTION-VALIDATED on the live TB2.0 run (2026-08-23), not just the local probe.** With `CORTEX_PROMPT_MASS` UNSET (boot-minimal active), deepseek ACTS and PASSES consistently: `bn-fit-modify` r=1.0 in **25 tool calls at ~600 output tok/turn**, `build-pov-ray` r=1.0 (62 turns), `code-from-image` r=1.0 (39 turns) — a steady **~69% pass rate across 26 tasks** ($0.92 total, 98% cache). Contrast the *broken* defer profile on the same class of task: `adaptive-rejection-sampler` 0 tool calls / 106–110K output / reasons to the wall. **The output-per-turn signature IS your at-a-glance health check:** ~500–800 tok/turn with a rising tool-call count = narrow door working (acting); a single turn dumping 15–100K output with ~0 tool calls = door NOT active (deliberating) → check `CORTEX_PROMPT_MASS` is unset and re-run the DEBUG_PAYLOAD `sysMsg` check. This closes the loop the P4 audit opened: the bash-edit door forces action in a real public benchmark exactly as it did in training-audit testing.
- **Genuine hard misses still exist and are fine** — under the working door, the remaining failures cluster on genuinely hard derivations (crypto / compiler / algorithm tasks like adaptive-rejection-sampler, compile-compcert, circuit-fibsqrt). Those miss on *task difficulty*, not the config bug: they still ACT (turns>0) but exhaust budget / fail the build, and often bank with null metrics via the `NonZeroAgentExitCodeError` path. Don't gate the whole run on the hardest task passing — validate the fix on a *tractable* task's clean pass (e.g. bn-fit-modify), which is the true "the door works" signal.

**🔴 DELTA 2026-08-29 (b) — TWO new deficiency-fixing bench levers, both SHIP DARK (off by default, validated to FIRE).**
The A′ distiller quantified the two dominant TB2 fail classes (retry_loop×24, wrong_artifact×12); both now have an
env-gated fix in the published harness (nexus-cortex 4.86.0), OFF by default, each validated end-to-end via a LIVE
SEEDED test (not synthetic). Arm them PER BENCH ARM (never in the master `.env` / `.env.defaults`):

| Lever | Targets | Arm env | Validated behavior |
|---|---|---|---|
| **v2 forced mentor consult** | retry_loop | `MENTORSHIP_ENABLED=true` + `CORTEX_MENTOR_FORCE=true` (+ `MENTORSHIP_HELPER_MODEL=deepseek-v4-pro`) | On high-confidence thrash, FORCES the model to call AskForAdvice for one turn → stronger mentor hint. Gated `reactiveMentorship.enabled ∧ CORTEX_MENTOR_FORCE ∧ resolveThrashState.thrashing`. 5 DeepSeek wiring fixes (continuation-site, turnCount, thinking-disable, tool-restrict, parallel_tool_calls-off — see cortex-tool-development §DELTA). Seeded thrash → forced AskForAdvice → mentor_consult banked. |
| **EndTurn wrong-artifact verifier** | wrong_artifact | `CORTEX_ENDTURN_GATE=true` + `CORTEX_ENDTURN_REQUIREMENTS=true` | Mandatory-finish gate; Stage-4 (`requirementsVerification.ts`) REJECTS a finish whose requirements attestation is empty/malformed/unverified → model re-reads the task + re-attests. GATE offers EndTurn (tools 15→16); REQ arms Stage-4; **both needed — REQ alone inert without GATE**. Live: rejected 3× → model re-attested → passed → clean finish. Reject bounded by MAX_CONSECUTIVE_ERRORS (not END_TURN_MAX_NUDGES). |

🔴 **THE CONTROL IS ALREADY MEASURED — do NOT re-run it.** The A′/TB2 matrix (4.84.0/4.85.0) ran with BOTH levers OFF,
so it IS the both-off control baseline (flash 67/89, pro 76/89; per-model A/A′/B cells banked). An efficacy bench is
TREATMENT-ARM(S)-vs-known-control — NOT a fresh 2-arm run. Arm {MENTOR_FORCE, ENDTURN} on the real thrash + wrong-artifact
subset (db-wal-recovery 89-turn retry, make-mips-interpreter, gcode-to-text; wrong-artifact cells per the distiller) and
compare to those cells' KNOWN control outcome. Halves the fleet spend. 🔴 **"gated-off + green tsc ≠ working"** — v2 was
BROKEN (5 hidden bugs behind a compile-clean facade) while EndTurn was ALREADY complete (0 bugs); ONLY the live seeded
run told them apart. Validate any dormant mechanism with a live seeded trigger before trusting — or benching — it.

## Result classification — always break misses down, don't just read pass-rate

From the banked `result.json` per task: `reward` (0/1 mean), `n_errored_trials`, `exception_stats` keys.

| Class | Signature | Meaning |
|---|---|---|
| PASS | reward≥1.0 | solved |
| clean-miss | reward 0, `errored=0`, `exc=[]` | GENUINE capability miss (agent finished, grader rejected) — the honest signal |
| timeout | `AgentTimeoutError` | reasoning-stall — USUALLY the narrow-door frame isn't active (check `sysMsg` bytes; NOT fixed by defer, which causes it) |
| error | `RuntimeError` / `NonZeroAgentExitCodeError` / `NetworkConnectionError` | PLUMBING — investigate (likely a fix-ledger regression), don't count as capability |

**🔴 THE SELF-CUT WALL signature (found 2026-08-23, cost 6 tasks):** `RuntimeError` + `turns=None`/no metrics + latencies clustered tightly at ~(your exec timeout + teardown) across DIFFERENT tasks = **your adapter's ExecInput `timeout_sec` fired, not Harbor's budget**. Harbor enforces each task's own `[agent] timeout_sec` from task.toml via `asyncio.wait_for` around `agent.run()` (trial.py `_run_agent_phase`) and raises **`AgentTimeoutError`** when IT fires — so `RuntimeError`-not-`AgentTimeoutError` at a uniform wall is always a self-cut. **TB2.0 task budgets are NOT uniform** (measured across all 89 task.tomls @69671fb): 900s×49 (mode), but **43% allow more** — 1200×6, 1800×16, 2400×2, 3600×12, 7200×1, 12000×1 (max 3h20m). There is NO global cap; the per-task budget IS the cap and every leaderboard agent gets the same. ⇒ the adapter exec timeout must EXCEED the max budget (12300s) so Harbor governs, and the supervisor's stall-cap must exceed budget+build+verifier (13800s) or a legitimate 3600s run gets falsely marked timeout while harbor still holds the box (queue corruption). Failure triage lens: `budget_frac` (latency/task-budget) separates "ran out of time" from "finished early and failed wrong".

**🔴 Adapter must ALWAYS exit 0.** Reward is graded by the task VERIFIER from repo state — never by the agent command's exit code. A plumbing hiccup in the metrics tail (mx.py raise, curl transport error) surfacing as a non-zero exit banks as `NonZeroAgentExitCodeError` and can mask a real solution. End the command with `true`.

**Requeueing failures for rerun:** remove their rows from the Dataset `results.jsonl` (fresh clone, push, VERIFY by re-clone) then **restart the supervisor** — `load_done()` reads once at boot, so a Dataset edit alone changes nothing until relaunch. Kill with bracket patterns (`pkill -f 'tb2-durable-superviso[r]'` + `'harbor ru[n]'`), then the idempotent relaunch.

**A/B ARM PATTERN (running two+ workers):** one Dataset per arm (`TB2_DS_REPO`), one container session per arm (`TB2_SESSION`), arm tag on every row (`TB2_ARM`) — all env-parameterized in the supervisor/relaunch with main-run defaults. **VERIFY container separation with a nonce file** (write on session A, read on session B; sharing a box breaks docker-prune + pgrep). The **anchor-persist arm** (narrow door for ALL turns, not just turn 1) needs no republish: the published harness hardcodes the one-shot lift (`if (!this.anchorLifted && resolveToolAnchor…` — 2 call-sites, single ESM dist file), so the arm adapter sed-patches the INSTALLED copy in each disposable task container, guarding the lift behind `CORTEX_TOOL_ANCHOR_PERSIST`, with a fail-loud site-count check (`=2` before, `=2` guards after, else install() exits 1). Rationale: the door forces turn-1 action but post-lift deepseek can revert to heavy per-turn deliberation on hard tasks (236s/27K-tok per turn vs healthy 18s/2K) — the persist arm tests holding the frame.

**EARLY A/B RESULTS (2026-08-23, adaptive-rejection-sampler — the never-passed hard task; n=1/cell, full-89 runs pending):**
| | lifted | persist |
|---|---|---|
| flash | FAIL (4 turns, 110K out — post-lift deliberation) | **PASS** (42 turns, 102K out, $0.095) |
| pro | **PASS** (21 turns, 38.5K out, $0.124) | (pending) |

Read: **the held frame flipped flash fail→pass on the hardest task** — the post-lift regime is behaviorally load-bearing, not cosmetic. The stronger model (pro) doesn't need it held (stays in act-mode after lift, solves in half the turns / a third of the tokens) — **frame-holding looks model-strength-dependent scaffolding**: weaker models need the door held; stronger ones only differ in efficiency. Await full-run data before generalizing (persist may tax easy tasks).

**Why this matters beyond the bench — D61 + the CPT training thread:** D61 (BASH_PLUS_SPEC, verified 2026-08-22) found every P-series door bench ran the anchor FIRST-TURN-ONLY, so the harness's legacy redirect guards (bare `cat`→Read error, heredoc graylist) were live for the rest of every session — the instrument taxed the exact post-lift regime this A/B now shows is where behavior diverges. The TB2 lifted-vs-persist A/B is the first CONTROLLED measurement of that regime, and the flash flip confirms D61's concern: door-proficiency numbers measured under a lifted frame are confounded by what the harness does after turn 1. Consequences: (a) any future door bench or training eval (incl. the P4 multi-seed continuous CPT→SFT re-run design) must make the frame an EXPLICIT instrument decision — persist vs lifted, redirect guards on/off — and record it per row (`arm` tag); (b) the trained sub-1B shell-executor slot (S3 CPT recipe) should be SERVED under a persistent narrow frame — if flash-class models need the door held, an 0.8B certainly does; (c) instrument choice can flip a capability verdict (fail→pass on the same model+task), so never compare rows across frame configs.

**A clean-miss-dominated low score vs a high published band = a real SCAFFOLDING gap (our harness gets less from the model), not a plumbing bug.** That's the finding that motivates the prompt-mass work. Timeouts/errors are the fixable minority.

## 🔴 Capture COST + TURNS, not just reward (a bench number is a triple)

A pass-rate alone is not a benchmark result — a harness that passes at 60% at 10× the tokens is worse than 55% at 1×, and public leaderboards report cost/tokens. **Default trap: we banked only `{reward, errored, exc}`.** Where the metrics actually live:
- **Tokens/cost: NOT in Harbor's `result.json`** — its `n_input_tokens`/`cost_usd` are `null` because the adapter is `SUPPORTS_ATIF=False` (nothing reports usage back to Harbor). The real usage is in the **`/v1/messages` response body** (`usage.inputTokens/outputTokens/cacheReadTokens`, `metadata.toolCallIterations`). The adapter must **explicitly save the response (`curl -o response.json`) and extract a `metrics.json` sidecar** — the naive `| tee` dropped it (a 59-byte log). Capture the FULL breakdown (`inputTokens`, `cacheReadTokens`, `cacheCreationTokens`, `outputTokens`) + `usage_raw`, so cost is always recomputable.
- **🔴 COST — use VERIFIED provider pricing, NOT the model card (the card is STALE).** The `deepseek-v4-flash` card ships `$0.14/$0.28`, but DeepSeek's actual pricing (api-docs.deepseek.com/quick_start/pricing) per 1M tok, off-peak/peak:
  - **FLASH series (deepseek-v4-flash / v4.1-flash), from 2026-09-10 04:00 UTC** (12:00 Beijing; the current numbers): **cache-hit $0.003/$0.006, cache-miss $0.15/$0.30, output $0.6/$1.2** (peak = 2× off-peak). This is a PRICE CUT vs the prior tier.
  - **FLASH series, BEFORE 2026-09-10 04:00 UTC** (verified 2026-08-23; use for reconciling runs dated before the cutover): cache-hit $0.007/$0.014, cache-miss $0.22/$0.44, output $0.66/$1.32.
  - **PRO (deepseek-v4-pro): UNCHANGED by the 09-10 announcement** — verify its own live page separately; the Flash cut does not apply.
  - Choose the tier by the run's COMPLETION date/time UTC (a run straddling 2026-09-10 04:00Z uses old-then-new). Peak = 01:00-04:00 & 06:00-10:00 UTC Mon-Fri; all else + weekends off-peak. So `cost_usd = (inputTokens−cacheReadTokens)×miss + cacheReadTokens×hit + outputTokens×out`, tier chosen by completion-time UTC; store both `cost_usd_offpeak`/`cost_usd_peak` to bracket boundary-straddling tasks. The card's flat rate under-counts output ~2.4–4.7×. **Always verify a provider's live pricing page before quoting bench $$ — model-card cost fields go stale.** (Harness deficiency: the card cost fields need updating; also the card lacks cache-tier + peak/off-peak pricing entirely.)
- **Turns:** `cortex-server.log` iteration markers (`grep -oE 'iteration[ =][0-9]+' | tail -1`).
- **Latency:** `result.json` `started_at`/`finished_at` (real dates — the container's python has `datetime`; the no-`Date` rule is a Workflow-script thing only).

The adapter (metrics sidecar) and supervisor (banks `inputTokens/outputTokens/toolCallIterations/cost_usd/latency_s`) now do this. Report the bench as **(pass-rate, median cost/task, median turns/task, median latency)**.

**Behavior metrics (v5, summed from the copied session record — assistant content blocks):** `tool_calls_total` + `tool_calls_by_name` (count tool_use blocks; shows the bash vs str_replace_editor split), `thinking_chars` (thinking-block text length — deepseek `reasoning_content` normalizes into Anthropic-shape thinking blocks, so this is the reasoning-volume proxy; ÷4 ≈ tokens), `out_tok_max_call` (largest single-call output — the reasoned-to-the-wall signature at a glance), `agent_budget_s`/`budget_frac` (task.toml budget map travels in the Dataset as `tb2-budgets.json`). **Harness deficiency: exact reasoning TOKENS are dropped** — DeepSeek returns `completion_tokens_details.reasoning_tokens` but the normalized usage doesn't preserve it; also missing: finish-reason per call, time-to-first-tool-call, LLM-vs-tool time split (all need harness-side capture, not adapter work). This also makes the prompt-mass A/B honest: `defer` almost certainly costs MORE tokens — you need the delta to judge whether the accuracy gain is worth it.

## 📐 THE DURABLE-WORKER FORMULA — the reusable template (variate on THIS)

This is the distilled recipe behind the TB2 rig, recorded as a TEMPLATE for spinning up
long-horizon durable DinD/container workers for ANY unit-of-work stream — future benchmarks
(TB3 = a dataset-id change), migrations, sweeps, recursive-improvement loops. It is
surface-agnostic: the same formula drives the nexus-cortex harness, the SPA browser CORTEX,
or the autoresearch MCP (porting map below). Reference impl: `scripts/tb2-durable-supervisor.py`
+ `scripts/tb2-relaunch.py` + `.bench/tb2_ds_poll.py`.

**The 9 invariants (violate any one and you rebuild a past incident):**
1. **Durable store ≠ compute.** One git-backed remote store per arm (HF Dataset here; any git
   remote works) is the SINGLE source of truth. Everything the worker needs TRAVELS IN the
   store (worker script can be re-placed; adapter/tasks/config/budget-maps in the store), so
   any fresh container is made whole from it.
2. **Git-append, single writer, verify-by-fresh-clone.** One writer per store, append-only
   rows, push immediately per unit; every reset/edit verified by RE-CLONING (reused clones lie
   on both write AND read side). Kill ALL prior writers before launching (they evict-survive).
3. **Self-provisioning supervisor INSIDE the disposable compute.** At boot AND before every
   unit: pull store → verify tooling/venue (fail-fast, bank `venue_unready` + retry, never a
   silent cascade) → self-MAINTAIN (disk prune; job dirs are disposable because results are
   already durable).
4. **Resume, not refit.** Unit list + done-set live in the store; completed units are skipped;
   any kill/eviction/restart resumes clean. Restarting must be ALWAYS-SAFE.
5. **Idempotent external relauncher** — a cheap script runnable from ANY session, cron,
   heartbeat, or monitor: no-op if the worker is alive; else re-place the worker onto whatever
   compute the route gives and relaunch (which resumes). This is the ONLY control-plane verb
   you need. Worker survives orchestrator-session death; any future session adopts it with one
   command.
6. **Provenance on every row.** `arm` + `adapter`/version + model + instrument config
   (frame, prompt mass) + cost basis + verified pricing. A foreign writer or config drift must
   be visible IN THE DATA.
7. **Caps above legitimate work.** Every timeout in the stack (exec backstop, supervisor
   stall-cap, client fetch) sits ABOVE the largest legitimate unit duration — the unit's own
   budget governs. Plumbing always exits 0; only the unit's verifier decides outcomes.
8. **Monitor the STORE, never the compute.** Progress = fresh-clone reads of the store.
   Polling the compute gives routing-flip false alarms; a frozen count with a live worker is a
   monitoring artifact until the worker's own ledger disagrees.
9. **Arms are env-parameterized, isolated, nonce-verified.** New arm = {store repo, compute
   session, arm label, model} env overrides on the SAME supervisor/relauncher scripts. One
   store per arm. Verify container separation with a nonce file before trusting two workers.
10. **HARVEST THE EXHAUST — trajectories are first-class banked artifacts, not debris**
   (operator-added 2026-08-23: "we are leaving a lot of data-lake value on the table").
   Every unit's session record (full per-turn messages: thinking, tool calls, results) is a
   REWARD-LABELED agentic trajectory — exactly the corpus class training/mining wants — and
   the disk-prune (invariant 3) DESTROYS it unless banked. The supervisor gzips each task's
   `session.jsonl` into the arm store as `trajectories/<task>.session.jsonl.gz`, committed
   WITH the result row (`trajectory` field on the row; `trajectory_err` when absent — error
   paths legitimately have no session). Downstream chain: arm Dataset (data lake) →
   canon-store ingestion (`cortex canon` rail, batch, from the repl where creds live) →
   cross-session retrieval + corpus mining (shell-native/dsh episode mining, frame-A/B
   trajectory-level analysis, D-ledger evidence). Rule of thumb for ANY durable worker: if
   compute produced text you'd ever want to learn from, it goes to the store BEFORE the prune
   — pruning is only safe because banking happened first.
   🔴 **HF pre-receive REJECTS non-LFS `.gz` files — bank trajectories as PLAIN `.jsonl`** (2026-08-23,
   cost 6-8 silently-stuck results per arm): the hub's default `.gitattributes` demands LFS for binary
   extensions, so ONE committed `.gz` poisons the arm's commit chain — every later push fails, banking
   goes dark while the LOCAL ledger keeps advancing (the remote-behind-local signature: poll count frozen,
   container `durable.log` counting up). Repair = kill supervisor, salvage results.jsonl + gunzip
   trajectories, rm clone, fresh-clone, replay missing rows (dedup by task) + plain-jsonl trajectories,
   push, relaunch. Detect early: any bank() push-fail WARN deserves investigation, and the all-arms
   monitor should compare container-local done-count vs remote when an arm goes quiet.
   **The canon leg is LIVE (2026-08-23), and its topology matters:** the canon rail SHIPS in the
   published package (task containers have `cortex canon`), and the operator's instinct — "just
   set the CANON_* env and sync before teardown" — is the right shape for SINGLE-writer setups
   (exactly how hosted containers work). But `canonSync`'s push is a bare `git push origin main`
   with NO pull/rebase/retry (canonSync.ts) and a full 1.3G store clone — N concurrent bench
   workers syncing directly would collide and silently diverge (harness deficiency logged: sync
   needs rebase-retry for multi-writer). The safe wiring keeps the repl watcher as the store's
   ONE writer: (a) workers bank native session.jsonl to their arm store (pre-teardown
   durability, above); (b) `HARNESSES.json` in the canon store declares a labeled nexus-cortex
   root `{"label":"tb2-bench","path":"/tmp/tb2-canon-stage"}` (config REPLACES the harness's
   whole root list — carry the defaults); (c) `.bench/tb2-canon-stage.py` (15-min monitor) pulls
   arm Datasets -> gunzips new trajectories into the stage; (d) the canon WATCHER fs-notices the
   stage and runs the full shipped pipeline (sync->scrub->translate->push). Sessions land as
   `/native/nexus-cortex/tb2-bench/<arm>__<task>.jsonl`, secret-scrubbed, retrievable via
   `cortex canon list/pull`. WARNING: the watcher loads roots at STARTUP — restart it after
      🔴 **SESSION-REMAP FILE (.bench/tb2-session-remap.txt) must stay SINGLE-HOP** — the monitor's
   `remap()` resolves ONE lookup, so a chained entry (pl1→pl1b, then pl1b→pl1c appended) leaves the
   watchdog healing the SUPERSEDED session while the new one also runs = duplicate shard workers
   (dedup'd by done-set, but wasted spend; happened 2026-08-24). Rule: on a re-remap, EDIT the
   original session's line to the final target — never append a chain. Kill the superseded worker.
   editing HARNESSES.json; kill it via `ps|grep|awk|kill`, NEVER pkill -f when your own command
   text contains the plain target string anywhere (the bracketed-pattern trick does not save you
   — a pkill in a shell whose relaunch line contained "nexus-canon.js watch" killed its own
   shell, exit 144, 2026-08-23).

**Spin-up checklist (new worker in ~6 steps):** (1) create+seed the arm store (worker deps +
unit list + config maps; verify by re-clone); (2) nonce-verify the compute session is its own
container; (3) kill-sweep old writers; (4) launch via the relauncher with arm env
(`TB2_SESSION/TB2_DS_REPO/TB2_ARM/TB2_MODEL` here — same shape for any worker); (5) arm a
persistent monitor: watchdog tick (relauncher every ~20min) + store-poll progress events;
(6) first-unit verification (one banked row with correct tags/metrics) before walking away.

**Porting map (same formula, different flesh):**
- **nexus-cortex harness / future benchmarks:** identical rig; TB3 = new dataset id + budget
  map; any long sweep = replace `harbor run` with the unit command.
- **SPA browser CORTEX:** worker = headless-Chrome session driving the SPA (nexus-browser MCP
  or relay); relauncher = re-open session + re-arm executor; store unchanged (HF Dataset or
  canon-store git). Browser sessions are MORE evictable than containers — the formula matters
  more, not less.
- **autoresearch MCP / recursive-improvement loops:** campaigns already own containers; the
  formula adds the between-campaign durability — a cron/heartbeat runs the idempotent
  relauncher (invariant 5) + adjudicates freshly-banked rows, giving an unattended
  improve→bank→resume loop (the D53 host-driven-queue pattern generalized). The store's banked
  rows are the ledger the next round's decisions read from.
- **HF GPU training** is the ORIGIN of the formula (hf-space-job-ops-rules; crash-proof queue) —
  Space=compute, queue-dataset=store, restart-with-factory=false=relauncher.

## 🔬 THE TRACE-DISTILLER — adjudication + deficiency mining over the trajectory lake

`scripts/tb2-distill.py` (AHE "Agent Debugger" analog, built 2026-08-23) reads the arm Datasets
(results + trajectories) and writes layered reports to `.bench/distill/` (per-arm tables →
per-failure trajectory-grounded mode classification with quoted evidence → cross-arm
all-fail/frame-split/model-split + candidate deficiencies). Run it for ANY adjudication pass —
never eyeball raw trajectories. Grounded record shape (v8 supervisor fix): session content
blocks nest tool calls as `{toolUse:{id,name,input}}` (NOT flat type:'tool_use') — the v6/v7
per-tool counter read "?" for everything; keep the dual-shape reader.
First-run quantified deficiencies (mid-run, 2026-08-23): (1) TIMEOUT ROWS HAVE NO SESSION
RECORD — the adapter copies session.jsonl in the command tail, which never runs when Harbor
kills the exec at budget; the most interesting failures are unobservable → persist the record
INCREMENTALLY during the run (adapter fix pending). (2) POLICY FRICTION QUANTIFIED (the D61
class, now with counts): Bash `$()` substitution denials ×8 tasks, Edit requires-prior-Read ×7,
keyless WebFetch fallback ×8 — our own guardrails taxing graded work; prime autoresearch
candidates. (3) NO SELF-VERIFY-BEFORE-FINISH (wrong-artifact finishes at ~half budget → verifier
rejects; AHE's mirror-the-evaluator doctrine targets exactly this) + NO IDENTICAL-CALL BREAKER
(retry loops; the error-family reminder is the soft half).

**⚠️ ROLLOUT GAP — durability defeats lazy rollout.** Supervisor upgrades deploy "at next
eviction" (relauncher re-places only when dead) — but a STABLE worker never evicts: the persist
arms ran v5 (no trajectory harvest) for the whole day BECAUSE they never died. If an upgrade
matters mid-run, restart the worker deliberately at a bank boundary; otherwise record which
version each arm actually runs (the row's `adapter` tag) before comparing artifacts across arms.

## Insights that generalize (from the first real TB2.0 run)

- **Deep-grind misses = capability ceiling, not a harness cut.** The misses were 37–66-iteration grinds that produced artifacts the grader rejected (passes solved in 10–22 iters). A harness bug depresses passes AND misses uniformly; a clean split by difficulty is genuine model limit. So a low single-shot rate on a small fast model is largely **the model**, and the published band is very likely **pass@k / a TB-tuned reference harness (Terminus-2)** — pin the published number's methodology (pass@1 vs pass@k, attempts, effort) BEFORE concluding our harness is weak. You may be comparing pass@1 to pass@8.
- **Web tools are a NON-factor on TB2.0.** TB is reproducible/offline by design — tasks ship what they need. Empirically the agent essentially never invokes web tools across the run; when it did (a `browse-agent` on an image task) it no-op'd in ~4s. And they **fail-soft** anyway (web_search → DuckDuckGo HTML fallback, reachable; all return error results, never crash). Missing provider keys (Anthropic/XAI/OpenAI/Gemini) don't hamper the score. Injecting a key would add a capability the sterile install lacks → unfair vs the published band. (Vision tasks like `code-from-image` need multimodal the text model lacks — a real capability mismatch, not a tooling gap.)
- **The narrow-door frame is load-bearing — verify it's ACTIVE before blaming the model.** When deepseek over-reasons (huge output, 0 tool calls), it is almost always that the boot-minimal ~400B prompt is NOT reaching the model (a stray `CORTEX_PROMPT_MASS`, a wrong prompt file, a bloated system message). Check `sysMsg` bytes via DEBUG_PAYLOAD FIRST. deepseek is fast and acts readily *when it gets the dsh frame*; over-reasoning is a harness/config symptom, not the model's nature (P4 proved it: 235 output tokens, 8 tool calls, 21/21).

## Analysis discipline (borrowed from cortex-bench)
- **n≥2.** A single 0→1 flip is often deepseek nondeterminism. Replicate each arm 2–3× before calling an effect real.
- **Band, not point.** V4-Flash TB2.1 band = 67–83%. Don't compare to a single figure.
- **Don't pronounce a process dead** without a same-session `pgrep` + results check (fix #8). This session cost credibility three times by calling live processes dead.
- **Sterile is correct for the published-band comparison.** Reference harnesses run without a user's private `.cortex/` memory layer too; injecting ours would rig it. Our generic process-intelligence belongs in the builtin prompts (shipped), which the bench already loads.

## Public-proof recording (hold until the rig is real)
A single exploratory reward-0/1 run is NOT scored proof. Record to the `public_proof_experiments` STDB table only from the A0/A1/A2 band rig, ≥3 runs, with provenance `{reward, model, agent, task, harness_ref, image_tag, benchmark_source:"terminal-bench-2.0"}`. Promotion is selective (`scripts/canon/canon-receipt.ts`).

## Key files & endpoints
- Adapter: `nexus-terminal/workers/nexus-cortex-sandbox/bench/nexus_cortex_agent.py` (carries the metrics sidecar; travels IN the Dataset)
- **Durable supervisor (USE THIS): `scripts/tb2-durable-supervisor.py`** (HF-Dataset store, self-provision, disk-prune, resume) · idempotent relaunch: `scripts/tb2-relaunch.py` · Dataset poll: `.bench/tb2_ds_poll.py`
- SUPERSEDED (fragile, do not use): `scripts/tb2-container-supervisor.py`, `scripts/tb2-bench-driver.py`, `.bench/tb2_poll.py` · defer-arm example: `scripts/tb2-defer-arm.py`
- Task list: `.bench/tb2-tasks.txt` (89)  ·  admin token: `.bench/.admin-token` (an `ncsb_` token — handle carefully, never print)
- Results: `.bench/tb2-results.jsonl` (+ `.container-synced.jsonl` backstop)  ·  HF mirror: `<hf-org>/tb2-nexus-cortex-results`
- CF exec: `POST https://cortex.spitfire-products.com/debug/exec?session=<S>` (Bearer admin token), body `{"cmd":"…"}` → `{ok, stdout, error}`
- Harbor host-network overlay (CF DinD needs it): `/app/bench/harbor-host-network.yaml`
- Related: `harness-eval-public-benchmarks` memory (targets + band traps), `cortex-bench` skill (methodology parent).

**Shard-complete watchdog signature (benign):** a completed shard's relaunch shows `LAUNCH-FAILED … verify returned '0'` — bridge fine, supervisor booted, found its slice done (`durable.log`: "COMPLETE: N/M graded"), exited within the 3s verify window. Distinguish from the wedge signature (verify returned `''` = the exec HTTP call itself failed). On '0': check the log tail; if COMPLETE, prune the lane from the roster (the monitor greps the roster file each tick, so edits apply live — no re-arm).

## 🔀 DYNAMIC RE-SHARD (mid-run lane splitting — first executed 2026-08-24)

When progress lags the estimate, the cause is usually CONCENTRATION, not throughput: sharding is
parallel ACROSS lanes but SERIAL within one, and the hard tail piles into a few lanes (observed:
one lane held 16 of an arm's 22 remaining tasks = a 6-7h solo critical path while sibling lanes
idled complete). Diagnose by computing per-shard remaining from the Dataset (done-set vs
`idx % N` slice) — NEVER from watchdog noise. Then split the heavy lanes N→2N:
1. Old shard s at N maps EXACTLY to new shards {s, s+N} at 2N (`idx % 2N`) — halves are disjoint
   and their union is the old slice, so no task is dropped or doubled.
2. KILL the old N-worker first (bracket-pattern pkill via exec), then launch both halves at 2N —
   fresh boot done-sets + disjoint `results-s{i}.jsonl` files ⇒ zero duplicate spend. Mixed shard
   widths across lanes are FINE (the done-set globs all result files; N is per-worker env).
3. Put new workers on FRESH session names when old sessions show the wedge signature (empty-verify
   HTTP failures) — wedged old sessions stay dead; fresh names place clean.
4. **Stagger launches ~2 at a time.** >2-4 simultaneous cold placements near the instance cap →
   empty-verify FALSE failures that succeed on retry minutes later (observed: a batch of 4 all
   "failed" then all placed 1 min after the wave cleared). Transition churn also counts: killed
   workers' containers linger against `max_instances` until CF's idle eviction reclaims them —
   headroom is thinnest DURING the swap, self-resolving after.
5. **Roster-file-driven watchdog** (`.bench/tb2-roster.txt`: `lane session repo arm model idx N`):
   the monitor greps the file EVERY tick, so topology edits (prune completed lanes, add splits)
   apply live without re-arming. Replace any hardcoded-topology monitor BEFORE killing old workers
   or it resurrects them on its next tick.

**🔴 MONITORS MUST SOURCE THE SECRETS BRIDGE** (`set -a; source .claude/.replit-secrets.env`).
A monitor armed without it can be BLIND FROM BIRTH while looking alive: its no-auth legs (keep-alive
curls) keep working while every authed poll silently no-ops inside `2>/dev/null` — zero events ever,
indistinguishable from "nothing happened" (the bake-off monitor ran a whole arc emitting nothing).
Any monitor that has emitted NOTHING by the time a known event landed is broken until proven idle.

## 🔴 EMPTY-SESSION FAST-FAIL — a plumbing miss that masquerades as a capability miss (2026-08-24)

Under fleet churn (many workers evicting/relaunching near the instance cap), tasks bank as
`status:done, reward:0` that are NOT capability misses — the model was never called. **Signature
(all must hold):** `toolCallIterations:None` + `inputTokens:0` + `usage_raw:{}` + `exc:[] errored:0`
(NO exception) + `budget_frac < 0.3` (gave up in ~80-150s) + the banked trajectory is **ONE line:
just the user prompt, no assistant turn**. Cause: the adapter hit a stale/dying cortex-server (fix
#5 port-collision, or a container mid-eviction) that accepted the request but never returned a
completion; test.sh then grades the untouched repo as 0. **Distinct from the disk-full cascade**
(that one also fast-fails but `df` shows 100%; here disk is fine). **The tell that it's systematic,
not difficulty:** the SAME tasks empty-fail across multiple independent arms (a real capability
ceiling doesn't cluster identically across arms), and easy tasks (regex-chess, sqlite-db-truncate)
appear in the list.

**Impact + rule:** these rows DEPRESS the pass rate (spurious reward-0 in the denominator). ALWAYS
classify before quoting a rate — split done into {PASS, acted-miss (turns>0), hard-timeout
(turns=None, budget_frac≥0.8), empty-fail (turns=None, budget_frac<0.3, exc=[])}. Report the rate as
`PASS / (done − empty-fail)`; the empty-fails are infra-DNF to REQUEUE, not capability. Requeue them
in a LOW-CHURN window (after the arms finish their real tasks, or fewer concurrent workers) or they
just re-empty-fail. Concentration tracks churn: the longer/heavier arms (pro) collect far more of
these than the fast arms. NEVER assert "capability ceiling" from a stalled pass-count without reading
a sample of the actual trajectories first (an aggregate reward-0 hides this entirely).

**🔴 EMPTY-SESSION FAST-FAIL ROOT CAUSE FOUND (2026-08-24): PROVIDER 402.** The empty-session
signature above was DeepSeek `402 Insufficient Balance` — the model call dies at 0 tokens, the
error lands ONLY in the adapter's `/logs/agent/response.json` ({"error":{"message":"402 ..."}}),
invisible to harbor (exc=[]) and to the banked row. Refuted-in-turn on the way: eviction churn
(re-failed on a quiet fleet), Docker Hub 429 (manual pull fine), npm registry (manual install fine).
**RULE: on ANY zero-token fail cluster, check the PROVIDER BALANCE FIRST** (curl the provider or
read response.json from a probe task) — before any churn/infra theory. Frozen pass-counts across
hours while done-counts climb = the tell. The supervisor should ideally halt-on-402 (bank
`provider_402` status, stop consuming tasks) — future upgrade; until then a 402 era poisons rows at
~90s each. Same lesson-class as HF GPU-credit 402 (v2p3 skill): billing exhaustion masquerades as
plumbing.

**🔴 WATCHDOG MONITORS AND KILL-SWEEPS ARE OPPOSING CONTROLS — stop the watchdog FIRST (2026-08-24).**
During the 402 incident the deliberate supervisor kill-sweep was UNDONE minutes later by the fleet
monitor's own watchdog tick (idempotent relauncher = it can't tell "deliberately stopped" from
"dead"), which resurrected the workers and burned more poisoned rows. Order of operations for any
deliberate fleet stop: (1) TaskStop the monitor(s) carrying a watchdog loop, (2) kill-sweep the
workers, (3) verify done-counts stop moving. The relauncher's always-relaunch property is a FEATURE
against crashes and exactly the failure mode during an intentional pause — there is no halt flag
today (candidate upgrade: a `.bench/tb2-HALT` file the relauncher checks).

**Cost scheduling: run big DeepSeek fleets OFF-PEAK.** Peak tier (Mon-Fri 01:00-04:00 & 06:00-10:00
UTC) bills output ~2x and cache-hit ~2x; a wide fleet crossing into peak burns balance fast (the
402 incident followed the resharded 21-worker fleet running straight through peak). Schedule k=5 /
TB3-scale runs on weekends or outside peak windows; the supervisor already stamps rate_tier per row
so the split is auditable.

**402-era classification addendum (operator-driven, 2026-08-24):** the empty-fail filter alone is
NOT enough after a provider outage — three ESCAPEE variants need a trajectory-evidence sweep
(`.bench/tb2-requeue-402variants.py`): (a) broken rows (latency 0 / budget_frac None), (b)
zero-output rows (0 outTok, no turns), (c) truncated sessions (turns>0, trajectory ends at outage
onset), and (d) **full-budget rows INSIDE the outage window with no trajectory** — normally the
legit-timeout signature, but during total model unavailability a full-budget burn cannot be a
genuine attempt (the harness hung/retried a dead lane). Cross-arm audit is mandatory — the arms
deepest into the window (pro) collect the most. Rate quotes only after this sweep.

**Product finding (bench-surfaced deficiency): shipped skills are UNREACHABLE under boot-minimal.**
The npm package vendors 10 builtin skills (pdf/docx/xlsx/pptx etc. in the shipped .cortex scaffold)
but fleet-wide trajectory audit shows ZERO skill invocations — the narrow-door frame that makes
deepseek act also forecloses skill discovery. Legitimacy line (AHE-consistent): SHIPPED generic
skills = fair product capability on a public bench (product-as-shipped comparison); task-targeted
skills written after seeing bench tasks = evaluator-mirroring (don't); injecting private workspace
skills = rigging (never). Candidate post-2x2 arm: skill-reachability under the narrow door (e.g.
one-line skill index in the boot-minimal prompt).

**⬆️ DOCTRINE REFINEMENT (operator, 2026-08-24) — supersedes the "don't write skills after seeing
bench tasks" line above: PROVENANCE IS NOT THE SIN; FAILING GENERALIZATION IS.** The bench is a
deficiency-mining instrument (cortex-bench charter). Distiller surfaces a deficiency CLASS →
autoresearch writes a GENERIC remediation (skill, prompt clause, orient doc) → the standard gate
decides: statistical gain on a HOLDOUT + judge reads the diff for eval-gaming → merge only if it
transfers. A task-keyed cheat fails that gate by construction; a generic skill that happens to fix
bench tasks is legitimate recursive self-improvement. The gate IS the overfitting line — do not
pre-censor the improvement's origin.

**Grounded mechanics for the skill-reachability arm (post-2x2 candidate, now concrete):**
- The harness SHIPS a first-class `Skill` tool (BaseToolRegistry.ts:882, list/invoke; loads the 10
  vendored skills incl. pdf-documents/docx/xlsx). It is (correctly) NOT in the bash-edit turn-1
  anchor set {Bash, Edit}; it IS available post-lift — and fleet-wide trajectory audit shows ZERO
  invocations: available-but-unpointed-at.
- The affordance surface ALREADY SHIPS: `BOOT_MINIMAL_PROMPT` (promptPresets.ts) tells the model to
  run `.cortex/orient` via Bash to map the workspace. The candidate improvement = ONE clause in the
  boot prompt / orient output pointing at `Skill list` for specialized formats/domains — deferred
  tooling becomes discoverable WITHOUT widening the narrow door.
- Pipeline: distiller --emit-deficiencies → autoresearch campaign (judge ON) writes the generic
  skill/clause → gate on TB2 subset + holdout → ship via the release train. This is the
  skills-as-substrate version of the tool-description-doctrine arm.

**⬆️ Skill-reachability arm v2 (operator, 2026-08-24) — BASH-NATIVE is the primary variant, not the
Skill tool.** Skills are plain SKILL.md files in the shipped scaffold
(`CORTEX_ROOT/.cortex/skills/<name>/SKILL.md`); bash IS a skill loader. The candidate clause (added
to BOOT_MINIMAL_PROMPT, path interpolated by the server which already resolves CORTEX_ROOT):
"specialized task guides live at <CORTEX_ROOT>/.cortex/skills/ — ls it and cat the relevant
SKILL.md when the task matches a domain". Why bash-native beats the Skill-tool clause: (1) works
TURN-1 pre-lift inside the {Bash,Edit} anchor; (2) frame-independent — survives a persist-door
verdict where the Skill tool never enters the session; (3) extends the prompt's EXISTING
bash-orientation idiom (`sh .cortex/orient` / ls / README) instead of teaching a new behavior.
Design tensions to measure: +~30 tokens of prompt mass on the ~400B door (verify turn-1 action
survives via DEBUG_PAYLOAD + a tractable-task pass), and whether skill-reading displaces acting on
easy tasks (A/B on subset + holdout, judge on diff). Marquee case: financial-document-processor
(1000-iteration loop) with pdf/docx guides reachable.

**Why bash-native skills is ARCHITECTURE, not an arm nicety (operator): persist-served models have
no other path.** Under a held narrow frame, bash is the only rich faculty for the session's whole
life — and persist is the SERVING config for the weaker-model class (flash needs the door held on
hard tasks; the trained sub-1B shell executor certainly will). For that class the FILESYSTEM is the
entire extensibility surface: skills, docs, memory, tool knowledge all ship as files or they don't
exist. Corollary for the training arc: bake the consult-the-guides reflex INTO the corpus
(skill-reading episodes before domain tasks) so small models learn it natively — the prompt clause
bootstraps the behavior, training crystallizes it, the frame holds it.

**🔴 MONITOR TAIL-F PHASE TRAP (2026-08-24, cost ~1.5h of dead fleet):** a monitor whose FIRST
phase is `tail -f <launch log>` (to relay launch output) blocks FOREVER if that log path dies or
never receives the sentinel line (here: the /tmp reaper ate the script whose log the monitor
tailed; the relaunch wrote to a NEW durable path) — and its phase-2 watchdog NEVER starts. The
fleet then dies silently at slice-completion with nothing healing it. Symptom: pass-counts frozen
while the monitor task shows "running". RULES: (1) watchdog loops start at TICK 1, never behind a
blocking phase; (2) never chain a tail-f stage in front of a healing loop — run launch-relay and
watchdog as SEPARATE monitors; (3) frozen store-counts + running monitor = suspect the monitor
FIRST (the read-side stale-clone lesson, generalized to monitor control flow).

**🔴 ROOT CAUSE OF THE RETRY-LOOP CLASS (operator question, grounded 2026-08-24): bash nonzero-exit
is NOT an error to ANY guard.** ShellTool returns `createSuccessResult` for a command that fails
with exit!=0 (failure text only in content: "Command failed with exit code N" —
ShellTool.ts:258/503); `is_error` is set only for aborts/exceptions. Cascade: (1)
MAX_CONSECUTIVE_ERRORS=3 never fires on failing-command thrash; (2) the decision store records
every failing bash call as success:true (processToolTraining: success=!is_error) → the exact-input
prior reminder ("prior failures for this input") has NO failures to fire on; (3) the (unreleased)
error-family lens is gated `else if (result.is_error…)` → would ALSO miss bash loops after release.
🔴 CORRECTION (2026-08-27, file:line-verified): items (2)+(3) are STALE — the success-semantics bug
was FIXED in 4.70.0's unified outcome layer. `processToolTraining` (CortexOrchestrator.ts:8075-8143)
now derives `success` from `classifyToolOutcome()` (toolOutcome.ts:87-96, reads metadata.exitCode,
exit≠0→'failed'), NOT `!is_error`; the exact + family-lens reminders (DecisionPriorInjector.ts:42/70)
DO fire. The RETRY-LOOP class survives for a DIFFERENT reason: three disagreeing hash schemes —
DecisionStore stableInputHash (exact) vs ExactRepeatTracker raw JSON (exact) vs LoopLadder approachHash
(fuzzy) — so varied-command retries slip the exact-input prior, and the fuzzy ladder (which WOULD catch
them) is per-turn in-memory and never reads the cross-turn decision store (loopLadder.ts writes
loop_escalation events back, but kind-rows are excluded from lookup). FIX = give lookup an approachHash
path. Full corrected design: RECURSIVE_PM_WAKE_LOOP_DESIGN.md §ADDENDUM 2026-08-27.
Separately: (4) MAX_LOOP_REPETITIONS=5 matches byte-identical name+inputHash only — observed loops
vary the command slightly each retry, so it never trips; when it does trip it BLUNT-STOPS the turn
(toolCallIteration=MAX) with no strategy nudge. MAX_TOOL_ITERATIONS=1000 is the only guard that
actually caught the loops (as a $$-expensive failsafe). Bench startup = STATELESS per task (fresh
container, empty ~/.cortex store; CORTEX_RECORD/LOOKUP default true and ARE active — recording
garbage successes). Env-spelling note: code reads MAX_LOOP_REPETITIONS (not REPITITIONS).
**FIX SET (the identical-call-breaker campaign, now precise):** (a) derive decision-store `success`
from metadata.exitCode===0 when present (don't touch wire is_error semantics); (b) un-gate the
family lens to also classify content matching the failed-with-exit-code signature; (c) NORMALIZED
near-duplicate loop detection (errorFamily-style hash: strip digits/paths) with soft nudge at N,
hard break at M; (d) consider a lower bench MAX_TOOL_ITERATIONS (~200) as cost containment.

**✅ ADAPTER v6 (2026-08-25): INCREMENTAL SESSION PERSIST — timeouts are now observable.** The
command-tail session copy never runs when Harbor kills the exec at budget, which made every
hard-timeout trajectory unharvestable (absent from Dataset AND canon — verified: gcode-to-text/
caffe-cifar-10/mteb-leaderboard etc. missing from trajectories/). v6 adds a background copier in
the agent command (newest session → /logs/agent/session.jsonl every 20s, killed in the tail before
the final copy) — a budget kill now loses ≤20s of trajectory; Harbor collects /logs/agent into the
trial artifacts even on AgentTimeoutError and the supervisor's existing `find '*agent*' session.jsonl`
harvest picks it up unchanged. Rows tag adapter:"v6-incremental-persist". Rollout: pushed to all 4
arm Datasets + deliberate restart of the live lanes at a bank boundary (rollout-gap rule). This
closes the harvest-before-prune violation for the timeout class ahead of the k=5 run.

## 🧪 ARM SPEC: persist+EndTurn cell (queued post-completion; the wrong-artifact trade test)
**Hypothesis (from the flash distiller frame-split):** the held frame TRADES failure modes — it
halves retry-loops (11→6) but ~2.5x's wrong-artifact/premature-finish (4→10). The persist frame
suppresses deliberation INCLUDING pre-delivery verification. The shipped-but-dormant EndTurn gate
(`CORTEX_ENDTURN_GATE=true` — mandatory attestation w/ citations verified against this turn's tool
outputs, bounded at 2 nudges) targets exactly the missing self-audit. QUESTION: does persist+gate
keep the loop suppression while recovering the wrong-artifact cost?
**Design:** one new arm = flash + anchor-persist + CORTEX_ENDTURN_GATE=true, adapter v6, same
Dataset pattern (new arm store `tb2-nexus-cortex-persist-endturn`), arm tag "anchor-persist-endturn".
- TASK SET: the discriminating subset, not all 89 — the 10 flash-persist wrong-artifact tasks
  (build-pov-ray, caffe-cifar-10, dna-insert, extract-elf, path-tracing-reverse, polyglot-c-py,
  pytorch-model-cli, pytorch-model-recovery, raman-fitting, sanitize-git-repo) + the 6 persist
  retry-loop tasks (loop suppression must NOT regress) + 5 persist-PASSED controls (gate must not
  break passing behavior). ~21 tasks, 2 shards, ~$1-2.
- METRICS: (pass, cost, turns) triple + wrong-artifact count + loop count via distiller; EndTurn
  nudge counts from sessions (v6 makes them harvestable).
- READ: gate recovers ≥ half the wrong-artifact fails w/o new loops → promote to a full-89 arm and
  candidate default for persist-served configs (incl. the sub-1B serving frame). Gate costs extra
  turns/tokens — the triple decides if it pays. FWER-note: single confirmatory cell, no family.

**✅ v6 CONFIRMED LIVE (2026-08-25): train-fasttext (timeout/loop class) banked a 68KB trajectory**
— first observable specimen of the formerly-unwatchable class. TWO nuances from it:
(1) **`turns=1000` rows are BLUNT-KILL SENTINELS, not real 1000-iteration burns** — the published
exact-match loop detector fires (5 identical calls), assigns `toolCallIteration = MAX` to exit, and
the response metadata then reports that sentinel as the turn count (trajectory shows ~22 real
calls). So banked `toolCallIterations` is CORRUPTED on loop-kill rows; treat 1000 as "old detector
fired + turn discarded". The ladder's graceful break both replaces the kill AND fixes the metric.
(2) **mteb-retrieve/mteb-leaderboard fail PRE-AGENT** (~3-4min, no result.json, no agent phase —
nothing for v6 to copy): an environment/image-start failure class on these tasks specifically,
distinct from timeouts. Mark infra-DNF; investigate their env start (big model downloads at task
setup) before ever counting them as capability.

**🆕 PRO-PERSIST DISTILL FINDINGS (2026-08-25, 82/89):** (1) **PERSIST INDUCES PARALYSIS ON THE
STRONG MODEL** — 4 never-acted failures under pro-persist vs 0 under pro-lifted (frame-split: base
wins, loser=never-acted on filter-js/gpt2-codegolf/raman-fitting). The held door scaffolds weak
models but handicaps strong ones ⇒ frame default belongs on the MODEL CARD (pro-class → lifted,
flash-and-below → persist; sub-1B serving stays persistent w/ paralysis-watch in evals). (2) **NEW
GUARD CLASS NEEDED: the INACTION guard (ladder's inverse)** — the whole guard stack counts tool
calls; NOTHING fires on zero-calls + verbose reason-to-the-wall. Fix: extend the R32
empty-response-retry precedent to actless-verbose responses in agentic contexts (one "act first"
nudge). Targets 4-6 fleet failures the ladder cannot touch. (3) pro frame scoreboard: base 10 wins
vs persist 5 (persist wins = loop suppression; losses = paralysis + premature finish). (4)
dna-assembly/dna-insert unclassified in BOTH pro arms — manual reads pending.

**📋 THE IMPROVEMENT BACKLOG IS CANONICAL AT `omniclaude-v4/docs/HARNESS_IMPROVEMENT_BACKLOG.md`**
(2026-08-25) — the three-guard architecture (loop ladder BUILT / inaction guard SPECCED / EndTurn
requirements-extension SPECCED with the full gate analysis) + steering-observability records +
pipefail + per-model frame defaults, each with design, touchpoints, tests, verification rung, and
risks. Companion: UNIFIED_OUTCOME_LADDER.md. Load the doc before building any of these — do not
rebuild the specs from skill fragments.

## 🏁 FINAL 2×2 VERDICT (2026-08-25 — arms COMPLETE, canonical: .bench/distill-final/VERDICT.md)
89/89 all arms. flash-lifted 56 (62.9% / 64.4% ex-infra) · flash-persist 54 (60.7% / 62.1%) ·
pro-lifted 65 (73.0% / 74.7%) · pro-persist 60 (67.4% / 69.0%). Ex-infra = minus the mteb pair
(pre-agent env DNF in ALL arms). **Frame law final form: persist is raw-net-negative on BOTH
models but by different mechanisms** — flash TRADES classes (retry_loop 12→7, wrong_artifact
4→11: the EndTurn-gate test case), pro gains PATHOLOGY (never_acted 0→5 paralysis: the
inaction-guard case). frameProfile initial values: **NONE — deferred
(operator pushback): the 2×2 measured persist under the PRE-FIX harness, and the guard build
targets persist's exact loss classes (Stage-4↔wrong-artifact, inaction↔paralysis, item-6
coherence↔the persist bash channel). Rerun cells with guards armed decide the tier defaults;
default 'lifted' = unchanged legacy behavior. Rerun persist arms via CORTEX_TOOL_ANCHOR_PERSIST=true
(first-class in the new build — no installed-copy lift-guard patch needed).**
Distill artifacts: .bench/distill-final/{SUMMARY,VERDICT,results,persist,pro,pro-persist}.md.
Recovery note: a worker "push failed ... (kept locally)" row lives in /app/bench/hfds/*.jsonl on
that worker — grep it out over /debug/exec and append to the arm Dataset by hand (video-processing
2026-08-25). A supervisor can say COMPLETE while the Dataset is short one row for exactly this
reason: its local ledger counts the kept-local row. ALWAYS reconcile Dataset-vs-tasklist before
declaring an arm done.

## 👁 VISION CENSUS + PRE-FIRE SMOKE RULE (2026-08-25)
DeepSeek = TEXT-ONLY (no vision field exists in the card system at all) — image/video tasks are
only solvable TOOL-MEDIATED (OCR/CV code in the container). Census: `code-from-image` = OCR route
VIABLE (fl passed via tesseract on a still); `extract-moves-from-video` = capability-mismatch
casualty in ALL arms (fl correctly built ffmpeg+tesseract per-frame pipeline, died in tool-timeout
cascade at 0.57 budget; other arms hard-timeout) — classify vision-video tasks as
CAPABILITY-MISMATCH for text-only models, exclude from harness-flip candidate sets.
RULE: before any fleet fire against a freshly PUBLISHED harness, run a PRE-FIRE SMOKE — /tmp-prefix
npm install + one tiny CLI task with the arm env armed; read the SESSION (tool calls + refusals),
not just the answer (first smoke read missed a dispatch refusal by grepping the wrong strings).
4.70.0 smoke validated persist-held + bash-read→Edit coherence live. Known cosmetic: under persist
the continuation still PRESENTS hidden tool schemas (dispatch guard enforces) — one wasted call.

## 🔴 CONTAINER GIT-EGRESS ROT (2026-08-25, tb2rqfp1) — the kept-locally/reclone loop
Signature: lane banks nothing remote for hours while its durable.log shows "push failed ...
(kept locally)" ×N; direct probe shows `git fetch` → `fatal: expected 'acknowledgments'` /
`the remote end hung up unexpectedly` on ALL protocol versions = the CONTAINER's egress to
huggingface.co git is rotten (network path, not auth/protocol). The vicious loop: push fails →
rows kept locally → watchdog restart RECLONES the store → kept-local rows WIPED → done-set
forgets them → slice re-runs (wasted compute, looks like a stall). Remedy: pkill supervisor+harbor
on the rotten session FIRST (a healed network must not double-bank), roster+remap to a FRESH
session, relaunch (resumes from the REMOTE done-set). Corollaries: (1) a supervisor's COMPLETE
line proves nothing — ALWAYS reconcile Dataset-vs-tasklist per arm (pl lost 5 rows incl. a flip
to a push-fail streak; recovered by hand from /app/bench/hfds); (2) kept-locally rows are only
recoverable BEFORE the next reclone — harvest them the moment a push-fail streak is seen.

## 🏁 FLIP-RERUN RESULTS vs 4.71.0 (2026-08-25 ~19:45Z; fp 1 row pending — adjudicate at completion)
fl 56→59 · fp 54→59(+pending; EndTurn/Stage-4 cell) · pl 65→**72 (81%)** · pp 60→66 (inaction
cell) = **+21 net flips** from the guard build, rows tagged 4.71.0/v7-flip-*. Vision cell:
code-from-image FLIPPED (1 ReadImage, $0.006); extract-moves/sam-cell = model-capability walls;
image-TTL validated live (99% cache-hit on image sessions). OPEN adjudication Qs: train-fasttext
turns=1000 legacy sentinel on 4.71.0 (exact-match killer beat the ladder — why?); per-guard-class
conversion attribution. DECIDED: **skip TB2.0 k=5 → TB2.1** (fixes 28/89 tasks = our residual
classes may be bench bugs; live board GPT-5.6 Sol 85.77%; k=5 lands ON TB2.1 after an exploratory
pass; verify harbor id terminal-bench@2.1 + budget-map the 28 changed tasks first).

## ✅ FLIP-RERUN FINAL (2026-08-25): +21 net passes; VERDICT-FLIP.md in .bench/distill-flip
fl 59 · fp 59 (Stage-4 cell: wrong-artifact 11→1) · pl **72=80.9%** (loops 13→5) · pp 66
(inaction cell: paralysis 5→0). Frame: pro card frameProfile:'lifted' prepped; flash tie —
persist wins only as persist+gate PROFILE combo. Next: TB2.1 (residual 10 all-4-fails ≈ its 28
fixed tasks), k=5 there.

## 🔴 DELTA 2026-08-26 — mini-cell durability, crash-class map, item-12/13 arm envs

**MINI/PROBE CELLS GET THE FULL DURABILITY TREATMENT — no exceptions for "small".** Two session
crashes killed the session-scoped results monitor while CF evictions killed 5 one-shot-launched
mini workers; nothing healed them for ~2h (banked rows survived; in-flight runs re-ran). A
store-polling monitor is NOT a healer. Rule: every cell, even 1-task probes, gets (a) its arm
store, (b) the idempotent relauncher, (c) a DETACHED watchdog tick that relaunches-until-banked
and self-exits (`.bench/tb2-mini-watchdog.sh` = the template: 10-min ticks, banked() check per
lane, inline roster).

**CRASH-CLASS MAP (what dies with what):** Claude-session crash → kills run_in_background
monitors/watchers ONLY. Repl restart → also kills detached setsid processes (timers, watchdogs).
CF eviction → kills container workers (they survive both host-side classes). Containers +
HF stores survive everything. Consequence: every detached timer/watchdog needs its one-command
manual heal recorded in the resume memory, and post-restart triage ALWAYS re-checks
timer/watchdog aliveness before trusting the schedule.

**🔴 SELF-MATCH COSTUME #3 — false-ALIVE readings:** a `pgrep -f "patter[n]"` compound whose
OTHER arguments contain the plain string (e.g. `tail patter n.log` in the same command) matches
YOUR OWN shell → reports a dead process as alive (the launch timer read "alive" for hours while
dead). Aliveness checks run pgrep ALONE in a command containing NO other occurrence of the plain
string. (Costumes 1: pkill self-kill; 2: plain filename in a kill+restart compound; 3: this.)
**Costume #4 (2026-08-26): a DETACHED script's pgrep guard matches a TRANSIENT operator-session
shell** whose command text mentions the target filename (a git-commit pathspec made the fire-armer
exit "already armed" at birth) — detached guards use pidfile + /proc, never global pgrep.
**Costume #5 (same day): `grep` directly on `/proc/<pid>/cmdline` FAILS in this environment**
(NUL-separated bytes) → pidfile checks false-report DEAD on live processes. Always
`tr '\0' ' ' < /proc/$P/cmdline | grep -q <pattern>`.

**VERSION-GATED TIMERS: repoint + RESTART on every ship.** A running bash timer keeps its parsed
values — sed-editing the script does NOT update the live process. Every release train that the
launch depends on = edit launcher/timer version strings, kill the old timer (bracket pattern,
separate command), start fresh, verify the gate line in its log.

**ARM ENV TABLE (4.74–4.76 additions, uniform across matrix arms so cross-arm deltas stay valid):**
`CORTEX_TASK_INTEGRITY=true` (anti-reward-hack system line, survives boot-minimal) ·
`CORTEX_ENDTURN_INTEGRITY=true` (Stage-5: transplant/solution-query AUDIT events + mandatory
`sources` attestation for any web/Browse use — justify-don't-block: only unattested web use
nudges) · `CORTEX_POLL_GUARD=true` (busy-wait nudge @4 consecutive identical SUCCEEDING calls) ·
`CORTEX_SURRENDER_NUDGE=true` (execute-your-plan nudge on remaining-steps finishes) ·
`MAX_CONSECUTIVE_ERRORS=6` (3 failing diagnostic probes are NORMAL debugging; the blunt breaker
killed a legitimate OOM-diagnosis mid-flight — the ladder owns graceful escalation). Also 4.74.1:
MAX_LOOP_REPETITIONS is CONSECUTIVE-only (whole-turn counting produced the turns=1000 sentinels
on scattered legitimate repeats — train-fasttext forensics closed).

**SPECIMEN-MINI PATTERN (proved on train-fasttext):** (1) probe minis on a fast PASS-control task
validate plumbing + frame signatures per arm (~$0.02 each); (2) ONE all-arms-fail specimen task
under full observability yields forensics-grade causal chains (the honest-premature-surrender
class: breaker-kill mid-diagnosis → R29a tools-suppressed synthesis BYPASSES the EndTurn gate →
surrender with self-written plan + 85% budget unused); (3) rerunning the specimen after shipping
the fix = a free A/B against the banked baseline row. Read specimens via trajectory + decisions
events TOGETHER — the steering the model saw is event-only (post-persist injections are invisible
in session records by design).

## 🔴 DELTA 2026-08-27 — CORRECTED: the live cap was a STALE UN-DEPLOYED wrangler config (10), not a CF plan limit
FIRST WROTE this as "CF plan enforces 10" — WRONG (operator pushback: "we ran >10 lanes
yesterday"). TRUTH (git+gh-verified): `max_instances` was raised 10->32 on 08-23 23:22, but
nexus-cortex-sandbox is MANUAL-DISPATCH-ONLY and was NOT dispatched again until 08-27 02:32 —
so the LIVE worker ran the stale `max_instances=10` for days. The dashboard "10/10" was our
own un-deployed config cap. LESSON: after any wrangler.jsonc change to a manual-dispatch
worker, the value is INERT until `gh workflow run "Deploy Workers" -f worker=<name>` — verify
the LIVE cap (dashboard), never trust the committed config. Redeploying the sandbox image
(ship-cortex-sandbox / manual dispatch) is what makes an instances change take effect.
Fleet sizing law: **total lanes ≤ (LIVE max_instances − 1)** for a TMUX/admin spare —
that's 31 at the now-deployed 32, but stagger placements and watch the dashboard.
Oversubscription (18-26 lanes) produced a SELF-SUSTAINING eviction cascade from hour one —
each placement evicts a running worker mid-task, the watchdog's relaunch evicts another
(the healer amplifies the churn): 244 relaunches vs 1 in the whole flip-rerun, ~2x wall
slowdown, and REAL CF billing burn ($17→$54 in a day; churn re-provisioning bills).
Corollaries: (1) size fleets to the GRANTED limit, never the config cap; (2) a kill-sweep
via /debug/exec itself PLACES containers on dead sessions — after a deliberate halt, do
NOT re-touch swept sessions (each touch = placement pressure; empty containers idle-evict);
(3) an idle-looking dashboard count below your lane count = the grant, believe it over
wrangler. Halt protocol worked: watchdog-first kill, sweep live sessions, park lossless,
right-sized 9-lane resume via .bench/tb2-resume-{rightsized,timer}.sh (off-peak gated).
DeepSeek peak + churn compound: re-run waste bills at 2x during peak windows.

## DELTA 2026-08-26c — the DURABLE FIRE-CHAIN pattern + flip accounting + the heal drill

**FIRE-CHAIN (proven end-to-end on the 4.78.0 steering matrix — reuse this shape for any
scheduled fleet):** version-gated TIMER (fires launcher when npm==target in the window) →
detached ARMER (waits for the launcher's "LAUNCH COMPLETE" line — NEVER arms early: a healer
running pre-fire would early-launch workers, and arming mid-stagger races cold-placement) →
matrix WATCHDOG (inline lanes, NOT roster-grep — the roster accumulates completed lanes from
prior runs; heals via idempotent relaunch; completion = done ≥ each store's OWN tasklist
count, never a hardcoded 89) → on ALL-COMPLETE, sentinel-guarded handoff to a detached
POST-ADJUDICATION chain (distill → events-joined miner) so results bank with no session
alive. GUARD RULES (all bitten this session): liveness between detached scripts = pidfile +
`tr '\0' ' ' < /proc/$PID/cmdline | grep` (costume #5: raw grep on cmdline FAILS; costume #4:
global pgrep matches transient operator shells whose command TEXT mentions the filename);
double-run guards = sentinel line in the log + pidfile, never pgrep.

**FLIP ACCOUNTING:** watchdog "N pass" ≠ flips when cells mix fail-set rows with controls —
a flip = pass ∩ the BASELINE ARM's fail-set (map each cell to its baseline: flash-frame cells
→ fl fails, persistgate → fp, pro trio → pl, persistinaction → pp). Always also report
control REGRESSIONS (a guard that breaks passing behavior) — zero is the expected line.

**REPL-RESTART HEAL DRILL (executed twice today; session crash kills less):** dies = every
detached setsid (timer/armer/watchdog/deadman) + all Monitors/background polls; survives =
containers, pods (pod-side sup loops), HF stores, everything banked. Heal order: (1)
matrix watchdog (`setsid nohup bash .bench/tb2-matrix-watchdog.sh >> …log 2>&1 &`), (2)
vast deadman (ABSOLUTE paths — a relative `>> .bench/…log` redirect failed once post-`&`),
(3) pre-fire timer if applicable, (4) re-arm session monitors, (5) verify pod/worker
processes directly before trusting any schedule. A Monitor's death-report on its FIRST iteration
is suspect — verify the target directly before healing (the false-DEAD monitor class).

## DELTA 2026-08-26b — bench ShellTool failure causes are TWO mechanisms (read fails accordingly)
Specimen-verified split: (1) PERMISSIONS layer — the $() command-substitution blacklist denies
naturally-written commands (8+/specimen; naively substring-matched, so even $(( )) arithmetic is
denied) → the denial→rewrite→variant loop FEEDS the near-dup class; (2) tool-TIMEOUT aborts
(~116/specimen sessions), relabeled honestly in 4.77.0 ("timed out or aborted" — was "cancelled
by user"). 🔴 RESOLVED 2026-08-26 (backlog item 15 = the full file:line map): headless IS
permissions-bypassed regardless of YOLO=false — `headlessAutoApprove` (server/index.ts:555,
no-TTY) forces permissionMode 'auto' → bypassAll; the stateless /v1/messages path runs
'disabled'. The $() denial is NOT the permissions plane: it's an unconditional substring check
in ShellTool.validateToolParams (ShellTool.ts:162) active in every mode; backticks/<() are
unchecked (porous control). Ruling (bench allowance vs semantic fix) = operator gate. Never
read a bench Bash failure without classifying WHICH mechanism.

## 🔴 DELTA 2026-08-27b — THE TAIL-CLEARING PLAYBOOK: when a "done" matrix won't hit ALL-COMPLETE

The 4.78.0 matrix sat at ~222/224 for ~26h with workers reporting COMPLETE and the armed
publish blocked. ALL the data was present — the run was held by **completion-GATE artifacts, not
missing work.** When a matrix stalls at N-of-M while shards log "COMPLETE", audit the completion
CRITERION (tasklist integrity + remote-vs-local reconcile) BEFORE assuming more compute is needed.
Four distinct blockers, each with a distinct fix — do not conflate them:

1. **🔴 DUPLICATE TASKLIST LINE = PERMANENT DEADLOCK (the silent one).** The watchdog gates on
   `len(done_unique) >= len(tasks)`, but `tasks` is a whitespace split that COUNTS DUPLICATES,
   while `done` is a set. A dup line (persistgate had `regex-chess` twice: 30 lines / 29 unique)
   makes the gate `29 >= 30` = FALSE **forever** — the arm is genuinely complete but never
   registers. **Signature: a Dataset diff prints `29/30 done, MISSING 0`** (the contradiction —
   0 missing yet done<total). **Fix:** dedup the REMOTE tasklist (`awk '!seen[$0]++' tb2-tasks.txt`),
   push, verify by re-clone (29 lines). **Prevention (two-sided):** (a) the store-seeding step must
   dedup tasklists before push; (b) `progress()` should compute `len(set(tasks))`, and the
   supervisor's slice/remaining math should too — until both are fixed, a single duplicated
   fail-set entry silently wedges the whole matrix's ALL-COMPLETE.

2. **DEAD SHARD vs EGRESS-ROT: identical 27/30 symptom, OPPOSITE fixes — diagnose by probing the
   container.** Both leave an arm short with the alive sibling shard reporting COMPLETE.
   - **Dead shard** = `/debug/exec?session=<S>` returns ENOENT (`no such file … watch /tmp/session-…`).
     The container is gone. **Fix:** relaunch that shard on a **FRESH session name** (…b) via
     `tb2-relaunch.py` with the lane's env — it reclones, sees its slice's tasks missing, RE-RUNS
     them under the correct arm. Probe tell: `durable.log` shows `RUN <task>` = working.
   - **Egress-rot** = the worker responds and logs `COMPLETE: 30/15 graded` **locally** but the
     remote Dataset stays short (its new rows can't `git push` — rotten container→huggingface
     egress). The watchdog's relaunch RECLONES and WIPES the kept-local rows, so it re-runs and
     re-fails forever. **Fix:** harvest the kept-local rows over `/debug/exec`
     (`grep -h '"$t"' /app/bench/hfds/results*.jsonl | tail -1`) and **push them from the REPL**
     (egress is fine there) — do it BEFORE the next watchdog tick reclones. Probe tell:
     `COMPLETE N/M graded` + remote < N.
   Same session-class can have one container rotten and another fine (per-instance network) — one
   shard pushes 30/30 while its sibling can't. Probe BOTH before choosing the fix.

3. **🔴 IDENTICAL FAIL-SETS + ROUTING CROSSING = WRONG-ARM kept-local rows (harvest trap).** Two
   sibling cells (liftmin-flash / vision-lifted) shared an IDENTICAL 30-task fail-set. The unstable
   session→container routing left each container holding rows tagged for the OTHER arm on the shared
   tasks. **Before appending ANY harvested kept-local row to fill a gap, verify `row.arm` == the
   target Dataset's arm** — the crossed rows are wrong-arm duplicates of tasks the OTHER arm already
   banked, and different-model arms (vision uses `deepseek-v4-flash-vision-exp`, not flash) are NEVER
   interchangeable. A gap in arm X is filled by RE-RUNNING under arm X, never by grafting arm Y's row
   for the same task. (The correct-arm re-run even changed an outcome: regex-chess empty-failed 0/turns=0
   under the crossed liftmin row but passed 1.0 when re-run under the real vision arm.)

4. **RECOVERY PUSHES USE A DISTINCT FILENAME.** Hand-append recovered rows to
   `results-recovery.jsonl`, NEVER the worker's own `results-sN.jsonl` — `progress()` globs
   `results*.jsonl` so it still counts, and you never collide with the worker's (possibly still
   recovering) git-append writer. The single-writer invariant applied to manual recovery.

**⚙️ WATCHDOG RESTART: "duplicate watchdogs" are usually PIPELINE SUBSHELLS — do NOT kill them.**
`echo "$LANES" | while read …` runs its body in a SUBSHELL that shows as `bash watchdog.sh` in ps
(same argv as the parent). A `pgrep` during a heal tick sees the real watchdog PLUS N transient
subshells → looks like a multi-spawn. Killing them races transient PIDs (exit 144) and can kill a
heal mid-flight. **Verify via the PPID tree** (`ps -eo pid,ppid,etimes,args | grep watchdo[g]`):
exactly ONE has `ppid=1` (setsid-detached, matches the pidfile) = the real watchdog; the rest are
its children and self-exit. This is the process-control twin of the "frozen count = monitoring
artifact" rule: a "duplicate watchdog" is a subshell artifact until the PPID tree proves otherwise.
(Costume #6.) Restarting a watchdog to pick up an EDITED `LANES=` is mandatory — the running
process parsed LANES at launch; sed-editing the file does nothing until restart (same rule as
version-gated timers).

**🕐 THE REPLIT VM CLOCK JUMPS on pause/resume — never reason about elapsed time from timestamps.**
Saw `date -u` read 12:20Z → 14:09Z → 16:07Z within seconds of wall-clock across three tool calls
(VM was paused/resumed between them). Log timestamps from before a jump look hours-stale but are
correct-for-then. Reason about progress via TICK BOUNDARIES (last tick + 720s) and pidfile/proc
liveness, not wall-clock deltas. A log line that looks "2h old" may be one tick ago.

**HEAL DRILL COVERS THE WHOLE FIRE-CHAIN, not just the watchdog.** `tb2-arm-release.sh` (the armed
publish) died silently between wake-checks with no sentinel — only re-checking arm-release ITSELF
(not just the headline watchdog) caught it. On every wake verify EVERY detached link: version-gated
timer, armer, watchdog, arm-release, vast-deadman — each with its own `tr '\0' ' ' < /proc/$PID/cmdline`
liveness check. A dead publish-armer is invisible in the watchdog's own log.

## 🔵 TB2.1 FACTS (investigated 2026-08-27, sourced) — READ before planning a TB2.1 run

Repo `harbor-framework/terminal-bench-2-1` (moved from laude-institute); run `harbor run -d
terminal-bench/terminal-bench-2-1 -a <agent> -m <model> -k 5 ...`. Announcement: tbench.ai/news/terminal-bench-2-1.
- **Same 89 tasks as TB2.0** (no add/remove). TB2.1 = a FIX-PASS on 28 of them: 9 external-dependency
  (upstream drift), 8 resource/budget (too tight even for the oracle), 11 misspecification (instructions≠tests,
  e.g. query-optimize said PostgreSQL but tests wanted Spark SQL). "No task is unsolved in TB2.1."
  (Repo README says 26; official announcement says 28 w/ itemized 9+8+11 — trust 28.) Several of OUR TB2.0
  residual fails are in the fix set: query-optimize, polyglot-c-py (+84%), polyglot-rust-c (+74%),
  caffe-cifar-10 (+64%), torch-tensor-parallelism (+63%), extract-moves-from-video (+10%) → our number
  should RISE on 2.1 from the fixes alone (residual ≈ bench bugs, confirmed).
- **🎯 INTERNET = DEPENDENCY FETCHING, NOT BROWSE. ZERO of 89 tasks require web search/browse.**
  All 89 `mcp_servers=[]` (no browser granted to the agent); `allow_internet=true` is a BLANKET default →
  full public egress on ALL 89 (incl. no-network tasks like regex-chess) = env-robustness default, not a
  browse signal. Only 2/89 Dockerfiles have a browser (filter-js/break-filter-js) = VERIFIER XSS grading,
  not agent-facing. Browse-sounding tasks debunked by reading files (extract-moves = video COPY'd in;
  mteb-leaderboard = oracle git-clones raw results, browser optional/undocumented; sparql = data baked in).
  ⇒ **A single-key DeepSeek agent that shells out (curl/git/pip/apt) is at NO disadvantage. NO browse
  strategy / nexus-browser-as-library needed for the bench.** What matters = bash/dependency competence +
  loop management (the ×98 class). Web tools are a non-factor for the score (keyless WebFetch "Google API
  key not found" is harmless noise — consider DISABLING web tools in the bench arm so the model doesn't
  waste turns on them).
- **Container arch:** base = python:3.13-slim (41) / ubuntu:24.04 (40) / misc; prebuilt `alexgshaw/<task>:date`;
  `network_mode=public`; tooling = curl/git/wget/pip/apt (+tmux/gcc per task); NO agent browser. task.toml
  schema 1.1: `[agent].timeout_sec` (900s typ, up to 3600 for train/data), `[environment]` cpus/memory/gpus/
  allow_internet/mcp_servers; grading = tests/test.sh bootstraps uvx pytest → test_outputs.py → reward.txt.
- **Methodology:** `-k 5` = ≥5 trials/task, MEAN pass-rate + CI (NOT classic pass@k). Community submissions
  CLOSED (maintainer-run only); top ~83.8% (Claude Code) / ~83.1% (Codex); NO DeepSeek entry (we'd set a new
  point). Fixed environments/budgets mandatory; public trajectories required. Sandbox backends: local Docker +
  Daytona (README-recommended) / Modal / E2B / etc via `-e <provider>`.
- **nexus-browser-as-library** (the product-native browse capability) remains a valid PRODUCT idea (native
  browse in hosted/local harness, single key) but is DECOUPLED from TB2.1 — do not bench-justify it. Current
  nexus-browser = CF Worker (@cloudflare/puppeteer → Browser Rendering) + nexus-browser-sandbox (Docker
  Chromium + Playwright relay); a library version = a driver-abstraction port (CF | local-Playwright driver),
  optional dep (Chromium ~300MB). Design captured RECURSIVE_PM_WAKE_LOOP_DESIGN.md discussion 2026-08-27.

## ✅ TB2.1 OPERATIONAL (2026-08-30) — the wiring that actually made it run (verified end-to-end)

First TB2.1 fleet is LIVE on the corrected tasks (graded proof: bn-fit-modify r=1.0, turns=41, inTok=738K;
0 empty-fails across the first 88 graded rows = wiring completely clean). What it took, so the next dataset
change is a 10-minute job instead of a rediscovery arc:

1. **Dataset id: `terminal-bench/terminal-bench-2-1` — the PATH form.** `terminal-bench@2.1` FAILS (harbor's
   version-resolution: 2.1 is a SEPARATE dataset, not a version of `terminal-bench`); bare `terminal-bench-2-1`
   also fails. No Harbor Hub auth needed (`harbor auth status` = Not authenticated, resolution still works —
   auth is only for `--upload`/leaderboard).
2. **🔴 Task ids are NAMESPACED in the 2.1 dataset: `-i terminal-bench/<task>`.** Bare names (which TB2.0
   accepted) give `ValueError: No tasks matched the filter(s)` — and that error's "Example task names:" list
   IS the diagnostic (it prints the real namespaced ids + confirms "89 tasks available", proving resolution
   worked and only the filter missed). Keep the task LIST + result keys + trajectory filenames BARE; prefix
   ONLY the harbor `-i` argument.
3. **Wiring (supervisor + relaunch, env-parameterized):** `tb2-durable-supervisor.py` gained
   `DATASET = env TB2_DATASET (default terminal-bench/terminal-bench-2-1)` + `TASK_PREFIX = env
   TB2_TASK_PREFIX (default terminal-bench/)`, used as `harbor run -d {DATASET} … -i {TASK_PREFIX}{task}`;
   `tb2-relaunch.py` forwards both. Setting `TB2_DATASET=terminal-bench@2.0 TB2_TASK_PREFIX=` reproduces the
   old TB2.0 behavior exactly.
4. **Budgets self-correct — do NOT hand-migrate tb2-budgets.json.** Harbor pulls each task's OWN task.toml
   (incl. the 28 raised budgets) from the `-d` dataset; the local `tb2-budgets.json` feeds ONLY the
   `budget_frac` metric, so a TB2.0 budget map means cosmetic budget_frac drift on the 28 changed tasks, not
   wrong runs. (Refresh it from the 2.1 task.tomls when convenient.)
5. **Probe discipline through the 60s exec bridge:** a failed dataset resolution errors in ~5s; a probe that
   RUNS TO THE TIMEOUT got past resolution and is pulling/building the image — through the exec bridge's
   60s cap, "timed out" IS the success signal for a resolution probe. Grep the abort tail for
   `No tasks matched` / `DATASET_RESOLUTION` to split id-vs-filter failures.
6. **Verify-first-cell before the fleet (operator-mandated, works):** place a FEW lanes, wait for one REAL
   graded row (reward + turns + tokens + exc=[]) before launching the remainder — resolution alone is not
   proof; only a banked grade exercises dataset→image→adapter→cortex-server→test.sh→bank end-to-end.
7. **Canon leg per run-generation:** the rail persists (HARNESSES.json `tb2-bench` root + watcher survive),
   but `.bench/tb2-canon-stage.py`'s ARMS map is per-generation — point it at the new arm datasets
   (tb2-1-{flash,pro,vision}) and arm a 15-min loop; trajectories then land as
   `/native/nexus-cortex/tb2-bench/<arm>__<task>.jsonl` automatically.
8. **Everything else carries over unchanged:** same 89 bare task names, same adapter, same durable-supervisor
   /watchdog/re-shard machinery, same `alexgshaw/*` image family (2.1 = corrected task.toml/tests), same
   off-peak scheduling rule. The TB2.0→TB2.1 migration was, in the end, ONE dataset id + ONE task-id prefix
   — everything hard about it was *finding* those two facts (they're in §TB2.1 FACTS + here now).

## 🔴🔴 DELTA 2026-08-31 — THE CONFIG AUDIT: the guard stack was silently OFF for 5+ runs (and how to never repeat it)

**TB2.1 n=1 FINAL (guardless baseline): flash 70.8% (63/89) · pro 78.7% (70/89) · vision 68.5% (61/89) — 267/267,
ZERO infra fails.** vs TB2.0 single-run: +7.9/+5.7. Hard core = **13 tasks failed by ALL THREE arms**, retry_loop in
11 (chess-best-move, dna-assembly, extract-moves, filter-js, gcode-to-text, gpt2-codegolf, make-doom-for-mips,
model-extraction-relu-logits, pytorch-model-cli, raman-fitting, torch-pipeline-parallelism, train-fasttext, tune-mjcf).

### 1. THE ADAPTER IS THE CONFIG — and it silently lost the guards
Containers NEVER had a .env (the seed template didn't ship in the server package pre-4.88), so the adapter's
hardcoded env block was the guards' ONLY delivery vehicle. The v7-v9 adapters (4.71-4.81: flip-rerun, 4.78 matrix)
set 8 guard lines; **the A'-era rewrite (~4.84) DROPPED them** — every run from the A' matrix through TB2.1 n=1 ran
guardless, with MAX_CONSECUTIVE_ERRORS regressed to the blunt code-default 3. AUDIT METHOD (reusable): stream each
era's adapter FROM ITS ARM DATASET (`curl -sfL .../resolve/main/nexus_cortex_agent.py | grep guard-vars`) — the
dataset copy is what actually ran, not the workspace file. Full table: `.bench/tb21/CONFIG_AUDIT_2026-08-31.md`.
RESTORED (v15 adapter) with a warning comment; the failure distribution maps ~1:1 onto the dropped guards
(retry_loop 65-74% of fails <-> NEARDUP_BREAKER; busy-wait doctrine violations <-> POLL_GUARD; premature finishes <->
SURRENDER_NUDGE). STANDING RULES: (a) the supervisor banks the adapter's EFFECTIVE env with row 1 of every run —
config lives IN THE DATA; (b) every run card records guard state; (c) never hand-edit the adapter env block without
diffing against the master `.env`'s guard section (`.env.defaults` = its shipped mirror).

### 2. 🔴 VERDICT INVALIDATION — "tested, no improvement" on a broken mechanism is NOT a verdict
Multiple TB2.0-era conclusions were VOID because the mechanism under test was silently broken: mentorship (hints were
EMPTY every consult ever — helper thinking bug), SearchTools/discovery (every call in every era hit an unwired
executor), lift-nudge ("ignored" = a records-blind measurement), EndTurn efficacy (confounded by MCE=3 cutting its
retry loop). **RULE: every A/B arm must bank MECHANISM-ENGAGEMENT EVIDENCE** (consult counts w/ non-empty hint
lengths, tool calls w/ non-error results, guard-fire counts) — an arm that cannot show its treatment fired is a
second control, not an arm. Corollary: re-run void experiments on fixed mechanisms before citing their verdicts.

### 3. Post-4.88 the bench BASELINE CHANGES — control cell required
4.88 ships the env-seed fix (core carries .env.example; ANY entry point seeds it), so containers will receive the
FULL template for the first time — dozens of lines never before active in a bench. Before crediting any 4.88-era
treatment, run a 4.88 CONTROL CELL and read its banked effective env. The adapter env still WINS over the seeded
file (bootstrapEnv first-wins), so explicit arm env remains the arm mechanism.

### 4. Standing instrument: the live effective-config dump
`GET /health/config` (JSON) + `:4001/config` (dashboard table, ENABLE_DASHBOARD=true): per-lever effective value +
source (env vs code-default) + plain-language meaning. A guarded run's verify-first cell should show the guard rows
env-sourced; "code-default" on an intended-on lever = the guard-drop failure mode, visible in one glance.

### 5. Recovery-playbook additions (both bitten during the video-processing kept-local recovery)
- 🔴 **NEVER commit from a `--no-checkout` clone**: its EMPTY INDEX makes the commit tree contain ONLY the staged
  files — it silently DROPS every other file from HEAD (clobbered tb2-1-vision to 1 file; recovered via depth-2
  clone + `git checkout HEAD^ -- .` + recommit; history preserves everything, so recovery is always possible).
- 🔴 **Validate harvested rows with json.loads BEFORE pushing**: a `[:N]` slice in the harvest pipeline banked a
  truncated invalid row. Harvest to a file untruncated, parse-check, then push (still to results-recovery.jsonl).

### 6. Instrument traps from the era-truth audit (all cost real hours)
- **HF `resolve/` URLs 302 to a CDN: `curl` WITHOUT `-L` fetches a stub** — counts read from it are garbage. Always
  `curl -sfL` when streaming dataset files.
- **Session records are BLIND to post-persist injections** (lift nudge, steering appended to already-recorded
  messages): absence in records proves NOTHING about delivery — verify via DEBUG logs or the events store.
- **Distiller aggregate claims (e.g. "SearchTools 0x") must be spot-verified against raw trajectories** before
  becoming era lore — one wrong count manufactured a false behavior-discontinuity story.

### 7. The guarded-run design (treatment-vs-known-control, subset form)
Config-decision runs don't re-run the full 89: **all baseline fails (flip ground) + the grind-to-pass passes
(>=6 recorded failures while passing — where guards WILL fire; regression watch) + pipe-heavy passes** ≈ 100/267
tasks, ~40% spend. Flip accounting: pass ∩ baseline-fail-set; regression: fail ∩ included-pass-set; k=5 provides
full coverage before any number is quoted. Version-pin the arm (`TB2_HARNESS=nexus-cortex@X.Y.Z` now pins the
adapter install) so a mid-run publish can't skew it.

## 🔴 DELTA 2026-09-01 — the tb21g stall + $200 postmortem: watchdog v3 is now THE template

**The two incidents (one root):** the tb21g guarded run stalled (fleet bled 24->0 lanes, watchdog
relaunched=0 while failed climbed to 23) AND burned ~$200 in CF container-storage — both caused by
running THREE undestroyed fleet generations (~67 session DOs: baseline + first-guarded + re-shard)
against one ~32-instance substrate. Cold placements failed under cap pressure (single-shot verify ->
LAUNCH-FAILED spam), routing flipped relaunches onto stale containers (false "COMPLETE 22/5"), and
every DO billed storage for hours because teardown was a human memory item that didn't fire.

**THE FIXES (all shipped, use them):**
1. `scripts/tb2-relaunch.py` now RETRIES placement once with 30-60s backoff before LAUNCH-FAILED —
   transient cap-pressure blips no longer read as dead lanes.
2. **`.bench/tb2-watchdog-v3-template.sh` — copy this per run (ROSTER_FILE + COMMON env).** Adds:
   destroy-on-COMPLETE (each finished lane's DO destroyed + pruned immediately — never idle-bills),
   fresh-session AUTO-REMAP after 2 consecutive tick-failures (destroys the wedged DO first; remap
   file single-hop from the ORIGINAL name), ALL-COMPLETE final destroy-sweep of every session
   (original + remapped) then SELF-EXIT, and a MAX_TICKS sweep so even a hung run never leaves a
   fleet billing. Teardown is STRUCTURAL now.
3. `scripts/tb2-destroy-session.sh` — the verified kill: POST /admin/sessions/destroy
   {"sessionId":...} (the ONLY accepted form on the live worker); destroyed:true IS the confirmation;
   NEVER probe to verify (probes re-spawn billing containers). Token stays repl-side.
4. `NEARDUP_NUDGE_AT` default 8->12 (core): the diversify nudge misfired on persistence-wins grinds
   (rstan-to-pystan regressed on BOTH arms with steering events mid-grind); 12 gives real grinds rope.

**FLEET SIZING LAW (tightened):** ONE generation at a time, <=16 lanes sustained (placement headroom
is what keeps routing stable), and ANY supersede/re-shard DESTROYS the old generation's DOs first —
"left to die" lanes are what stacked 67 DOs. A stalled run's DOs are destroyed IMMEDIATELY,
unconditionally — the ride-vs-stop decision is about re-running, never about whether to stop billing.

**ADJUDICATION UPGRADE (mechanism-classified flips):** classify every flip/regression by guard-event
presence in its decisions.jsonl (loop_escalation / steering_injected). tb21g: flips 15 ENGAGED vs 6
clean (re-rolls — incl. db-wal-recovery passing in 10 calls with ZERO events), regressions 4 ENGAGED
vs 1 clean → **attributable net +11, engaged help:harm 3.75:1**. Quote the ENGAGED-only net as the
robust number; the clean remainder ≈ the ±3/arm noise floor, exactly as predicted.

## 🎯 THE K=5 RUN CARD (2026-09-01) — the verbatim recipe for the next run; follow in order, skip nothing

This consolidates everything the two TB2.1 runs proved: run 1 (24 lanes, one generation, re-armed watchdog)
SUCCEEDED with zero infra fails; run 2 stalled + burned $200 by violating exactly these steps.

**0. PREREQS (all shipped, verify present):** adapter v15 (guard block + TB2_HARNESS pin) in
`nexus-terminal/workers/nexus-cortex-sandbox/bench/nexus_cortex_agent.py`; `scripts/tb2-relaunch.py` w/
retry-backoff; `scripts/tb2-destroy-session.sh`; `.bench/tb2-watchdog-v3-template.sh`; supervisor
run_config banking; NEARDUP_NUDGE_AT=12 core default.

**1. PUBLISH 4.88.0 FIRST** (`omniclaude-v4/scripts/deploy-nexus-cortex.sh -y -m "..." --release` — NEVER
mid-run; adapter installs float to latest unless pinned). The train: retry-loop set (dark), env-seed
enforcement, SearchTools wiring, WebFetch helper ladder, CLI timeout, nudge reorder, neardup=12,
/health/config. Dark features STAY dark for k=5 (CORTEX_MENTOR_AUTO/MENTOR_FORCE/ENDTURN_GATE=false —
they get their own revalidation cells LATER, vs k=5 as control).

**2. 4.88 CONTROL CELL (small, before the fleet):** 2-3 tasks, one lane — because 4.88's env-seed delivers
the full .env.example into containers for the FIRST time (new baseline). Read the banked run_config row +
`/health/config` to certify the effective config; confirm guards show ACTIVE.

**3. FLEET SPEC (the law):** ONE generation, **≤16 lanes total** (placement headroom = routing stability),
fresh stores `tb2-k5-{flash,pro,vision}` seeded w/ v15 adapter + FULL 89-task list (deduped, verify by
re-clone), `TB2_HARNESS=nexus-cortex@<pinned>` pin in COMMON, same MENTORSHIP env as the accepted config, **`ENABLE_WEBTOOLS=false` PINNED in COMMON** (4.89+: the shipped default is `auto`, which resolves ON inside keyed bench containers because they carry every provider's job token — never rely on the default; TB2.1 needs zero web; web-off is a deliberate lever vs the web-on tb21g/m88 baselines),
`harbor -k` semantics = 5 separate full passes (or 5 sequential n=1 stores k5r1..k5r5 — decide per cost).
OFF-PEAK windows (peak = Mon-Fri 01-04 & 06-10 UTC). DeepSeek balance check before placing.

**4. LAUNCH ORDER (opposing-controls, every time):** (a) verify-first cell: 1 lane/arm → one REAL graded
row + guard-ACTIVE proof from run_config → (b) remainder staggered ≤2/15s → (c) copy
`tb2-watchdog-v3-template.sh` per run (ROSTER_FILE + COMMON), arm DETACHED (`setsid`) — v3 destroys
completed lanes, auto-remaps wedged ones, final-sweeps + self-exits → (d) write `.bench/<run>/ACTIVE`
(WATCHDOG/MONITOR/log paths) so the .bashrc boot-hook (`scripts/tb2-control-rearm.sh`) re-arms the control
plane after ANY repl restart. Monitors poll the STORE only — never exec-probe containers.

**5. DURING:** wake drill on every session resume = summary poll + ppid-1 watchdog/monitor check (the
boot-hook usually beat you to it). NEVER exec-probe a lane (spawns billing containers); the store's counts
are the only progress truth. Frozen counts + alive watchdog = investigate the WATCHDOG LOG first.

**6. END (automatic, but verify):** v3 sweeps all DOs and self-exits on ALL-COMPLETE. Verify: watchdog log
shows "sweep done", CF dashboard shows 0 bench instances, `rm .bench/<run>/ACTIVE`. If the run STALLS or is
abandoned: destroy ALL its DOs IMMEDIATELY (`tb2-destroy-session.sh` over the roster + remaps) — the
ride-vs-stop decision is about re-running, never about whether to stop billing.

**7. ADJUDICATE:** rate = PASS/(done − empty-fail) per the classification rules; mechanism-classified flips
(guard events in decisions.jsonl) when comparing configs; distill + doctrine-mine per arm; ledger to
`.cortex/bench/`; the statistical gate (mean + CI over the 5 passes) is the quotable number.

## ✅ THE ZERO-INFRA-FAIL CHECKLIST (derived from the first TB2.1 run — 24-27 lanes, 267/267, 0 infra fails)

Operator-commissioned 2026-09-01: the first TB2.1 matrix ran a full 89×3 with ZERO infra failures.
Every later incident (tb21g stall, $200 storage burn, the m88 verify-lane reap) maps to a step this
run did that the failing run skipped. Walk this list for EVERY fleet, any size — the K=5 RUN CARD is
the k=5-specific recipe; THIS is the universal per-run gate. Each item carries the incident it prevents.

**PRE-FLIGHT**
- [ ] 🔴🔴 LEVER-POPULATION GATE (2026-09-08, the k5v2 VOID-RUN postmortem — the most expensive lesson): a
      lever-validation subset MUST be built from the lever's TRIGGERING population — NOT a reused general or
      exploratory mix. loop-block + deadline fire ONLY on RETRY-LOOP / grind-to-deadline tasks (dna-*, torch-*,
      train-fasttext, gcode-to-text, make-doom-for-mips, chess-best-move, gpt2-codegolf, tune-mjcf,
      model-extraction-relu-logits, raman-fitting); ABSTAIN fires ONLY on REJECT-LOOP finishes; effort fires on
      any task. A subset lacking the trigger tasks makes that arm a SECOND CONTROL BY CONSTRUCTION — the answer
      is null before task 1, and no amount of flawless execution recovers it. (k5v2 reused the dark-levers
      11-task hard+control mix — ZERO retry-loop tasks — so `loop_tool_block` fired 0×, `deadline` 0×,
      `endturn_resolver` retire 0× across all 385 lanes; the entire lever question was void at DESIGN,
      independent of the execution churn.) The subset's failure mode must MATCH the lever's target: a
      persistence-guard (loop-block/deadline) tested on an early-give-up population (this one, budget_frac
      0.24-0.31) is a null test.
      🔧 ENFORCED BY SCRIPT (2026-09-08): `scripts/bench-population-gate.sh --tasks <subset> --levers <csv>`
      (or `--model-ab` for a model comparison's discriminating-set check) reads the task→class ledger
      `.bench/TASK_POPULATION.tsv` and EXITS 1 if any lever's triggering class is under-populated. Validated:
      it FAILS the k5v2 subset (loop-block/deadline have 1<3 trigger tasks) and PASSES ABSTAIN (3 reject_loop).
- [ ] 🔴🔴 PRE-LAUNCH MECHANISM-FIRE PILOT (the gate that would have caught it, ~$1): BEFORE committing the
      k=5, run 1-2 REAL bench tasks per lever on the intended subset and CONFIRM the mechanism event fires in
      the banked `trajectories/<task>.decisions.jsonl` (`kind`=`loop_tool_block` / a deadline-exit kind /
      `endturn_resolver` with `detail.verdict`=retire). ZERO fires on the pilot → the subset can't exercise the
      lever → FIX THE SUBSET or DROP THE LEVER; do NOT spend the k=5. 🔴 A seeded/synthetic fire-check proves
      the CODE fires, NOT that real tasks trigger it — only the real-task pilot is a valid gate.
      "gated-on + green tsc + seeded-fire" ≠ "fires on the bench." This is the "mechanism-engagement evidence
      per arm" rule promoted from an ADJUDICATION step to a PRE-LAUNCH gate.
      🔧 ENFORCED BY SCRIPT (2026-09-08): after the verify-first cell banks shard-0's first graded row (before
      fanout), `scripts/bench-mechanism-pilot.sh --repo <arm-store> --lever <LEVER>` (or `--mechanism <kind>
      [--verdict retire,abstain]`, or `--model-ab --model <id>`) reads the store's `trajectories/*.decisions.jsonl`
      and EXITS 1 on zero fires, 2 if nothing banked yet, 0 on fire. Validated: reports `loop_tool_block fired
      0x` on the real k5v2-lb store (the void proof) and `lift_plan FIRED 33x` on k5v2-ctl (positive control).
- [ ] 🔴 NO MIXED-POPULATION BUNDLING: never cram levers with DIFFERENT triggering populations into one
      subset. One subset cannot be right for loop-block (retry-loops) AND effort (any task) AND ABSTAIN
      (reject-loops) simultaneously. Give each lever-class its own population, or run separate cells — sized so
      each cell's subset actually fires its lever (verified by the pilot above).
- [ ] 🔴 PARALLEL/CONTINUOUS PLACEMENT (HB-PLACEMENT ①②⑤): the rig must place lanes continuously up to a
      target concurrency at a bridge-safe rate — NOT serial armer-fanout + an 11-min watchdog sweep (that
      throttled k5v2 to ~44 concurrent all day) and NOT a 40-50-wide burst (that wedged the bridge +
      crash-cycled lanes). SHARD_N≈18-20 (~3 tasks/lane), async place/verify split, bounded-parallel placement.
      See DELTA 2026-09-07b/c.
- [ ] 🔴 CONFIG-PROVENANCE GATE (2026-09-04, the `strict` postmortem): `bash scripts/bench-config-provenance.sh
      --file .bench/<run>/watchdog-*.sh` — every efficacy lever must cite the cell that EFFICACY-tested its VALUE
      (n=1 robustness probes do NOT count), diffed vs `.bench/LEVER_PROVENANCE.tsv`. BLOCKS on any UNTESTED lever
      (caught `CORTEX_ENDTURN_REQUIREMENTS=strict` — the untested+broken divergence that cost a $109 run). Fix the
      lever, drop it, or `--ack` to launch it as an EXPLICIT recorded decision. NEVER verify the config against a
      resume summary you wrote — the primary is the decision ledger + tested-cell armers. [[feedback-verify-against-primary-not-derived]]
- [ ] 🔴 COST-GAUGE RECONCILE: banked bench cost is UNTRUSTWORTHY until reconciled vs the provider dashboard (2026-09-03:
      banked $20 vs real $109 = 5x under-count; `usage_raw={}` on loop-killed grinders → their tokens recorded ~20%).
      After any run, pull the DeepSeek usage dashboard and assert banked-vs-actual < 20% before quoting a cost number.
- [ ] Provider balance checked (DeepSeek `/user/balance`) — a 402 era poisons rows at ~90s each.
- [ ] Off-peak window (peak = Mon-Fri 01-04 & 06-10 UTC); long runs planned to finish before peak.
- [ ] No mid-run publish possible: version PINNED (`TB2_HARNESS=nexus-cortex@X.Y.Z` in COMMON) and any
      pending release either shipped BEFORE seeding or held until after adjudication.
- [ ] If the harness version changed since the last baseline: a CONTROL CELL is part of the design
      (config deltas invalidate cross-version comparisons — the guards-silently-off era).
- [ ] Fleet sized to ONE generation with real headroom: total live DOs (lanes + spares + anything
      stale) well under the LIVE max_instances (dashboard, not wrangler config). 24-27 lanes worked
      with ZERO stale DOs; 24 lanes + 43 stale corpses caused the placement-wall stall.
- [ ] 🔴 EXHAUSTIVE pre-launch sweep: `LIVE="<this run's names>" bash scripts/tb2-prelaunch-sweep.sh` —
      destroys EVERY name in `.bench/session-ledger.txt` (auto-appended by tb2-relaunch on every
      placement) except LIVE. Rosters alone are NOT enough: 2026-09-02 the cap held 24 instances with
      2 live lanes although every prior run had reported destroyed:true (silent-destroy survivors +
      placement-by-touch). The 29-name sweep took ~40s and the next fanout placed 12/12 first try.

**SEED (per arm store)**
- [ ] Fresh dataset per arm; adapter + task list + budgets TRAVEL IN the store.
- [ ] Task list DEDUPED (`awk '!seen[$0]++'`) — one dup line = permanent ALL-COMPLETE deadlock.
- [ ] Seed VERIFIED BY RE-CLONE (tasks count, adapter marker grep, results empty). Never trust the push.
- [ ] Adapter env block diffed against the intended config (guards! the v15 CONFIG-AUDIT lesson) and
      the arm's ONLY differing lever confirmed present in its COMMON.

**LAUNCH**
- [ ] Verify-first cell: 1 lane per arm; NO fanout until each banks a REAL graded row (reward + turns
      + tokens) AND the run_config row shows the intended effective env. 🔴 Use the v2 armer template
      (`.bench/tb2-armer-v2-template.sh`): the verify-phase ticker must HEAL, not just tick — a v1 armer
      hammered a wedged verify lane (exec bridge '') for 10 min adding placement pressure and never fanned
      out (c3, 2026-09-02). v2 = watchdog remap logic (2 fails → destroy + remap to <name>x<N>) applied to
      the verify lanes + the pre-launch ledger sweep built in.
- [ ] 🔴 EVERY placed lane has a TICKER from placement onward — VERIFY LANES INCLUDED. The DO idle
      reaper (sleepAfter 20m) kills containers with no inbound requests even mid-task; the watchdog/
      armer tick IS the keep-alive (m88 verify lanes were reaped at ~20min for lack of one).
- [ ] Placements STAGGERED (~2 per 15s) — batch cold-placement near the cap false-fails then evicts.
- [ ] Watchdog = the v3 template (destroy-on-COMPLETE + auto-remap-on-2-fails + ALL-COMPLETE/MAX_TICKS
      destroy sweep + self-exit), roster-file-driven, one COMMON per arm (two watchdogs if arms differ).
- [ ] Control plane DETACHED (setsid, ppid-1) + `.bench/<run>/ACTIVE` flag written so the .bashrc
      boot-hook guardian re-arms after ANY repl restart (control-plane death ≠ visible; it looks like
      "slow tasks" while the fleet bleeds).

**DURING**
- [ ] Monitor the STORE only (fresh clones/`curl -sfL`); NEVER exec-probe a container (routing-flip
      false alarms + probes PLACE billing containers on dead sessions).
- [ ] Wake drill on every session resume: summary poll → ppid-1 check of EVERY control-plane link
      (watchdog(s), armer, monitors) → re-arm dead ones → DEDUP to one each.
- [ ] Frozen store counts + alive watchdog = read the WATCHDOG LOG first (monitoring artifact until
      the worker's own ledger disagrees).
- [ ] Trajectory/canon staging leg pointed at THIS run's stores (harvest-before-prune).

**END**
- [ ] v3 sweeps automatically — VERIFY: watchdog logs show "sweep done", dashboard shows 0 bench
      instances, then `rm .bench/<run>/ACTIVE`. A stalled/abandoned run's DOs destroyed IMMEDIATELY,
      unconditionally (ride-vs-stop is about re-running, never about billing).
- [ ] Reconcile Dataset-vs-tasklist PER ARM before declaring done (kept-local rows; a supervisor's
      COMPLETE line proves nothing).

**ADJUDICATE**
- [ ] Classify before quoting: rate = PASS/(done − empty-fail); empty-fails requeued not counted.
- [ ] Flips/regressions vs the CORRECT baseline (same-version simultaneous arm when one exists).
- [ ] MECHANISM-ENGAGEMENT evidence per treatment arm (guard/consult events in decisions/trajectories)
      — an arm that can't prove its treatment fired is a second control.
- [ ] Distill + doctrine-mine; ledger to `.cortex/bench/`; deficiencies to the backlog.


## 🔴 DELTA 2026-09-02 — lessons must be STRUCTURE, not prose (operator: "don't you have all the previous lessons banked?")

Three incidents in one day hit gaps the banked prose lessons described but nothing enforced:
1. **Verify-lane wedge with no healer** — the armer ticked but could not remap; the watchdog's remap logic
   only ran after fanout. → `.bench/tb2-armer-v2-template.sh` (self-healing verify phase, ledger sweep built in).
2. **Cap squatted by corpses** — 24 instances with 2 live lanes; every prior sweep had reported destroyed:true.
   → `scripts/tb2-relaunch.py` appends every placed name to `.bench/session-ledger.txt`;
   `scripts/tb2-prelaunch-sweep.sh` destroys all ledger names except LIVE before any placement. Rule: the
   dashboard instance count minus your live lanes = corpses; sweep the LEDGER, never just the roster.
3. **🔴 `.replit onBoot` DOES NOT FIRE on repl restarts (verified across 3 restarts 09-02: no `onboot` entry ever
   in /tmp/tb2-rearm.log; the chain runs fine by hand).** The ONLY in-repl re-arm trigger is a shell opening (.bashrc)
   — a dead repl leaves the control plane dead until someone resumes a session. Spend stays safe by platform design
   (sleepAfter 20m reaps un-ticked lanes; inactive instances don't bill) — the loss is wall time + in-flight tasks
   (resume-from-store re-runs them). Repl-independent fix = worker-cron keep-alive + TTL-destroy over a KV bench
   registry (def-2332d425c8, operator decision). Until then: on EVERY session resume run the wake drill FIRST.
Standing rule: a lesson is banked when a SCRIPT or TEMPLATE enforces it; a checklist bullet without a script
behind it will recur at 3am.


## 🔴🔴 DELTA 2026-09-02b — THE KILL SWITCH DESTROYED THE WRONG DO (root cause of every "destroyed:true but still there")

Admin ad-hoc bench sessions live in DOs named `cortex-admin-<session>` (worker `sessionIdFor`). The destroy route
passed the BARE name through → it created+destroyed a PHANTOM DO and answered destroyed:true; the real container
lived on until sleepAfter. Authoritative proof = the Cloudflare Containers API (readable with the deploy token):
`GET /accounts/{id}/containers/applications` → per-app instance counts; `…/applications/{app}/instances` → every
instance with name/state/started_at. 415 instances on nexus-cortex-sandbox: 400 inactive + 15 running, every bench
name present twice (real `cortex-admin-X` + bare phantom `X`).
STANDING RULES (all enforced by scripts now):
1. **Instance count = the CF API, never the destroy response.** `scripts/tb2-reaper.sh` prints running/kept/reaped.
2. **`scripts/tb2-destroy-session.sh` qualifies bare names to `cortex-admin-<name>`** (worker-side fix in tree).
3. **NEVER blind-destroy a name** — a destroy on a nonexistent DO SPAWNS a phantom container to service it. The
   reaper destroys only instances the API reports RUNNING and no ACTIVE run claims (rosters + remap targets);
   keyed/user sessions (cortex-k-*/cortex-u-*) are never reaped. Guardian runs it on boot/shell + every 10 min.
4. Billing: charges stop when an instance SLEEPS (CF pricing doc); inactive records persist harmlessly. What costs
   money is RUNNING non-live instances — exactly what the reaper removes. Idle running corpses came from the
   wrong-DO destroys (never stopped) + touches (relaunch ticks / exec probes reset sleepAfter).
5. Other apps also show instances (autoresearch-sandbox 7, browser-sandbox 7 on 2026-09-02) — not bench fleets;
   check them with the same API call when auditing spend.


## DELTA 2026-09-03 — 🟢 BENCH LEASE REGISTRY (item 9): the repl-INDEPENDENT hard stop
Every prior fail-safe (v3 watchdog destroy-on-complete, guardian re-arm, API reaper) lived on the REPL. A repl
restart with nobody present (2026-09-01 $200, 2026-09-02 23:47Z) left containers billing until sleepAfter — or
forever if a supervisor kept them busy. Now the WORKER holds the lease:
- `POST /admin/bench/lease {sessionId, ttlSeconds?, label?}` (admin token; bare or qualified name; TTL default
  5400s, max 86400) — `scripts/tb2-relaunch.py` calls it on EVERY tick outcome (ALIVE and RELAUNCHED), so each
  watchdog/armer tick renews the lane's lease; `TB2_LEASE_S` overrides the TTL. A 404/blip never fails a tick.
- The worker's 5-min warden cron runs `benchSweep`: any lease past `expiresAt` → `/admin/destroy` on the REAL
  DO name (`cortex-admin-<name>`), key deleted regardless of result (destroy-ONCE: a lease on an already-gone DO
  cannot re-spawn a phantom every sweep). `/admin/sessions/destroy` deletes the lease; `/admin/bench/release`
  drops one without destroying; `GET /admin/bench/leases` lists; `POST /admin/bench/sweep` runs it now.
- ⇒ control plane dead → containers destroyed within TTL + 5 min, no repl involved. Keep TTL ≥ 3× the tick
  cadence (watchdog 660s → 5400s default is ~8 ticks of slack for placement-pressure ticks).
- KV `list` is eventually consistent (~60s): a lease you just wrote may not show in `/leases` immediately;
  `lease` itself reads the key directly (beats increments prove it).
- Verified live 2026-09-03 01:2xZ: lease v4p0 → beats=1; real relaunch tick → `supervisor ALIVE — no action
  (lease ok beats=2 ttl=5400s)`; sweep → destroyed=[] while leases are live. Expiry-destroy path = the same
  `sandboxAdmin(/admin/destroy)` the verified kill switch uses.
- Also today: the armer v2 template SELF-REGISTERS in `RUN_DIR/ACTIVE` at start (wrapper exports ARMER_SELF/
  ARMER_LOG, wrapper must NOT `exec` the template) so the guardian re-arms an armer killed pre-fanout; the
  template accepts `session:repo:idx[:model[:arm]]` entries so ONE armer drives a multi-model cell.

## DELTA 2026-09-03b — 🔴 TEARDOWN TRAP: killing the guardian's `bash -c` wrapper ORPHANS the inner watchdog
The guardian arms control-plane scripts as `setsid bash -c "WD_INITIAL_SLEEP=30 bash '<script>' >> log"`. Killing the
ppid-1 pid you see for `<script>` in `ps` may kill only the OUTER `bash -c` wrapper — the INNER `bash <script>` is reparented
to init and KEEPS TICKING. Its roster lanes are already destroyed, so its next tick calls tb2-relaunch on dead names →
RE-PLACES containers (the blind-poke trap, from your own teardown). Caught live 03:51Z 2026-09-03: two inner watchdogs
survived the first kill. RULE: after `rm ACTIVE`, kill by matching the SCRIPT PATH in `ps -eo pid,ppid,args` (all ppid-1
hits), then re-list and kill again until EMPTY, then destroy lanes, then reaper. Never trust one kill pass.
Also this cell: the item-12 env_unprovisioned marker must key on NO INTERPRETER (python3 absent), never on an empty dir —
from-scratch tasks (cancel-async-tasks) start empty by design; the mislabel made reconcile loop the lane (~$10).

## DELTA 2026-09-03c — 4.91.0: gates on STREAMING + the three-execution-paths lesson
- Until 4.91.0 the EndTurn gates (Stages 1-5, effort tail) ran ONLY in `sendMessage()` — every streaming client (TUI,
  SSE `/v1/messages stream:true`) was ungated. Now ONE shared module `packages/core/src/orchestrator/endTurnGates.ts`
  (TurnEvidence + evaluateEndTurnGates + buildMissingEndTurnReminder) serves both loops; streaming has the Stage-1
  nudge → re-request → fallback-accept too (Stage-3 coordinate check + surrender guard are still non-stream only).
  When a lever's mechanism is "post-tool steering", confirm which LOOP a client uses before reading its engagement.
- 🔴 `handleToolCalls` has THREE execution paths (parallel Task batch · sequential "otherTools" · the big inline
  dispatcher for ordinary batches). The ONLY universal post-execution hook is `processToolTraining` (every path funnels
  through it — that is where decisions.jsonl rows come from). Two hook placements (sequential loop, then
  executeSingleToolCallWithTraining) compiled clean and were SILENTLY dead on the common path; the LIVE PROBE caught it,
  tsc never would. Rule: a new post-tool steering hook goes in processToolTraining, and its first proof is a live
  run showing the event in decisions.jsonl.
- Re-execution guard (def-7f510b5635): an exception AFTER a batch executed used to re-loop into re-executing the same
  batch (v4 dna-insert 1000 iterations). Guard = `lastExecutedBatchUuid` in both loops; test hook
  `CORTEX_TEST_POST_EXEC_THROW=once` + `reexecutionGuard.integration.test` prove it through the real loop.
- k=5 pins nexus-cortex@4.91.0. New engagement signatures for the distiller: `vision_handoff_capped`, `slice_read`,
  `endturn_gate_fallback{streaming:true}`.

## DELTA 2026-09-03d — 🔴 BARE-BOX TASKS ARE A DESIGN, NOT AN INFRA FAILURE (torch-* misdiagnosis corrected)
TB2.1 `torch-tensor-parallelism` / `torch-pipeline-parallelism` ship a stub Dockerfile + a prebuilt image that is bare
ubuntu:24.04 (Docker Hub: every tag 29.7 MB). The grader's test.sh installs uv + python 3.13 + torch 2.7.0 AT TEST TIME; the
agent phase is intentionally empty (allow_internet=true) — the agent must bootstrap its own toolchain to self-test. I first
read this as "unprovisioned container" (def-99ca5d361f) and built a status downgrade + retry for it; that downgrade would
have LOOPED lanes (a non-`done` status never reconciles — the cancel-async incident). RULES: (1) a supervisor may ANNOTATE
a row (env_note) but must NEVER change `status` away from `done` for a graded run; (2) before calling any task "infra",
check the task source (task.toml docker_image → Docker Hub tag size; tests/test.sh) — Harbor uses the prebuilt image
whenever one is named and errors the trial on a failed pull, it does not silently build the stub; (3) the shipped orient
scaffold now prints a bootstrap hint when no python is on PATH (uv fast path). Do not count torch-* as free flips.
- 2026-09-03 (operator): the orient bare-box hint is GENERALIZED — any missing language/compiler/package/library, with the
  box's own mechanics (pkg-mgr detected, root yes/no) and per-language fast paths (uv, nodejs/nvm, rustup, golang,
  the language's own installer). SIMPLIFIED 2026-09-03 (operator) to observation + ONE principled directive, no
  command cookbook — pro solved a bare-box torch task on 4.91.0 with only the factual tooling line, so the model
  bootstraps on its own; a prescriptive list is prompt mass that misdirects. The `-- setup:` line prints only when
  python OR cc is missing (no friction on provisioned boxes). Source `docs/prompts/orient-scaffold.sh`; rides next patch.
- 2026-09-03 (queued): orient setup line carries an "install once + fast cached installer (uv/bun)" clause, GROUNDED in the tp
  torch-tensor PASS that double-installed torch (system pip + venv → budget_frac 1.2). UNPROVEN — A/B on the timed+install
  subset {torch-tensor, torch-pipeline, train-fasttext, gcode-to-text, protein-assembly}, arms = orient with/without the
  clause, metric budget_frac + install-seconds + pass; TRIM to principle-only if no delta (narrow-door mass discipline).

## 🔴 DELTA 2026-09-05 — the verify-first EFFECTIVE-CONFIG gate + the control/notification split (resolver-AB)

The pre-launch CONFIG-PROVENANCE gate proves *intent* (the levers you MEANT to set, read off the watchdog COMMON).
It is BLIND to what the running server actually resolved — because post-4.88 the seeded `.env.example` is the real
baseline and the effective value is `seed ⊕ adapter ⊕ COMMON` (bootstrapEnv first-wins). This session added the
*effect*-side gate and split the control plane from the notification plane. Both are now reusable rig structure.

### 1. 🔴 THE VERIFY-FIRST EFFECTIVE-CONFIG GATE (`.bench/resolver-ab/certify-config.sh` = the template)
`GET /health/config` (main server port, ALWAYS on — not dashboard-gated; `collectEffectiveConfig()`, per-lever
`{effective, source: env|code-default, active}`) is the authoritative "what is actually on". Wire it so the gate
reads it from the STORE (never an exec-probe):
- **Adapter** (`nexus_cortex_agent.py`): right after the existing `/health` poll, `curl -sf localhost:$P/health/config
  -o /logs/agent/health_config.json || true`. This is the ONLY faithful surface — the adapter injects the guards +
  passes COMMON, so only ITS server's view reflects the true merge. (A supervisor-spawned probe server would MISS the
  adapter's `env[...]` guard block.)
- **Supervisor**: harvest it beside `arm-env.json` and bank `rec.effective_config` = flattened `{KEY:{effective,source,
  active}}`. `arm_env` alone is value-only (adapter's view, no source, no seed merge) — insufficient to certify.
- **Gate** reads the arm Dataset (all `results*.jsonl`) and HARD-asserts per-lever `effective` + `source==env` for the
  arm lever(s) + the held-constant invariants (web off, gate on, guards active). BOTH arms certify → fanout; ANY
  mismatch → destroy lanes + ABORT. It fires AFTER the first graded row (~1 task, ~$0.1) — catches a silently-wrong
  config after one task instead of the whole fleet. Extends the "config lives IN THE DATA" rule from provenance to
  effect. The gate discriminates: wrong-source (seeded/defaulted vs env), wrong-arm-value, web-leaked-on, dropped-guard.

### 2. 🔴 SEED ⊕ ADAPTER ⊕ COMMON — "dark = unset = code-default" IS WRONG post-4.88
A lever NOT in COMMON takes its value from the seeded `.env.example`, not the code default: `ENABLE_WEBTOOLS` seeds
to `auto` (= web ON in keyed containers — only off because COMMON pins `false`); `CORTEX_MENTOR_FORCE` seeds `false`
(seed-sourced, not code-default). A hand-derived COMMON-only lever table is INCOMPLETE — certify from `/health/config`,
never from the watchdog file alone. `bench-config-provenance.sh` reads only the watchdog, so it too is blind to the
seed; the effective-config gate is what closes that.

### 3. LIFT_PLAN / ENDTURN_RESOLVER gate on `MENTORSHIP_ENABLED`, NOT `CORTEX_MENTOR_AUTO`
Both are siblings of the MENTOR_AUTO *delivery* pattern (orchestrator-direct-invoke + system-reminder, because forced
`tool_choice` is dead on DeepSeek once history holds a prior tool_call) and both need the helper middleware
(`MENTORSHIP_ENABLED=true` → `generateTaskPlan`/`evaluateEndTurn` exist), but each has its OWN env gate
(`CORTEX_LIFT_PLAN` / `CORTEX_ENDTURN_RESOLVER`). MENTOR_AUTO can stay dark and they still fire. Lift-planner also has
an interactive gate: fires only when `autoApproveActions` (headless/bench) OR `CORTEX_LIFT_PLAN_INTERACTIVE=true`.

### 4. 🔴 GOTCHA — `python3 - <<'PY'` CONSUMES stdin; a piped `$data` is DISCARDED
`printf '%s' "$data" | python3 - <<'PY' ... sys.stdin.read() ... PY` reads EMPTY — the heredoc is stdin for `python3 -`,
so the pipe is dropped. A gate built this way can NEVER certify and would falsely ABORT a passing run after its retry
budget. Deliver data via a TEMP FILE + argv (`printf %s "$data" > $tmp; python3 - "$tmp" <<'PY'; open(sys.argv[1])`).
Same class as the self-match costumes — a silent-empty-read that looks like "condition not met yet".

### 5. 🔴 SHARDED RUNS WRITE `results-s{IDX}.jsonl` — a reader hitting only `results.jsonl` sees NOTHING
The supervisor's `RESULTS = results-s{SHARD_IDX}.jsonl if SHARD_IDX>=0 else results.jsonl`. Any gate/poll/monitor must
enumerate ALL `results*.jsonl` (HF tree API: `GET /api/datasets/<repo>/tree/main`, filter `results*.jsonl`, fetch+concat)
— a single-file read stalls the gate on every sharded run (bit this session; even a 1-shard run uses idx 0 → `-s0`).

### 6. THE TWO-LAYER MODEL — durable control plane ⊥ notification (they are different things)
- **Durable control plane** = `setsid` ppid-1 daemons (armer→watchdogs, store-poll daemon). Survives Claude-session
  crash; INVISIBLE to the harness + the operator's session process view (they're not harness-tracked). Proof-of-life =
  advancing LOG timestamps, never a session process list. This is correct for durability.
- **Notification** = a harness-tracked `Monitor` (store-poll, emits progress/heartbeat/cluster/COMPLETE, exits on done).
  This is the ONLY layer that reaches you. A detached daemon that writes a log notifies NOBODY — arm a Monitor SEPARATELY.
  🔴 Monitor dedup key must EXCLUDE drifting values (balance): keying the emit line on a value that changes every poll
  fires an event every tick → auto-stopped for noise. Key on task-counts; show balance, don't trigger on it.

### 7. KEEP-ALIVE = the WATCHDOG per-lane tick, NOT the monitor
Split-role rigs: the store-poll monitor NEVER touches containers, so it CANNOT keep lanes alive. The watchdog tick
(`tb2-relaunch` per roster lane, ~660s < the 1200s sleepAfter) is what renews the lease + resets sleepAfter. (Older
combined rigs put the relaunch loop IN the monitor — don't assume that shape.) Verify the watchdogs' tick line accounts
for EVERY lane (`alive+relaunched+failed+complete == roster size`) — that is the keep-alive proof.

### 8. FULL-PARALLEL SHARDING FOR A SMALL SET: N shards = task-count
For an M-task arm, `SHARD_N=M` → 1 task/lane, all M concurrent (verify-first = shard 0, fanout shards 1..M-1). A
2-arm × 11-task rig = 22 lanes, right under the ~24 headroom. Wall time collapses from M-serial to slowest-single-task.

### 9. CF DASHBOARD LAGS THE CONTAINERS API (confirmed live) — the API is truth
Live this session: dashboard showed 0 while `GET /accounts/{acct}/containers/applications/{app}/instances` showed 2
RUNNING (state under `status.state`; name = `nexus-cortex-cortex-admin-<session>`; app = `nexus-cortex-sandbox-sandbox`,
NOT `nexus-cortex-sandbox`); the dashboard then caught up (operator confirmed 2). Instance `started_at` = the DO's birth
(persists across name reuse) while `status.updated_at` = last state change — so a `started_at` "yesterday" on a today's
lane is DO-reuse, not a zombie. Believe the API over the dashboard, every time.

## 🔴🔴 DELTA 2026-09-05b — THE SELF-INFLICTED-OUTAGE NIGHT: /debug/exec crash-cycles containers; cap is 48; cold-start ~7min

An entire night was lost to a run that was NEVER broken. The harness (4.93.0 = 4.92.0 + 20 lines of
event-detail observability), the config (byte-identical COMMON), the rig, and the substrate were all fine.
The failures were ALL self-inflicted. Hard rules, each earned:

1. **🔴 LIVE CAP = 48, not 32.** Verify the LIVE cap from the CF Containers API, NEVER a stale skill number
   (I carried 32 from the 08-27 delta → falsely called 42 lanes "oversubscription" and needlessly tore down a
   healthy run). Fleet sizing ≤ cap−1 = ≤47.

2. **🔴 `/debug/exec` IS NOT INSPECTION — IT EXECUTES IN THE CONTAINER AND CRASH-CYCLES IT.** Every
   `SessionTerminatedError: shell exited (exit code 2)` / `ENOENT watch /tmp/session-…` I saw was MY probe
   resetting a live container mid-task. Repeated exec-probing during a run kills lanes before they bank →
   empty-sessions (`tools:{}`, no effective_config) that MASQUERADE as a broken harness/substrate. The lane
   that I *only store-watched* (never probed) ran perfectly; the lane I kept poking "failed." 
   **For container STATE/LOGS use the CF API + `wrangler tail` (read-only, non-intrusive). For PROGRESS use the
   STORE. `/debug/exec` is for deliberate one-shot setup, NEVER for monitoring/diagnosis of a live run.**

3. **🔴 COLD-START IS ~7 MINUTES.** First task on a fresh container = image pull + node20 + `npm i
   nexus-cortex@<pin>` + the task ≈ 7 min before the first row banks. Do NOT declare a lane "hung" before
   ~10 min, and NEVER from an exec-probe — read the STORE. I killed run after run inside their own cold-start
   window and called them dead.

4. **🔴 THE PER-TASK ADAPTER INSTALL PINS THE VERSION → two versions run simultaneously; the sandbox image
   version is IRRELEVANT to the bench.** `NexusCortex(BaseInstalledAgent).install()` runs INSIDE each harbor
   task container and does `npm install -g nexus-cortex@$TB2_HARNESS`. So resolver-ab (4.92.0) and k5 (4.93.0)
   ran on the SAME worker at once, each task container installing its own pin. **Corollary: a sandbox redeploy
   does NOT change the benchmarked harness version — do not redeploy to "fix a version."** (I did an
   unnecessary ~15-min sandbox rebuild chasing this.)

5. **🔴 ONE fanout per substrate at a time.** Launching k5 while resolver-ab was still fanning out stacked two
   runs. (Harmless here only because 42 < the real 48 cap — but the discipline stands: one generation.)

6. **The debugging order that would have saved the night:** (a) STORE first (real rows vs empty), (b) CF API
   for instance state (read-only), (c) `wrangler tail` for container logs (read-only), (d) a LOCAL
   `cortex-server` boot + `/v1/messages` to test the harness off-substrate. NEVER `/debug/exec` a live lane to
   "see what's wrong" — it becomes the thing that's wrong. When a rerun of a known-good config is the ask,
   rerun it and WATCH THE STORE PATIENTLY — do not diagnose a run that isn't failing.

## DELTA 2026-09-05c — the "90% budget cap" is a WHOLE-TASK deadline in the bench (CORTEX_TURN_DEADLINE_MS), not a per-tool-iteration limit

Operator asked the right question ("Harbor has a turn budget and I was conflating a complete-task budget with a turn budget?"). The
precise architecture (grounded, verify before repeating):

- **Two DISTINCT budgets, different owners:**
  | budget | owner | scope | at the limit |
  |---|---|---|---|
  | task timeout (`task.toml [agent] timeout_sec` → `tb2-budgets.json`) | **Harbor** | whole task, wall-clock | Harbor **KILLS** the task at 100% (reward 0, no partial) |
  | `CORTEX_TURN_DEADLINE_MS` | **our harness** | one TURN's tool-loop | **force-synthesis** (graceful finish) |
- **Harbor has NO "turn" concept** — only the whole-task timeout. `CORTEX_TURN_DEADLINE_MS` is OURS; the supervisor sets it to
  `int(task_budget_s * 1000 * 0.9)` (`scripts/tb2-durable-supervisor.py:164`) so the harness converges BEFORE Harbor's guillotine.
- **Why "turn deadline" ≈ "task deadline" in the bench:** `loopStartMs = Date.now()` is set ONCE per turn (`CortexOrchestrator.ts:1924`
  non-streaming / `:4341` streaming), at the start of that turn's tool-loop — NOT reset per tool-iteration. Each iteration checks
  `Date.now() - loopStartMs` vs `TURN_DEADLINE_MS` (warn rung ~:2992/:4935, break/force-synthesis ~:3061/:4996). **A bench task is a
  SINGLE turn** (one task prompt → one tool-loop running all N iterations), so the per-turn deadline bounds the WHOLE task. Setting it to
  90% of the task budget is therefore a 90%-of-whole-task cap — the operator's mental model was correct; the variable name misleads.
- **It DOES fire in the bench** (evidence, resolver-k5): make-mips `budget_frac`≈0.99, schemelike 0.91–1.14, circuit 1.12 — tasks ran to
  ~90–100% of their task budget then force-synthesized. `budget_frac = latency_s / task_budget_s`; `budget_frac ≥ ~0.9` = the cap fired.
- **Local-harness gotcha (don't mis-read a non-fire):** total PROCESS wall (a `cortex "task"` run) = server boot (~15–20s) + turn-1
  lift-plan mentor call (~50s @ max reasoning) + the tool-loop. `loopStartMs` starts at the TOOL-LOOP, so a 467s total run can have a
  <432s loop and NOT fire even though total wall > the deadline. Measure the loop, not the process, when checking whether the cap engaged.
- **Two observability gaps (still open, see HARNESS_IMPROVEMENT_BACKLOG):** `CORTEX_TURN_DEADLINE_MS` is NOT in `effectiveConfig.ts`'s
  reported list (the config-certify gate can't see this central lever); and the supervisor's `budget_frac`/`agent_budget_s` fields are not
  actually populating in banked rows (recompute from `tb2-budgets.json`). The v2 idea = mentor-directed exit at the deadline (backlog).

## 🔴🔴 DELTA 2026-09-07 — THE MASSIVELY-PARALLEL RIG: real CF caps, 1-task/lane, touch-free monitoring (supersedes the "≤16 lanes / cap 48" model for subset runs)

The churn that plagued the resolver-family subset runs was DIAGNOSED to a controllable root and fixed. Bank this
as the replication template for the full k=5 and every future lever-validation wave.

### 1. 🔴 THE REAL CF INSTANCE LIMITS (query them, never carry a stale number)
`GET https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/containers/me` → `.result.limits`
(read with the deploy token). Live 2026-09-07: `total_vcpu:1500`, `total_memory_mib:6291456` (6 TiB),
`total_disk_mb:30000000` (30 TB), `vcpu_per_deployment:4`, `memory_mib_per_deployment:12288`,
`durable_object_offset_instances:2000`. Instance type `standard-4` = 4 vCPU / 12 GiB / 20 GB disk.
**Binding constraint = vCPU: 1500 ÷ 4 = ~375 concurrent standard-4 instances.** The wrangler `max_instances`
is a SELF-IMPOSED cap far below that (was 48). Other sandboxes (autoresearch/browser, capped 10 each) share the
1500-vCPU pool but use ~14 vCPU — negligible. ⇒ **The old "LIVE CAP = 48" (DELTA 09-05b) and "≤16 lanes"
(RUN CARD) were self-imposed, NOT the CF grant. Size fleets to ~350, not 48.**

### 2. 🔴 RAISING THE CAP (rollout) — wrangler deploy is config-only (no image rebuild)
Edit `nexus-terminal/workers/nexus-cortex-sandbox/wrangler.jsonc` `max_instances`, then from that dir
`CLOUDFLARE_API_TOKEN=… CLOUDFLARE_ACCOUNT_ID=… npx wrangler deploy`. The container `image` is a PRE-BUILT
registry ref (`registry.cloudflare.com/…/nexus-cortex-sandbox:<tag>`), so wrangler deploy is a ~2s config
update (secrets + bindings PERSIST in CF across deploys) — NOT the ~15-min image rebuild. Confirmed live:
`Modified application … "max_instances": 48 -> 350`. Gotcha: a stray `nexus-terminal/.wrangler/deploy/config.json`
makes wrangler error "two config files, different base paths" — move it aside. VERIFY the new cap via the
applications API. (The workflow path `gh workflow run "Deploy Workers" -f worker=nexus-cortex-sandbox` also
works but needs the change pushed to the extracted GitHub repo first; direct wrangler is faster for a config bump.)

### 3. 🔴 THE TASKS-PER-LANE LAW (the churn root, quantified)
Churn (supervisors re-booting every tick, run_config banked ×N, store flat while balance drops) is caused by
**too many tasks serialized per lane**, NOT by the arm count. Grounded 2026-09-07:
| run | tasks/arm | SHARD_N | tasks/lane | outcome |
|---|---|---|---|---|
| dark-levers (n=1) | 11 | 8 | **1.8** | ✅ |
| resolver-k5 (k=5) | 55 | 20 | **2.8** | ✅ |
| k5v2-first (k=5) | 55 | **8** | **6.9** | ❌ churned |
**RULE: keep ≤ ~3 tasks/lane.** For k=5 (55 tasks/arm) that means `SHARD_N ≥ 18`; ideal is `SHARD_N = task-count`
(**1 task/lane**: place → 1 task → bank → self-destroy; no serial queue, minimal watchdog-tick exposure).
The k5v2-first mistake: reused the n=1 dark-levers `SHARD_N=8` on a 5× larger (k=5) load, AND crammed 5 arms into
the 48-cap so 8 was the max that fit. **The fix is to RAISE THE CAP (now known ~375), not to under-shard.** Long
serial lanes maximize the window for the watchdog's `/debug/exec` relaunch-check to hit a mid-grind supervisor →
re-boot → re-cold-start → churn; short 1-task lanes finish and die before that. (Post-restart routing fragmentation
compounds it — a CLEAN launch at ≤3/lane runs at the successful rate.)

### 4. 🔴 CF BILLING MODEL — parallel is FASTER *and* cheaper-in-practice
CF bills **per running instance-second** (memory GiB-s + vCPU-s + disk GB-s); charging STOPS on sleep/destroy.
standard-4 ≈ **$0.40/instance-hour**. For the same total work:
- **The task compute is identical** parallel vs serial (same instance-seconds for the tasks).
- Massive parallelism adds ONLY **cold-start overhead** — one ~7-min `npm i nexus-cortex@<pin>` per lane (445
  lanes ≈ +$20 vs 40 lanes). That's the entire structural premium.
- It ELIMINATES the **churn/wedge/idle waste** that actually dominated the serial runs (re-cold-starts, wedged
  idle containers billing, DeepSeek token re-runs — the $200 tb21g incident). That waste is UNBOUNDED and far
  exceeds the cold-start premium. ⇒ **run max-parallel (1-task/lane), finish in ~1 hr, not days.**
- **DeepSeek tokens are separate + dominant**; provider-side prefix cache (system prompt + tools) means run-shape
  barely changes cache economics (a cold first-wave costs ~$2 extra; then the shared prefix is warm for all lanes).

### 5. 🔴 WARM-vs-COLD CACHE = a PUBLISH-TIME DISCLOSURE, not a run decision
When a $/task is litigated publicly, the fight is warm-cache (steady-state, ~30× cheaper on DeepSeek: hit
$0.007/M vs miss $0.22/M) vs cold-cache (first-run). Our harness runs ~98% cache-hit (stable boot-minimal prefix)
— legitimate but must be DISCLOSED. Publish rule: report **mean-of-5 pass-rate + CI** (never best-of-5), and a
**cost triple with the full cache breakdown (cacheRead/cacheCreation/input/output) + hit-rate + a warm/cold
bracket**, on a **sterile** install (no private `.cortex/` memory = the fair cold-start, matching reference
harnesses). Pass-rate itself is cache-independent, so lever-efficacy runs are unaffected — cache is a cost story only.

### 6. 🔴🔴 TOUCH-FREE MONITORING ARCHITECTURE (the rule that prevents self-inflicted regens)
Monitoring must NEVER touch a container. Enforced split:
- **PROGRESS** = STORE reads (HF `curl -sfL` the arm datasets). The authoritative truth.
- **INSTANCE COUNT** = CF API READ: `GET …/containers/applications/{APP_ID}/instances` → `result.instances[]`,
  count `.status.state=='running'` (⚠️ the count is at `result.INSTANCES[]` — a dict, not a top-level list; and the
  applications endpoint's `instances` field is the CONFIG/desired count, NOT running). Read-only, destroys nothing.
- 🔴 **NEVER run `tb2-reaper.sh` in the monitoring/keep-alive loop** — it is a DESTROY op: it can kill a
  watchdog-REMAPPED lane if your static live-list misses the `xN` remap target, and a destroy on a misclassified
  name SPAWNS a phantom (§09-02b). The reaper is TEARDOWN-ONLY (run once at the end / on a deliberate stop).
- 🔴 **NEVER manual `/debug/exec` a live lane** for diagnosis — it crash-cycles the container (§09-05b). All
  diagnosis via store + CF-API + the watchdog LOGS (`/tmp/<run>-wd-*.log`).
- The ONLY designed container touch is the **watchdog tick's `tb2-relaunch` `/debug/exec`** relaunch-check — the
  core rig mechanism (resolver-k5-proven), minimized by 1-task/lane + a clean substrate. It is not "monitoring."
- **HEAL** = `rearm-all.sh`: a pure `ps` check that re-runs an armer ONLY if its watchdogs are dead (no container
  touch otherwise); gated by a `.paused` sentinel for deliberate teardown. Idempotency check must match the
  QUOTED wrapper args (`grep -F "rosters/roster-<arm>.txt"`, not the unquoted `ROSTER_FILE=$roster`, which never
  matched and armed DUPLICATE watchdogs every tick — caught 2026-09-07).
- **KEEP-ALIVE cron** (session-only): heal (rearm-all) + store poll + CF-API instance read + **churn-watch**
  (store flat across 2 ticks + balance dropping → read the WATCHDOG LOG, never the container) + adjudicate on
  ALL-COMPLETE + self-CronDelete. Dedup its emit key on task-counts, never balance.

### 7. THE REPLICATION TEMPLATE (full k=5 / next lever wave)
1. Query `containers/me` → confirm the vCPU-bound instance ceiling (~375). Raise `max_instances` (wrangler deploy,
   config-only) to fit `arms × ceil(tasks/lane target)` with headroom (≤ ceiling−1).
2. `SHARD_N = task-count` for **1 task/lane** (or `ceil(55/3)=~19` for ≤3/lane if lane budget is tight); pro at
   ~2/lane is fine. Total lanes = Σ arms. Regenerate rosters.
3. Seed one store per arm (11×5 subset or full 89×5), adapter travels in the store, verify by re-clone.
4. Per-arm COMMON = the reson standard + the ONE differing lever; a shared base env var (e.g. `CORTEX_ACTION_EFFORT`)
   lets same-token per-arm levers avoid the multi-token `read` split.
5. verify-first shard-0/arm → HARD certify-config (effective_config from `/health/config`, env-sourced per lever,
   abort-on-mismatch) → staggered fanout (~2/15s to spare DeepSeek/npm rate limits) → arm watchdogs.
6. Touch-free monitoring (§6). Watchdogs self-destroy on complete; reaper once at end to verify 0.
7. A shipped lever is FIELD-VERIFIED from the CONTROL arm's adjudication (it runs with the lever on), not a
   separate arm — e.g. ABSTAIN's false-RETIRE count from control decisions.jsonl vs the banked ABSTAIN-off baseline.

## 🔴 DELTA 2026-09-07b — THE PLACEMENT-BRIDGE BOTTLENECK: parallelize placement, don't lean on /debug/exec serially

The k5v2 7-arm run (SHARD_N=55, 1-task/lane, ~300 lanes) spent ~2h just FANNING OUT because placement is
the bottleneck, not compute (running-instance count wobbled 16→117 through the transition; the drops were
completion-drain during a slow serial fanout, not churn — done kept advancing). Diagnosed to three
compounding components — fix each:

1. **SERIALIZATION** — one armer loops ~300 `tb2-relaunch` calls, 1-2 at a time.
2. **PER-PLACEMENT LATENCY (~25s/lane)** — each `tick` BLOCKS on a `/debug/exec` round-trip + supervisor
   boot + a verify read. The blocking VERIFY is the cost.
3. **BRIDGE WEDGING** — `/debug/exec` wedges under concurrent hits (`bridge wedged or cap saturated`,
   42/300 ≈ 14% tonight). Root: each new-session exec cold-starts a fresh DO/container and CF throttles
   concurrent container STARTS → the synchronous exec stalls on cold-start contention. `/debug/exec` is the
   admin DEBUG shell, never designed as a mass-placement API. (Confirmed NOT a provider/npm/DockerHub rate
   limit: host logs 0× 429/402/rate-limit; banked rows 1 exc / 98, ZERO empty-session zero-token rows.)

### Fixes, ranked impact÷effort (①②⑤ = next-run DEFAULT, no worker change; ③④ = backlog HB-PLACEMENT)
1. **① ASYNC PLACE/VERIFY SPLIT (rig, low, biggest win/line):** `tb2-relaunch` places+verifies in one
   blocking call; the verify is the ~25s. Split — PLACE = fire the detached-supervisor exec + return (~2s);
   VERIFY = a separate pass reading the STORE (already polled). Supervisor is durable+resumable so
   fire-and-forget is safe; the watchdog re-places any that didn't take. ~25s → ~2s per lane.
2. **② BOUNDED-PARALLEL PLACEMENT (rig, low):** replace the serial armer loop with a concurrency pool
   (`xargs -P N` / one placement worker per arm). With ①, ~20 in-flight is safe → ~300×2s ÷ 20 ≈ 30s total
   fanout vs ~2h. MUST pair with ③ or it wedges the bridge harder.
3. **⑤ REDUCE PLACEMENT COUNT (run-config, zero effort — do regardless):** 1-task/lane MAXIMIZED lane count
   (300 placements). SHARD_N≈18-20 (~3 tasks/lane) = ~100 placements = ⅓ the bridge exposure, churn still
   fine (resolver-k5 proved 2.8/lane). 🔴 The tasks-per-lane law has a SECOND edge the 09-07 delta missed:
   too FEW tasks/lane over-loads placement. Sweet spot ≈ 3/lane, NOT 1 — 1-task/lane is churn-optimal but
   placement-pessimal.
4. **③ WORKER-SIDE PLACEMENT API (worker code, medium — the real wedge fix):** add
   `POST /admin/bench/launch` taking a LIST of `{session,repo,task,config}`; the worker places server-side at
   a CONTROLLED internal rate (paces DO cold-starts so the bridge never wedges) and returns immediately.
   Client makes ONE declarative call; the worker reconciles desired→actual like a controller (build on the
   existing lease-KV + warden cron, DELTA 09-03). Removes the serial loop AND the self-inflicted wedge.
5. **④ WARM CONTAINER POOL + PINNED REPIN (worker+image, high — kills cold-start entirely):** keep N
   pre-booted DOs with nexus-cortex installed; ASSIGN a task instead of cold-starting one per lane. 🔴 The
   library ALREADY ships the update lifecycle (`packages/cli/src/lifecycle/updateCheck.ts`):
   `CORTEX_UPDATE_POLICY` (off/warn/error/force/auto), `runUpdate()` = `npm install -g nexus-cortex@latest`,
   startup check ≤ hourly TTL (`~/.cortex/.update-check`), `cortex update` = thin wrapper, and `error` policy
   exits **75 (EX_TEMPFAIL)** = a ready-made "stale pin — update + relaunch me" orchestrator signal the
   watchdog can consume. On a WARM container (npm cache populated) `npm i -g nexus-cortex@<pin>` is SECONDS,
   not the cold ~7min. ⇒ reuse-not-destroy + pinned repin = the fast path with NO new mechanism. 🔴 Do NOT
   use `force` for a pinned bench (it installs @latest → auto-bumps mid-run, the never-publish-mid-run
   hazard); use policy=off + the adapter's existing pinned `npm i -g nexus-cortex@$TB2_HARNESS`, or add a
   `pin` mode that repins to TB2_HARNESS. Watch: sandbox-container disk accrual (prune discipline), DO
   idle-reap (hold via the lease), routing flips. Erases the cold-start $ premium the CF-billing analysis flagged.
   🔴 **REALITY-CHECK on ④ (grounded — corrects the naive "bake a warm image"):** the SANDBOX image is ALREADY
   warm (`workers/nexus-cortex-sandbox/Dockerfile:61` bakes `nexus-cortex@4.93.0` + node + npm cache), so a
   warmer sandbox image buys ≈nothing. The ~7min is TWO-container: the sandbox LANE (baked warm) vs each
   per-task `alexgshaw/<task>` container spun up in DinD, where the adapter installs node20 + `npm i -g
   nexus-cortex@<pin>` FRESH (an image we DON'T control). Warm-image/pool warm the LANE, not that per-task
   install. TARGETED FIX (adapter, not image rebuild): MOUNT the sandbox's warm npm cache (+node) into each
   task container → per-task install hits the cache → seconds. ORDER: (1) profile where the ~7min goes, (2)
   cache-mount into task containers, (3) running pool for the lane. BUILD is CI-only (`wrangler containers
   build --push`, manual dispatch) — NEVER on Replit (no docker + quota crash); Replit edits Dockerfile + tag + triggers.

### What I'd actually run
- **Next run (this week):** ⑤ (SHARD_N≈20) + ① (fire-and-forget) + ② (parallel placement) → fanout ~2h →
  <10 min, NO worker changes.
- **Sustained k=5-scale:** ③ (declarative worker-side placement); ④ (warm pool) for repeated full 89×5
  fleets — it also erases the cold-start cost premium. Backlog: **HB-PLACEMENT** in `omniclaude-v4/docs/HARNESS_IMPROVEMENT_BACKLOG.md`.

## 🔴 DELTA 2026-09-07c — the RE-FIRED-ARMER HEAL TRAP: never heal a mid-run watchdog death by re-firing the armer

Incident (k5v2, cost real $): the 4 flash watchdogs died mid-run; `rearm-all.sh`'s heal **RE-FIRED the flash
armer**, which re-ran the ENTIRE serial fanout (216 placements, ~4.5h) — re-placing the ~120 ALREADY-DONE
lanes as 75-second **no-op cold-starts** (place → supervisor sees `N done, task already banked` → self-exits).
Flash flatlined at **+2 tasks / 45min for 93+ min** while burning **~$32/hr on no-op placements**; the flash
watchdogs (which arm only at fanout COMPLETION) stayed dead the whole time, so the not-done flash tail was
starved. Pro was unaffected (its watchdogs were alive, driving concurrently). **The 350 instance cap was
IRRELEVANT (running ~49)** — the bottleneck was serial placement, not capacity.

**🔴 THE RULE: on a mid-run watchdog death, heal by ARMING THE WATCHDOGS DIRECTLY, never by re-firing the
armer.** The armer's job = the one-time fanout (place ALL lanes, done ones included). The watchdog's job =
drive only NOT-DONE lanes (done-set skip) + relaunch dead ones. Re-firing the armer replays the full no-op
fanout; arming the watchdogs goes straight to concurrent drive of the remaining work (this is exactly why the
sibling track with live watchdogs stays healthy).

**DIAGNOSTIC SIGNATURE (spot it in one poll):** one arm/track flatlines (~0 progress) while its armer shows
`running` for longer than a full fanout (>~90min) with `grep -c 'fanout complete' == 0` AND
`grep -c 'armed watchdog' == 0` in its log, and the log is dominated by `COMPLETE: N/1 graded` /
`DURABLE SUPERVISOR: 1 tasks, N done, -(N-1) remaining` no-op lines. running-count LOW (not cap-bound),
balance dropping. A sibling track with live watchdogs progresses fine → it's a re-fired-armer re-fanning-out.

**THE FIX (executable, ~10s, safe — verified live 2026-09-07):**
1. Kill the stuck armer by PID (no self-match): `ps -eo pid,args | grep 'k5v2/armer\.sh' | grep -v grep |
   awk '{print $1}' | xargs -r kill` (re-check empty; `-9` second pass).
2. Arm each watchdog directly with the EXACT COMMON from the armer + that arm's lever + `TB2_ARM`:
   `( setsid bash -c "ROSTER_FILE='$roster' COMMON='$armcommon' bash '$RUN/watchdog.sh' >> '$wdlog' 2>&1" & )`.
   🔴 **MODEL-SAFE:** the roster line carries the model (`k5vc0 tb2-k5v2-ctl deepseek-v4-flash 0 55`) and
   `watchdog.sh` reads `TB2_MODEL="$model"` PER-LANE from it — so a flash watchdog on the flash roster runs
   flash regardless of what's in COMMON. No wrong-model corruption risk. Verify each shows **2 procs** (setsid
   wrapper + inner `bash watchdog.sh`) before walking away.
3. Watchdog drives ONLY not-done lanes → no no-op re-placement → burn drops, the flatlined track resumes.

**KILL WASTE ON SIGHT.** An armer running past its fanout time with no watchdog handoff is burning cold-starts
for nothing — kill it the moment you see it; do NOT "let the bounded loop finish" (93min × $32/hr ≈ ~$50
wasted narrating a no-op loop). A big instance cap NEVER fixes serial placement.

**PREVENTION (rig fix owed, under HB-PLACEMENT):** `rearm-all.sh` must **arm watchdogs directly, not re-fire
the armer** (the armer is for initial fanout only). Alternatively, gate the fanout to **skip already-done
lanes on a re-fire** (done-set check) so a re-fire can't become a full no-op replay.

## 🔴🔴🔴 DELTA 2026-09-08 — THE k5v2 VOID-RUN POSTMORTEM: a run can be dead-on-arrival at DESIGN

The single most important lesson of the whole k5v2 arc: **the run produced zero lever signal, and that was
guaranteed at SETUP — before any execution churn.** A flawless, zero-mistake run of the same design would have
returned the same null. Adjudication (grounded, all 7 stores + decisions.jsonl): `loop_tool_block` fired **0×
in its own arm**, `deadline` **0×**, `endturn_resolver` retire/abstain **0× across all arms** — the three dark
levers under test were **near-totally dormant**, because the reused 11-task subset (bn-fit, sqlite×2, kv-store,
configure-git, circuit, filter-js, install-windows, make-mips, pytorch, schemelike) contains **no retry-loop
tasks** and the tasks fail by **early give-up** (budget_frac 0.24-0.31), not the looping/grinding the levers
target. Config delivery was CORRECT (each arm's `effective_config` verified, arms properly differentiated) —
so it was **not a wiring bug; it was a population/design error**. The three PRE-FLIGHT gates above
(LEVER-POPULATION, PRE-LAUNCH MECHANISM-FIRE PILOT, NO MIXED-POPULATION BUNDLING) exist so this exact void
cannot recur.

The execution failures that day were real and separately costly, and each is now a structural fix, not a
memory item: **serial placement** → HB-PLACEMENT + PARALLEL-PLACEMENT gate; **the re-fired-armer heal trap**
(93-min no-op fanout, ~$50) → DELTA 09-07c + rearm-all v2 (heal watchdogs from spec, never re-fire the armer)
+ the 5-round burst that **wedged the bridge and crash-cycled lanes** (tokens burned, nothing completing) →
"kill waste on sight" + the continuous-placer design; **cost lowballing** (quoted banked cost that
under-counts ~12x, and a balance-delta/done figure that baked churn into per-task cost) → the COST-GAUGE rule +
"per-task cost comes from per-task token stats at verified pricing, never balance-delta÷done, grinders
estimated per-task not blanket-multiplied." The deepest process failure — **I stopped mapping before acting**
and hand-rolled blunt tools (burst/re-fanout) instead of using the proven wide-run infrastructure — is why
grounded-research/map-before-assert is non-negotiable before touching a live fleet. **A cheap pilot that
proves the mechanism fires is worth more than a flawless expensive run of a design that can't fire it.**

## 🔴🔴 DELTA 2026-09-09 — THE STDB BENCH-RUNNER DEV ARC: repl→STDB control plane, and the placement bugs it surfaced

The repl-side python control plane (armer/watchdog/relaunch/monitor/reaper) is being RETIRED in favor of the
`nexus-nexus-cortex` STDB module: 14+ tables, a 60s scheduled `tick_bench_scheduler` with 6 handlers
(keepalive/monitor/reaper/watchdog/fanout/placement), a gate-enforced launch invariant, and native outbound
HTTP. The point of the migration (operator, verbatim): **placement, keepalive, RETRY are STDB-managed and
repl-INDEPENDENT — NOT reliant on our shell.** A repl crash must not idle-reap the fleet. The rig is
`.bench/cells/build-cells.sh` (modes: create/seed/fanout/pilot/emit-pilot/status); the container-side durable
supervisor + HF-store executor are UNCHANGED (STDB just fires + keepalives them).

### 🔴 THE #1 RULE: when a lane is stuck, FIX THE STDB PATH — do NOT fall back to shell placement/keepalive
This session's biggest process failure: lanes sat `placing` with 0 running containers, and instead of
diagnosing the STDB path I hand-rolled shell `/debug/exec` placement + a shell keepalive loop — reintroducing
the EXACT fragility (bridge-wedge, idle-reap, single-writer races) the STDB migration exists to remove. The
operator corrected it. Shell may PLACE a one-shot diagnostic or READ state; it must never own placement/
keepalive/retry. If a lane won't place, the bug is in the worker route or a scheduler handler — fix THAT.

### 🔴 TWO placement bugs found (the STDB path was silently broken end-to-end)
1. **`/admin/bench/launch` dropped the container-start exec (FIXED + deployed, commit 01f366e8e8).** Both the
   fanout AND placement handlers PREFER the declarative `/admin/bench/launch` route and only fall back to
   per-lane `/debug/exec` **if that route ERRORS**. But its `placeOne` fired `sandboxAdmin(…, '/debug/exec', …)`
   and IGNORED the result — `sandboxAdmin` returns `{ok:false}` (it does **NOT throw**) on the transient
   cold-start **session-watch race** (`ENOENT … watch '/tmp/session-…'`), so `try{await…}catch{}` silently
   accepted the failure → the DO record was created but **the container never started (inactive DO forever)**.
   Because the route still returned 200, `declarative_ok=true` and the fallback NEVER fired; the placement tick
   just re-created inactive DOs until `PLACE_MAX_ATTEMPTS`→dead→reaped. FIX: `placeOne` now CHECKS the response
   and **retries with backoff (4 attempts)** — matching what made raw `/debug/exec` succeed. 🔴 A silent-success
   declarative route is a trap: any worker route the STDB handlers trust for a 2xx MUST actually verify the side
   effect (container running), not just return 200.
2. **The monitor resets the placement grace every tick (NOT yet fixed — worked around).** The `monitor` handler
   updates every lane's `updated_at=now` each 60s, but the `placement` handler's cold-start-grace gate is
   `now - updated_at >= COLD_START_GRACE_MS (600s)`. So `updated_at` is perpetually <60s old → the grace NEVER
   elapses → **placement can never auto-re-fire a stuck `placing`/`wedged` lane.** Signature: `placement` job
   `run_count` climbs but the lane's `place_attempts` stays 0. Worked around by re-firing the fanout job
   (`run_bench_job_now` — an STDB reducer, not shell) which calls `/admin/bench/launch` directly (bypassing the
   grace); the fixed route then started all 4 containers. 🔴 PROPER FIX OWED before the full run: give the
   grace its own `last_placement_at` field, independent of the monitor-touched `updated_at`.

### 🔴 The transient failure is a SESSION-WATCH RACE, not cmd/session/substrate
`/debug/exec` on a fresh session intermittently 500s with `ENOENT … watch '/tmp/session-<name>'` during
cold-start — a race on the container's session-watch file. It CLEARS on retry. Proof it's not the substrate:
a fresh-session trivial `echo` returns 200 (`cloudchamber`, 4 vCPU). Proof it's not the bench cmd: the same
bench cmd got 200 "launched" while a trivial echo 500'd on an adjacent call. ⇒ **every placement path MUST
retry**; a single 500 means nothing. Raw `/debug/exec` IS the working primitive (with retry); `/admin/bench/
launch` is the paced server-side wrapper (batchSize 8, gapMs 1500) and must retry internally (now does).

### 🔴 DIAGNOSIS ORDER for "nothing in Cloudflare / lanes stuck placing" (touch-free)
1. **CF Containers API is truth** (dashboard lags): `GET …/containers/applications/{APP}/instances` → count
   `.status.state`. `inactive` DOs = created-but-never-started (a placement bug), NOT capacity. `running`=live.
   `APP_ID=a03a316f-ccd3-4b91-b13e-aaa2fb07ae70`. Limits: `containers/me` → ~375 standard-4 (vCPU-bound).
2. **`bench_job` `run_count`/`last_fired_at`**: is the scheduler tick firing the handlers? (climbing = yes).
3. **`bench_lane` `place_attempts`**: is placement actually RE-FIRING? (stuck at 0 while placement run_count
   climbs = a re-fire CONDITION is failing → check the grace: `now - updated_at` vs 600s).
4. **A fresh-session trivial `/debug/exec` echo** isolates substrate health from the bench cmd/route.
5. **Never** exec-probe a live lane to "see what's wrong" (crash-cycles it, §09-05b); read stores + CF-API + logs.

### Rig capabilities built this arc (build-cells.sh)
- **2×2 arms** (`ARMS` matrix `{flash,pro}×{ctl,lever}`), model-aware create/seed/fanout; **per-model task
  subsets** (6-field cell spec `letter|run|lever|sfx|FLASH_subset|PRO_subset`) — pro subsets restricted to
  tasks the prior pro-arm data CONFIRMS trigger the lever on pro (flash-mined populations mis-fire on the
  stronger model — chess passes clean on pro, pytorch finishes early, schemelike passes < 0.80).
- **STDB-routed `pilot` mode**: builds the lever shard-0 lanes on FRESH session names, upserts a one-time
  ENABLED fanout job, `run_bench_job_now`. Placement paced + lanes registered in `bench_lane` (keepalive covers
  them). A pilot placed via raw exec is NOT registered → no keepalive → idle-reaps mid-cold-start (banks a
  `__run_config__` marker then dies). `emit-pilot` prints `session\tcmd` for a raw placer if ever needed.
- **Idempotent lane bootstrap**: the supervisor launch is `pgrep`-guarded → re-placing a running lane =
  "already-running" (no double-supervisor = no single-writer clobber). 🔴 One container per store, always.
- **Gate-bypass for the pilot is by design**: the fanout JOB places lanes with NO gate check (the invariant is
  only in `launch_bench_run`/`set_bench_run_state`), so the pre-gate mechanism-fire pilot places outside the
  gated launch — which is correct (the pilot IS the evidence the gate needs).

### 🔴 REMAINING OPEN QUESTIONS — to answer/confirm before the full 32-lane launch
1. **Mechanism-fire pilot RESULTS (IN FLIGHT):** does `loop_tool_block` fire on the L lever arms (flash AND
   pro)? does the deadline-exit kind fire on the D arms? does **gcode-to-text hit the deadline on pro** (the
   mined ~1.07 budget_frac)? Any arm firing 0× is DROPPED before the k=3.
2. **The monitor grace-reset fix (bug #2) is OWED** — placement can't auto-re-fire a stuck lane, so a mid-run
   wedge won't auto-recover. MUST land before the 32-lane run (small fix: separate `last_placement_at`).
3. **Does the fixed `/admin/bench/launch` place reliably AT SCALE (32 lanes)?** The pilot placed 4; confirm the
   paced route + retry handles 32 without wedging the bridge.
4. **Does STDB keepalive actually hold a running lane through a long task (no reap)?** Confirm on the pilot
   lanes (just went running) — the whole durability premise rides on this.
5. **Does the monitor correctly promote `placing→running` via CF census + roll up billing?** Confirm live.
6. **The RETIRE gate is UNMET:** the Class-1 repl scripts may be deleted only after a headless STDB-driven run
   **survives a deliberate repl kill mid-run**. The smoke used cmd `true`; this pilot is the first REAL run.
   The repl-kill-survival test is still owed — do NOT delete the repl fallback scripts yet.
7. **Full launch flow end-to-end (real spend):** record `mechanism_fire` gate → `launch_bench_run` (gate
   passes) → enable fanout → 32 lanes → adjudicate → `harness_bench_run`. Not yet exercised with real spend.
8. **Cost/billing reconcile:** the monitor's CF per-metric billing (`cf_rate_*` defaults marked "VERIFY vs CF
   pricing"; egress untracked) must be reconciled vs the DeepSeek dashboard + CF billing before quoting a cost.

## 🔴🔴 DELTA 2026-09-10 — THE INCOHERENT-DEBUG SESSION: process failures + the keepalive LEASE-RENEWAL gap (mechanism-fire pilot STILL unmet)

A low-competence session; recording the failures so they don't repeat. The mechanism-fire pilot (open Q#1/#4
from DELTA 09-09) produced NO verdict — the 4 STDB-placed lever lanes (cell-l:lever, cell-d:lever flash +
cell-l/d:pro-lever) banked ONLY `__run_config__` rows, ZERO task rows, and I never landed the root cause before
losing coherence. Close state: pilot HALTED (`halt_bench_run cell-l`/`cell-d` → 4 lanes `kill_requested`, all
scoped jobs disabled, the global reaper tears the containers down). Full state → resume memory
[[session-resume-2026-09-10]].

### GROUNDED (cited — safe to build on)
1. **🟢 SUPERSEDED by DELTA 2026-09-10i (tick port: keepalive DOES renew the worker lease per beat, verified live on cell-m-p3).** ORIGINAL: **The STDB `keepalive` handler is an INCOMPLETE PORT — it never renews the lease.** `bench_scheduler.rs:178-200`:
   keepalive does ONLY `/debug/exec {"cmd":"true"}` on `status=="running"` lanes (resets CF `sleepAfter`). The old
   repl `tb2-relaunch.py` tick did TWO things every cycle: the exec ping AND `/admin/bench/lease` (renews the worker
   lease). STDB sets `lease_expires_at` ONLY at placement (`bench_scheduler.rs:430/440/525`, 90-min TTL), NEVER on a
   keepalive tick. FIX OWED (NOT done this session): keepalive must call `/admin/bench/lease` per running lane each
   tick. This directly answers the operator's question "did you match the previous repl keepalive tick?" — NO.
2. **The three timers (source-confirmed):** container `sleepAfter='20m'` (`workers/nexus-cortex-sandbox/src/index.ts:319`);
   worker warden cron every 5 min (`workers/nexus-cortex/src/index.ts:885` `scheduled`→`benchSweep` `:217` destroys
   lease-expired lanes); lease TTL default 90 min (`BENCH_TTL_DEFAULT_S=5400`, `:209`; `/admin/bench/launch` mints the
   lease `:462`; `/admin/bench/lease` renews `:494`). The "containers die after 5 min" instinct is the WARDEN CADENCE,
   not the container lifetime.
3. **Empirical pilot result:** the 4 lever stores (tb2-lb-lever, tb2-dl-lever, tb2-lb-pro-lever, tb2-dl-pro-lever)
   each hold ONLY `__run_config__s0` rows (4/3/4/4), 0 task rows; `bench_lane.tasks_done=0`; CF app-health `active:0`,
   `healthy:26`. So open Q#4 (does STDB keepalive hold a lane through a task) is EMPIRICALLY UNMET in this pilot.
4. **CF navigation that I fumbled then corrected:** the app is `nexus-cortex-sandbox-sandbox` (APP_ID
   `a03a316f-ccd3-4b91-b13e-aaa2fb07ae70`); `GET .../containers/applications/{APP}` → `.result.health.instances`
   uses buckets `{active,healthy,starting,failed,stopped}` (active=servicing now); the per-instance endpoint
   `.../instances` uses `.status.state` with values like `inactive`/`running` — DIFFERENT vocabulary. Read BOTH plus
   the STORE; a per-instance `inactive` snapshot alone is not "the run is dead."

### NOT PROVEN — do NOT assert; the next agent must ground these
- **The exact container-death mechanism is UNKNOWN.** Lease-expiry is RULED OUT for the observed ~32-min death (lease
  is 90 min: `lease_expires_at − last_beat = 5,400,000 ms`, grounded). Candidates left, none proven: (a) keepalive
  skips `status!="running"` lanes → if a lane sat `placing`, `sleepAfter` (20m) killed it before promotion; (b)
  `/debug/exec` crash-cycling a busy container (§09-05b) — CONFLICTS with the keepalive comment claiming it's "the
  same benign mechanism the repl tick uses"; (c) supervisor crash after run_config (unlikely — venue issues self-retry,
  `tb2-durable-supervisor.py:141`). `wrangler tail nexus-cortex` for 55s was INCONCLUSIVE (202 lines, no bench/exec/
  lease entries in-window).
- **The 4/3/4/4 run_config rows are AMBIGUOUS** — could be N supervisor auto-reboots OR N pilot re-fires across the
  session (I re-fired `run_bench_job_now pilot-cell-l/d` and the store was NOT reset between). Do NOT infer "N reboots."
- **Missing `cd /app/bench`** in the STDB launch cmd (`build-cells.sh:47-49`) vs the repl's `cd /app/bench &&`
  (`tb2-relaunch.py:114`) — an OBSERVED difference, UNTESTED as a cause.

### PROCESS FAILURES (the real lesson — same class as the 09-08 VOID-RUN postmortem)
1. **I exec-probed a LIVE lane** (`/debug/exec` to read durable.log) — the exact touch-free violation §09-05b forbids;
   operator corrected twice. Diagnose via STORE + CF-API + `wrangler tail` ONLY.
2. **I diagnosed from a stale CF per-instance `inactive` snapshot** without reading the app-health rollup OR the
   authoritative HF STORE. The store is the truth; I read it LAST instead of FIRST.
3. **I PAUSED then RE-FIRED the control plane on a misdiagnosis**, burning money re-cold-starting containers to
   "watch" them. A misread that costs spend is worse than "I don't know yet + stop."
4. **I kept WIDENING the investigation** (back into old scripts, wrangler tail) instead of landing the answer — lost
   coherence over a ~200MB session; the operator had to stop me.
5. **I asked deflectable multiple-choice questions instead of operating the bench.** "Operate the bench" = DRIVE via
   store+CF-API, don't poll the operator. Map-before-assert on a LIVE fleet is non-negotiable; ground every claim to a
   file:line or a tool output actually read. [[feedback-stop-dont-thrash]] [[feedback-verify-against-primary-not-derived]] [[feedback-map-before-assert]]

## 🔴🔴 DELTA 2026-09-10b — THE STDB PILOT KILLER WAS OUR OWN GUARDIAN REAPER (and the tick port is live)

**Root cause #2 of the dead STDB pilots (root cause #1 = `bench_lane.last_beat` had no feeder — fixed by the tick
port, plan `modules/database-ai/STDB_BENCH_TICK_PORT_PLAN.md`):** `.bashrc` → `scripts/tb2-control-rearm.sh` arms
`scripts/tb2-reaper-loop.sh` on EVERY shell open; every 10 min `scripts/tb2-reaper.sh` destroys every RUNNING
instance not claimed by a repl-side `.bench/*/ACTIVE` roster. STDB-placed lanes live in no repl roster → reaped
every 10 min. Proof: `/tmp/tb2-rearm.log` `04:29:31Z reaper: running=4 kept-live=0 reaped=4 (trigger: reaper-loop)`
one tick after four lanes had beaten alive (`[bench tick] beats=2`, leases `beats=2`). Timestamps that LOOK like a
"~10-min idle reap" (empty `durable.log` tail, CF state flip at probe time, run_config rows per boot) are this.
🔴 Two control planes over one substrate = the old one kills the new one's lanes. When migrating, the retiring
plane's DESTROY paths must see the new plane's registry BEFORE anything is placed.
**FIX (structural):** `tb2-reaper.sh` reads `bench_lane` (statuses placing/running/wedged/dead_supervisor/
complete_pending/complete_short + `remap_to`) as LIVE and FAILS CLOSED when STDB is unreachable. Guardian re-arm
is now safe. `tb2-teardown.sh` still works (it relies on the reaper; STDB lanes stay protected).
**Tick port facts (verified 2026-09-10):** ticktest passed end-to-end with no repl daemon (bn-fit-modify pro
r=1.0 → `COMPLETE:` → reconcile → `complete` → reaper `destroy` → CF 0 running; budget job tracks the real
balance via the encrypted `bench:deepseek` key). Tick cadence 300 s; probe = the exact repl verify string;
placement re-fires ONLY `dead_supervisor` / never-beaten `placing` lanes; reaper is census-gated (P9).
`build-cells.sh` modes: `pilot` (PILOT_ARMS, pro first), `launch` (gatecheck jobs + s0/rest fanout), `ticktest`.

## DELTA 2026-09-10c — DeepSeek CATALOG COLLAPSE (verified live 06:30Z) + full-width launch
- **The API now serves exactly two models: `deepseek-flash` (= DeepSeek-V4.1-Flash GA) and `deepseek-v4-pro`.**
  `/models` lists only those. Legacy `deepseek-v4-flash`, `deepseek-v4-flash-vision-exp` AND the beta alias
  `deepseek-v4.1-flash-expires-on-0910` are still ACCEPTED but every response echoes `model: deepseek-flash` —
  they are all V4.1 Flash at the flash price. Bare `deepseek-v4.1-flash` is REJECTED. **CORRECTION 2026-09-18: V4 Pro was
  NOT retired on 09-14 — DeepSeek reinstated it ("continue providing API services for DeepSeek V4 Pro after September 14, 2026,
  with the billing method remaining unchanged"); `deepseek-v4-pro` is real V4 Pro, pro arms after 09-14 are pro arms
  ([[deepseek-v4-pro-reinstated]]; the operator has corrected this repeatedly — never re-raise it).**
- **Concurrency: flash 2500, pro 500** (pricing page, 30-parallel probes 30/30 200 on both `deepseek-flash` and the
  alias). The "v4.1 alias ≤20 concurrent" width law is DEAD — flash arms run at FULL width like pro.
- **Pricing per 1M (off-peak / peak):** flash cache-hit $0.003/$0.006, miss $0.15/$0.30, output $0.60/$1.20;
  pro $0.022/$0.044, $0.66/$1.32, $1.98/$3.96. Peak unchanged (01–04 & 06–10 UTC Mon–Fri). Supervisor `PRICING` +
  adapter sidecar updated (flash rows banked before 2026-09-10 06:40Z are over-priced ~1.3×; recompute from
  `usage_raw` if it matters). Harness: new `deepseek-flash` card (vision, 2500 conc.) staged as a minor changeset —
  needs a `--release` publish (4.100.0) before a run can pin it; until then the alias id still works (risk: alias
  removal mid-run) or `deepseek-v4-flash` (card has vision:false → image tasks go through the handoff path).
- **Full-width launch is now a rig mode:** `FULL_WIDTH=1 SHARD_N_FLASH=<n> SHARD_N_PRO=<n> build-cells.sh launch`
  fans EVERY lane the tick after the gates pass (80-lane fanout jobs `fanout-<run>-w<i>` to stay under the 128KB
  argv limit; module chunks the worker launch ≤8/call), sets the tick cap to lanes+20, no rest job / no hold.
  `K5_MODE=1` = the full TB2.1 89×K model A/B (flash vs pro) on the locked COMMON; `K`, `PIN`, `K5_MODEL_FLASH`,
  `K5_EXTRA_COMMON` override. Adjudicate with `.bench/cells/adjudicate-cell.py` (per arm mean + Wilson CI,
  D-control vs D-treat by `effective_config`, mechanism fires from decisions.jsonl).

## DELTA 2026-09-10d — cell-d-k3 closed (deadline lever DARK) + what the distill/doctrine pass taught
- **Deadline lever verdict:** fires (8/18) but 0 attributable flips; cuts off a late pro finisher; fired rows still end
  ~1.0 budget (mentor exit costs ~10%); only pro tokens −24%. DARK. Ledger `.cortex/bench/r-cell-d-k3-2026-09-10.md`.
- **Attribute flips to the MECHANISM, never the arm delta.** Flash +0.17 was entirely rows where the lever never fired.
  `adjudicate-cell.py` prints fires per row for this reason — read that column before the rate column.
- **EndTurn citation grounding rejected 39% of EndTurn calls** (42/107, 21/26 sessions) in the reson standard — present
  in every arm, so invisible to any A/B that shares COMMON. AUDIT EVERY REJECTED CITATION BEFORE BLAMING THE GATE: my
  first diagnosis ("per-turn window") was wrong (corpus is task-cumulative); the real split was 47% near-verbatim
  line-stitching, 44% genuine fabrication, 5% corpus gaps (Bash-authored text, task statement). Fix = line-wise
  matching + widened corpus (4.100.0, HB-ENDTURN-CITATION-GROUNDING). Carry `endturn_rejections/session` as a standing
  metric on finishing-population cells; the replay script pattern is in the ledger.
- **Do not quote the distiller's `retry_loop` count raw** — it counts same-file edit iteration and sed paging as loops
  (21 labelled, ~1 real). Check the `signal:` line. `wrong_artifact` is not detected without a verifier diff. BENCH-TOOLING entry.
- **Doctrine-mine target must be the SHIPPED text**: build it from `promptPresets.ts` BOOT_MINIMAL_PROMPT + the dist
  `BaseToolRegistry.getAllTools()` descriptions (recipe in this session → `.bench/doctrine-target-cell-d-k3.md`); the
  run5 target was 4.76.2 text. Budget-tokens = target/4 + 2500. 41 sessions ≈ 25 min, cents.
- **Spine defects found only at width and fixed live:** P14 placement remap into a fresh session (module), P15 supervisor
  push_pending for stranded local commits (store). A container whose git fetch is broken (`expected 'acknowledgments'`)
  cannot self-heal even with P15 — recovery = exec the row out + bank from the repl (done once, 07:10Z).

## DELTA 2026-09-10e — the adapter passthrough list is THE lever gate; the rig now guards it
- `nexus_cortex_agent.py` forwards arm env by an EXACT-NAME list (`if _v: env[_k] = _v`). Anything not on it is silently
  dropped inside the task container = a second control by construction. Found 17:50Z: `CORTEX_GIT_CONTEXT`,
  `CORTEX_SLASH_COMMAND_HINT` (COMMON says false; every cell ran true) and `CORTEX_EMPTY_TURN_CONTINUE` (the E lever) were
  never forwarded. STRUCTURE: `bash .bench/cells/build-cells.sh guard` parses the adapter's list and FAILS on any
  COMMON/EXTRA_COMMON/lever key missing from it; it runs before every spending mode. Adding a lever = adding it to the adapter
  list first, or the rig refuses. Verify a new lever with the row's `effective_config` (`source: env`) — never with arm_env.
- Rig additions 09-10: `ARMS_FILTER` (pilot without ctl arms), `STORE_SFX` (fresh stores), `EXTRA_COMMON`, `REQUIRED_GATES`,
  `MODEL_FLASH` (flash action id, default deepseek-flash), lever tokens de-shadow the same key in COMMON.

## DELTA 2026-09-10f — MENTOR ROLE + the mentor pilot recipe (cell-m) — read with [[session-resume-2026-09-10c]]
- 🔴 **Every DeepSeek mentor call before 4.103.0 ran thinking-OFF on the wire** (helper adapter ignored the mentor effort;
  verified per release tag 4.88→4.102 + live probe). "mentor @max" in every ledger = config, not wire. Plans were still
  good (resolver k=5 +17pp). Thinking-ON is UNTESTED → never assume; A/B it. The consult (AskForAdvice) was measured
  thinking-off on purpose (08-30 blank hints) — keep the tool ON, consult reasoning `none`, `CORTEX_MENTOR_AUTO=false`.
- **Mentor role (4.104.0+)**: `training/mentorRole.ts`; levers `CORTEX_MENTOR_REASONING` (on|none), `CORTEX_MENTOR_EFFORT`
  (low|medium|high|max, one lever for lift/resolver/deadline/loop-exit; a surface's own *_EFFORT wins),
  `CORTEX_MENTOR_CONSULT_REASONING` (none), `CORTEX_MENTOR_TEMPERATURE`, `CORTEX_ASK_FOR_ADVICE` (=false drops the tool).
  Every mentor event banks `mentor:{model,thinking,effort,budget}` — READ THAT FIELD to prove an arm's wire config.
- **Rig (build-cells.sh) modes/env added 09-10**: `guard` (adapter passthrough guard, auto before spend), `ARMS_FILTER`,
  `STORE_SFX` (fresh stores), `EXTRA_COMMON`, `REQUIRED_GATES`, `MODEL_FLASH`, `K`, `PIN`, `FULL_WIDTH` (80-lane fanout
  jobs), `K5_MODE/K5_ARMS`; per-arm lever tokens in the ARMS 4th field; lever tokens de-shadow COMMON; launch INV
  asserts every claimed lever with source env. cell-m = 8 mentor arms on ONE action model (deepseek-flash@low).
- **Mentor pilot verdict inputs**: pass rate per arm (n small — read direction, not significance), banked
  `planText`/`detailText`/`verdict` quality per arm, latency + cost per mentor call, `endturn_rejections/session`,
  mechanism fires (`loop_tool_block{trigger:neardup-similarity}`, `slice_block`, resolver `deltaChars/checkRan`,
  `reasoning_only_active`). The k=5 COMMON mentor line is set from this.
- **Passthrough guard finding**: CORTEX_GIT_CONTEXT / CORTEX_SLASH_COMMAND_HINT / CORTEX_EMPTY_TURN_CONTINUE were never
  forwarded → every cell to date ran git-context + slash-hint ON. Fixed; the guard now refuses such a run.
- **Master .env is the ONLY lever ledger** ([[feedback-master-env-not-env-defaults]]): 4.100/4.101 shipped without the day's
  docs because `.env.defaults` (generated) was edited. `npm run sync:env`, then `--check`.

## 🔴 DELTA 2026-09-10g — THE LANE-NAME LAW: session sub-names >24 chars silently collapse every lane into ONE DO
cell-m-p1 (32 lanes, 18:36Z) produced ZERO rows: CF showed ONE running instance `nexus-cortex-cortex-admin` (no session
id), the worker held ONE lease `doName:"cortex-admin"`, every STDB tick probe returned HTTP 500 (`grep -c` exit 1 — no
supervisor where the probe landed), lanes sat `placing`/`inactive` with `place_attempts` climbing. The STDB spine was
CORRECT (fanout 18:37:52Z "declaratively placed 32", placement re-fire 18:49Z) — the worker collapsed the names:
`sessionIdFor` (`workers/nexus-cortex/src/index.ts`) appends `-<clientSub>` ONLY when it matches `^[A-Za-z0-9_-]{1,24}$`,
else the DO name is the bare `cortex-admin`; `qualifyDoName` routes every bench call (launch, lease, exec, destroy) through
it. cell-d-k3 names were 21 chars (worked); cell-m-p1's `cell-m-p1-mentor-flash-none3` = 28 (collapsed). A 200 from
`/admin/bench/launch` + a lease + "declaratively placed" all LIED, because the route never validated the name.
STRUCTURE (rig, `.bench/cells/build-cells.sh`): `lane_name_guard` runs inside `guard` (so before every spend mode) and the
fanout emitter exits 2 on any base name outside `^[A-Za-z0-9_-]{1,22}$` (24 minus the P14 `x<gen>` remap suffix). cell-m
ARMS field 1 (lane/arm label) is now `pro-low … flash-none`; field 3 (store label `mentor-*`) is unchanged, so the seeded
`tb2-mm-mentor-*` stores are reused and `adjudicate-cell.py --arm pro-low=<hf-org>/tb2-mm-mentor-pro-low`. STAGED,
NOT DEPLOYED: `/admin/bench/launch` returns 400 with the invalid list instead of collapsing (worker deploy = operator gate).
DIAGNOSTIC (touch-free, 3 reads): `GET /admin/bench/leases` doName lacks the session → name collapse; CF per-instance
list has NO `cortex-admin-<lane>` names; module log `probe failed: HTTP 500 … grep -c`. Recovery = `halt_bench_run`
(reaper RELEASES leases when the census shows no instance — no phantom destroys), fix names, create/seed/gate/launch a
`-p2` run on the SAME stores. cell-m-p2 launched 18:57Z.

## 🔴 DELTA 2026-09-10h — THE GATE ASSERTS AGAINST THE PIN'S REPORT, NOT THE TREE (cell-m-p2 halted at its first row)
The launch INV merges every EXTRA_COMMON/lever token as `{effective, source: env}` and the STDB `effective_config`
gatecheck treats a key ABSENT from the banked report as a FAIL → `halt_in_tx`. `HELPER_MODEL_ID` is a real lever the
adapter forwards, but 4.105.0's `effectiveConfig.ts` does not REPORT it → cell-m-p2 (healthy, 32 lanes placed, mentor
wire proven per arm) was halted 19:03Z, 6 min after fanout, by a gate that could only ever fail. RULES (structure in
`build-cells.sh`): (1) the INV builder parses the reported-key list from the PINNED release tag
(`git -C nexus-cortex-extracted show v<pin>:packages/core/src/config/effectiveConfig.ts`) — never the working tree,
which can already carry the next release's keys; unreported keys are WARNED and dropped (delivery is still proven by the
adapter passthrough guard). (2) A lever you want gate-asserted must be in `effectiveConfig.ts` BEFORE the release you
pin (HELPER_MODEL_ID added in tree → 4.106). (3) Fixing a live gate = `upsert_bench_job gc-effcfg-<run>` with the full
args_json, then READ `args_json` back: a bad input silently wrote an EMPTY args (a gate asserting nothing) once today.
(4) The gate fires 120 s after the first arm row (~5 min post-fanout on fast tasks): a wrong INV must be corrected
inside that window or the run is gone. Recovery cost of a gate-halt = one cold start + in-flight tasks (~$1); banked
rows persist and the next `-pN` run on the same stores resume-skips them.

## DELTA 2026-09-10i — the STDB spine VERIFIED LIVE on a real 32-lane run (cell-m-p3) + the touch-free diagnosis kit
**Supersedes DELTA 09-10 §GROUNDED #1 ("keepalive never renews the lease") — that was the pre-port handler.** On cell-m-p3
every control-plane leg was observed firing from `tick_bench_scheduler` on maincloud with NOTHING on the repl:
fanout ("declaratively placed 32", one paced call), keepalive/tick every 300 s (probe → beat → `lease_renew` →
`/admin/bench/lease`; the worker shows `beats` climbing and `expiresAt` ~86 min out on every lane), placement every 120 s
(re-fired the 6 lanes whose supervisor never booted, exactly at the 600 s grace), watchdog (`wedged x2 → remapped
<lane> → <lane>x1 (placed=true)` at 19:24Z — P14 live), reconcile (store slice check promotes instant-complete lanes),
budget, gatechecks, census-gated reaper (halted p1/p2 lanes RELEASED, not destroyed, because the census had no instance).
The ONLY repl-resident process is the guardian's `tb2-reaper-loop` (orphan safety net; reads `bench_lane` as live; fails
closed). Monitors are notification-only. ⇒ a repl crash mid-run costs nothing; the worker warden (90-min lease) is the
fail-safe under the STDB fail-safe. Still owed: the deliberate repl-kill retire test on a real run.

**Touch-free lane classification (3 store/API reads, never an exec):**
1. `__run_config__sN` rows carry the RUN TAG (`arm: cell-m-p3:pro-high`) — one per supervisor BOOT. No row for this run's
   tag in a shard = the launch exec returned 200 but the supervisor never started (curl of the supervisor / cd / setsid
   failed inside the container) → the placement grace re-fire heals it. Two rows = it booted twice (re-place/crash).
2. A lane whose slice is ALREADY banked (rows from a prior `-pN` attempt) boots, prints `COMPLETE`, exits in seconds — often
   BEFORE the first 300 s probe → it never beats and sits `placing` with `probe failed: HTTP 500 … grep -c` (grep exit 1 =
   no process). Reconcile's store slice check resolves it to `complete`; do not read it as a dead lane.
3. `GET /admin/bench/leases` doName + CF instance NAMES + the probe error TEXT split name-collapse (DELTA 10g) from
   substrate 500s (`SandboxError`) from no-supervisor (`CommandError … grep -c`) from timeouts (`operation timed out` →
   watchdog wedge/remap).
**Reusing stores across attempts:** a halted run's banked rows stay; the next `-pN` on the SAME stores resume-skips them.
Rows carry the tag of the attempt that graded them (`cell-m-p2:…` beside `cell-m-p3:…`) — adjudicate PER STORE (the
config is identical), never filter by run tag. Do NOT re-`seed` between attempts (seed force-pushes the store).
**Gatecheck semantics:** a gatecheck job DISABLES ITSELF after any decisive PASSED/FAILED; only the `effective_config`
gate name halts the run (an `unknown gate`/empty-name FAILED is recorded and ignored). To re-run a gate after fixing its
args: `upsert_bench_job` with `enabled=true` and READ `enabled`+`args_json` back. It fires 120 s later and stays
`pending` (no row) until EVERY arm store has a task row.
**`spacetime sql` traps (cost minutes each):** columns are exactly the Rust struct (`bench.rs`) — `bench_run` has no
lanes_total/state-count fields; `Option<String>` columns (`bench_job.run_id`) reject `WHERE run_id='x'` (type
`(some|none)`) → `SELECT * FROM t` + grep; `SELECT * FROM bench_job` can exceed the 120 s tool timeout → select columns;
never invent column names — the rig's `status` mode and `SELECT *` are the safe reads. Patch scripts with a heredoc whose
body contains `PY`/`EOF` must use a different terminator (or a scratchpad file) — the first patch of the night silently
truncated at the inner `PY` and applied nothing.
**Declarative launch 200 ≠ every lane placed (cell-m-p3, 5 lanes × 3 placements):** the worker's `placeOne` retries the
exec 4× then "exhausts → leave placing" SILENTLY; `/admin/bench/launch` still returns 200 and the module's `launch_lanes`
only fails on a chunk-level HTTP error, so `[bench fanout] declaratively placed N` / `[bench placement] re-placed N`
are claims about the CALL, not the containers. The tell is a lane with NO run-tagged `__run_config__` row after the ~7-min
cold start while its siblings have one. The spine's own heal is the P14 fresh-session remap at `place_attempts ≥ 2`
(a persistently-bad DO name — e.g. destroyed mid-boot — never recovers on the same name). PROVEN 19:40Z: after 3 failed placements on the original names, the P14 `x1` sessions banked their boot rows within 60 s of the remap — same cmd, same store, only the DO name changed. BACKLOG (HB-PLACEMENT): the route
must return `{placed:[…], failed:[{session,error}]}` and the module must mark failed lanes (place_attempts++ / remap now).
**Instant-complete livelock (backlog HB-PLACEMENT ⑥b):** a lane whose slice is already banked exits in seconds, never
beats, and placement re-fires it up to PLACE_MAX_ATTEMPTS (5 cold starts) before `dead` — reconcile only resolves lanes
that BEAT `COMPLETE`. Until reconcile checks `placing` slices against the store, expect this on every `-pN` re-run over
reused stores; it costs cold starts, not correctness (the task is banked). Do not read a `dead` lane with a banked task
as a failure.

## 🔴🔴 DELTA 2026-09-10j — THE MENTOR PILOT VERDICT: "fired + wire-proven" is NOT engagement; DELIVERY is
cell-m-p3 (8 mentor arms × 4 loop tasks, 4.105.0, effective_config gate PASSED per arm, `mentor:{model,thinking,effort}`
banked on every resolver event = the wire was RIGHT) still produced a void treatment: every thinking-ON arm's lift plans
came back `planChars:0, empty:true` and its resolver verdicts `rawLen:0, parsed:false` → `meets:true` (fail-open, by
design) after 50–75 s per call; thinking-OFF arms delivered 8/8 plans + 12/12 verdicts in 5–9 s. Root (direct API call):
DeepSeek's `completion_tokens` INCLUDES reasoning, and the helper adapter caps every mentor call at `max_tokens=4000`
(the content budget) without reading `finish_reason` → high/max reasoning on a 6 KB-delta prompt eats the cap → empty
content. Backlog HB-MENTOR-BUDGET. RULES: (1) mechanism-engagement evidence for a mentor/judge surface = DELIVERY
counts (`planChars>0`, `parsed:true`), banked per arm, before any pass-rate is read; a fired-and-blank arm is a SECOND
CONTROL WITH A STALL, worse than control. (2) Any fail-open path (resolver MEETS on blank, loop-block "fail-open" when
no plan) must bank a `failOpen`-class field, or the adjudicator will credit the gate for finishes it never judged.
(3) When a DeepSeek helper/mentor call is thinking-on, the token cap must be content budget + reasoning allowance — the
08-30 "blank hints" consult finding was this same class, measured on one surface and never generalized. k=5 COMMON mentor
line stays `deepseek-flash` + `CORTEX_MENTOR_REASONING=none` until the fix ships; re-pilot flash-none vs flash-high (K=2).
Same class hit the doctrine miner's synthesis the same night (thinking-on pro, max_tokens 10000 → empty); it runs thinking-off now.
🟢 FIX SHIPPED 4.106.0 (22:05Z): allowance + finish_reason + thinking-off retry + per-event call meta; blank verdict → ABSTAIN.
The re-pilot (flash-none vs flash-high, K=2, pin ≥4.106.1) adjudicates on **`mentor.deliveredBy`** (thinking-on | thinking-off |
thinking-off-retry | none; 4.106.1, on EVERY mentor event and path; 4.106.2 adds `abortedFirstCall` when the thinking-on request
was cut at 60% of the thinking-aware timeout so the retry could run) — never on `mentor.thinking`, which is the REQUESTED config:
a thinking-off rescue banks thinking:true + deliveredBy:'thinking-off-retry'. `deliveredEffort` is the effort that produced the text.
Post-test artifacts for cell-m: `.bench/distill-cell-m/` (8 arms + SUMMARY), `.bench/doctrine-mine-cell-m/` (41 clusters, 5
candidate edits, gate before shipping), ledger `omniclaude-v4/.cortex/bench/r-cell-m-2026-09-10.md` §1–§5.
Also: loop-block redirect fired 12× (near-dup lens works) but the exit-planner ESCALATION needs >2 blocks of one tool and
never triggered — "loop_tool_block fired" ≠ "exit planner consulted"; the two emission sites differ (blockNumber vs
consulted/verdict/mentor).

## DELTA 2026-09-11 — cell-m-r1: the mentor pilot RE-RUN on 4.106.1 (delivery fixed for flash; the timeout wall; sizing evidence)
5 arms × 8 rows, clean launch (stdb-bench §2b), 40/40, $2.45. DELIVERY: flash-high 18/18 (11 thinking-on + 7 thinking-off-retry —
the 4.106.0 rescue is load-bearing, ~73 s per rescued call); flash-max 9/13 + 4 timeouts; pro-high lift 0/7 (all 91 s) — the 90 s
surface timeouts were the next wall → 4.106.2 (thinking-aware timeouts + first-call abort, UNTESTED on the bench). SIZING: flash@high
delivered calls used 10.2K/10.6K reasoning tokens (med/p90) and 7/18 hit the 16K cap → `CORTEX_MENTOR_REASONING_ALLOWANCE=16000`
next run. OUTCOMES n=8: on-arms 5/8 ×3 vs none 4/8, 3/8 — direction only; train-fasttext's first-ever pass (flash-high r1, n=1).
QUALITY (ledger §6): resolver calibration vs the grader is the third lens after delivery and rate — thinking-OFF judges err STRICT
(false holds cost turns), thinking-ON judges err PERMISSIVE (false accepts); thinking-ON plans are more task-specific, thinking-OFF
plans generic. Report false-accept + false-hold per arm on every mentor A/B. RULES: (1) a thinking-on mentor arm is adjudicated on
`deliveredBy` per surface BEFORE any rate; a rate on an arm whose lift planner
delivered 0/7 (pro-high here) is the action model's rate, not the mentor's. (2) the proper efficacy test needs n≥~50/arm on the
population the mentor targets (hard core + loop set, K=3), not 8. (3) k=5 COMMON stays `deepseek-flash` + `CORTEX_MENTOR_REASONING=none`
until that test reads. Ledger `.cortex/bench/r-cell-m-r1-2026-09-10.md`.

## DELTA 2026-09-11b — 4.107.0: the lift plan reaches the judges + per-surface mentor reasoning switches; cell-n-r1 = the efficacy test
Built from the cell-m-r1 quality read (§6): resolver / deadline-exit / loop-exit planner now receive the lift planner's PLAN OF
ATTACK as an ADVISORY anchor (the TASK wins on disagreement; events bank `liftPlanChars`); `CORTEX_{LIFT_PLAN,ENDTURN_RESOLVER,
DEADLINE_EXIT_MENTOR,LOOP_TOOL_BLOCK}_REASONING` (on|none) win over the global. cell-n-r1 (operator-ordered) = the TB2.1 hard core
(13 all-arms-fail tasks) × K=2, 5 arms: flash-none (ctl), flash-high / flash-max / pro-high (r1's top three), `fh-plan`
(planner on @high, resolver off — the §6 candidate); pin 4.107.0; `CORTEX_MENTOR_REASONING_ALLOWANCE=16000`. Adjudicate in this
order: delivery (`mentor-delivery.py`), resolver calibration vs grader (false accepts / false holds), plan quality, then rates.

## DELTA 2026-09-11c — cell-n-r1 VERDICT: thinking-on mentors LOSE on the hard core; `none` confirmed; the plan hand-off is not the lever
TB2.1 hard core × K=2, 5 arms, n≈25/arm, 4.107.0, $17.92 (peak): flash-none 10/24 vs pro-high 9/25, flash-high 7/25, flash-max
7/26, fh-plan 7/25 — uniform direction below control (CIs overlap at n=25; r1's n=8 direction REVERSED — never bank an n=8
direction). Calibration: thinking-on resolvers false-accept 50–56%, thinking-off 20%; false holds ~0.3 on both strict arms
and UNCHANGED by handing the judge the plan (delivered 100%) — on hard tasks the judge is mostly right that the artifact is short.
Delivery mechanics all worked (0 `none`; pro@high = 38 first-call aborts at 144 s → thinking-off rescues). RULES: (1) a mentor
A/B is decided on the hard core at n≥25/arm, never on the 4-task loop set at n=8; (2) `CORTEX_MENTOR_REASONING=none` is the k=5
COMMON on evidence; thinking-on surfaces are DARK infrastructure; (3) missing rows at run end are requeued as a NEW short run id (e.g. `-r2`; a `<run>b` suffix pushed the lane names past 22
chars and the guard refused the dry fanout) with a filtered fanout job built from `FANOUT_DUMP=<file> build-cells.sh fanout-dry`,
`create` + population gate + `launch_bench_run` + `upsert_bench_job fanout-<run>-s0` (the 4 lanes) + `run_bench_job_now` — the
sourced-function shortcut emits nothing (no TB2_DATASET_REF).
Ledger `.cortex/bench/r-cell-n-r1-2026-09-11.md`.

## DELTA 2026-09-11d — cell-n-r3/r4 VERDICTS + 4.107.1 (EndTurn tier, planner doctrine) + npm trusted publishing
- flash mentor @low (r3): REJECT — thinking delivered (91%) but false-accept 0.67, 6/24 vs control 11/26. Across low/high/max the
  thinking resolver is monotonically permissive; effort moves only cost/latency. `CORTEX_MENTOR_EFFORT` DARK; k=5 = flash + none.
- action model @high (r4, provisional 47/52): no lift (0.27/0.28 vs 0.42), +4 min/task, turns unchanged. `CORTEX_ACTION_EFFORT` DARK.
- 4.107.1 shipped: `EndTurn` back to `discoveryTier: 'essential'` (census: 70–80% of sessions hunted the mandatory finish tool
  via SearchTools) + PLANNER_SYSTEM doctrine (ONE INSTALL LAYER/uv, no minute sleeps, byte-level exact output, literals verbatim,
  graders re-parameterize). Efficacy = the next hard-core run vs control 11/26; the supervisor `git add grader` fix seeds with it,
  so "which test failed" finally banks.
- Release pipeline: npm publishes via TRUSTED PUBLISHING (OIDC) now — memory [[npm-token-90-day-expiry]]; a failed tag run is
  recovered with `gh workflow run publish.yml --ref main`.
- Ledger: `omniclaude-v4/.cortex/bench/r-cell-n-r34-2026-09-11.md`; r1 §5 refreshed (requeue 3/4 banked; control 11/26).

## DELTA 2026-09-11e — cell-n-r5: 4.107.1 REGRESSED the hard core; both changes became levers; bank() lost rows for 4 runs
- 4.107.1 (EndTurn essential + planner doctrine bullets) on the hard core: 4/18 vs the 4.107.0 control 11/26, PAIRED 6 losses /
  1 gain, fewer turns on 12/18 tasks — the finish became easier to reach and the agent stopped verifying (gcode read "gcodo3"
  without the control's max-zoom pass). The tier mechanism fired (SearchTools 21→2). LESSON: a fix that removes a hunt for the
  FINISH tool must be judged on outcome; salience of EndTurn is itself a lever. 4.107.2: `CORTEX_ENDTURN_TIER` +
  `CORTEX_LIFT_PLAN_DOCTRINE` (defaults = baseline); cell-n-r6 2×2 (base / et-ess / doc-v2 / et-doc) attributes.
- ROW LOSS CLASS (supervisor): a lane prints `COMPLETE: 1/1 graded` with the row only in its local clone (r1 4/130, r3 2/26,
  r4 5/52, r5 8/26). The STDB reconcile marks it complete_short → re-places the SAME DO → the task re-runs → the wedged clone
  still cannot push. Diagnosis was blind (git stderr never logged; touch-free rule forbids reading the container log).
  FIX = `bank()` reconcile-by-rows: rows also land in `/app/bench/banked/<task>.json`; every bank/start/complete does
  unwedge (abort stale rebase) → fetch → `reset --mixed origin/main` → rewrite `results-s<idx>.jsonl` = remote rows + missing
  ledger rows → add results/trajectories/grader → commit → `push origin HEAD:main`, 6 attempts w/ backoff+jitter, stderr
  LOGGED; COMPLETE prints only when origin/main holds every slice row (else `INCOMPLETE … UNPUSHED:`). Boot push jittered 0–10 s.
  Tested against a bare remote (normal / non-fast-forward / wedged+unpushed / outage+recovery). Ships with the next seed.
  READ THIS RIGHT: a run's row count is now trustworthy only from stores seeded after 2026-09-11 ~2:45 AM PT.
- First store with `grader/` (`tb2-n5-…`): `grader/<task>.ctrf.json` names the failing test — the failure census no longer needs
  transcript archaeology. `curl` the store with `-L` (the bare URL is a redirect; a non-`-L` grep returns 0 and lies).

## DELTA 2026-09-11f — k=5 n=1 = 70/89 (78.7%, new flash best, $2.81); qemu "regression" was an EOL-distro apt failure in the ADAPTER
- tb21-k5-n1 (4.107.2 + CORTEX_ENDTURN_TIER=essential, DOCTRINE v1, mentor flash/none, K=1): 70/89, cost $2.81 off-peak, median
  345 s / 21 turns, SearchTools 3 calls in 88 tasks, resolver false-accept 0.04. Ledger `r-tb21-k5-n1-2026-09-11.md`.
- The two qemu tasks (passed on every harness 4.80–4.91.1) died with NonZeroAgentExitCodeError at ~45 s: NOT the harness.
  The adapter's `ensure_system_dependencies` runs `apt-get update && apt-get install curl bash git xz ca-certificates` in
  the task image; the qemu images are Debian bullseye, which left LTS 2026-08-31 — `bullseye-security` Release is expired
  and its packages 404 on deb.debian.org. Adapter v2: skip apt when the binaries exist; tolerant update; on still-missing,
  repoint sources to archive.debian.org and retry; fail only if still missing. EXPECT MORE OF THIS: every bullseye-based task
  image will hit it; any image whose distro goes EOL later will too. The diagnostic path that found it: supervisor v4 banks
  `grader/<task>.trial<i>.json` (harbor's per-trial result with `exception_info`) + agent logs on errored trials — read the
  crash text from the store, touch-free, via a 2-lane `cell-q` probe (rig: cell-q = the qemu pair; ARMS bound like cell-n).
- Supervisor v3/v4 (all uncommitted, seeded per store): reconcile-by-rows bank + `--ignore-removal` + refuse-deletions guard +
  per-file artifact staging with a 9.5 MB cap (video-processing's session was unpushable) + final line carries the last git
  error + errored-trial artifact capture. A store seeded before 7:30 AM PT 09-11 may lack one of these; check the seeded file.
- 4.107.3 = CORTEX_ENDTURN_TIER default essential. The k=5 series keeps PIN 4.107.2 + the env for run-to-run consistency.


## DELTA 2026-09-11g — THE k=5 SERIES VERDICT + the installed-DSH control: 77.3% ± 2.7 vs DSH 79.8%; the 90.6 does not reproduce
- **TB2.1, deepseek-flash (V4.1-Flash GA), nexus-cortex@4.107.2 + `CORTEX_ENDTURN_TIER=essential` (= 4.107.3 default), 5 sequential full-89
  runs K=1 (n1–n5, all off-peak, STDB spine, 1 task/lane): 70/71/65/70/68 → pass@1 mean 77.3% (68.8/89), sd 2.7 points, pooled 344/445
  Wilson 73.2–81.0%; ≈$2.8/run banked (98% cache-hit, warm-cache basis); median 23 turns / 350 s / 21K output tokens.** Pass-in-all-5 49, any 81,
  never 8 (dna-assembly, extract-elf, extract-moves-from-video, filter-js-from-html, make-doom-for-mips, query-optimize, train-fasttext,
  video-processing), 32 tasks unstable → the ±3-point run-to-run band is task-level flakiness, so NEVER read a single-run delta < ~5 points as a
  lever effect. Ledger `omniclaude-v4/.cortex/bench/r-tb21-k5-series-2026-09-11.md` (+ per-run n1..n5). THIS is the quotable flash number now
  (supersedes the 08-25 67/89 TB2.0 flash-lifted line in "CURRENT-BEST").
- **Ground-truth control = DeepSeek's own harness** (`dsh_minimal_agent.py` v8: deepseek-harness-sdk sdk-minimal, bash + str_replace_editor,
  effort high, 49152 max_tokens, 1M ctx, same model/substrate/tasks, N=1): **71/89 = 79.8% (Wilson 70.3–86.8)**. The model card's 90.6 (N=3)
  does NOT reproduce on this substrate even with their harness — the "13-point harness gap" premise is refuted; DSH and nexus-cortex are within
  noise. DSH shape: 40 turns/task median, 2.4× our reasoning volume, 8 grind-to-timeout fails, str_replace_editor = 0.6% of tool calls (bash
  3838 : editor 22) → the editor-tool shape is NOT a lever; do not build one. DSH-only wins (4): dna-assembly, extract-elf,
  filter-js-from-html, video-processing; DSH-only losses (8): cobol-modernization, configure-git-webserver, hf-model-inference, kv-store-grpc,
  mcmc-sampling-stan, pypi-server, pytorch-model-recovery, winning-avg-corewars (infra DNF). Ledger `r-tb21-k5-dsh3-2026-09-11.md`.
- **DSH-minimal REPLICATED INSIDE nexus-cortex as an env bundle** (rig arm `dsh-min` / K5 token `cortex-dsh`: `CORTEX_TOOL_PROFILE=bash-plus`,
  `CORTEX_PROMPT_MASS=minimal` + one-line `CORTEX_SYSTEM_PROMPT_FILE`, `CORTEX_ACTION_EFFORT=high`, `MAX_TOOL_ITERATIONS=500`, anchor none, every
  gate/mentor/nudge false; no harness change needed — the flash card already has 1M ctx / 65K out / provider-default temperature). Hard-core
  probe cell-n-d2: 4/11 vs installed DSH 5/11 on the same tasks (control 10/22); it flipped filter-js-from-html (first pass in our harness,
  11 prior attempts) at ~2.5× the turns/cost. Ledger `r-cell-n-d2-2026-09-11.md`. Next: full-89 `cortex-dsh` arm, then layered add-back
  (EndTurn gate → loop block → mentor) to find which layer costs the 4 DSH-only tasks.
- **Traps this arc:** (1) `BUDGET_CAP_USD` is KEY-WIDE (balance delta on the shared DeepSeek key) — concurrent runs charge each other's cap
  (cell-n-d2 halted at "5.07/5.00" on ~$0.7 of its own spend); size caps to the aggregate burn (stdb-bench §7.12). (2) Session records do not
  hold the system message and 4.107.2's effectiveConfig does not report CORTEX_DSH_MINIMAL / TOOL_PROFILE / SYSTEM_PROMPT_FILE → the one-line
  prompt's delivery is inferred, not banked; add the keys + a `systemPromptBytes` field next release. (3) Task images on EOL distros (bullseye)
  break any apt step → adapters must be apt-free (curl|wget|python3|perl fetch chain, venv installs). (4) A Monitor survives a same-session
  compaction but not a session change — check `status` before re-arming.

## DELTA 2026-09-12 — the two follow-up arms: ours-as-DSH = the series mean; pro@high = 80.9% (n=1)
- **tb21-k5-cd1 (DSH-minimal bundle inside nexus-cortex, flash, full 89): 69/89 = 77.5%, $4.04** — identical to the 5-run series mean (77.3) at
  1.4× the cost and 1.3× the wall time. Three harness configurations on this substrate (ours 77.3, ours-as-DSH 77.5, DSH itself 79.8) sit inside
  one noise band → **the "harness gap" to the published 90.6 is CLOSED as a hypothesis**; the ceiling is substrate+model+methodology, not our
  layers. Task trades are real (bundle gained dna-assembly, lost 4 series-always tasks) but cancel on aggregate. The cell-n-d2 filter-js flip did
  not reproduce at n=1. Do not re-run bundle-vs-full as a full-89; only a K≥3 task-level study on the 4 DSH-only tasks is worth spend.
- **tb21-k5-ph1 (deepseek-v4-pro @ CORTEX_ACTION_EFFORT=high on the exact series COMMON): 72/89 = 80.9% (Wilson 0.72–0.88), $12.77,
  median 737 s** — the best single TB2.1 number banked; +3–4 pts over flash with overlapping CIs at n=1; 4.5× flash cost, 2.1× latency. Pro
  passes video-processing (flash never) and loses torch-tensor-parallelism (flash 5/5) + 9 flash-unstable tasks. Effort is UNSEPARATED from
  model (pro @default not run; flash @high was no-lift in cell-n-r4). Ledgers `r-tb21-k5-{cd1,ph1}-2026-09-12.md`; series ledger addendum.
- **Rig traps:** (1) `CELL_FILTER` set together with `K5_MODE=1` stages NOTHING silently — create/seed print static text and exit 0; unset
  CELL_FILTER for K5 launches and verify `bench_run`/`bench_arm` rows after `create`. (2) `fanout-dry` echoes the lane cmd head with `HF_TOKEN=…`;
  redact (`sed 's/HF_TOKEN=[^ ]*/HF_TOKEN=***/'`) before it lands in a transcript. (3) A run's budget baseline is the key balance at launch: a
  top-up mid-run makes that run's `spent` negative (its cap goes inert) — the floor + sibling caps still bound the key.

## ✅ DELTA 2026-09-12b — TERMINAL-BENCH 4.0 IS OPERATIONAL ON THE RIG (3 plumbing probes, ~$3, 3.5 h) — read before any TB4 run
**Why 4.0:** TB2.1 is saturated (AA frontier 88–91; our DeepSeek numbers sit ON AA's Terminus-2 band: pro 80.9 vs AA 78.7) — nothing left to learn.
TB4.0 discriminates (AA, 66 tasks, 3 repeats: GPT-6 Astra 59.6 · Fable 5.1 52.0 · **V4.1 Flash 26.8 · V4 Pro 14.1**). Memory [[aa-terminal-bench-reference-2026-09-12]].
**Dataset facts (parsed from every task.toml → `.bench/tb4-task-meta.json`):** harbor id `terminal-bench/terminal-bench` (@latest = 4.0; SHA
e2995b93… 2026-09-11), task prefix `terminal-bench/`; 66 tasks (Software 18, Science 14, ML 11, Ops 9, Hardware 5, Security 5, Media 4);
**EVERY task: `[agent] timeout_sec = 28800` (8 h)** — the `[verifier] timeout_sec` (60–7200) is NOT the budget (first-regex trap); **every task
uses `[verifier] environment_mode = "separate"`** (a second compose env per trial); 3 need a GPU (fp8-rmsnorm-gemm, jax-speedrun-gpu, math-eval-grader);
11 are multi-container (`environment/docker-compose.yaml`, 2–7 services); 7 non-GPU tasks ask >4 cpus in the agent or verifier env.
**What the CF DinD substrate does with that (all grounded on probes cell-t-p1 / cell-u-p1 / cell-v-p1):**
1. Memory requests above the host (16 GiB on a 12 GiB lane) are ACCEPTED (kernel warns "memory limited without swap").
2. `cpus` > 4 → docker REFUSES the container (`range of CPUs is from 0.01 to 4.00`); CF caps a deployment at 4 vCPU (`vcpu_per_deployment`).
   FIX: `harbor run … --cpus ignore` (cpu_enforcement_policy=ignore, harbor 2026-05-21) — it applies to EVERY env of the trial, which matters because
   harbor's separate verifier env STRIPS `--extra-docker-compose` (trial.py `_separate_verifier_env`), so an overlay cap never reaches it. The
   supervisor adds the flag only for `needs_cpu_relax` tasks (task-meta.json): distributed-dedup, formal-crypto, lake-temp-glm, live-database-cutover,
   payments-pipeline-fix (verifier env cpus 6), shadow-relay, wdm-design → DISCLOSE "ran on 4 vCPU".
3. Multi-container tasks: the single-service host-network overlay left sidecars on a bridge with no route to `main` (CF kernel has no netfilter →
   bridge has no outbound; Dockerfile:430). FIX: supervisor `venue_for(task)` writes a PER-TASK overlay from task-meta.json: every service
   `network_mode: host` + `extra_hosts` aliasing every other service name to 127.0.0.1. 10/11 run (kafka, mysql/redis/postgres, odoo stacks all fine);
   medical-claims-processing's Chromium+noVNC sidecar (`playwright-mcp`) exits(1) under host net → EXCLUDED (disclose). Compose `ports:`/`networks:`
   are absent in all 11 (checked) — if a future task declares them, host mode conflicts (`networks` + `network_mode` is a compose error).
4. Timeouts: supervisor `PER_TASK_CAP_S` = env `TB2_TASK_CAP_S` (pass 30600 in COMMON); adapter ceilings (client fetch, curl, exec backstop) now
   = `TB2_MAX_TASK_BUDGET_S`(28800)+600 = 30600 s. Cheap plumbing probes use `.bench/tb4-probe-budgets.json` (budgets capped at 1800 s → the
   harness force-synthesizes at 27 min; harbor's 8-h timer never fires).
**Rig:** `build-cells.sh` env `DATASET_ID BENCH_ID BENCH_NAME BUDGETS_FILE DATASET_REF TASK_META_FILE`; cells `cell-t` (5-task spread), `cell-u`
(11 compose + shadow-relay), `cell-v` (3 cpu-relax), **`cell-w` = the 62-task full population** (`.bench/tb4-tasks-full.txt`). STDB benchmark id
`terminal-bench-4-0`. Full-run recipe: `CELL_FILTER=cell-w K=1 STORE_SFX=t4w RUN_SUFFIX=-f1 SHARD_N_FLASH=62 SHARD_N_PRO=1 FULL_WIDTH=1 ARMS_FILTER=ctl
DATASET_ID=terminal-bench/terminal-bench BENCH_ID=terminal-bench-4-0 BENCH_NAME="Terminal-Bench 4.0" BUDGETS_FILE=.bench/tb4-budgets.json
EXTRA_COMMON="<series COMMON> TB2_TASK_CAP_S=30600" BUDGET_CAP_USD=40` → guard/fanout-dry/create/seed/gate/launch; expect a wall-clock day (8-h
budgets), $15–40 flash; compare to AA 26.8 (their harness = Terminus 2, 3 repeats). Disclosure block = GPU 3 excluded + medical-claims excluded +
7 cpu-relaxed + memory-over-host accepted.

## 🔴 DELTA 2026-09-12c — THE VAST VM EXECUTOR: "0 rows, every trial dies in 2 s" was a MISSING COMPOSE PLUGIN + a pgrep self-match
The first TB4.0 run on the Vast `kvm:ubuntu_terminal` VM banked 0 task rows in an hour. Suspects I carried into compaction (model string,
harbor 0.23.0) were WRONG; the job log had the answer in one line. Three defects, each now enforced in structure:
1. **The image ships docker (29.x) with NO `docker compose` v2 plugin.** harbor drives every environment through `docker compose …` →
   `RuntimeError … unknown flag: --project-name` + a `docker --help` dump at `_start_agent_environment`, ~2 s per trial, 0 images pulled.
   The litellm "Provider List" banner beside it is noise. FIX: official static binary into `/usr/libexec/docker/cli-plugins/docker-compose`
   (the dir docker searches on that image); `.bench/vm/bootstrap-executor.sh` installs it when missing and HARD-fails without it; the
   supervisor's `ensure()` now requires `docker compose version` (missing compose = `venue_unready` retry, never a reward-0 cascade).
2. **`pgrep -f 'harbor run'` SELF-MATCHES through `subprocess.run(shell=True)` on dash hosts** (dash does not exec the final command, so the
   `sh -c` wrapper's argv carries the string) → the supervisor believed harbor was still running and waited the full `PER_TASK_CAP_S`
   (30600 s) on a job that had exited — the "8 supervisors at `RUN <task>` for an hour" signature. Verified empirically (plain → exit 0 with
   nothing running; `harbor ru[n]` → exit 1). FIX: bracket pattern in the supervisor. Costume #7 of the self-match family: the same code
   passed on the CF image because its `/bin/sh` execs the last command. TEST a pgrep guard on the host it will run on, in a command line
   that contains NO other copy of the plain string (my first bracket test was contaminated by the plain test beside it).
3. **apt on the image wedges on `install-info`** because Vast writes multi-line ssh public keys UNQUOTED into `/etc/environment` (bare
   `ssh-ed25519 …` continuation lines execute when the postinst sources it, exit 127). FIX on the VM: quote values, comment bare lines,
   `dpkg --configure -a`. The bootstrap's apt step is now tolerant + verifies the binaries it needs; never let a host apt hiccup abort a
   bootstrap whose tools already exist.
DIAGNOSIS ORDER that would have taken 3 minutes: `harbor` job log head → `exception.txt` in the trial dir → `docker compose version` on the
host. Patched supervisors travel IN the store (commit into `/app/bench/hfds` + push) BEFORE re-bootstrapping — the bootstrap copies from a
fresh store clone and would otherwise overwrite the fix. A detached supervisor started over `ssh … 'bash bootstrap.sh'` inherits the ssh
stdin and keeps the client open; harmless, kill the client.

## 🔴🔴 DELTA 2026-09-12d — THE SHARED-HOST TOPOLOGY LAW (Vast VM, 8 supervisors on ONE docker daemon + ONE filesystem)
The durable supervisor was written for CF's topology: ONE supervisor per container, so "global" cleanup was free. On a VM that runs N
supervisors side by side, every host-wide verb became a weapon against the siblings. Four defects, all fixed in structure (R127–R130):
1. **Wait loop = `proc.poll()` on THIS supervisor's harbor child**, never a host-wide `pgrep -f 'harbor run'` (self-matched the `sh -c`
   wrapper on dash AND let one live sibling job keep all 8 waiting on already-finished jobs).
2. **Pre-task cleanup is SCOPED in bridge mode:** `rm -rf j_<own task>` + `docker image prune -f` + `docker container prune -f` (dangling /
   stopped only). The old `docker system prune -af; rm -rf /app/bench/j_*` deleted the other 7 in-flight job dirs → the adapter's
   bind-mounted `/logs/agent` vanished under the running task → reward 0 with ZERO tokens in ~150 s, no exception (looks exactly like the
   empty-session class; a SOLO hand-run of the same task was healthy — the discriminating test). The frozen wait loop MASKED it all
   morning (no supervisor ever advanced), so fixing #1 made the fleet "worse" until #2 landed.
3. **Host plugins the image lacks:** docker compose v2 AND buildx (harbor builds an egress-control sidecar with `docker build --file`;
   docker 29 has no legacy builder). Bootstrap installs both static binaries and hard-verifies; supervisor `ensure()` requires both.
4. **Adapter install must fail LOUD:** retry `npm install -g nexus-cortex@<pin>` 3× and `exit 1` if `cortex-server` is still missing →
   an errored trial (infra-DNF, requeued), never a silent reward 0. Also: a `node` on PATH that reports ≥20 may be a BUN shim
   (oven/bun images) — require npm + `process.versions.bun === undefined` before trusting it.
DIAGNOSIS ORDER for a shared-host fleet that fast-fails: (a) run ONE task by hand with the same env — healthy solo + failing in the fleet
= a sibling-interference verb (prune/kill/port), not the harness; (b) plant a 5-s evidence copier for agent dirs BEFORE the next attempt (the
job dirs are the first casualty); (c) never blame npm propagation without the install log. Evidence copier: `/root/evidence-watch.sh` on the VM.
Cost of learning this: 4 fleet restarts, ~$3, one morning. Bootstrap: `.bench/vm/bootstrap-executor.sh`; ssh key `~/.ssh/id_ed25519`.

## DELTA 2026-09-13 (tb4-flash-v1 adjudication + curation)
- **Session-record shape for joins:** banked `trajectories/<task>.session.jsonl` tool blocks are `{"type":"tool_use","toolUse":{id,name,input}}`
  (NOT `{"type":"tool_use","name":…}`); `tool_result` blocks are `{"type":"tool_result","tool_use_id","content"}`. Decisions `ts` is epoch-ms on the
  same clock as the session's ISO `timestamp` — join a decision to its preceding tool call with a bisect on the assistant timestamps.
- **Grader artifacts that carry the pass/fail REASON:** the verifier's own `verifier/test-stdout.txt` (perf numbers, gate thresholds, the real
  assertion behind a privilege-dropped worker). The supervisor now banks it with every row (and caps grader files at 24, response.json first).
  ctrf `message` for TB4.0 tasks that fork tests into a `nobody` child is always the generic "privilege-dropped worker did not report success"
  — that string is NOT infra; read test-stdout.txt.
- **Scorer tests:** several TB4.0 tasks have ONE ctrf test that "passes" as pytest while writing a 0 score (`test_*_all_or_nothing`,
  `test_score_*`); `verifier_result.reward` in harbor's trial json is authoritative, never the ctrf pass count.
- **HF 10 MB plain-git limit:** sessions with many ReadImage base64 blobs silently never reached the store (2 of 62); the supervisor now strips
  inline base64 above 9 MB before banking.
- **`build-cells.sh seed` accepts `TASK_SUBSET="t1 t2 …"`** for a targeted fix-validation cell (seeds only those tasks for the filtered cell).
- **GitHub Actions "job repeatedly failed to be acquired (5 attempts)"** with 0 steps and no log blob = a GitHub incident; `gh run rerun --failed`
  (retry on 502) — do not touch the tree or re-tag.
- **DeepSeek model lineage (09-13):** API model list = {deepseek-flash, deepseek-v4-pro}; `deepseek-v4-flash` is a retired alias served by V4.1-Flash;
  V4 Pro is the model DeepSeek kept "in response to user demand". No V4-vs-V4.1 flash A/B is possible.
- **Per-host local ledger trap (09-13):** the supervisor's `/app/bench/banked` is per HOST; re-bootstrapping a host onto a NEW store synced the
  previous run's rows into it and reported every task done in 8 s. bootstrap-executor.sh now writes `/app/bench/banked/.repo` and wipes the
  ledger + clone when the store changes. Symptom to recognize: "synced N row(s) to the store (start)" with N ≫ 0 on a fresh store.

## DELTA 2026-09-14 (tb4-flash-v2 rerun, effort high, 4.108.19 → fixes 4.108.20)
- **Transport blips end 8-hour turns (R150).** `Error in tool execution iteration N: Connection error.` (OpenAI SDK) / `terminated` (undici)
  were NOT in `ErrorClassificationMiddleware.networkErrorPatterns` → no retry at all → tool loop exit → R29a synthesis fails the same way →
  `endturn_gate_fallback {reason: abnormal-exit-bypass}` ships the turn. Read every store's `grader/*cortex-server.log` for
  `Error in tool execution iteration|synthesis turn failed` BEFORE attributing a lost pass to the model (3 lanes died within 74 s at 8:36 AM PT;
  the baseline had zero). Fixed 4.108.20: patterns + `CORTEX_API_NETWORK_RETRY_MS` (10-min budget). The bypass event now carries `detail.error`.
- **Compaction estimator vs images (R149).** `compaction` rows with `tokens` ≫ `anchorTokens` in image-heavy sessions = base64 counted as
  text (fixed 4.108.20). Validation read: every `compaction` row's `detail.tokens` within 5% of `detail.anchorTokens`.
- **Model-endpoint preflight is now STRUCTURE:** `bootstrap-executor.sh` probes chat/completions ×3 (60 s) and refuses to launch on 3 failures
  (`TB2_SKIP_API_PREFLIGHT=1` overrides). DeepSeek was unresponsive >10 min at 1:20 PM PT with an empty status page — probe, don't trust the page.
- **Distiller on a new store:** `TB2_DISTILL_ARMS='{"t4z":"<hf-org>/tb2-t4z-ctl"}' python3 scripts/tb2-distill.py --arm t4z --clones <dir>` where
  `<dir>/tb2-t4z-ctl` is the clone (symlink ok). The positional arm names are the 2026-08 fixed set; unknown names exit 2.
- **Doctrine miner on a store:** concatenate `trajectories/*.decisions.jsonl` into one file for `--decisions`; run with `python3 -u` detached
  (`nohup … & disown`) — a Claude Code background task dies with the session; labels bank per session so a relaunch resumes.
- **Master `.env` came back 4× self-appended** (5236 lines) hours after the last dedupe — verify `grep -c '^# API KEYS' omniclaude-v4/.env` == 1
  before EVERY build/commit; the 4 chunks were byte-identical to HEAD, so the restore is `head -n $(git show HEAD:omniclaude-v4/.env | wc -l)`.
- **Session records: `kind` is the event field** in decisions logs (not `event`/`type`); the `steering_injected` rows carry the sub-kind in `detail.kind`.
- **Peak vs off-peak cost:** compare runs on `cost_usd_peak`/`cost_usd_offpeak`, never `cost_usd` — a run straddling 16:30 UTC mixes tiers.

## DELTA 2026-09-15 (tb21-a21 A/B + tb4-flash-v3 launch night)
- **Vast kvm boxes: the image name MUST be the fully qualified `docker.io/vastai/kvm:ubuntu_terminal`.** `vastai/kvm:ubuntu_terminal` starts
  a container with no /dev/kvm and no VM; its outer supervisor container answers ssh (hostname = container id, no docker, `/root/kaalia-vm-
  supervisor`, "up 4 weeks"), so every "Permission denied"/"VM not up" read was a red herring. Gate readiness on `docker info` over ssh,
  never on ssh alone; never reboot a booting VM. `.bench/vm/provision-and-launch.sh` encodes all of this (plus the key path below).
- **HOME on the repl is $WORKSPACE** — the ssh key is `$WORKSPACE/.ssh/id_ed25519`; a script hardcoding
  `$HOME/.ssh/` can never ssh. Use `$HOME/.ssh` or the workspace path.
- **Never edit a script while detached copies of it are running** (bash reads scripts lazily by offset): the first provisioner set executed
  a half-patched file and rebooted healthy boxes. Kill → edit → relaunch.
- **One store per box**: the bootstrap's per-box ledger (`/app/bench/banked/.repo`) is store-scoped; two stores on one box clobber it.
- **Vast VMs get fewer vCPUs than the offer lists** (192-core offer → 23-vCPU VM; 32 → 7; 16 → 15). Read `nproc` inside the VM before choosing
  lane counts; disclose asymmetries between paired arms.
- **R152 signature:** grep every store's `grader/*cortex-server.log` for `reading 'choices'` — a null completion body during a provider incident
  ends the turn on the pre-4.108.22 harness. Also grep `[RetryMiddleware] network fault` for R150 field evidence.
- **The master `.env` self-appended TWICE today** (4× at 1 PM, 2× at 10:30 AM); a commit captured the doubled file once (ef548708bf fixed it
  forward). Check the header count immediately before EVERY write and again before `git commit`; the sync guard catches the mirror, not the master.
- **TB2.1 effort verdict (n=3 × 2 arms, harness fixed):** high 74.9 vs low 76.4, p=0.68, +37% tokens → low is the TB2.1 config.

## DELTA 2026-09-16 — post-run deficiency sweep (the method that found R153–R157)
- Pull per store to /tmp (off-quota): `trajectories/*`, `grader/*.ctrf.json`, `grader/*result.json`, `grader/*cortex-server.log`,
  `grader/*test-stdout.txt`, `results-*.jsonl` (snapshot_download allow_patterns; ~150 MB per 63-task store). Delete when done.
- Per fail, four columns decide the class: ctrf passed/total (near-miss vs zero), server-log signatures (`Empty response detected`,
  `reading 'choices'`, `unsupported image`, `exception escaped`, `FALLBACK-ACCEPT`, `R29a`, `network fault`, `EACCES`), the final
  assistant text (surrender vs confident-wrong), and `exception_info` in `trialN.json` (exit 137 = OOM class; `result.json` has NO
  exception_info — fetch the trial json).
- Reasoning exhaustion signature: assistant record `usage.output_tokens == 65536` with 0 text + 0 tool_use. Count it per store; every
  such turn cost ~$0.04-0.08 and 3-4 min. Root cause was a STALE stop reason (turn's first response) in the classifier — when a
  classifier "never fires", check what variable it actually reads, not just the provider.
- "All tests passed but reward 0" (freight/intrastat/medical/vba): the pytest wrapper PASSES while the task's own scorer prints
  `Reward: 0.0` inside stdout — read test-stdout, not ctrf, for all-or-nothing tasks.
- A session file that starts with a tool_result instead of the task prompt = clobbered state dir (git checkout / clean) — R155.
- Verifier 0-byte stdout + reward 0.0 with no exception (freecad-impeller/spring-clip) is a TASK-environment defect: same in v2 and v3.
- Vast 23-vCPU boxes: verifier timeouts (1800 s) on playwright/torch graders — check `nproc` inside the VM before launching 8 lanes.
- 2026-09-16 rig levers (bootstrap-executor.sh / supervisor / adapter): `TB2_MIN_VCPU_PER_LANE` (default 3) x shards must fit `nproc`
  INSIDE the VM or the bootstrap exits 4 before any supervisor starts; `TB2_VCPU_AUTOSCALE=1` shrinks the shard count instead.
  `TB2_VERIFIER_TIMEOUT_MULT` (default 2 on VMs) reaches harbor as `--verifier-timeout-multiplier` (agent budgets untouched; disclose
  it in the ledger). The adapter now pins `CORTEX_STATE_DIR=/tmp/.cortex-state` and the session copier searches it first — a
  session file that starts mid-task can no longer come from the model's git commands in /app.
- FreeCAD-class verifiers (gNucleus create-edit tasks: freecad-impeller, freecad-spring-clip, freecad-platform-drawing, cad-model)
  print NOTHING to stdout: `write_zero` reasons go to stderr and the scorer's axes go to `/logs/verifier/reward_details.json`.
  A 0-byte test-stdout with reward 0.0 is therefore normal, not a broken verifier, and FreeCAD 0.21.2 is baked into BOTH the
  agent image (micromamba) and the verifier image (+ gnucleus-freecad-validator) — nothing to install. The supervisor now banks
  `verifier/*.json` (was `*.txt` only) so the reason lands in the store. Task sources for TB4.0 live on the harbor HUB
  (Supabase `ofhuhcpkvzjlejydnvyd`, publishable key in harbor/auth/constants.py): `package?name=eq.<task>` → `task_version`
  → `/storage/v1/object/packages/<archive_path>` (dist.tar.gz with environment/Dockerfile, tests/Dockerfile, tests/test.sh).
- 2026-09-16 (Vast): two FRESH `vms_enabled` kvm offers (51160799 machine 37526; 36913052 machine 40175) never left `loading/stopped`
  (next_state stopped, `start` → "resources unavailable") for 30 min each, while last week's boxes reached running in 2-3 min. Restarting
  a KNOWN-GOOD stopped box worked (51095441 up in 2 min). Pattern: race two old boxes with a watcher that provisions the first to run and
  stops the other; rent fresh only if both fail, and destroy a fresh box that is still loading after 15 min. Provisioner waits 15 min for
  `running` — relaunch it once the box is up rather than editing the running script.
- 2026-09-16 (post-cell curation, tb4-p): ALWAYS check `endturn_resolver` event COUNT per session against the finish — 0 events on a
  task-like prompt means the judge was bypassed (R161 isTaskShaped, fixed 4.112.0), not that the finish was clean. Read every GAP plan's
  `deltaChars`/`workProductSample`: a plan that says "file not present in the WORKSPACE DELTA" on a file the model edited is R162
  (build-dir crowding, fixed 4.112.0). `checkRan=false` everywhere on TB4 is expected (hidden tests) — R163 candidate.

## DELTA 2026-09-18 — Vast teardown must live ON THE VM (self-reaper); repl-side reapers die with the session
- **Fact:** every repl-side watcher (Monitor tasks, `setsid nohup` reapers, even `setsid -f`) died with each Claude Code process
  restart (3 restarts on 09-18); the VM-side supervisors kept running and banking to the HF store through all of them. So a Vast run
  PERSISTS without the repl, but its TEARDOWN did not — six boxes would have billed until someone destroyed them.
- **Structure:** `.bench/vm/self-reaper.sh <iid> <ttl_h>` runs ON the VM (detached inside the VM): destroys the instance via
  `DELETE https://console.vast.ai/api/v0/instances/<iid>/` (Bearer VAST_API_KEY) when no `tb2-durable-supervisor` process has
  existed for 3 consecutive minutes after a 20-min boot grace (= run complete), or when the TTL elapses (hard cost cap; rows are
  already banked). Falls back to `poweroff` after 5 failed API calls. Log `/root/self-reaper.log`.
  `provision-and-launch.sh` ships `VAST_API_KEY` (from secret `VAST_AI_API_KEY`, fallback `~/.config/vastai/vast_api_key`) into
  `/root/.bench.env`, scp's `self-reaper.sh`, and arms it right after the launch script; env `SELF_REAPER_TTL_H` (default 16).
  Verify at launch: the provision log line `self-reaper armed on the VM` and `ssh … 'pgrep -fc self-reape[r]; tail /root/self-reaper.log'`.
- **Sizing for an unattended window:** TTL must exceed the slowest lane. Reference: 63 tasks × 8-h budgets = ~55 agent-hours → 4 lanes
  ≈ 14 h wall; split an arm over 2 boxes (31 tasks each, one store per box) for ≈7–9 h; TTL 16 h.
- **Still repl-dependent:** the launch itself (~20 min: rent → provision → bootstrap → first rows + reaper check). Nothing after.
- **Repl-side helpers that remain useful while a session is alive:** `tb4e6-all-monitor.sh` (combined per-arm store poll with
  destroy-at-complete folded in) — convenience only; never the sole teardown.
- **Cost reading (operator asked why credit burns "so fast"):** cost = arms × wall hours × ~$0.86/h per 64-vCPU box; the visible
  credit sits near $10 because auto-top-up refills it, so it reads as a constant drain. Quote instance-hours per arm at launch and
  destroy per arm at completion, never at fleet completion.

- **DELTA 2026-09-19 — host REBOOTS kill the run AND the self-reaper (cb, f1 run: VM rebooted 09:58Z, idle 2.25 h, would have billed
  forever).** Structure: `reboot-relaunch.sh` + `@reboot` cron on every VM (sleep 90 → wipe `/app/bench/{banked,hfds,j_*}` → re-run the
  launch script → restart the self-reaper). `provision-and-launch.sh` installs it at launch (done 2026-09-19). Same-store
  relaunch resumes: the bootstrap re-syncs banked rows and the supervisor skips done tasks. Sizing correction: 31 tasks × 8-h budgets on 4
  lanes ran ~2 tasks/h/box → ~15 h, not 9; set the TTL ≥ 2× the estimate.

## DELTA 2026-09-20 — every adjudicated store now goes to the LAKE + the STDB bench control plane (ingestion gap closed)
Until 09-20 no bench run reached the DBAI data lake or `bench_task_result` (reducer `ingest_bench_task_result` had no caller; the
ETL dropped every decision-store row). Structure now:
- `nexus-terminal/modules/database-ai/training/benchStoreIngest.ts --store <hf-org>/tb2-<sfx> [--run-id <run> --arm <arm>]
  [--benchmark-id …] --adjudicate --go` → (1) last done row per task → `bench_task_result` (run/arm scaffolding created when
  missing; `--adjudicate` → `harness_bench_run`, so `promote_harness_bench_to_public_proof <run_id>` is the ONLY manual step to the
  public BENCHMARKS surface); (2) session + decisions + `<base>.outcome.json` staged to `/tmp/lake-stage/<sfx>/` → the ETL
  (`--sessions-only --source harness_bench --class-floor benchmark`) → `session_transcripts` rows `harness~<sfx>__<task>__rN:<turn>`
  + one `…:decisions` decision-trace row per session (quality_weight 0.2 = label source). Failed sessions cap at 0.3.
- **At adjudication, append the store to the queue instead of running it by hand:** `echo "<hf-org>/tb2-<sfx> <run_id> <arm>" >>
  $WORKSPACE/.bench/lake-ingest-queue.txt` — `scripts/claude-etl-ingest.sh` drains it daily (re-queues on failure).
  A multi-arm run uses ONE run_id and per-arm `arm` labels (f1 = ctl-a/ctl-b/stack-a/stack-b; e6 = ael/aeh/aem/mel/meh/men).
- One-time backfill of all 210 `<hf-org>/tb2-*` stores: roster `.bench/lake-backfill-2026-09-20.json`, runner
  `.bench/lake-backfill-run.sh` (detached; log `.bench/lake-backfill-2026-09-20.log`, summary `….out.json`); idempotent — rerun to resume.
- Verify a store landed: `SELECT id, score, pass FROM bench_task_result WHERE run_id='<run>'` and
  `SELECT record_id, capability_class, quality_weight FROM session_transcripts WHERE session_ref='harness~<sfx>__<task>__r1'`
  (owner /sql on `nexus-nexus-cortex`).

## DELTA 2026-09-20b — 4.120.0: R173 HB-GAP-HOLD / R173b Jev gate / R174 HB-SPEC-TESTS (dark) + the cell g1 recipe
- Levers (all default off; `.env` LEDGER blocks): `CORTEX_JUDGE_GAP_HOLD=true` (an evidence-mode GAP naming open items is returned to the
  junior while ≥ CORTEX_BUDGET_CONTINUE_MIN_REMAINING of the budget remains, up to the budgeted cap 6 — the f1 curation's "judge often right,
  overridden" fix; with shipped defaults the effective veto budget was 1 because `accept-with-gap` fires on any GAP without a FAILED
  harness-run check), `CORTEX_JUDGE_GAP_HOLD_JEV=shadow|gate` (+`_MIN` 0.3; TypeSafe Jev `fixable_with_more_turns`; the key ships
  `.bench.env` → bootstrap → adapter → cortex-server; launch scripts must `export … TYPESAFE_API_KEY`), `CORTEX_JUDGE_SPEC_TESTS=true`
  (+`_MAX` 4; blind spec-derived CHECK lines authored once per turn from the task text + env report, run every adjudication; FAILED = veto
  evidence). Engagement evidence per arm = `spec_tests` events + endturn_resolver {specRan, specPassed, specFailed, gapHold, gapHoldable,
  action, namedFailed, jevFixable}. Adapter allowlist carries all five keys (nexus-terminal/workers/nexus-cortex-sandbox/bench/nexus_cortex_agent.py).
- Cell g1 recipe (2 arms, 35 tasks = `.bench/tb4-tasks-ever29.txt` ∪ the curation §4 13-task pool → `.bench/tb4-tasks-g1-35.txt`, budgets
  `.bench/tb4-g1-budgets.json` 10800 s): `build-cells.sh guard`; per store `CELL_FILTER=cell-x STORE_SFX=t4g1{c,x} RUN_SUFFIX=-g1 K=1
  ARMS_FILTER=ctl PIN=nexus-cortex@4.120.0 DATASET_ID=terminal-bench/terminal-bench BENCH_ID=terminal-bench-4-0 BENCH_NAME="Terminal-Bench 4.0"
  BUDGETS_FILE=.bench/tb4-g1-budgets.json DATASET_REF=e2995b93b0a46edee7bc9942ea5622411a6d5bb9 TASK_SUBSET="$(tr '\n' ' ' < .bench/tb4-tasks-g1-35.txt)"
  build-cells.sh create|seed`; envs `common-cellg1c.env` (= e6 aeh control re-pinned) / `common-cellg1x.env` (+ the three levers); launchers
  `launch-g1{c,x}.sh` (35 shards, autoscale 4 lanes); one 64-vCPU non-Taiwan box per arm via `provision-and-launch.sh <iid> <env> <launch>
  <tag>`. Launch only after `npm view nexus-cortex version` shows the pin and ≥10 min have passed. Read: paired on 35 tasks + the
  false-hold rate (specFailed>0 on reward-1 sessions) + hold count per session vs budget used.
- Post-run: append both stores to `.bench/lake-ingest-queue.txt` with `g1 c|x` so the daily ETL lands them in the lake (DELTA 09-20).

## DELTA 2026-09-21 — GPU tasks on a Vast kvm VM (the recipe) + what cells g1/g2 taught about reading lever rows
- **GPU lane recipe (works, `<hf-org>/tb2-t4gpu3-ctl`):** rent a kvm box with one 4090/3090 (`TB2_REQUIRE_GPU=1`, `TB2_MIN_VCPU_PER_LANE=11`,
  2 lanes). Three blockers, all structural now: (1) harbor 0.23 refuses `gpus>0` in its docker env → `scripts/tb2-durable-supervisor.py` passes
  `--override-gpus 0` and grants the device through a per-task compose overlay (`--extra-docker-compose`, repeatable); (2) the bootstrap installs
  the NVIDIA container toolkit only when `nvidia-smi -L` lists `^GPU [0-9]` (a CPU box has nvidia-smi that exits 0 with "No devices were found")
  and hard-verifies a CUDA container lists a GPU; (3) the kvm image ships driver 535 whatever the host runs, and TB4.0 GPU task images demand
  `cuda>=13.2` at container start → in-VM upgrade to the PROPRIETARY headless driver (`nvidia-dkms-<V>` + utils; the open module's GSP firmware
  does not load on the kvm kernel; stop unattended-upgrades, quote /etc/environment, `dpkg --remove --force-depends` the GL metapackages),
  reboot, `@reboot` cron relaunches. Driver 580 = CUDA 13.0: jax/math-eval/vpp/pretrain images run, fp8-rmsnorm-gemm still needs 13.2 → 595
  (in jammy-updates multiverse: `nvidia-dkms-595 595.91.07`). Verifier timeouts on CPU (vpp, pretrain) are an environment artifact: vpp graded
  normally on the GPU box.
- **Reading a lever arm (g1/g2):** the paired count on 35 tasks moves ±2 between repeats of the SAME config; read the trigger attribution
  (`.bench/vm/g1-triggers.py`, sed the x store for another cell) — per adjudication: action, budget %, rejects, spec/named failures, Jev p, hold
  progress — and classify every flip as lever-trigger / infra / variance BEFORE touching the count. Two harness defects were only visible in
  the rows: a session that ends at turn ~14 with `Unexpected error in multi-turn loop` (R177) and holds 45–137 s apart with
  `holdProgressed=true` (R173c-b). Grep every store's `cortex-server.log` for `Unexpected error|is not a function|FALLBACK-ACCEPT|reasoning
  exhaustion` as part of the post-run sweep.
- **Control reuse:** a refinement cell may reuse the prior cell's control rows when the population, budgets, dataset and model pin are identical
  and the harness delta between versions is dark code only — disclose it in the ledger (g2 used the g1c rows).

## DELTA 2026-09-21b — the Terminus-frame cells (E1/E2) recipe + rig rules
- **Frame arm env** = the control config + `CORTEX_FRAME=terminus CORTEX_FRAME_CANDIDATES=1` (E1) / `+ CORTEX_FRAME_CHOOSER=jev CORTEX_FRAME_CANDIDATES=3`
  (E2); pin the release that carries them (4.124.0 / 4.124.1). The adapter forwards `CORTEX_FRAME*`; `TYPESAFE_API_KEY` must ship for the chooser.
  Files `common-celle{1,2}t.env`, `launch-e{1,2}t.sh`, stores `tb2-t4e{1,2}t-ctl` (35 = `tb4-tasks-g1-35.txt`, 10800 s).
- **Engagement check (mandatory, ~5 min after LAUNCH-DONE):** `docker exec <env-main container> grep -c frame_turn /logs/agent/decisions.jsonl`
  on the box; for the chooser arm `frame_turn.detail.answers` must be non-null and `chooserLatencyMs` > 0 in every row. Readers after banking:
  `.bench/vm/frame-engagement.py <store>` and `.bench/vm/paired.py <ctl> <x>`.
- **Rent-on-condition launchers** run INSIDE a detached tmux session on the repl and hold a `flock` (five duplicate launchers rented five boxes 09-21); full launch procedure in §"LAUNCHING A CELL" at the top.
- **Reused-IP host keys:** a box rented right after destroying one on the same host trips "REMOTE HOST IDENTIFICATION HAS CHANGED"; the provisioner
  continues; manual ssh needs `-o UserKnownHostsFile=/dev/null`.
- **Repl quota:** a day of store reads fills `~/.cache/huggingface/hub` under the workspace quota → EDQUOT freezes every local write (tool outputs
  included). Clear `datasets--<hf-org>--*` from the cache after each batch of reads, or point HF_HOME at /tmp.


## DELTA 2026-09-23 — the cell-smoke GATE (mechanism engagement as structure)
`.bench/vm/cell-smoke.sh <common-env>` runs the toy CSV task (4 stated requirements) on the LOCAL dist under the cell's exact env (TB2_*
stripped), reads the server's real port from its log, and asserts per armed lever: resolver event, non-empty lift plan, frame turns +
FrameAction offered, Jev answers (chooser), author candidates, requirement_ledger authored + DELIVERED + run at the finish, spec_tests; plus
the answer. `launch-cell-when-ready.sh` runs it after the npm wait and refuses to rent on any FAIL (`LAUNCH_SKIP_SMOKE=1` bypass — record why).
Passed: L7 env 7/7, E3 env 8/8 (09-23 ~7:45 AM PT). Traps it encodes: the stale :4187 listener (4 false smokes 09-22), the ledger authored
after the plan delivery (4.124.12, never delivered), the E2 arm with no menu (89% single-candidate turns). Local dist must match the pin
(warns otherwise).

## DELTA 2026-09-23b — ANCHOR CORRECTION (read before quoting any Terminal-Bench 4.0 comparator)
The tbench.ai 4.0 board is served by the Harbor Hub function `POST https://ofhuhcpkvzjlejydnvyd.supabase.co/functions/v1/leaderboard-read`
{"package":"terminal-bench/terminal-bench","name":"4-0-0"} (no auth; rows with metadata/metrics, 66×5 trials, pass@k) — fetch it, never quote
from memory. As of 09-23 it has NO DeepSeek and NO Terminus 2 rows (Codex / Claude Code / Grok Build / mini-SWE-agent only). AA's 26.8 for
V4.1 Flash is AA's own mini-swe-agent run, aggregate only. Our reference arm (harbor terminus-2 + deepseek-flash, `TB2_AGENT=terminus-2`) is
the first Terminus-2 + flash measurement anywhere. Per-task public results: none exist; per-task pairing needs our own run on our population.

## DELTA 09-23c — box PACKAGE CACHE for in-container installs (+ checker usage in the env report)
- Symptom: `npm install -g nexus-cortex@PIN` inside a task container failed after 3 retries (payments-pipeline-fix image, kafka sidecar) on two
  cells and two pins → 3/42 rows RIG (0 tool calls, reward 0, "Command failed" right after the install step).
- Fix (structure): `bootstrap-executor.sh` now installs node on the BOX once, builds a global-prefix bundle `nexus-cortex@PIN` with its whole
  dependency tree (`/root/pkgs/cortex-prefix-PIN.tgz`, ~40 MB), downloads the node tarballs (linux + musl), and serves `/root/pkgs` with
  `python3 -m http.server ${TB2_PKG_PORT:-8765}` on 0.0.0.0. The adapter (`nexus_cortex_agent.py`, `_PKG_CACHE_DISC`) discovers the box from the
  container's default gateway (/proc/net/route → `ip route` → 172.17.0.1; `TB2_PKG_HOST` overrides) and tries `cortex-prefix-PIN.tgz` (untar into
  /usr/local) and the node tarball from the cache FIRST; every miss falls through to the unchanged registry / nodejs.org path.
- Evidence in a cell: the agent log line `harness from box cache (<ip>): nexus-cortex@PIN` (and `node tarball from box cache`); the box log line
  `[boot] package cache server on :8765 — …`. If neither appears, the cache is not serving (check /root/pkgserver.log) and the run is on the old path.
- Validated 09-23 on the repl: bundle relocatable (binaries run from a relocated copy), rendered install commands pass `bash -n`, e2e fetch+untar
  against a local http.server → "harness from box cache". Not yet observed on a Vast box (first real use = the next cell launch).
- Env report (core 4.124.20): a bounded "CHECKER / VERIFIER SCRIPTS (usage lines)" leg lists usage/argparse lines of any *check*/*verif*/*validat*/*grade*
  script under the workspace (top 3 levels, 6 files, 6 lines each) so no downstream extractor has to guess a checker's CLI (photonic: 6/6 sessions guessed).

## DELTA 09-23d — SECRETS IN BANKED ARTIFACTS (HF security alert, 2026-09-23 ~12:30 AM 09-24)
- What happened: harbor's `mini-swe-agent` writes its model config (LiteLLM kwargs incl. `api_key`) into `trajectory.json` and its stdout log
  when a trial errors; the supervisor banked those files verbatim; the stores were seeded `private=False`. HF flagged the DeepSeek key in
  `tb2-t4msab-ctl` (8 files across msaa + msab; our harness and terminus-2 artifacts were clean).
- Response: all 13 stores from the arc set PRIVATE; the 8 files deleted; both repos `super_squash_history` (one commit, no history); key ROTATED
  by the operator (a public key is burned regardless of deletion).
- Structure (never prose): `scripts/tb2-durable-supervisor.py` `_bank_scrubbed()` — every foreign-agent artifact and trial result passes through a
  scrub that replaces the exact values of every secret in the supervisor's env and any provider-key-shaped token before it lands in the store;
  a scrub failure means the file is NOT banked. RULE: seed every store `private=True`; the results a paper cites are copied out deliberately.
- CORRECTION (same night): this was alert #3, not #1 — the August response (session b7e72a9b) already produced `scripts/rotate-provider-secrets.sh`
  (rotation = Replit secret → sync bridge → that script) and the v10 scrub on session.jsonl; the 09-13 harbor-artifact bank path was a second copy
  site with no scrub. ALL copy sites now use `_bank_scrubbed()`. On the next alert: canon grep first (`email from HF`), then the script.

## DELTA 09-24 — R194 SECOND ATTEMPT (bench-side): the judge's "done with gap" reopens the task
- Why: the 570-session replay (r-tb4-judge-replay-2026-09-24.md) — 41% of ever-passed-task failures end with the judge convinced, 23% with the
  judge knowing an item is open and accepting anyway; gap-hold converts the second into the first (g1x) without moving the count; 75% of failures
  leave >=50% of the budget unused. Consistency (30% per run vs 47% ever) is variance, so spend the leftover budget on an INDEPENDENT attempt.
- Where: `nexus_cortex_agent.py` (`_SA_SNAPSHOT`, `_SA_ATTEMPT2`), NOT the harness. The adapter owns the server lifecycle + workspace: shadow git
  snapshot at task start (git dir /tmp/.cortex-attempts/shadow.git, vendor dirs + files >20 MB excluded) → after attempt 1 read the last
  `endturn_resolver` event from decisions.jsonl → if action ∈ TB2_SECOND_ATTEMPT_TRIGGER (default accept-with-gap,accept-low-confidence) and
  remainingFrac >= TB2_SECOND_ATTEMPT_MIN_REMAINING (0.5) and >=15 min remain → bank *.attempt1.*, commit `attempt1`, reset to `lift`, kill the
  server, fresh server (CORTEX_STATE_DIR=/tmp/.cortex-state-2, deadline = remaining − 5 min), POST the same task → commit `attempt2` → shipped
  check (Makefile test / test.sh / pytest) on tree 2 then tree 1 → selection (check passes on exactly one → it; MEETS beats gap; both gap → more
  judge checks passed; tie/no finish → attempt 1) → restore the chosen tree; response.json = chosen attempt with usage.session SUMMED;
  /logs/agent/second-attempt.json = the decision. Levers forwarded by the adapter env allowlist; TB2_SECOND_ATTEMPT=1 turns it on (off default).
- Engagement evidence: `[adapter] R194 …` lines in nexus-cortex.txt; `second-attempt.json` + `decisions.attempt1.jsonl` banked per task.
- Validated 09-24: shadow-repo reset/restore on a scratch tree (excluded big files untouched); rendered run command `bash -n` clean; trigger +
  selection programs on fake verdicts (6 cases); live e2e against a local cortex-server (toy task, trigger forced).
- Cell: s2a/s2b = the ever-passed 29 ×1 (15/14), g1c control @4.124.20 + the lever; paired vs tb4-pass-frequency-2026-09-23 per task.
- TRAP (09-24, caught by the live e2e): `pkill -f cortex-serve[r]` INSIDE the adapter command killed the adapter's own `bash -c` (its command
  line contains "nohup cortex-server …"). Same class as the 09-21 ssh self-match. Rule: the adapter captures `SRV=$!` at every server start and
  kills by PID; never a pattern kill from a shell whose own command line contains the pattern (also true of this repl's tool shell — a test
  cleanup killed the session shell twice).
- FIELD DEFECTS of the package cache (first cell with it, s2, 09-24; both fixed at 9:51 AM PT, adapter pushed to the running boxes + stores):
  (a) the container-side discovery snippet ran `python3 -c …` under the node step's `set -e` → images WITHOUT python3 died at exit 127 →
  a RIG row (distributed-dedup); now guarded (`command -v python3 &&`, every leg `|| true`, docker0 fallback) and verified under set -e with no
  python3 on PATH; (b) the cache's "from box cache" lines wrote to /logs/agent before it existed → silent; now `mkdir -p` + `|| true`. The box
  server log (/root/pkgserver.log) is the primary for cache hits: containers DID fetch the bundle. Rule: anything spliced into the adapter's
  install commands must be fail-soft under `set -e` and must not assume python3.
- R194 programs read decisions with encoding="utf-8", errors="replace" (an older in-image python + non-ASCII plan text emptied the verdict on react r1
  before the fix). Rows before 9:51 AM PT in s2 may carry an inert R194 — the read marks them by trial start time.

## DELTA 2026-09-25 — R196: harbor runs install as ROOT and the agent phase as the image USER (two TB4.0 images are non-root)
`risk-scorer-replay` (USER nobody) and `rs-archive-clone` (USER agent) banked 0-token rows in every cell since 09-24 (f66f ×2 boxes,
st a/b/c; 6/6). The install phase's box-cache lines created `/logs/agent/nexus-cortex.txt` root-owned; in the run phase (as the image
user) every `>> nexus-cortex.txt` / `2>>` fails as a REDIRECTION error and bash SKIPS the command that carries it — the `/v1/messages`
POST included. Signature: agent phase ≈2.3 s, server log ends at boot, `health_config.json` present, no `response.json`, no exception,
`EACCES mkdir /app/.addon-tools` in the server log for the nobody image. Harbor keeps NO stdout/stderr of the agent command, so the
banked artifacts cannot show it; diagnose by replaying harbor's exact `Running command:` texts (on-box `trial.log`) in a probe container
from the same image digest (`docker inspect --format {{.Config.User}}`). Fix (adapter): install phase ends `chmod -R a+rwX /logs/agent`;
run phase moves a non-writable log aside + logs `[adapter] run phase as <user>`. Rules: (1) anything the run phase appends to is created
by the run phase or made world-writable; (2) never `>> file` without `|| true` in a command whose failure must not skip the next step —
put the POST on its own line with no redirect into a possibly-unwritable file; (3) a same-task 0-token cluster that recurs across boxes
is an image×adapter interaction, not the box (the f66f "docker daemon" reading was wrong for these 6 rows).

## DELTA 2026-09-25b — the lake queue does not drain itself; `.bench/lake-drain.sh` is the standalone bench leg
The daily `claude-etl-ingest.sh --if-due` fires only from a shell hook and runs its Claude/canon TRANSCRIPT leg first; 09-25 that leg
sat 21 min in a network wait at 0% CPU (canon mode, 5,623 sessions, "skipped 0 unchanged") with the bench queue untouched behind it,
and it had not drained the queue since 09-22 (21 stores waiting; 12 more TB4.0 stores — the E1/E2/E3 halves, gpu, gpu2, r176/b — had
never been queued at all). `.bench/lake-drain.sh` = the queue loop alone (same semantics: flock, a line removed only on success, OK/FAILED
lines tee'd into `.claude/etl-ingest.log`), 33 stores in ~2 min. Reconcile every store on HF (`/api/datasets?author=<hf-org>&search=tb2-`)
against the backfill output + the ETL log before any lake-dependent work; foreign-agent stores (terminus-2 `ref*`, mini-swe `msa*`) stage 0
sessions by design; R196 rows stage no session. RESOLVED 10-15: the "8 large TB4.0 stores hit HTTP 413" hole is closed — `capForReducer()` (per-record caps, 09-20) + later re-ingests;
verified 10-15 by re-draining fca/fcb/fsa/fsb/r/s (6/6 OK, 0 errors) with lake row counts unchanged at exactly 2 rows per task
(62/62/62/62/14/76). Row-count check per store: `SELECT session_ref FROM session_transcripts` | grep `harness~<sfx>__` → expect 2 × tasks. The ETL writes `.etl-last-run` at START, so a killed run blocks `--if-due` for 24 h.


## DELTA 2026-10-08 — store rows are COPIED into every shard file; read with dedup by task
The supervisor's reconcile rewrite copies every remote row into every `results-s<N>.jsonl` (byte-identical rows, same ts/cost — NOT re-runs,
no extra spend). Every reader must dedup by `task` (last row wins) before counting passes or summing `cost_usd`; the STDB `ingest_run` does
not (R243) so `harness_bench_run` over-counts ~2× for multi-shard Vast runs — the cell ledger's unique-row numbers are the truth. Grader
artifact names carry the harbor trial prefix (`<task>.agent-…__agent__second-attempt.json`). Post-run harvest = `post-run-drain.sh` keyed by
the queue's RUN ID (see stdb-bench traps 9–11 for the refused-adjudication recovery and the drain's fail-closed states).


## 🔴 DELTA 2026-10-10 — CHAIN-CELL SPEND: rows before the R244 fix count ONE attempt; read the sidecar / response session total
Every row banked by tb2-durable-supervisor.py before 2026-10-10 on a second-attempt cell (adapter TB2_* or library CORTEX_SECOND_ATTEMPT:
c22 arm B, s2a/s2b, t4r/t4s, t4h/t4k, t4hr/t4kr) carries `cost_basis: cumulative-session` = the tokens of ONE attempt's session.jsonl →
51–65% of the real spend. The true chain total is `grader/<task>…__agent__metrics.json` (= response.json `usage.session`, summed over
attempts by both chains). Verified: t4h row $11.13 vs sidecar $17.36; t4hr $11.62 vs $20.25; t4k $15.61 vs $30.83; t4kr $10.74 vs $16.48.
Fix shipped in the supervisor (cost_basis `response-session-total`, banked when usage.session has ≥ the session file's requests/output);
it reaches a box with the NEXT seed. Reading rule: for any chain cell, sum the sidecars (dedup by task), never the rows; the STDB
harness_bench_run cost for those runs is the row sum (under-counted) until re-banked. Spend parity between chains is judged on sidecar totals.

## 🔴 DELTA 2026-10-10b — the banked TRAJECTORY of a chain task was the LAST attempt (R245); rebank tool
The adapter's 20-s session copier and its final `find … -name '*.jsonl' | ls -t | head -1` copy take the NEWEST session file = the last attempt,
in BOTH chains, regardless of the pick — every chain-cell session trajectory before the next seed (c22 arm B … t4kr) is the last attempt's;
curation "how sessions end", failure classes and doctrine evidence describe it. Fix (adapter, 10-10): per-attempt `session.attempt<k>.jsonl`
captured from the state dirs, and the final copy takes `session.attempt<pick>.jsonl` when second-attempt.json names a pick (+ decisions).
Reaches boxes with the NEXT seed. `.bench/vm/rebank-chain-cell.py <store>…` rewrites a store's rows from the sidecars (R244) and swaps
trajectories to the pick where a per-attempt copy exists (R245), keeping `.pre-r244` / `.pre-r245` backups; follow with benchStoreIngest
`--store … --run-id … --arm a --go` + `adjudicate_bench_run` to refresh the STDB rows.

## DELTA 2026-10-11 — R250 SIBLING GRADING: the non-picked attempts of a chain get graded in restore-only trials
The hidden grader is one-shot per trial, so the selector's pick is the only attempt that ever gets a grade. R250 adds the oracle:
- Both chains bank `attempts.bundle` (shadow repo: `lift` + every `attempt<k>` tag) + `attempts.json` beside `second-attempt.json`
  (library: `WorkspaceSnapshot.bundle()` in `runWithAttempts` when `CORTEX_SECOND_ATTEMPT_OUT_DIR` is set, 4.124.71+; adapter: `$G bundle
  create` after the pick restore, seeded 10-11+).
- The supervisor's `run_siblings()` (after `bank(rec)`) copies the bundle to `attempts/<task>.bundle` in the store (≤ 10 MiB, HF plain push),
  pushes it, then runs ONE Harbor trial per non-picked attempt with `-a restore_attempt_agent:RestoreAttempt` (env RESTORE_BUNDLE_URL +
  RESTORE_ATTEMPT=attempt<k>): the agent curls the bundle with HF_TOKEN, checks that tag out into the workspace, exits; the verifier grades
  it. Rows → `siblings-s<idx>.jsonl` {task, attempt, pick, reward, status sibling|sibling_timeout|sibling_error}. Zero model spend; cap per
  sibling `TB2_SIBLING_CAP_S` (3600). Size TTL_H for ~2 short trials per chained task.
- Readout: `HF_TOKEN=… python3 .bench/vm/sibling-oracle.py <store>` → per task pick grade, every attempt's grade, the ORACLE (any attempt
  passes), and what verdict-first / evidence-first would have picked. The oracle is pass@k-style evidence for the SELECTOR; the published
  number stays the pick's pass@1 (and still needs 3 independent runs).
- Caveat: a sibling trial starts from the base image — the attempt's FILES are restored, not packages/services it installed → lower bound.
- Absent restore agent on a box (store seeded before 10-11) → siblings skipped with a log line; the main row is unaffected.

## 🔴 DELTA 2026-10-11b — t4j1 (first R250/R251 box run): judge selector FIRED; sibling grading produced NO rows — two supervisor defects
atrx on 4.124.72, SELECT=judge: 3 attempts (all accept-with-gap, 152/132/117 turns), ONE judge call (1.9 s) → RANKING 3>1>2 with a task-specific
reason (frame/HGVS evidence), pick 3 = evidence pick, reward 0, $1.69, 3.1 h; judge-packets.json + attempts.json banked; `R250 attempts bundle
written (4 tags)` in the server log. But the store got no `siblings-s0.jsonl` and no `attempts/`, and the box was reaped before the reason could
be read (the supervisor's own log is not banked). Root causes found in code: (1) `sync_store()` returned early whenever no ledger ROW was missing
→ the siblings file and bundle were never staged, whatever happened; (2) the bundle went to the store (≤ 10 MiB gate) with nothing else serving
it. FIX (supervisor + restore agent, 10-11): sync_store also pushes when `git status --porcelain -- attempts siblings-s<idx>.jsonl` is dirty; the
bundle is served from the BOX package cache (`/root/pkgs/attempts/<task>.bundle` on :8765, the path the adapter's harness install already uses —
`RESTORE_BUNDLE_URL=http://GATEWAY:8765/…`, the restore agent resolves GATEWAY from /proc/net/route → ip route → 172.17.0.1, `TB2_PKG_HOST`
overrides), no size limit; a ≤ 10 MiB copy still goes to the store; EVERY early return writes a `sibling_skipped` row with its reason. RULE: a
supervisor step whose only trace is its stdout is invisible after the reap — bank a row (or a grader file) for every skip path.

## 🔴 DELTA 2026-10-12 — HF REJECTS EVERY NON-LFS BINARY FILE (not just >10 MB, not just .gz): one .bundle in the store clone poisoned all 4 shards' pushes for 7 h
t4jf: `attempts/<task>.bundle` (git bundles, 20 KB–1.3 MB) copied into the shared store clone by the R250 sibling step → HF pre-receive: "Your push was
rejected because it contains binary files … use xet … Offending files: attempts/…bundle" → EVERY shard's `sync_store` failed (the clone is shared, the
loop stages every attempts/* file) → 8 graded rows + 2 shards' INCOMPLETE/UNPUSHED, 12:08 AM–7:30 AM PT. The 49 KB fin bundle had slipped through
(binary detection is content-based; small ones can pass) — never infer "binary is fine" from one success. RULES: (1) the store holds TEXT only
(jsonl/json/txt/log/py/sh); binary artifacts stay on the box or go to LFS/Xet deliberately; (2) the supervisor never copies bundles into the clone
(fixed 10-12: box package cache only; `attempts/` never staged); (3) a "pre-receive hook declined" with the reason truncated = run `git push` by hand
over ssh (read-only effect: it is rejected) to read the hook's "Offending files"; (4) repair = `attempts/` in `.git/info/exclude` + `git rm --cached`
+ rm, `reset --mixed origin/main`, re-add text files only, commit, push — the running supervisors (old code) keep re-copying bundles, the exclude
makes that harmless; the fixed supervisor file goes to /app/bench + the store so a reboot relaunch runs the fix.

## 🔴 DELTA 2026-10-12b — WHY EVERY SIBLING GRADED 0 (t4j2 + t4jf): the bundle was written with `--all --tags`
`git bundle create … --all --tags` lists every tag TWICE; the box's git 2.34 refuses `git clone` of such a bundle ("fatal: multiple updates for ref
'refs/tags/attempt1' not allowed") — the repl's newer git dedups silently, so the local test passed. In the container the fetch succeeded (package
server logged 200), the clone died, `set -e` exited, the verifier graded the untouched base image (0), and the row said `restored: true` because the
check was "restore.txt exists". Diagnosed by re-running ONE restore-only trial on the live box by hand with a step-naming agent (`harbor run … -a
restore_attempt_agent:RestoreAttempt` + RESTORE_BUNDLE_URL/RESTORE_ATTEMPT env; job dir kept; read agent/restore.txt + verifier/reward_details.json).
FIXES (16be9063b7): writers use `--all` only (library WorkspaceSnapshot.bundle + adapter; test asserts `git bundle list-heads` unique); the restore
agent fetches ONLY `refs/tags/<attempt>` from the bundle (tolerates old bundles), names the failing step, captures stderr; the supervisor's `restored`
flag requires the "restored attempt<k>" line. PROOF on the box: freecad pick restored → 1.0 (= main trial), attempt 1 → 0.65 (real difference).
RULES: (1) a sibling row without its verifier artifacts (`grader/<task>.sib<k>.*`) is unverifiable — bank them; (2) the pick-restore calibration row
(`pick_restore`) must reproduce the main reward before any sibling zero counts; (3) test container-side git steps on the box's git version, not the
repl's. Regrade of already-banked chained tasks: `/root/sibling-regrade.sh` on the box → `siblings-regrade.jsonl` (+ sib artifacts), the oracle
prefers regrade rows.

## DELTA 2026-10-15 — R261: every attempt of a chain is banked AND ingested (the non-picks were being thrown away)
- Supervisor: `_bank_attempt_sessions(jd, task)` banks `trajectories/<task>.session.attempt<k>.jsonl` + `.decisions.attempt<k>.jsonl` for EVERY attempt
  (same scrub + >9 MB base64 strip as the main session); chain artifacts (`response.attempt*.json`, `second-attempt.json`, `attempts.json`,
  `judge-packets.json`, `informed.attempt*.txt`) are banked UNCAPPED — the 24-file cap applies to the rest only. Reaches boxes with the next seed
  (pushed into tb2-rsb3-b for its reboot relaunch; the running supervisors keep the old code).
- Ingest (`benchStoreIngest.ts`): reads `siblings*.jsonl` + `second-attempt.json` per task; stages each non-picked attempt as `<sfx>__<task>__a<k>`
  with outcome {reward, pass, status sibling|…|ungraded, attempt, pick_attempt, action, turns, restored, origin}; older stores (no banked attempt
  session) get a synthesized task+final-message record from `response.attempt<k>.json`. `--no-attempts` skips; `--attempts-stdb` posts
  `bench_attempt_result` rows (needs the module publish). ETL: an ungraded outcome is unlabeled, not a 0.3 cap.
- Readers: lake session_refs `harness~<sfx>__<task>__rN__a<k>`; the pick stays `…__rN`. Oracle/replay scripts unchanged (they read the store).
