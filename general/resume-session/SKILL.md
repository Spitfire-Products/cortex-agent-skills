---
name: resume-session
description: Build and maintain the RESUME MEMORY — the one file a fresh context (post-compaction, new session, or a different agent) reads first to recover the FULL scope of a long session with no context loss — plus the project checkpoints and memory pointers behind it. Load this skill (1) whenever the context-pressure hook says the window is near full, (2) before any long autonomous/overnight stretch, (3) after every major milestone (release, run adjudicated, decision taken), (4) at the end of a session, and (5) IMMEDIATELY after a compaction or session change, to REBUILD context from the resume memory and its pointers. Covers the checkpoint template, what must be in it (skills to load, doc/ledger/memory pointers, runs in flight, work done, work outstanding, operator decisions pending), and how to recover a context gap from the primaries — the Claude JSONL session store and the canon-store session history + knowledge graph (skill canon-store) — instead of guessing.
---

# resume-session — checkpoints, resume memories, and context recovery

The resume memory is the contract between the agent that did the work and the agent that continues it. It lives in the
auto-memory directory (`$WORKSPACE/.claude/projects/-home-runner-workspace/memory/`) as
`session-resume-<YYYY-MM-DD>[suffix].md`, is indexed by ONE line in `MEMORY.md` under "🟢 Active work / resume points", and is
kept as a RUNNING checkpoint — not written once at the end. A summary produced by auto-compaction is lossy and drops fleet
breadth; the resume memory is the durable, agent-authored counterpart.

## 1. When this skill fires
| trigger | what you do |
|---|---|
| hook says `CONTEXT-PRESSURE` (≈85% / 92% of the window) | STOP new work; run §3 (write/refresh the resume memory NOW); then continue |
| hook says `POST-COMPACTION` / `SESSION-START (resume)` | run §4 (rebuild): read the resume memory FIRST, load the skills it names, verify live state against primaries |
| hook says `FRESH SESSION (startup/clear)` | do NOT run §4 (operator rule 2026-09-24: the wake protocol is for a continued context only); take the new request; read the entry-point memory only if the operator asks to continue prior work |
| before a long autonomous stretch (operator asleep / away) | §3 + write the operator's instructions VERBATIM into the memory (a "work order" block) |
| after a milestone (release shipped, run adjudicated, decision recorded) | §3 delta: update the state block, don't rewrite history |
| end of session | §3 + make sure MEMORY.md's line for it says "CURRENT ENTRY POINT" and supersedes the previous one |

## 2. What a resume memory MUST contain (the template)
Frontmatter: `name`, `description` (a one-paragraph state summary — this is what recall shows; make it the executive summary
with dates in PT), `metadata.type: project`. Then sections, newest state FIRST:
```
## 0. PROTOCOL — the ordered load list for a fresh context
   1. skills to load (by name, with WHY): resume-session (this), pm-wake-loop (if durable workers/missions are in flight),
      stdb-bench (control plane), harbor-bench (executor + history), canon-store (gap recovery), cortex (harness), any
      domain skill the outstanding work needs
   2. files to read, in order: this file's newest state block; the prior resume memory (if any) for traps; the ledgers
      (`omniclaude-v4/.cortex/bench/r-<run>-<date>.md`), design docs, work orders (`.bench/WORK-ORDER-*.md`)
   3. live-state reads (touch-free, read-only): what to query and what you expect (e.g. STDB `bench_run` states, balances,
      npm versions, monitors that should be re-armed)
## 0a. STATE <timestamp PT> — the current snapshot (one block per checkpoint, newest first; older blocks stay as history)
   - runs/jobs in flight: id, where (STDB run id, store, monitor task id), expected end time, what to do at terminal
   - what is DONE this session (with commit hashes / versions / ledger paths)
   - what is OUTSTANDING, ORDERED, with the exact next command(s) — copy-paste ready env blocks
   - decisions awaiting the operator (each one sentence + the recommendation)
   - working-tree state: uncommitted files that must travel with the next step (and why they are uncommitted)
## 0b. WORK ORDER — the operator's standing instructions VERBATIM (quote them; never paraphrase a mandate)
## N. history blocks (earlier checkpoints, verdicts, traps) — keep; they are the "why" for the current state
```
Rules of content:
- Every number is cited to its primary (a ledger path, a store, an STDB row), never to an earlier summary.
- Every pointer is a real path or id that exists NOW (verify with `ls`/`sql` before writing it).
- Name the skills the next agent must load — a resume memory that omits the operating manual forces re-derivation.
- Convert every relative date to an absolute one; report times in PT (operator rule) but keep UTC where a system logs it.
- Keep it under ~25 KB; when a section becomes history, compress it to its verdict + pointer.

## 3. Writing / refreshing the checkpoint (≈5 minutes, do it in one pass)
1. Snapshot the live state from primaries (STDB run states + lane counts, store row counts, npm versions, balances, git
   `status --porcelain` on the files you touched, background task ids that will die with the session).
2. Prepend a new `## 0a. STATE <PT timestamp>` block (or update the current one if <30 min old) — done / outstanding /
   decisions / next commands.
3. If the operator gave instructions since the last checkpoint, add/refresh `## 0b. WORK ORDER` verbatim.
4. Update the frontmatter `description` to the new executive summary.
5. Update the ONE line in `MEMORY.md` (≤200 chars, "CURRENT ENTRY POINT", supersedes the previous). Never byte-shred MEMORY.md
   (the memory-archive-index-system rule); it is an index, not a store.
6. Write the durable lessons of the interval as their own memories (feedback/project) and link them with `[[name]]`.
7. Say so in your reply (one line): "checkpoint written: <file> §0a <time PT>".
8. **ROLL-OVER (operator rule 2026-09-26).** The resume file is ONE indexed memory; its body size is invisible to the MEMORY.md cap, so nothing
   prunes it. When the current file passes ~25 KB, or an arc closes, START A NEW dated file: self-contained §0 / §0a / §0b, plus a §1 history
   that compresses the prior file to one line per item (verdict + ledger pointer — the detail already lives in the ledgers). Mark the old file
   `HISTORY ONLY` in its description + a banner, repoint the MEMORY.md line (old line becomes a history pointer; the Stop-hook prune moves it to the
   archive in time). Each auto-compaction then resumes from a small file that carries the salient points forward instead of a delta on top of
   40 stale blocks. The post-compact hook now injects a ROLL instruction when the file is over the cap. (09-10c grew to 421 KB / 39 blocks.)

## 4. Rebuilding context after compaction / session change (in this order)
This is the WAKE PROTOCOL of the `pm-wake-loop` skill applied to a single-session resume (load that skill too when the
session owns a mission with durable workers — bench fleets, STDB runs, training jobs):
1. **ORIENT from the ledger, not the summary**: `MEMORY.md` → the CURRENT ENTRY POINT resume memory → §0 PROTOCOL, §0a
   STATE, §0b WORK ORDER. For a mission, its own ledger (mission.md / roster.json / decisions.jsonl tail / open-questions.md)
   is the source of truth; memory and canon ENRICH, never carry, mission state.
2. **REHYDRATE cheap-to-deep, only as needed**: hot index → the skills §0 names (Skill tool; never skip because the
   summary "seems enough" — it is lossy by design) → the ledgers/docs §0 lists → `canon graph`/transcripts (§5) only when
   depth demands.
3. **VERIFY live state against primaries** before acting (STDB run states, store row counts, npm/tag, balances): runs
   finish, die, or wedge while the context is gone. Silence is never evidence of health.
4. **HEAL / RE-ARM only what died with the session** — monitors, background waits, idempotent relaunchers. Never relaunch,
   re-place, or repeat spend by hand; the durable spine owns the fleet.
5. **ADJUDICATE what banked** since the last checkpoint (batch, from the stores), **ACT within the guardrails** (hard
   gates: deploys of published projects, STDB `--clear`, new recurring spend, anything the operator gated), **RECORD**
   (ledger rows, STDB gates/adjudications, the resume memory's §0a, memory anchors for load-bearing facts).
6. If the compaction summary contradicts pre-compaction success recorded in the memory, trust the memory + primaries.
7. **SLEEP well**: tell the operator in one short paragraph where things stand (PT times), what advanced, what is pending,
   what is gated — then continue the outstanding list or end the turn; monitors wake you.

## 5. Recovering a context gap (when the resume memory does not answer a question)
Retrieve before you reconstruct. Three primaries, cheapest first:
1. **This project's Claude JSONL session store** — the per-session record of tool calls and results:
   `$WORKSPACE/.claude/projects/-home-runner-workspace-nexus-terminal/<session-id>.jsonl` (and the sibling
   project dirs under `~/.claude/projects/`). The resume memory should name the session id(s) of the work. Look up a
   specific command, path, or error with a FIELD-PROJECTED `jq` read — never `cat`/`grep` whole records. Whole records
   carry model-internal fields (thinking, reasoning, signatures, usage telemetry); pasting them bloats the window and
   an input-safety classifier can read a raw-record dump as a reasoning-extraction attempt (Fable-tier safeguard,
   [[resume-session-reasoning-extraction-safeguard]]). Project only the field you need:
   - a tool invocation: `jq -rc 'select(.type=="assistant").message.content[]?|select(.type=="tool_use").input.command // empty' <session>.jsonl | grep doctrine-mine | sort -u`
   - a tool result / error text: `jq -rc 'select(.type=="user").message.content[]?|select(.type=="tool_result").content' <session>.jsonl | grep -i "error\|<pattern>"`
   The file is segmented by `"subtype":"compact_boundary"` lines; `grep -c compact_boundary <session>.jsonl` counts the
   segments. Prefer the canon store (§5.2, scrubbed) or the harness `SearchConversationHistory` tool over a raw read.
2. **The canon store** (skill `canon-store`; the operator also calls it the nexus-canon skill) — the provider-neutral,
   append-only capture of every harness session as JSONL in a git repo, with `cortex canon list | pull | translate | graph`
   for cross-session "how did X work / what did we decide" questions and a knowledge graph over sessions. Use it when the
   fact predates this project's JSONL store or came from another harness.
3. **System-of-record reads**: STDB tables (`bench_run`, `bench_lane`, `bench_gate`, `bench_job`), the HF stores
   (`results-s*.jsonl`, `trajectories/`, `grader/`), git log, npm, the `.env` LEDGER lines, `.bench/LEVER_PROVENANCE.tsv`.
Never assert a fact you cannot cite to one of these; say "not recorded" and stop (the stop-don't-thrash rule).

## 6. Hooks that drive this skill (configured in `.claude/settings.json`, scripts in `.claude/hooks/`)
- `context-watch.py` (UserPromptSubmit + PostToolUse): estimates the live context from the transcript bytes after the
  last compaction boundary and injects `CONTEXT-PRESSURE` notices at 85% and 92% of the window → run §3 immediately.
  Tunables: env `CONTEXT_WATCH_WINDOW` (tokens, default 1000000), `CONTEXT_WATCH_BYTES_PER_TOKEN` (default 4).
- `post-compact.py` (PostCompact + SessionStart): injects `POST-COMPACTION` / `SESSION-START` with the path of the
  current resume memory → run §4 before anything else. Also emits `SETTINGS GUARD` when either guard below is missing.
- **PRECONDITION (operator rule 2026-10-12): `"idleCompaction": false` in `.claude/settings.json`.** Claude Code ≥ 2.1.29x
  compacts a session that sits idle ≈54 min (0.9 × the 1-hour prompt-cache TTL) once it holds ≥ 200K tokens — the notice reads
  "Compacted while idle, before the prompt cache expired". On 2026-10-12 that fired at 359,578 tokens (36% of the 1M window),
  so neither threshold above could fire first and the checkpoint survived only because a milestone checkpoint had been written
  56 min earlier. The setting turns the idle path off (the binary's own schema: "Set to false to stop Claude Code from
  compacting a long conversation while the session is idle"); `env.CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS=850000` raises the
  idle floor to the 85% line as a second layer (parsing of that env var is unconfirmed; harmless if ignored).
- `precompact-guard.py` (PreCompact, matcher `auto`): third layer — exits 2 (blocks) any AUTO compaction while the API-usage
  estimate is below 80% of the effective window (min of `CONTEXT_WATCH_WINDOW`, `autoCompactWindow`,
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW`); manual `/compact` is never blocked; fails OPEN on any error so the real wall (~97%)
  always passes. Decisions log to `/tmp/claude-precompact-guard.log`. Memory: [[feedback-idle-compaction-off]].
- **IDLE CACHE-WARM routine (operator rule 2026-10-12: "I don't want to come back to a compacted session ever again").** Instead of
  idle compaction, every session arms a session-scoped cron at start — AUTOMATICALLY: `.claude/hooks/cache-warm-arm.py` (SessionStart,
  sources startup/resume/clear) returns `initialUserMessage`, which the harness submits as the session's first user message, so the
  model arms the cron as the FIRST of its session-start steps and then carries out every other SessionStart instruction as given —
  the §4 rebuild for a continued context, the fresh-session rule for a new one, pending-item notices (operator rule 2026-10-12: "any
  time I start up Claude Code or /resume a session the idle cache cron should be started automatically", and "I want the model to arm
  it with the other session start instructions, I don't want it to override all other instructions and stop them"). `post-compact.py`
  keeps the same instruction as additionalContext fallback (`ARM IDLE CACHE-WARM`). The arm step is:
  `CronCreate cron "4,19,34,49 * * * *"` (every 15 min) with the `[idle cache-warm]` one-word prompt. **The timer is keyed off
  the LAST ACTIVITY, not the wall clock (operator 2026-10-13):** `.claude/hooks/cache-warm-gate.py` (UserPromptSubmit) sees every
  cron fire before the model does and BLOCKS it (no API call, nothing spent) unless the newest user/assistant record in the
  transcript is ≥ 40 min old (`CACHE_WARM_MIN_IDLE_MIN`). A blocked fire still prints a one-line notice (`suppressOriginalPrompt`
  trims it; it cannot be hidden), which is why the cron is 15 min, not denser. Result: zero pings while the operator works; once
  idle, one ping every 40–55 min (worst case 55 min + ≤1.5 min jitter), always inside the 1-hour prompt-cache TTL, so the operator returns to a warm,
  uncompacted session. Each ping costs one cache read of the context (≈10% of a cold read) plus one word; break-even against a cold
  resume is ≈10 idle hours, and the context is never lost. When a ping arrives: reply with ONE word, no tools. Jobs die with the
  session and auto-expire after 7 days (the operator closes sessions nightly, never leaves them open for a week). Log:
  `/tmp/claude-cache-warm.log`. Cron fires only while the REPL is idle; cron cannot express a uniform 50-min period and an hourly job
  plus 10% jitter can land past the TTL — hence the dense cron + gate.
If a notice arrives mid-task, finish the current tool call, then obey it; a checkpoint written 2 minutes before compaction
is worth more than the tool call it delays.

## 7. Related memories (load if present)
[[feedback-resume-memory-post-compaction]] (the priority rule) · skill `pm-wake-loop` (the wake protocol for missions) ·
[[feedback-post-compaction-rebuild]] ·
[[feedback-checkpoint-before-autocompaction]] · [[feedback-retrieve-before-reconstruct]] · [[feedback-stop-dont-thrash]] ·
[[memory-archive-index-system]] · [[feedback-times-in-pacific]]
