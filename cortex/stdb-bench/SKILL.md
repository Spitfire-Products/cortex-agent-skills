---
name: stdb-bench
description: Operate the STDB BENCH CONTROL PLANE — the `nexus-nexus-cortex` SpacetimeDB module that places, keeps alive, heals, budgets, gates, reaps and completes a Harbor/TB2.1 lane fleet with NOTHING running on the repl. Covers the rig (`.bench/cells/build-cells.sh` create/seed/guard/launch/status), the job kinds + timings, the gate-enforced launch, touch-free monitoring, the self-heal mechanics and their expected timings, the diagnosis kit, and every trap the first real runs hit (lane-name law, gate-vs-pin, silent per-lane placement failure, instant-complete livelock). Use for ANY STDB-driven bench run (cells, pilots, the k=5). Pairs with harbor-bench (the executor: adapter, in-container supervisor, HF stores, classification rules) — this skill is the control plane ONLY.
triggers:
  - stdb bench
  - bench_lane
  - build-cells
  - cell-m
  - k=5
---

# stdb-bench — the repl-independent bench control plane

**Boundary.** harbor-bench owns the EXECUTOR: the Harbor adapter (`nexus_cortex_agent.py`), the durable in-container
supervisor (`scripts/tb2-durable-supervisor.py`), the HF arm stores, the result-classification and adjudication rules,
and the whole repl-era history (armers/watchdogs/relaunchers — RETIRED, keep for archaeology). THIS skill owns the
CONTROL PLANE that replaced them: the STDB module drives placement / keepalive / lease renewal / wedge remap / reconcile /
budget / gates / reaper, and the rig (`build-cells.sh`) is the only thing you type. Read harbor-bench DELTAs 2026-09-09
→ 09-10i for the build history; read THIS file to run one.

**Grounding rule (non-negotiable):** every claim here is a pointer to verify, not a fact to trust. Module source:
`nexus-terminal/modules/database-ai/spacetimedb-module/src/{tables/bench.rs, reducers/bench.rs,
procedures/bench_scheduler.rs, bench_tick.rs}`; plan: `nexus-terminal/modules/database-ai/STDB_BENCH_TICK_PORT_PLAN.md`
(§2c build state, §2d pilot ledger, P14/P15); rig: `.bench/cells/build-cells.sh`. Worker routes:
`nexus-terminal/workers/nexus-cortex/src/index.ts` (`/admin/bench/{launch,lease,release,leases,sweep}`,
`/admin/sessions/destroy`, `/debug/exec`).

## 1. Architecture (verified live 2026-09-10 on cell-d-k3 / cell-m-p3)

```
you (repl, ANY session)            SpacetimeDB maincloud (nexus-nexus-cortex)           Cloudflare
  build-cells.sh create/seed/  ──▶  bench_run / bench_arm / bench_lane / bench_job /     nexus-cortex WORKER
  guard/launch (reducer calls)      bench_gate (+events)                                   /admin/bench/launch (paced 8/15s,
                                    bench_scheduler_job → tick_bench_scheduler (60 s      per-lane exec w/ 4 retries)
  Monitor (store + CF-API reads,    meta-tick) runs each due bench_job by kind:           /admin/bench/lease (per beat)
  notification ONLY)                  keepalive 300s · placement 120s · watchdog 120s ·   /admin/sessions/destroy
                                      monitor 60s · reconcile 600s · budget 180s ·         warden cron 5 min (lease TTL 90m)
                                      gatecheck 120s (max 45) · fanout (one-shot) ·           │
                                      reaper-global                                           ▼
                                                                                          nexus-cortex-sandbox DOs
                                    HF arm stores (<hf-org>/tb2-<sfx>-<arm>) ◀── supervisor banks rows + trajectories
```

- **Scheduler:** `tick_bench_scheduler` (procedure, native outbound HTTP) fires every 60 s and runs every enabled
  `bench_job` whose `interval_secs` is due; `run_id` scopes a job to one run (`None` = global, e.g. `reaper-global`).
  Job kinds and the rig's intervals (`build-cells.sh` create/launch): keepalive 300 (`max_lanes_per_tick` = lanes+20),
  monitor 60, watchdog 120 (`stale_secs` 1500), placement 120 (`batchSize` 4 / `gapMs` 15000), reconcile 600 (mode
  pending, cluster watch), budget 180 (`cap_usd`, `min_balance_usd`, `key_id: bench:deepseek`), gatecheck 120 ×45,
  fanout one-shot (`{"lanes":[{session,arm_id,model_id,shard_idx,shard_n,cmd}]}`, FULL_WIDTH = one job ≤80 lanes).
- **Constants (`bench_scheduler.rs:70-82`):** `PLACE_MAX_ATTEMPTS 5`, `COLD_START_GRACE_MS 600 000`,
  `TICK_FAILS_REMAP 2`, `TICK_LANE_CAP_DEFAULT 20`, `LEASE_TTL_S 5400`; CF billing rates `CF_RATE_*` (marked VERIFY).
- **Run states (`reducers/bench.rs`):** draft → gated → running → adjudicating → complete; `halted` is terminal.
  **Lane states:** placing · running · wedged · dead_supervisor · complete_pending · complete_short · complete ·
  kill_requested · dead · reaped. The lane's LIVE session is `remap_to` when set, else `lane_id`.
- **Reducers you call (rig does most):** `register_benchmark`, `create_bench_run`, `add_bench_arm`, `upsert_bench_job`,
  `run_bench_job_now`, `set_bench_job_enabled`, `record_bench_gate`, `set_bench_run_gates`, `launch_bench_run` (refuses
  until every `required_gates` entry is recorded passed), `halt_bench_run`, `kill_lane`, `release_bench_lane`,
  `set_bench_run_state`, `adjudicate_bench_run`. Only ever via `.local/bin/spacetime call nexus-nexus-cortex <reducer>`
  with JSON args (`optsome`/`optnone` helpers in the rig for `Option<T>`).

## 2. The lifecycle, in order (each step idempotent; nothing spends before `launch`)

```bash
cd $WORKSPACE && set -a; source .claude/.replit-secrets.env; set +a; export PATH=$WORKSPACE/.local/bin:$PATH
export CELL_FILTER=cell-m K=1 STORE_SFX=mm RUN_SUFFIX=-p3 PIN=nexus-cortex@4.105.0 SHARD_N_FLASH=4 SHARD_N_PRO=3 FULL_WIDTH=1 \
  REQUIRED_GATES=population BUDGET_CAP_USD=20 BUDGET_FLOOR_USD=20 \
  EXTRA_COMMON="CORTEX_LOOP_TOOL_BLOCK=true CORTEX_EMPTY_TURN_CONTINUE=true HELPER_MODEL_ID=deepseek-flash VISION_HELPER_MODEL=deepseek-flash"
date -u; npm view nexus-cortex version         # off-peak (peak Mon–Fri 01–04 & 06–10 UTC) + the pin is published
bash .bench/cells/build-cells.sh guard         # adapter passthrough guard + LANE-NAME guard (auto before every spend mode)
bash .bench/cells/build-cells.sh fanout-dry    # builds every lane cmd, validates JSON/size, prints lane count — no writes
bash .bench/cells/build-cells.sh create        # bench_run (draft) + arms; run_id = <cell><RUN_SUFFIX>
bash .bench/cells/build-cells.sh seed          # HF stores: tasks×K, budgets, adapter, supervisor — FORCE-pushes (wipes rows)
spacetime call nexus-nexus-cortex record_bench_gate '"cell-m-p3"' '"population"' true true '{"some":"{\"gate\":\"…\",\"result\":\"PASSED\"}"}'
bash .bench/cells/build-cells.sh launch        # scoped jobs + gatecheck jobs + launch_bench_run; fanout fires next tick
bash .bench/cells/build-cells.sh status        # read-only STDB view (runs / lanes / jobs)
```
Other modes: `pilot` (PILOT_ARMS shard-0 lanes on fresh names, outside the gate — the mechanism-fire evidence the gate
needs), `emit-pilot`, `fanout` (non-FULL_WIDTH verify-first s0 + rest), `ticktest` (one pro lane, proves the spine),
`widen`. Env knobs: `CELL_FILTER RUN_SUFFIX K PIN STORE_SFX SHARD_N SHARD_N_FLASH SHARD_N_PRO FULL_WIDTH ARMS_FILTER
EXTRA_COMMON REQUIRED_GATES BUDGET_CAP_USD BUDGET_FLOOR_USD MODEL_FLASH MODEL_PRO LANE_PREFIX K5_MODE K5_ARMS
K5_EXTRA_COMMON K5_MODEL_FLASH EFFCFG_SRC`. Cells: `CELLS` specs (`letter|run|lever|sfx|flash_subset|pro_subset`);
`ARMS` (`label|model|store_label|lever_tokens_or_0/1`) — for cell-m the 8 mentor arms.
- **Re-running after a halt:** bump `RUN_SUFFIX` (`-p2`, `-p3`), `create` + `record_bench_gate` + `launch` on the SAME
  stores — do NOT `seed` again (it wipes banked rows). Supervisors resume-skip banked tasks; rows keep the tag of the
  attempt that graded them; adjudicate PER STORE.

## 2b. THE CLEAN-LAUNCH FORMULA (cell-m-r1, 2026-09-10 22:44Z — 40 lanes, 5 arms, 0 errors; follow it VERBATIM)
The first launch of the day (p1) died to lane names, the second (p2) to a gate asserting an unreported key, the third (p3)
needed a live gate rewrite. The fourth (r1) placed 40 lanes and passed every gate untouched because every check ran BEFORE
the spending step, in this order, with these exact knobs:

```bash
cd $WORKSPACE && set -a; source .claude/.replit-secrets.env; set +a; export PATH=$WORKSPACE/.local/bin:$PATH
# 0. the PIN must be (a) published and fetchable BY VERSION, (b) tagged in the release repo — the INV filter reads the tag
npm view nexus-cortex@4.106.1 version                       # prints the version (the `latest` dist-tag lags ~4 min; ask by version)
git -C nexus-cortex-extracted tag | grep -c v4.106.1          # 1 — effcfg_src_for_pin reads the pinned report from here
date -u                                                       # off-peak: not Mon–Fri 01–04 / 06–10 UTC; the run must FINISH off-peak too
# 1. ONE run id, FRESH stores, the EXACT arm set, 1 task/lane (SHARD_N = tasks × K), a real budget cap
export CELL_FILTER=cell-m K=2 STORE_SFX=mm2 RUN_SUFFIX=-r1 PIN=nexus-cortex@4.106.1 SHARD_N_FLASH=8 SHARD_N_PRO=8 FULL_WIDTH=1 \
  REQUIRED_GATES=population BUDGET_CAP_USD=20 BUDGET_FLOOR_USD=20 \
  ARMS_FILTER="flash-none flash-high flash-max pro-none pro-high" \
  EXTRA_COMMON="CORTEX_LOOP_TOOL_BLOCK=true CORTEX_EMPTY_TURN_CONTINUE=true HELPER_MODEL_ID=deepseek-flash VISION_HELPER_MODEL=deepseek-flash"
# 2. zero-spend staging, in this order — each prints a line you READ before the next
bash .bench/cells/build-cells.sh guard        # passthrough OK + lane names OK (≤22 chars)
bash .bench/cells/build-cells.sh fanout-dry   # "<run>: N lanes, args=… B (OK <128KB)" — N must equal arms × SHARD_N
bash .bench/cells/build-cells.sh create       # run (draft) + arms; then: spacetime sql … bench_arm | grep -c <run>  == arm count
bash .bench/cells/build-cells.sh seed         # one "✅ <store>: tasks=<tasks×K> sup=yes adapter=yes" per arm (verify-by-reclone)
spacetime call nexus-nexus-cortex record_bench_gate '"<run>"' '"population"' true true '{"some":"{\"gate\":\"…\",\"result\":\"PASSED\"}"}'
# 3. the ONLY spending step
bash .bench/cells/build-cells.sh launch       # guard re-runs; "[launch] <run>: FULL WIDTH — N lanes … fan out next tick"
# 4. read back what the module will enforce, BEFORE the first row can land (~5 min)
spacetime sql nexus-nexus-cortex "SELECT run_id, state FROM bench_run" | grep <run>                    # running
spacetime sql nexus-nexus-cortex "SELECT job_id, args_json FROM bench_job WHERE job_id='gc-effcfg-<run>'" # every EXTRA_COMMON key you expect, none you don't
# 5. arm the notification layer NOW (Monitor template §4) + a one-shot wait for the first row's proof (e.g. deliveredBy)
```
**Why it was clean (each line is a structural guard, not a habit):** the pin was verified fetchable by version AND tagged
(a `latest`-tag lag or a missing tag would have failed the adapter install or the INV filter); `STORE_SFX`+`RUN_SUFFIX` were
fresh (no resume-skip surprises, no instant-complete livelock); `ARMS_FILTER` named every arm explicitly; `fanout-dry`
proved the lane count and JSON size; `create` was verified by counting `bench_arm` rows; `seed` was verified by its
re-clone line per store; the population gate was recorded BEFORE `launch` (the launch invariant refuses otherwise); the
gate's `args_json` was read back immediately after launch; the Monitor went up within the same minute. Fanout placed
40/40 declaratively, 28 lanes beat inside 2 min, gates version_pin + sweep passed at +2 min, first row at +4 min.
**If any read-back disagrees with the expectation, STOP before `launch` (or `halt_bench_run` right after) — a wrong
gate arg costs the whole run at its first row (~5 min on fast tasks), and it is a one-line `upsert_bench_job` to fix.**

## 2c. VAST CELLS THROUGH STDB (P2–P4 shipped 2026-10-03) — the ONLY cell launch path now
`launch-cell-when-ready.sh` / `provision-and-launch.sh` are RETIRED for cells (exit 2 unless `LEGACY_REPL_LAUNCH=1`). Design:
`nexus-terminal/modules/database-ai/STDB_BENCH_VAST_EXTENSION_DESIGN.md`. Rig: `.bench/cells/stdb-vast-cell.sh`.
```bash
cd $WORKSPACE && export RUN=<fresh id> PIN=nexus-cortex@<published+tagged> \
  ARMS="<label>|<model>|<common-env-file> ..." TASKS=<task__rN list> KIND=tb4|mimo [MIMO_SRC_STORE=tb2-mimo64-nano1] \
  SHARD_N=8 LANES_PER_HOST=8 VCPU_PER_LANE=8 RAM_GB_PER_LANE=16 DISK_GB=150 MAX_DPH=1.5 TTL_H=6 BUDGET_CAP_USD=25 \
  [BENCHMARK_ID=mimo-tb64 DATASET_REF=XiaomiMiMo/MiMo-V2.6-RL-oss@639865fd] [GEO_EXCLUDE="TW RU BY CN HK IR KP SY CU VE"]
bash .bench/cells/stdb-vast-cell.sh guard    # pin published+tagged; STDB secrets bench:<provider> resolved per arm from the arm MODEL + every helper
                                              # slot in its env (gemini → bench:gemini|google, whichever exists); INV from the PINNED report
bash .bench/cells/stdb-vast-cell.sh seed     # private store per arm (tasks, adapter, supervisor, box bundle, common-box.env) + ENV-FORWARD gate
bash .bench/cells/stdb-vast-cell.sh create   # bench_run + arms + set_bench_arm_vast (offer filter: vcpu/ram/disk/price + GEO_EXCLUDE; box_env = secret: refs)
bash .bench/cells/stdb-vast-cell.sh launch   # RE-RUNS the forward gate; host_place/watch/reap @60 s, ingest @300 s, budget (if any arm's resolved keys
                                              # include DEEPSEEK_API_KEY), gc-version + gc-effcfg; appends "<RUN> <hf-org>/<store>" to .bench/post-run-queue.txt
bash .bench/cells/stdb-vast-cell.sh status   # run state, hosts (state/vast_status/cost), gates, rows in STDB
```
🔴 Run the phases as SEPARATE commands and check each exit code (`if ! bash … $m; then break; fi`). NEVER `bash … | tail | cut || …` —
the pipe masks the phase's exit (g6rs 10-03: seed's forward-gate FAIL was piped away, create+launch ran, a box was rented for a
would-be control). `launch` now re-gates itself, but the habit is still wrong.
What the spine does: host_place rents (secrets resolved at rent time, never on the repl) → the box's onstart fetches `bootstrap-box.sh` from the
store → heartbeats every 60 s (on `bootstrap_failed:*` the heartbeat carries `boot_tail` = the executor log's last lines, secrets masked — read it
from `bench_host.heartbeat_json`, no ssh) → supervisors (on-box LEVER AUDIT at the first graded row: bank `__lever_audit__`, stop the slice on FAIL) →
each graded row POSTed to `bench_task_result` (+ `ingest` back-fills from the store every 300 s and before adjudication) → `effective_config`
gate 120 s after the first row (ABSENT/mismatched key = HALT) → when every shard is terminal in the heartbeats: run → adjudicating → ingest →
`adjudicate_core` (auto, private; REFUSED if the effcfg gate did not pass) → complete → host_reap destroys the box. Halt = `halt_bench_run`
(hosts reaped). A box that `exited at boot` is destroyed, its machine banned, and the arm re-placed automatically (g6rs2 10-03, $0).
ONE ARM PER HOST today (an arm may span hosts; two arms never share one) — packing several arms per host is a future module change.
🔴 ONE ARM PER RUN for A/B cells (10-03, rsys): the gc-effcfg job carries ONE run-wide `invariants` map (the rig merges every arm env into
it), so a two-arm run whose arms differ by the lever under test FAILS the gate on the control arm ("expected on") → halt → both boxes reaped
($0.21). Until the module accepts `invariants_by_arm`, launch each arm as its own run (RUN=<cell><arm>, ARMS="a|<model>|<env>") and pair them
in the readout. 🔴 RE-HIT 10-14 (run `rs`, resolver A/B, ~$6 + a morning lost) by a session that had NOT loaded this skill — the wrapper's
`launch` now REFUSES a multi-arm launch whose per-arm INVs conflict (CONFLICT check); the rule stands until the module takes `invariants_by_arm`.
Post-run: `post-run-drain.sh` (bashrc hook, flock'd) completes a queued cell when every planned task is banked AND bench_run.state for the
queue's RUN ID is complete/halted (10-08: the guard had matched the STORE name since 10-03 and never found a run → 4 premature harvests; the
legacy "box gone" heuristic is RETIRED — `__not_found__` / `__unreachable__` = WAIT; when the hook shell's CLI misbehaves, run it from a real shell) → `cell-post-adjudicate.sh` (adjudicate → distill → curate → doctrine-mine ≥20 sessions → lake ingest → STDB sync). MiMo-40 readout
vs gpt6a + the Flash bar: `HF_TOKEN=… python3 .bench/mimo/adjudicate-g6.py tb2-<run>-a …`.
Keys: `agent_encrypted_secrets` `bench:<provider>` via ADMIN › Inference › Bench keys (list of your keys / Add new Bench key from SECRETS /
Refresh = rotate / Remove; the bench id comes from the SECRETS entry's own naming, huggingface → hf). A rotation elsewhere must be re-synced
there (10-03: stale bench:deepseek → box preflight rc3, nothing launched). Any provider id is accepted (bench_provider_ok).
Verified live 10-03: p2live-20261003 (boot, heartbeat, repl-crash survival, halt→reap) · p2l2 (row POST, lever audit PASS, version_pin +
effective_config PASS, ingest idempotent) · g6pro2/g6rs2 (mixed OpenAI+DeepSeek keys, gates PASS, boot-fail self-heal).
TTL (`TTL_H`, per host) is a HARD STOP for the RUN: host_watch reaps the box and HALTS the run (published 10:30 AM PT 10-03; before that the
arm was re-placed on a fresh box and the work restarted — p2l2). Size TTL_H to the longest task, not to "about an hour".
🔴 NEVER adjudicate a live STDB run from the repl (10-03 fsppfj): post-run-drain's old "box-gone" heuristic harvested a running STDB cell at
8/40 → lake-drain → benchStoreIngest --adjudicate → `adjudicate_bench_run` marked the RUN complete → host_watch reaped the box mid-run.
Three guards now: post-run-drain reads bench_run.state (running/adjudicating = WAIT); benchStoreIngest skips live runs; the module's
`adjudicate_bench_run` refuses a run with LIVE hosts (event `adjudication_refused`, published 10-04 6:55 PM PT). The control plane
(host_watch P3) is the ONLY completer of a Vast run.
Traps: a box in RU/CN/… → OpenAI 403 → preflight rc3 (GEO_EXCLUDE); a box stuck `created` >25 min → host_watch destroys + bans (do not wait by
hand); `spacetimedb-publish-*.sh publish` ships the EXISTING wasm — always `cargo build --target wasm32-unknown-unknown --release` first; the
budget job is KEY-WIDE (§7.12); DS V4 Pro pricing = $0.66 miss / $0.022 hit / $1.98 out per M off-peak (×2 peak) — read the page, never memory;
long commands run in the background; monitors poll at the signal's rate (no 5-min polls on multi-hour single tasks, no baseline events).

## 3. Gates (the launch invariant)
`launch_bench_run` needs every `required_gates` entry (default `population,mechanism_fire`; `REQUIRED_GATES=population`
for a pilot) recorded PASSED via `record_bench_gate`. `launch` also wires three gatecheck JOBS that record into
`bench_gate` after launch: `version_pin` (the pin string), `sweep` (destroys running bench instances no live lane
claims; report `{running,destroyed}`), `effective_config` (reads each arm store's latest row `effective_config` and
asserts the INV: `{KEY:{effective,source:env|active}}`; ABSENT key = FAIL = **halts the run**; fires 120 s after the
first row lands in EVERY arm; stays `pending` (no row) until then; DISABLES itself after any decisive result).
🔴 The INV is built from COMMON + EXTRA_COMMON + the cell/arm lever tokens, filtered to keys the PINNED harness REPORTS
(`effcfg_src_for_pin` reads `git -C nexus-cortex-extracted show v<pin>:packages/core/src/config/effectiveConfig.ts`;
unreported keys are WARNED and dropped — they are still delivered, proven by the passthrough guard). Fix a live gate with
`upsert_bench_job gc-effcfg-<run> {some:<run>} gatecheck {some:120} {some:45} true {some:<args_json>}` and READ
`args_json`+`enabled` back.

## 4. Touch-free monitoring (the ONLY allowed reads while lanes run)
- **Progress = the STORES**: `curl -sfL https://huggingface.co/datasets/<repo>/resolve/main/results-s<i>.jsonl` per shard
  (enumerate `results*.jsonl` via the tree API). Task rows have `"task"`; boot rows are `__run_config__s<i>` and carry
  `arm: <run>:<arm>` — ONE per supervisor boot.
- **Instances = CF API**: `GET …/containers/applications/a03a316f-ccd3-4b91-b13e-aaa2fb07ae70` → `.result.health.instances`
  `{active,starting,healthy,…}`; `…/instances` → per-instance `.name` (`nexus-cortex-cortex-admin-<session>`) +
  `.status.state` (`running|inactive`). The dashboard lags; the API is truth.
- **Control plane = STDB**: `SELECT run_id, state FROM bench_run`; `SELECT status FROM bench_lane WHERE run_id='…'`;
  `SELECT job_id, enabled, run_count, last_fired_at FROM bench_job`; `SELECT * FROM bench_gate`; `spacetime logs
  nexus-nexus-cortex -n 300 | grep <run>` (every line is stamped `tick_bench_scheduler`).
- **Worker = leases**: `GET https://cortex.spitfire-products.com/admin/bench/leases` (admin token `.bench/.admin-token`):
  `doName`, `beats`, `expiresAt` per lane — `beats` climbing proves keepalive + lease renewal.
- **Monitor template — QUIET (operator rule 2026-09-10: monitor events must not eat the session's context):** poll every
  600 s; emit ONE line only when the run STATE changes or the banked row count crosses a 5-row milestone
  (`key="$state|$((rows/5))"`), plus NEW module-log lines matching `halt|FAILED|budget|adjudicat|→ dead` only; exit on a
  terminal state with the final row count. Do NOT emit per-tick lane-status tables, placement/reconcile/remap lines, CF
  counts or balance — the spine handles those; read them on demand (`status` mode, `spacetime logs … | grep <run>`) when
  a milestone or failure line makes you look. Reference shape: the cell-m-r1 quiet monitor (session 2026-09-10 23:40Z).
  A Monitor dies with the session — on resume, re-arm it; nothing else needs re-arming.
- **Mentor A/B adjudication = `.bench/cells/mentor-delivery.py --arm <label>=<repo> …`** (touch-free): per arm, every
  mentor event by `mentor.deliveredBy` (thinking-on | thinking-off | thinking-off-retry | none; pre-4.106.1 rows inferred
  from content) with latency med/p90, reasoningTokens med/p90, maxTokensSent, finishReason, truncated / retriedThinkingOff /
  abortedFirstCall counts, resolver parsed/blank/abstained/failOpen, loop-block triggers, per-task rewards. Read DELIVERY
  first; pass direction last.
- 🔴 NEVER `/debug/exec` a live lane (crash-cycles it), NEVER run `tb2-reaper.sh` as monitoring, NEVER re-`launch`/`pilot`
  by hand to "see" a lane. If a lane is stuck, the bug is in a handler or a worker route — fix THAT.

## 5. What the spine does by itself (expected timings — do not intervene inside them)
| event | mechanism | when |
|---|---|---|
| lanes placed | fanout job → one paced `/admin/bench/launch` (8/15 s) | the tick after `launch` (≤60 s) |
| `placing → running` | keepalive tick probe finds the supervisor (`ps … grep -c`), beats, renews lease | first tick ≥ boot (≤300 s) |
| first task row | cold start ~5–7 min (per-task container `npm i nexus-cortex@<pin>`) + task | fast tasks ~5 min post-fanout |
| unbooted lane re-fired | placement: `placing` + never beaten + `now − last_placed_at ≥ 600 s` → re-place, `place_attempts++` | ~10–12 min after placement |
| fresh-session remap (placement) | `place_attempts ≥ 2` → `<lane>x<gen>`, old DO destroyed census-gated (else lease released) | 2nd re-fire (~20 min) |
| wedge remap (watchdog/tick) | `TICK_FAILS_REMAP 2` consecutive probe failures outside grace → `wedged x2 → remapped …x1 (placed=true)` | ~10 min of failed probes |
| give up | `place_attempts ≥ PLACE_MAX_ATTEMPTS 5` → `dead` → reaper | ~50 min |
| complete | supervisor prints `COMPLETE` → beat → `complete_pending` → reconcile (600 s) store-slice check → `complete` → reaper destroys | ≤10 min after the last row |
| budget halt | budget job at `cap_usd` / `min_balance_usd` (live DeepSeek balance) | 180 s |
| run terminal | every lane terminal → `adjudicating` (P5) | automatic |
| worker fail-safe | warden cron destroys any lane whose lease is 90 min stale (only if STDB stopped beating) | 5-min cron |

## 6. Diagnosis kit (3 reads, no touch)
1. **Run-tagged boot rows per shard**: no `__run_config__` for THIS run's tag after ~7 min while siblings have one =
   the launch exec returned 200 but the supervisor never started → wait for the placement re-fire/remap; if the same
   DO name fails 3× the fresh session fixes it (proven: `x1` booted in <60 s). Two boot rows = booted twice.
2. **Probe error TEXT** (`spacetime logs … | grep 'probe failed'`): `CommandError … grep -c` = container up, no supervisor
   (never booted OR instant-complete exit); `SandboxError: HTTP 500` = container-side failure; `operation timed out` =
   busy/unreachable (watchdog handles); `ENOENT … watch /tmp/session-…` = cold-start race (retried by the worker).
3. **Leases + CF names**: a lease `doName` WITHOUT the session (bare `cortex-admin`) or CF names missing
   `cortex-admin-<lane>` = the LANE-NAME collapse (§7).
Instant-complete lanes (slice already banked) exit before the first probe → look "unbooted" → re-fired up to 5× → `dead`
(reconcile only resolves lanes that BEAT `COMPLETE`). Costs cold starts, not correctness. Backlog HB-PLACEMENT ⑥b.

## 7. Laws and traps (each bit a real run on 2026-09-10)
1. **LANE-NAME LAW**: worker `sessionIdFor` keeps `-<sub>` only if `^[A-Za-z0-9_-]{1,24}$`; longer names silently
   collapse EVERY lane into the bare `cortex-admin` DO (cell-m-p1: 32 lanes → 1 container, 0 rows). Base names ≤22
   (P14 appends `x<gen>`). Enforced: rig `lane_name_guard` + emitter exit; ARMS field 1 short (`flash-none`), field 3
   long (store label). Worker 400 on invalid names is STAGED in tree, undeployed.
2. **GATE-VS-PIN**: assert only keys the PINNED report contains (cell-m-p2 halted 6 min in on `HELPER_MODEL_ID: ABSENT`).
   A lever you want gate-asserted must be in `effectiveConfig.ts` BEFORE the release you pin.
3. **Declarative 200 ≠ placed**: `placeOne` exhausts 4 retries silently; "declaratively placed N" describes the call.
   Tell = §6.1. Backlog HB-PLACEMENT ⑥ (per-lane results).
4. **A gatecheck job with EMPTY args records `unknown gate` FAILED and disables itself** (does NOT halt) — after any
   `upsert_bench_job`, read `args_json` back; an unparsable input once wrote empty args.
5. **`seed` force-pushes** — never between attempts on the same stores.
6. **`spacetime sql`**: columns are the Rust structs; `Option<String>` columns reject `WHERE col='x'` → `SELECT *` + grep;
   `SELECT * FROM bench_job` can exceed 120 s → select columns; never invent column names.
7. **Two control planes over one substrate kill each other**: the repl guardian reaper reads `bench_lane` as LIVE and
   fails closed (fixed 09-10b); anything else that destroys instances must read `bench_lane` first.
8. **Patch scripts**: a heredoc whose body contains the terminator (`PY`) truncates silently — use a scratchpad file.
9. **FANOUT WAVE SIZE is byte-bound, not lane-bound** (cell-n-r1, 130 lanes × 1.63 KB): `spacetime call` passes `args_json` as ONE
   argv string (Linux MAX_ARG_STRLEN 128 KB). A fixed 80-lane chunk overflows as soon as the lane cmd grows (more lever tokens).
   The launcher now sizes chunks from the actual per-lane bytes against a 110 KB ceiling and prints the plan
   (`[launch] wave chunking: N lanes, B/lane → k jobs of ≤c`); `fanout-dry`'s "OVER-128KB" on the WHOLE wave is expected for
   >~70 lanes — read the chunk line at launch instead.
10. **A REQUEUE IS A RUN** (cell-n-r2, 2026-09-11): a run created from `FANOUT_DUMP` + a hand `launch_bench_run` gets ONLY the
   fanout job — no keepalive/placement/watchdog/reconcile/budget — so its lanes sit `placing` forever with expired leases and
   nothing reconciles or reaps them (the in-container supervisors still banked 3/4 rows). Requeues go through the rig
   `launch` mode like any run; if you ever hand-build one, read `bench_job` back and expect the 6 spine jobs, not 1.
11. **complete_short ≠ "rows lost by the spine"** (cell-n-r5): the supervisor's row never reached the store (local-only commit);
   the spine's re-placement re-runs the task on the same wedged clone up to PLACE_MAX_ATTEMPTS and never recovers it. Since the
   2026-09-11 supervisor (reconcile-by-rows), a lane that cannot push prints `INCOMPLETE … UNPUSHED:` instead of COMPLETE — the
   tick then keeps it `running` until the watchdog; halt the run if `UNPUSHED` shows up in several `log_tail`s (store/token problem).

12. **THE BUDGET CAP IS KEY-WIDE, NOT RUN-WIDE** (cell-n-d2, 2026-09-11 3:13 PM PT): the budget job computes `spent = provider_balance_start −
   balance` from the DeepSeek key's live balance (`bench_scheduler.rs:972`, `budget()`), so every run sharing the key charges every other run's
   cap. cell-n-d2 (`BUDGET_CAP_USD=5`, 13 lanes) was halted at "spent 5.07" while tb21-k5-n5 and tb21-k5-dsh3 were burning on the same key —
   its own rows cost ~$1.5; the last 2 lanes (dna-assembly, train-fasttext) were killed mid-task. RULE: `BUDGET_CAP_USD` must cover the
   AGGREGATE key burn expected during the run's lifetime (sum of every concurrent run's cost), or run probes alone. Fix owed: per-run cost from
   banked `cost_usd` rows (or a per-run key) — backlog HB-BUDGET-KEYWIDE.
### Trap 13 (2026-10-11, R250 sibling grading) — a chain cell now runs EXTRA restore-only trials after each task
`run_siblings()` launches one Harbor trial per non-picked attempt after the main row banks (zero model $, box minutes). The STDB host
rows only see the main `done` row; `siblings-s<idx>.jsonl` + `attempts/<task>.bundle` live in the HF store (ingest ignores them). Expect
a lane to stay busy ~5–15 min after a chained task's row posts; size TTL_H for it. Readout: `.bench/vm/sibling-oracle.py <store>`.

## 8. Wake / resume protocol for an STDB run (short by design)
1. Read the resume memory for the run id + arms + stores. 2. `SELECT run_id, state FROM bench_run`; lane status counts;
rows per arm (stores). 3. Re-arm the Monitor (§4). 4. Do NOT relaunch, re-place, or touch a lane. That is all — the run
survived your absence (verified: p3 remapped lanes at 19:52Z/20:03Z with no session alive).

## 9. Halt, adjudicate, close
- Emergency stop: `spacetime call nexus-nexus-cortex halt_bench_run '"<run>"'` → jobs disabled (reaper kept), lanes
  `kill_requested`, reaper destroys running ones / releases the rest (census-gated, no phantom destroys).
- At `adjudicating`: `python3 .bench/cells/adjudicate-cell.py --run <run> --lever <KEY> --kinds
  lift_plan,endturn_resolver,deadline_exit_mentor,loop_tool_block --arm <label>=<hf-org>/tb2-<sfx>-<store_label> …
  --out omniclaude-v4/.cortex/bench/r-<run>-<date>.md` (mean + Wilson CI per arm, mechanism fires per row from
  `trajectories/<task>.decisions.jsonl`, `mentor:{model,thinking,effort}` wire proof per arm); then distill
  (`scripts/tb2-distill.py`), doctrine-mine, `record_bench_gate` + `adjudicate_bench_run`, master `.env` LEDGER lines
  (never `.env.defaults`), skill delta. Classification rules (empty-fail, budget_frac, flips vs baseline) = harbor-bench.
- Verify teardown: CF `active` = 0 bench instances; `GET /admin/bench/leases` empty for the run.

## 10. Open items (2026-10-03 9:45 AM PT)
- Arm packing: several arms per host (host_place/host_watch groups) — wanted before the TB4 validation cells (A: scope A/B + R208-R214; B: MiMo SCOPE).
- P3 completion chain PROVEN LIVE 10-03 10:06/10:12 AM PT on g6pro2/g6rs2 (complete → ingest +0 → adjudicate_core → harness_bench_run verdict=auto → host_reap).
- `OPENAI_API_MODE` is not in the harness effective-config report → delivered by the forward gate, not gate-asserted (moot: GPT-6 cards pin Responses).
- Scrubber: `_bank_scrubbed` copies files > 2 MB unscrubbed (every key class) — fix before any public store.
## 10a. Open items carried from 2026-09-10
- HB-PLACEMENT ⑥ per-lane launch results; ⑥b reconcile checks `placing` slices (instant-complete livelock).
- Worker `/admin/bench/launch` 400-on-invalid-name: staged, undeployed. `HELPER_MODEL_ID` in the report: tree, ships 4.106.
- Retire gate for the repl scripts: a deliberate repl kill mid-run on a REAL run is still owed (p3 survived a session
  restart, not a repl restart).
- CF billing rates in the monitor are marked VERIFY; reconcile banked cost vs the DeepSeek dashboard before quoting.

## §2d Rules banked 2026-10-05/06 (structure over prose — each is enforced somewhere, the pointer says where)
1. **BUDGET_CAP_USD is PER RUN since module commit 9522abafb (10-05):** the budget job sums the run's own `bench_task_result.cost_usd`; the
   `min_balance_usd` floor stays key-wide. Before that, four concurrent runs halted two of them at "$25" on $6 of own spend (t4r/t4s 10-04).
2. **The planner's first-call clock:** `CORTEX_LIFT_PLAN_TIMEOUT_MS` reaches the helper's first-call abort only from nexus-cortex 4.124.60
   (0.6 × max(lever, thinking table)); on older pins use `CORTEX_MENTOR_THINKING_TIMEOUT_MS`. Verify in the lift_plan events:
   `firstCallTimeoutMs` must equal 0.6 × the lever, or the lever did not land (10-05 cap cell shipped with 180,000 everywhere).
3. **DeepSeek output cap:** cards carry 393,216 since 4.124.58 and the gateway sends the card on every call. A LOWER cap is a lever
   (`CORTEX_OUTPUT_CAP_TOKENS`), never a card edit. 65,536 reproduces the pre-10-05 behaviour as a control.
4. **Walls under a high cap are degenerate loops, not thinking** (40/40 at 393K; retries re-loop from the first tokens). The non-streaming bound is
   `CORTEX_WALL_RETRY_LADDER=65536,16384` + `CORTEX_WALL_FORCE_ACTION_AT=2` (4.124.60, dark). Mechanism evidence = `wall_retry_ladder` events
   {wallIndex, cap, forceAction}; a laddered arm with zero such events did not fire.
5. **Harbor ≥ 0.24 refuses tasks that ship skills unless the agent declares `capabilities.skills=True`** — the adapter does since 10-06 and stages
   `skills_dir` into `$HOME/.cortex/skills` (log line `[adapter] skills staged`). cumulative-layout-shift was lost in all four 10-05 arms this way.
6. **Fixed vocabulary for arms (operator 10-05):** bundle = the c23 eight levers; rules = bundle + R208–R214; scope = bundle + SCOPE=task;
   judge = Flash as judge; old caps = 65K/20K/180 s; new caps = 393K / planner 60K+6K / 600 s. Never rename a config mid-conversation.
7. **No launch / halt / config change without the operator's explicit go to THAT action** (10-05). Prepare envs, verify with check-bundle, stop.
8. **Two writers on the workspace git race for `index.lock`:** a background chain that commits must not overlap a foreground commit — serialize
9. **A REFUSED adjudication is never retried (R242, 10-08 t4k) — FIXED 10-09 (host_watch retries every tick once no host is live; the by-hand recipe below remains the fallback):** host_watch auto-adjudicates only runs in state `running`; when `gc-effcfg-<run>` exhausted its window (45 × 120 s = 90 min) before the first task row (108 min) the gate was never recorded, adjudicate_core REFUSED, and the run sat `adjudicating` for 5.5 h with its box reaped. The rig now sets gatecheck `max_runs = TTL_H*30`. Recovery by hand: verify every invariant in the job's `args_json` against the banked rows' `effective_config` offline → `record_bench_gate <run> effective_config true true {some:<note json>}` → `adjudicate_bench_run <run> <benchmark_id EXACTLY as bench_run has it> {some:vast} {some:"auto: … retried by hand"} {none:[]} {none:[]} {none:[]} {some:auto} false` (the auto path's own args; upsert by result_id, so a wrong benchmark_id is fixed by re-calling).
10. **`harness_bench_run` rows were INFLATED (R243) — FIXED 10-09: the real cause was the lake ingest posting the STORE label as the arm (`t4h:t4h-a`) beside the box's bench_arm id (`t4h:a`); the module now canonicalizes arm ids on upsert and adjudicate_core dedups by (task, replicate); t4h/t4k re-adjudicated to 14 tasks each. Historical note:** the in-container supervisor's reconcile rewrite copies every remote row into every `results-s<N>.jsonl`, and `ingest_run` inserts each shard file's copy → t4h read 28 tasks / 18 pass / $22.25 for a 14-task run (truth 14 / 9 / $11.13). Until ingest dedups by (run, task, replicate), the readout's unique-row numbers (dedup by task) are the truth and no STDB verdict row from such a run is publishable as-is.
12. **The repl-side harvest trigger runs DETACHED IN TMUX, never as a Bash-tool background task** (10-09: four watchers died with four session crashes). `tmux new-session -d -s watch-<tag> "cd $WORKSPACE && RUNS='<run> <run>' bash .bench/watch-stdb-runs.sh"` — polls bench_run.state every 1800 s, drains when all are terminal; log `.bench/vm/logs/watch-<tag>.log`; `tmux ls` to see it; a REPL restart kills tmux too → re-create the session (nothing else; the control plane owns the run).
11. **Fixes are filed in three surfaces the same session** (Rxx line + def-hex backlog row + cell ledger) and mirrored with `syncDeficiencyPool.ts --track` right after the lake drain.
   (poll for the lock + `pgrep -x git`) or let the chain own all commits (lost a chain commit 10-06, recovered by hand).


## DELTA 2026-10-15 — host_place RE-RENTED FINISHED SHARD GROUPS (rsb3): "covered" must include self-reaped DONE hosts
A box whose shards all completed prints COMPLETE, its self-reaper destroys it (~23 min later), host_watch marks it Gone → `reaped`, and
`host_place` (which counted only LIVE hosts as covering a group) rented a fresh box for the finished group every ~30 min — 11 boxes between
7 PM and 11:30 PM PT (each booted, found its slice banked, printed COMPLETE, self-reaped; ~$1.5, no data harm). Signature: `[bench host_place]
… shards [3]` repeating for the same group while the store already holds every row of that shard; `bench_host` rows `reaped` with ~$0.1 cost
and `heartbeat_json.shards.<n>.state == complete`. FIX (commit 62ee84a142, `bv::host_covers`): a host covers its group when LIVE **or** its last
heartbeat satisfies `heartbeat_host_done` — publish owner-gated. MITIGATION on a live run without a publish: `set_bench_job_enabled
'"host_place-<run>"' false` once every remaining group has a live host (host_watch/reap/ingest/budget keep running → completion still auto);
re-enable if a working box dies. Read `bench_host.heartbeat_json` before any such toggle.

## DELTA 2026-10-15b — P1 of the feature-flag parity plan: a FEATURE PAYLOAD per arm (R262 in the bench), commit 8343cc97da
`ARMS="label|model|envfile|features.json"` (4th field optional; a GrowthBook-format payload = `{"features":{KEY:{defaultValue,rules}}}`, e.g. from
`omniclaude-v4/config/features.json` with the arm's rules edited in). What rides where: `seed` uploads it to the store as `features.json` and stamps
`CORTEX_FEATURES_FILE=features.json` into the arm env (so the adapter forward gate sees the key); `bootstrap-executor.sh` copies `features*.json` into
`/root/pkgs/features/` (served by the box package cache on :8765); the adapter (allowlist + install phase) curls it into the task container at
`/usr/local/share/cortex-features.json` and rewrites the key to that path (a miss logs `WARN: features payload … not served` and leaves NO payload);
the library applies it at launch and reports `CORTEX_FEATURES_HASH`; the supervisor banks `features_hash` (from `/health/config.featuresHash`) in
`metrics_json`; `inv_for` asserts `CORTEX_FEATURES_HASH:{effective:<sha256 via core dist featurePayloadHash>,source:env}` in the effective_config gate
and skips the FILE/JSON path keys (the lever audit skips them too). Engagement evidence per arm: `feature_exposure` events in decisions.jsonl +
`features_hash` on every row == the gate's hash. NOT YET: `bench_run.features_hash` / `bench_arm.feature_rules_json` columns and grouping by
`variation` in adjudicate_core (design §4.4; the metrics_json carrier covers the first cells); the first P1 cell = a 2-task mechanism-fire pilot
(payload forcing one dark lever on, e.g. CORTEX_ENDTURN_RESOLVER) before any A/B spend.

## DELTA 2026-10-16 — per-SHARD coverage: a boot-dead shard is re-placed, never counted done (published 3:55 PM PT; commits c5367ce8b7 +)
p1pilot: shard 0's supervisor died at boot (`FATAL: cannot reach the durable Dataset store`, a 30-s HF blip), its heartbeat read `fatal`,
`heartbeat_host_done` treated `fatal` as terminal → the run completed at 1/2 tasks, was adjudicated, and the live host (still serving shard 1)
made the whole group look covered so nothing re-rented shard 0. Now (`bench_vast.rs`): `heartbeat_done_shards` counts complete | incomplete |
fatal-WITH-work only; `heartbeat_boot_dead_shards` = fatal with done=0; `host_covered_shards` = a LIVE host's group minus its boot-dead shards, a
dead host's finished shards; `uncovered_shard_groups` chunks the missing shards per_host for renting; host_place and the P3 completion use
them (`host_covers` dropped). Expect: a `[bench host_place] … shards [<n>]` line for the dead shard while the original box keeps running, and
completion only when every shard was graded by some host. The supervisor also retries the boot store reach 6×60 s (the trigger).

## TTL EXTENSION mid-run (first done 5:25 AM PT 2026-10-19, t4w2 b/c +16 h)
TTL is enforced TWICE: the controller (`bench_host.ttl_at` → host_watch `Destroy("ttl")` → host reaped → run HALTED) and the box's own
`self-reaper.sh <iid> <hours>` (its OWN clock; `/root/reaper-hold` suspends only the idle rule, never the TTL). Extend BOTH, in this order:
1. Box first (no publish needed): upload a tiny script and run it — never put `self-reaper.sh` in the ssh command line itself, `pkill -f` would
   kill the ssh shell: `printf '...pkill -f "self-reape[r].sh"; setsid nohup bash /root/self-reaper.sh "$1" "$2" &...' | ssh … 'cat > /root/rearm-reaper.sh'`
   then `ssh … 'bash /root/rearm-reaper.sh <iid> <hours>'`; hours = (new controller TTL − now) + 1 so the controller fires first. Direct SSH route =
   `vastai ssh-url <iid>` (public ip + mapped port 22) with `.ssh/id_ed25519`; the ssh5/ssh9 proxy ports refuse.
2. Controller: `spacetime call nexus-nexus-cortex extend_bench_host_ttl '"<host_id>"' <ttl_at_ms> -s maincloud` (admin-gated; future only; refuses
   reaped/failed). Verify `SELECT host_id, ttl_at FROM bench_host`. A publish keeps `bench_scheduler_job` (verified 1 row before/after) — re-arm with
   `arm_bench_scheduler` only if it is 0.
TRAP (10-19): workspace `.cargo/bin` was EMPTY (rustup proxies lost) → the publish script silently built with /usr/bin rustc 1.88 and failed on the
MSRV; fix = symlink cargo/rustc/rustdoc from `.rustup/toolchains/1.93.0-x86_64-unknown-linux-gnu/bin` into `.cargo/bin` (GLIBC_TUNABLES still required).

## DELTA 2026-10-20 — the control plane generalises: a PROXY POOL is a bench run with no tasks (schema + rules)
Design `nexus-terminal/docs/research/vast-proxy-pool-design-2026-10-20.md`. `bench_run` `proxy-pool`; one `bench_arm` per country (arm_id = ISO
code; shard_n = pool slots; lanes_per_host 1; offer_filter_json `num_gpus eq 0, cpu_cores_effective gte 2, inet_up gte 50, rentable, vms_enabled,
dph_total lte 0.03, geolocation in [cc]` — same grammar as the cells, `in` beside `notin`; onstart = bootstrap-proxy.sh; box env PROXY_SSH_PUBKEY
(public), host_ttl_hours 24; NO HF store, NO provider secrets on the box). Unchanged: host_place/pick_offer (banned+busy), host_watch (TTL, boot-dead
ban, cost), host_reap, bench_host_heartbeat (box token), bench_machine_ban, extend_bench_host_ttl. ADDITIVE schema (Option<T>, appended):
`bench_host.ssh_host, ssh_port` (from the Vast instance record via parse_instance), `egress_ip, net_class` (from the heartbeat
`{phase:"proxy", egress_ip, asn, asn_org, net_class, tunnels, up_mbps}`). NEW RULE in host_watch: run_id starting `proxy-` and net_class
`datacenter` → state failed + ban_vast_machine 30 d (host_place re-rents); `unknown` is never picked. Worker reads `bench_host` over the /sql
path it already uses for `browser_mcp_keys` (60-s KV cache); picks running + country + class ∈ {residential, isp} + fewest tunnels. Per-key
policy = `browser_mcp_keys.proxy_allowed / proxy_daily_seconds` (platform module, appended Options). Publish = owner gate; code lands dark.
Gateway concurrency test method (from the SpacetimeDB benchmark + our 06-17 restore memory): N connections × D in-flight; mean ± sd + p50/p99;
30-s warm-up, ≥3 repeats; contention = one box vs spread; count end-to-end (bytes in the browser) and raw (SOCKS) separately; disclose placement.

## REFERENCE 2026-10-20 — the SpacetimeDB concurrency benchmark, catalogued (operator ask; for any future STDB throughput question)
**Vendor numbers (spacetimedb.com/blog/benchmarking, corrected May 2026; the March 2026 "100K+ TPS" claim was RETRACTED for harness bugs):**
SpacetimeDB Standalone on one Intel 14900K (24 vCPU), server + DB colocated: **303,920 ± 4,712 TPS contended (α=1.5) / 279,025 ± 4,763
uncontended (α=0)**; earlier Rust-client run 265,541 ± 940. Same harness: Bun+Postgres 10,730 / 2,773; Node+Postgres 9,905 / 961; Node+SQLite
3,122 / 3,188; Convex 1,140 / 127; CockroachDB (5-node GCP) 4,253 / DNF. Workload = account-to-account transfers, counted only when persisted.
**Method:** 64 clients (384 PlanetScale HA, 320 CRDB); **up to 40 requests in flight per client (pipelining) for STDB** — competitors got none
in the headline run (giving them 40-deep changed throughput little but raised p50 sharply); no client batching; 5-minute windows after a 30-s
warm-up; throughput = mean ± sd; latency p50/p99; **Little's law (mean latency ≈ in-flight ÷ throughput) matched the measured p50s**;
Postgres pool = 2× DB cores, max_connections 100; no PgBouncer; reproduction `pnpm run bench test-1 --seconds 300 --connectors <backend>`.
**The five confessed faults (the checklist for OUR benches too):** asymmetric pipelining (16,384 in flight on one side), a test whose UPDATEs
never executed (SQLite), client-language mismatch (Rust vs TS), undisclosed warm-up, undisclosed placement/replication (original numbers came
from a replicated Cloud deployment, not Standalone; cloud AZ names are not physical). Fixed in-flight counts make latency climb once throughput
saturates — report both or report nothing.
**Our own measurements (memory `nexus-autoresearch-mcp-keysystem`, lattice restore 06-17):** HTTP `/call` per row = 183 rows/s (one txn/commit
per row, fsync-bound); batch-1000 at concurrency 8 = 4,212 rows/s (23×); concurrency 16 × batch 1000 CRASHED a local `spacetime start` on
per-request REMOTE JWT validation (the auth path, not the data path) → bulk work uses a local identity or concurrency ≤ 8; identity-keyed tables
restore per row. The vendor figure is SERVER capacity over the WebSocket SDK with pipelined calls — "in the pipe" — not HTTP batching "on the wire".
**Implications for this control plane:** the scheduler's one-tick-per-60-s reducer fan-out is nowhere near these limits; the costs that matter are
per-request auth, per-row commits (batch), and confirmed reads (fsync before delivery — enable only for financial/critical subscriptions).

## DELTA 2026-10-20b — proxy pool P0 BUILT (module code in tree; publish = owner gate)
`bench_host` + `ssh_host, ssh_port, egress_ip, net_class` (Option, `#[default]`, at the END); `parse_instance` reads `ssh_host/ssh_port/public_ipaddr`;
`bench_vast.rs` `is_proxy_run` / `parse_proxy_heartbeat` / `proxy_reject_reason` / `proxy_arm_country` (tests); host_watch: a RUNNING host of a `proxy-*` run
is judged every tick (datacenter → now; unknown / no heartbeat / sshd down → after 10 min; country ≠ arm → now) through the BootFailed path (destroy +
failed + 30-day machine ban, host_place re-rents the slot); a proxy host's TTL never halts the run (rolling refresh); the P3 completion loop skips proxy
runs; the heartbeat reducer fills `egress_ip/net_class` from a `phase:"proxy"` heartbeat. `cargo test --lib` 1083 passed. Rig `.bench/proxy/stdb-proxy-pool.sh`
(the arm's onstart EMBEDS bootstrap-proxy.sh + stdb-box-client.sh + self-reaper.sh as a base64 tarball — no HF store on a pool box; box env is only the
worker's PUBLIC key, named `PROXY_SSH_AUTHORIZED` because `set_bench_arm_vast` refuses literals whose name contains KEY/TOKEN/SECRET). Read the module log
after `create` exactly as for a cell. Pilot checks owed: Vast's accepted onstart size (13.6 KB), `geolocation in [CC]` on the search API, `-D` through the
ssh gateway, classifier precision (heartbeat `asn_org`).
