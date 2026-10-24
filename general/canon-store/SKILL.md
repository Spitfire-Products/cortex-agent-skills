---
name: canon-store
description: >
  Operate the CANON STORE — the canonical, provider-neutral, lossless memory + context-retrieval
  rail that captures THIS workspace's Claude Code sessions (and every harness's) as append-only
  JSONL in a git repo. Load this BEFORE rebuilding context after a compaction, before answering a
  cross-session "how does X work / what did we decide", or any time you're tempted to reconstruct
  prior work from your own head. Canon is how a harness that lost its context gets itself back.
  CLI: `cortex canon {list,pull,sync,translate,watch,graph,artifacts,tools}`.
---

# Canon Store — the memory / context-retrieval rail

## 🔴🔴 REFLEX RULE — grep canon the INSTANT you hit "how did this work before"

Before you EVER say "X is missing / blocked / not configured," or reconstruct/derive how a
working system authenticates, clones, deploys, or is configured — **grep the store FIRST.** The
canonical mechanism is almost always recorded verbatim in the session that built it.

```bash
# the store is at /tmp/canon-store (re-clone if /tmp was wiped — see Operations)
grep -rliE "<the term: credential name, command, config key, feature>" /tmp/canon-store/native/ | head
grep -rhoE ".{80}<term>.{60}" /tmp/canon-store/native/**/*.jsonl.part-* | sed -E 's#//[^@]*@#//<tok>@#g' | sort -u | head
```

Also grep `.claude/projects/**/*.jsonl` (raw session history) and search MEMORY.md + topic files.
Deriving from the live system is the LAST resort, not the first move.

**This rule exists because (2026-08-09) the answer to "how did the canon watcher authenticate?"
was `gh auth token` — recorded verbatim in canon session `17dea8d8` (the session that built canon)
— and instead of one grep, a whole detour was spent reverse-engineering the SPA `secrets` table +
AES-GCM. Do NOT repeat it.** See memory `[[feedback-retrieve-before-reconstruct]]`.

---

**Read this first, act second.** The recurring failure this skill exists to prevent: after a
long/compacted session you *reconstruct* how the systems work from memory instead of retrieving
the canonical record — and get it wrong. Canon is the retrieval apparatus. Use it.

## What canon IS

A git-repo-backed, **provider-neutral, lossless, append-only JSONL** store of every agent session
across every harness. Store-once-in-a-superset (text, thinking spans, tool calls, results, system
events, compaction boundaries are all first-class records), translate-at-the-edge into each
provider's dialect at request time. Full spec: `omniclaude-v4/docs/CANON.md`.

- **Remote (private):** `github.com/Spitfire-Products/nexus-canon-store` (env `CANON_REPO`).
- **Local store (2026-10-24):** `~/.cache/canon-store` on the workspace disk (`CANON_STORE` is set in settings env + both bashrc files);
  `/tmp/canon-store` is a symlink to it, recreated at boot by `scripts/canon-store-link.sh` — so the `/tmp/canon-store/...` paths below
  still work. Why moved: this repl's `/tmp` became a 4 GiB RAM tmpfs (2.7 GB of RAM held by the clone). nexus-canon ≥1.12 resolves the
  default itself: `CANON_STORE` → an existing `/tmp/canon-store` → `~/.cache/nexus-canon/store` (`defaultCanonStore()`).
- **It captures THESE Claude Code sessions.** Verified: this workspace's sessions live under
  `native/claude-code/-home-runner-workspace-nexus-terminal/<uuid>.jsonl.part-*` and are
  canonicalized into `canon/claude-code/…`. When you lose context, **your own history is in here.**

## Relation to the `.claude` memory system (they are DIFFERENT rails — use both)

| | `.claude/…/memory/*.md` | Canon store |
|---|---|---|
| Content | curated, hand-distilled notes (MEMORY.md hot index ~17.1KB + ARCHIVE_INDEX + per-topic files) | raw, byte-exact, machine-derived FULL transcripts |
| Use | fast orientation, rules, pointers | deep rehydration, "what exactly happened", training substrate |
| Layer | the index/summary | the transcript layer *beneath* it (canon is UPSTREAM of training) |

Canon does **not** replace the `.claude` memory files; it's the lossless source under them. Distilled
memory + the harness contract are explicitly out of canon's scope (`CANON.md`).

## WHEN to load + use this skill

1. **Post-compaction / new session on ongoing work** — before building or answering, rehydrate.
2. **Cross-session questions** — "how does the relay/canon/webmcp work", "what did we decide about X",
   "what was I doing" — the answer is in the canonical record, not your reconstruction.
3. **Before claiming how any multi-session system works** — pair with `grounded-research` /
   map-before-assert: open the source or the canon record FIRST.

## Agent-callable faces (2026-08-13, nexus-cortex 4.58.0) — canon is no longer CLI-only

- **In-harness TOOLS**: `CanonListSessions` + `CanonPullSession` are first-class nexus-cortex agent
  tools (standard discovery tier — SearchTools finds them; whitelisted; a "Cross-Session Memory"
  system-prompt section advertises them). An agent IN the harness pulls its own history now —
  no more "no canon tools" + filesystem spelunking.
- **Hosted MCP**: the public `cortex.spitfire-products.com/mcp` endpoint's `cortex_exec` runs in a
  container with CANON_* env pre-stamped (when the user saved a canon connection), so
  `cortex canon …` / the canon tools work there identically.
- Browser CORTEX's `canon_pull_session` exists but remains UNVERIFIED end-to-end.

## CLI surface — TWO published entry points, ONE implementation

Canon is the standalone npm package **`nexus-canon`** (Apache-2.0, dependency-free, Node built-ins).
The **`nexus-cortex`** harness embeds the SAME package as `cortex canon <verb>`. Either bin works;
they call one implementation (`packages/canon/src/*`).

- **Harness-less / direct (deterministic, no LLM):** `nexus-canon <verb>` (global install), or in-repo
  `node $WORKSPACE/omniclaude-v4/packages/canon/bin/nexus-canon.js <verb>`.
- **Inside the harness:** `cortex canon <verb>` (themed).

All verbs accept `--store <dir>` (default: `defaultCanonStore()` — `CANON_STORE`, an existing `/tmp/canon-store`, else `~/.cache/nexus-canon/store`; `CANON_REPO` env for the remote).

| Verb | What it does |
|---|---|
| `list [--all] [--project <id>]` | List canon sessions (uuid, size, origin harness, recovered title). `--all` includes sessions <4KB. |
| `pull <uuid> [--to <dir>] [--force] [--strip-signatures]` | Materialize a session — **rehydrate**. `--to` is a target DIR (e.g. `.cortex/sessions`), NOT a harness name. **Default dest since nexus-canon 1.11.11 = `<cwd>/.cortex/sessions`** (was `~/omniclaude-v4/.cortex/sessions`, a hard-coded dev path — 10-09 hygiene): run it from the project you resume in, or pass `--to`. `--strip-signatures` converts thinking to `<prior_reasoning>` text in the materialized COPY only (canon line untouched) — needed when pulling another account's session (thinking signatures validate against the ORIGINATING account). |
| `sync [--dry-run]` | Copy changed native sessions → store (secret-scrubbed), fold in `browser-cortex-<id>` branches, commit + push. |
| `translate [--dry-run]` | Maintain the canonical line: `/native` → `/canon` + `/projections` (deterministic, incremental, blob-SHA provenance). |
| `graph [--project <id>] [--merge-graph <path>] [--cognition] [--no-touched]` | Project knowledge graphs → `/projects/<id>/graph.json` (§27l): session→file `touched` edges + optional graphify code graph, confidence-tagged. |
| `artifacts [--dry-run]` | Capture capability artifacts (skills/agents/mcp/plugins/plans/projects) into the store (§27p). |
| `tools [--json]` | Observed tool inventory per harness + cross-harness concept map (Phase E rung 1). |
| `watch [--debounce <ms>]` | Daemon: fs-watch harness roots, run FULL pipeline (sync→translate→graph) debounced on change; catch-up at startup. |
| `init [dir] [--remote <url>]` | Scaffold a canon store repo (layout, `.gitattributes`, verify workflow, README). |

**Sync roots are DISCOVERED (nexus-canon 1.11.10+, 10-09 hygiene):** the `nexus-cortex` / `nexus-cortex-decisions` sources scan HOME itself, every `HOME/<project>` and every `HOME/<project>/packages/<pkg>` that carries `.cortex/` (`discoverCortexRoots` in canonSync.ts; labels = dir basenames → here `workspace`, `omniclaude-v4`, `nexus-terminal`, `server`, `cli`, `tui`, plus any new project dir that grows a `.cortex/`). The fixed harness roots (`~/.claude/projects`, file-history, `~/.cortex/autoresearch-stage`, `~/.grok`, `~/.gemini`) are unchanged. A store's `HARNESSES.json` still overrides (`loadHarnessSources`). The artifact capture's mcp/project lists are discovered the same way (`discoverProjectDirs`). NEVER hard-code a project name or `$HOME/...` in the package again — the published 1.11.8 carried the author's workspace layout as defaults ([[project-public-tarball-hygiene]]).

🔴 **CLI GOTCHA — use the RIGHT bin.** `node packages/cli/bin/cortex.js canon <verb>` in this repo can
fall through to the **LLM agent** (I saw a `[41551 in | 201 out | 1 tool]` token line on `canon sync`),
which does NOT run the real command. For deterministic runs use `nexus-canon <verb>` / the direct
`packages/canon/bin/nexus-canon.js` bin, or the pipeline scripts (below). Verify a real run by its
structured output (`[canon-sync] pushed: N copied…`), never the agent token line.

## Fast rehydration recipe (do this when you've lost the thread)

1. Ensure the store exists locally (Operations below); then `cortex canon list --json` to see sessions.
2. To read a specific prior session without materializing it, grep the store directly (cheap, no LLM):
   `grep -rl "<term>" /tmp/canon-store/native/claude-code/…` then read the matching `.jsonl.part-*`.
3. To actually resume one in a harness: `cortex canon pull <uuid> --target <harness>`.
4. The store also holds `/projects/<id>/` knowledge graphs + `/agents /skills /plugins /plans` capability
   artifacts — use those for "what capabilities/plans exist" questions.

## On-disk layout (verified)

```
/native/       raw per-harness sessions: browser-cortex/ claude-code/ gemini-cli/ grok-build/ nexus-cortex/
                 (+ SKIPPED.md skip log; large sessions chunked as .jsonl.part-NNNN @25MB; events in
                  <uuid>.events.jsonl sidecars; subagents under <uuid>/subagents/)
/canon/        the canonical line per harness + artifacts/ + MAPPING.md + TRANSLATED.md
/projections/  per-harness ref-based projections
/projects/     project-scoped knowledge graphs + ROOTS.json
/agents /skills /plugins /plans /memory   ArtifactManifest capability dimensions
/receipts/     public bench/resume receipts
```

## Operations / restart the sync (THE runbook — verified 2026-08-08)

The reactive pipeline has three paths (README): (1) `nexus-canon watch` daemon [full pipeline on change],
(2) the cortex per-turn hook (`cortex config set CANON_AUTO_SYNC true`), (3) a 6h cron catch-up for gaps.
In THIS workspace the wired cron is `omniclaude-v4/scripts/canon/canon-cron.sh` (chains sync→translate→graph,
flock-guarded, `--if-due` = 6h). The deterministic legs are the `tsx` scripts under `scripts/canon/`
(`canon-sync.ts`/`-translate.ts`/`-graph.ts`) — these are what actually ran, NOT the `cortex.js` NL path.

**To restart canon sync after finding the watcher down / a failed cron:**
1. **Catch-up now (foreground, real output):**
   `cd $WORKSPACE && timeout 580 bash omniclaude-v4/scripts/canon/canon-cron.sh`
   then read the tail of `.canon/canon-cron.log` — want `sync OK / translate OK / graph OK / canon cron OK`.
2. **Restart the watcher (detached, off-quota log):**
   `setsid bash -c 'cd $WORKSPACE/omniclaude-v4 && exec node packages/canon/bin/nexus-canon.js watch --store /tmp/canon-store' >/tmp/canon-watch.log 2>&1 &`
   verify: `ps -eo pid,args | grep 'nexus-canon.js watch'`; the log lists every watched root incl.
   `$WORKSPACE/.claude/projects` (THIS session). Debounce default 60000ms.
   ⚠️ The watcher lives in the repl process tree — a repl restart kills it. Durable version = the
   `--if-due` cron in `~/.bashrc` (see cron-script header).

- **Health check before trusting currency:** `ps` for `nexus-canon.js watch`; `git -C /tmp/canon-store log -1`
  for last commit time; `tail .canon/canon-cron.log` for the last run's per-leg result. Stale store or a
  `translate/graph FAILED` line ⇒ run the catch-up above.
- **🔴 PARTIAL /tmp reap (2026-08-23): the working tree can lose thousands of TRACKED files while
  `.git` survives** — every canon commit then aborts on the mass-deletion guard ("N staged
  deletions — nothing committed", `pushed=false` in the watcher line) while syncs keep "working".
  This is the guard SAVING you (3rd prevented wipe-commit). Recovery is one command:
  `git -C /tmp/canon-store checkout -- .` (restores tracked files from the intact object store;
  untracked new natives survive), then re-run the pipeline. Treat any `pushed=false` watcher line
  as a red flag to chase immediately.
- **Re-clone if `/tmp` was wiped:** both sync/translate auto-clone the store from `CANON_REPO` (remote = truth).
  🔴 **AUTH — do NOT chase a separate PAT.** Git here authenticates via the **`gh` CLI credential** (logged in as
  Spitfire-Products, `repo` scope — the SAME credential every `deploy-*.sh` push uses). The canon store is that
  same org, so it clones with no extra secret. Just point `CANON_REPO` at the repo URL carrying the gh token:
  `export CANON_REPO="https://$(gh auth token)@github.com/Spitfire-Products/nexus-canon-store"` then run
  `canon-cron.sh` (auto-clones) or `git clone … /tmp/canon-store`.
  (The `GITHUB_CANON_STORE_ACCESS_TOKEN` in the SPA `secrets` table is `scope=user`, AES-GCM-encrypted with the
  owner's WorkOS session key = **browser-decrypt-only**; it is the SPA canon-push leg's credential, NOT reachable
  from the CLI. Don't try to decrypt it — use the gh token above.)
- **Secrets:** `sync` scrubs (SECRET_PATTERNS incl. hex64); canon stores results verbatim otherwise
  (byte-exact provenance = git blob SHA of the native part → deterministic re-translate).
- The user's own canon repo + GitHub PAT are theirs and never federated with ours (`INBOUND_ACCESS_AND_SPA_CANON_DESIGN.md §2`).

## Deeper references
- `omniclaude-v4/docs/CANON.md` — full spec (authoritative; read before any load-bearing canon claim).
- `nexus-terminal/modules/database-ai/CANON_CROSS_HARNESS_PLAN.md` — the phase plan (§27* rungs).
- Memory: `[[canon-cross-harness-plan]]`, `[[feedback-post-compaction-rebuild]]` (canon is step one of the rebuild).

## DELTA 2026-09-26 — the hot/archive split, as it actually behaves now (nexus-canon 1.11.5 / harness 4.124.22)
- **Local store = live tree only.** Every clone excludes `archive/` (non-cone sparse `/*` + `!archive/`); the remote keeps everything.
  `/tmp` has a ~5 GB PER-USER quota that `df` does not show — the cron guard measures `du -sm /tmp` vs `CANON_TMP_QUOTA_MB`.
- **What the archive run does** (`canonArchive.ts`): per SESSION (`sessionUnit`: chunks, sidecars, subagent files move together) —
  DROP the live copy when every file is byte-identical to an archived copy; MOVE when every file is older than 30 d; otherwise keep.
  Never archived (`isArchivablePath`): `canon/artifacts/**`, any `*/memory/*`, `*.md`, `.gitkeep`.
- **Sync never re-adds archived sessions:** `dropArchivedDuplicates()` runs before sync's add. The browser fold-in (`git checkout
  FETCH_HEAD -- native/browser-cortex`) STAGES every file the branch holds, archived ones included — that was a 77-file re-add/drop
  churn per cycle until 09-26. A cron log line `[canon-archive] … dropping N live duplicate(s)` with N>0 on consecutive runs = a new
  re-add path; find the writer, don't just let archive eat it.
- **Reading archived sessions:** `canon pull` / `pull-native` fall back to the archive (hydrated to a temp dir from git objects);
  `canon graph` includes archived canon sessions via `canonArchiveRead.ts` (no disk writes; touched cache `~/.canon/touched-cache.json`
  keyed by blob id, titles in `~/.canon/archived-titles.json`). Healthy graph line: `[canon-graph] <live> live + <archived> archived`.
- History: the pre-fix archive run d723f686f (09-20) left 16,357 moved files on disk and the next sync re-committed them; the dedup
  (store commit f07c5c778, 17,242 files, 1.45 GB) resolved it. Stop the watcher by PID only (see §Operations + self-match rule).
- **Echoes + pull resolution (1.11.6):** sync skips a new session already stored byte-identical under another project dir
  (the hosted box's hydrate→sync round trip lands sessions under `-root`); `canon pull`/`pull-native` resolve identical or
  continued copies themselves, name the harnesses when a session was continued in another harness (`--harness <h>`), and
  take `--rel <stored path>`.
- **Graphs are cwd-independent since 1.11.6** (a rootless project's code-graph path used to resolve against the cwd —
  cron 69k vs watcher 25k nodes; the 69k were inflated). Quote session counts, not node counts, as coverage.
- **Restart the watcher after every canon build** — it keeps the old modules in memory (09-26: an 11:44 AM watcher kept
  re-adding files a later fix already skipped).

## DELTA 2026-09-30 — `canon-verify` CI is DISABLED (it was the GitHub Actions budget overrun)
- `Spitfire-Products/nexus-canon-store` is a PRIVATE repo, so its Actions minutes count against the account's 2,000 min/month. Its
  `.github/workflows/verify.yml` (`canon-verify`, every 3 h since the 08-14 per-push trigger removal) did `actions/checkout` with
  `fetch-depth: 0` — a full-history clone of the multi-GB store — which alone took ~10 min, so the job hit `timeout-minutes: 10` and was
  cancelled before linting anything (58 of 60 recent runs cancelled). ≈80 billed min/day, ≈1,364 wall-min in Sept → the account went past
  2,000 and the operator got a ~$9 overage bill (09-30).
- Disabled 09-30: `gh workflow disable canon-verify --repo Spitfire-Products/nexus-canon-store` (state `disabled_manually`). Re-enable with
  `gh workflow enable canon-verify --repo Spitfire-Products/nexus-canon-store` ONLY after the checkout is shallow (`fetch-depth: 2`, ideally
  sparse to the changed paths) and a run is measured well under the timeout. Capture/sync (watcher, `canon sync`) is unaffected — this was
  only the verification lint; run `.github/scripts/canon-verify.mjs <base> HEAD` locally when a check is wanted.
- Rule: never add or re-enable CI on this repo without estimating minutes/month (runs × billed minutes per job). Memory:
  [[gh-actions-budget-canon-verify]].
