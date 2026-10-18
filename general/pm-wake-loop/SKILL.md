---
name: pm-wake-loop
description: The WAKE PROTOCOL for a PM agent resuming a long-horizon mission after sleep — orient from the mission ledger, rehydrate memory cheap-to-deep, heal the worker fleet with idempotent relaunchers, adjudicate newly banked results, act within guardrails, record, re-arm, sleep. Load at the START of any session (scheduled wake, watchdog tick, or manual resume) that owns an ongoing mission with durable workers. Design: nexus-terminal/modules/database-ai/RECURSIVE_PM_WAKE_LOOP_DESIGN.md.
triggers:
  - wake
  - mission
  - resume the loop
  - heartbeat
  - pm loop
---

# pm-wake-loop — the wake protocol

You are a PM waking from sleep over a long-horizon mission. Your session is disposable; the
MISSION is not. Everything you need to orient lives in durable stores — never reconstruct
mission state from your own head (retrieve-before-reconstruct).

## The protocol (execute in order; every step is idempotent)

1. **READ THE MISSION LEDGER** (the PM's own arm-store — location listed in memory /
   `MEMORY.md` hot index; current: HF Dataset `<hf-org>/pm-mission-ledger`, fresh-clone it —
   never reuse a clone). Files: `mission.md` (goal, phase, constraints), `roster.json` (worker
   fleet: sessions, store repos, relaunch envs, monitor specs), `decisions.jsonl` (append-only
   adjudication log — read the tail), `open-questions.md` (operator-gated items pending).
   Orient from the LEDGER ALONE; memory and canon enrich, never carry, mission state.

2. **REHYDRATE, cheap-to-deep, only as needed** (the knowledge-plane curriculum):
   memory hot index → relevant skills (harbor-bench for bench fleets, canon-store, autoresearch)
   → per-window CORTEX.md for any SPA surface the mission touches → `canon graph`/`artifacts`
   for relations/capabilities → canon transcripts (`cortex canon list/pull`, grep the store)
   only when depth demands.

3. **HEAL THE FLEET** — run EVERY roster entry's idempotent relauncher (no-op if alive,
   resume if dead; safe to fire blind). A wedged compute session (exec bridge errors) → move
   the worker to a FRESH session name per the roster's env pattern; verify with a nonce.
   Restart session-scoped monitors listed in the roster (they died with the last session).

4. **ADJUDICATE** — fresh-clone worker stores; batch-judge rows banked since
   `decisions.jsonl`'s last entry. Compare container-local ledgers vs remote when an arm looks
   quiet (silence is never evidence of health; remote-behind-local = banking failure).
   Classify results honestly (pass / genuine miss / plumbing — see harbor-bench result
   classification). Run the trace-distiller (`scripts/tb2-distill.py`) when trajectories are
   part of the mission.

5. **ACT within guardrails** — adjust/launch/stop workers; queue gated autoresearch campaigns
   for improvement candidates. HARD GATES (never cross without the operator): deploys of
   published projects, STDB `--clear`, new recurring spend, security-posture changes,
   anything in `open-questions.md`. Cost-sensitive actions: state $ before spend; no
   auto-retry of failing GPU runs; batch adjudication — never serialize the session on a run.

6. **RECORD** — append every adjudication + action to `decisions.jsonl` (provenance: ts, what,
   why, evidence pointer); update `roster.json` if the fleet changed; move newly-gated items
   to `open-questions.md`; update memory anchors only for load-bearing facts. Push the ledger
   (verify by re-clone on any doubt).

7. **RE-ARM** — session-scoped monitors for this wake window (store-poll progress + watchdog
   ticks per roster); verify the next WAKE exists (scheduled agent / cron / STDB tick per the
   ledger's heartbeat spec). A PM that dies mid-wake loses at most one window — the next
   heartbeat replays this protocol.

8. **SLEEP** — end the turn with a one-paragraph state summary (what advanced, what's pending,
   what's gated). Do not linger polling; monitors wake you.

## Failure-mode inheritance (why this is reliable)
Ledger = single source of truth (monitor the STORE, never the compute). Waking = resume, not
refit. Relaunchers = always-safe. Caps above legitimate work. One writer per store. Provenance
on every row. If the ledger and reality disagree, trust neither — verify against the workers'
own banked state, then fix the ledger.

## Related
- Design + asset map: `nexus-terminal/modules/database-ai/RECURSIVE_PM_WAKE_LOOP_DESIGN.md`
- Durable-worker formula: harbor-bench skill §📐 · Memory rail: canon-store skill
- PM role doctrine: autoresearch skill (plan-gated, delegate, arbitrate holdout-verified)
