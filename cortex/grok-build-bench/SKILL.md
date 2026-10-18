---
name: grok-build-bench
description: >-
  Drive xAI's real grok-build CLI (the `grok` / grok-shell agent) headless — to
  (a) proxy-capture its exact transport (headers + OpenAI /v1/chat/completions
  JSON), (b) benchmark models in xAI's own harness as a ground-truth control for
  the nexus-cortex / browser-CORTEX harnesses, and (c) route external / arbitrary
  OpenAI-compatible models THROUGH grok-build. Use whenever comparing our harness
  behavior against xAI's reference, capturing grok's wire format, or analyzing the
  now-open-source grok-build (github.com/xai-org/grok-build). Pairs with
  cortex-bench (methodology) and the grok-build-proxy-capture-setup memory.
---

# grok-build-bench — proxy-capture + benchmark xAI's real grok CLI

**What this is.** xAI ships `grok-build` (binary `grok`, client id `grok-shell`) —
a Rust terminal coding agent, now open-source. This skill drives it **headless**
so you can: capture its exact request transport, use it as a **ground-truth
control** when benchmarking models in our harnesses (the browser CORTEX and the
nexus-cortex/omniclaude-v4 CLI), and route arbitrary OpenAI-compatible models
through it. It is the reference-harness companion to **cortex-bench** (which
benches *our* harness). Full field notes + the establishing session:
`grok-build-proxy-capture-setup` memory.

> **Surfaces (don't conflate):** *this* = xAI's grok-build CLI (reference).
> `cortex-bench` = benching the omniclaude-v4 harness. `nexus-terminal-cortex` =
> the browser agent. See `docs/SURFACES.md`.

---

## 0. Locations (already installed, survives across sessions)

- **Binary:** `$WORKSPACE/.grok/bin/grok` → symlink →
  `.grok/downloads/grok-<ver>-linux-x86_64` (Rust ELF).
- **Versions on disk:** `0.1.211` & `0.1.212` (May — native model `grok-build`),
  `0.2.117` (current — native model `grok-4.5`). `grok --version`.
- **Config:** `~/.grok/config.toml` (= `$WORKSPACE/.grok/config.toml`).
- **Auth:** `.grok/auth.json`. **Sessions/transcripts:**
  `.grok/sessions/<url-encoded-cwd>/<session-uuid>/`.
- **OSS source:** `github.com/xai-org/grok-build` → clone to **/tmp** (off-quota).
- **This skill's proxy:** `grok-build-proxy.py` (in this dir).
- **Prior captures:** `grok-captures/2026-07-31/` (grok-build-0.1 live) and
  `grok-captures/` root (May: system_prompt.md, tool_definitions.json).

---

## 1. Non-negotiables (hard-won)

1. **Tool-call counts are NOT in the `-p` stream.** `--output-format
   streaming-json/plain` emits only `thought`/`text`/`end` — zero visible
   `tool_use`. Real tool calls live in the **session `events.jsonl`** (grep
   `"tool_started"`). Counting the stream = undercount to zero. (§4)
2. **Model IDs differ by CLI version.** 0.2.117 REJECTS `grok-build-0.1` /
   `grok-code-fast-1` ("unknown model id"); its models are grok-4.5 (+ what your
   account exposes). To run **grok-build native**, use the **0.1.212 binary**
   directly (`-m grok-build`). `grok-code-fast-1` is **API-only** (not in any
   grok-build CLI) — bench it against api.x.ai, not through grok.
3. **`XAI_API_KEY` shadows OAuth models.** When set, grok uses it and only shows
   that key's models. For OAuth/session models: `env -u XAI_API_KEY grok …`.
4. **Repl auth = `grok login --device-auth`, NOT plain `grok login`** (plain uses
   a localhost callback the repl browser can't reach → hangs). (§2)
5. **Custom `base_url` bypasses login** (Bearer auth via `env_key`) — the key to
   both capture and external models.
6. **Back up + restore `config.toml`** around any `[model.*]` edit.
7. **Never scan `/nix`** (thrashes the fs). **Clone OSS to /tmp**, not workspace
   (quota). See `workspace-storage-quota-ceiling` memory.
8. **cortex-bench discipline applies:** pin the model (never `auto`), n≥2 fresh
   runs, ground-truth verifiable task, produce a deficiency/finding ledger.

---

## 2. Auth (once per session if tokens expired)

```bash
cd $WORKSPACE
setsid nohup .grok/bin/grok login --device-auth > /tmp/grok-deviceauth.log 2>&1 < /dev/null &
sleep 6; cat /tmp/grok-deviceauth.log        # prints URL + user_code
```
Relay the `https://accounts.x.ai/oauth2/device?user_code=XXXX-XXXX` URL + code to
the operator; they approve in a browser; the CLI polls and completes
(`✓ Signed in as …`). Verify the process stays alive (`ps aux | grep '[g]rok
login'`) while they authorize. Only needed for OAuth models; a custom `base_url`
model (§5) needs no login.

---

## 3. Headless invocation

```bash
grok -p "<PROMPT>" -m <model> --always-approve --output-format <fmt>
```
- `-p/--single` single-turn → stdout → exit (also `--prompt-file`, `--prompt-json`).
- `--always-approve` — auto-approve tools (REQUIRED headless, else it blocks).
- `--output-format`: `plain` | `json` | `streaming-json` (ACP NDJSON) |
  `streaming-messages-json` (**Anthropic Messages wire format** — useful to
  compare against our /v1/messages path).
- `-m <model>`: a built-in id, or a `[model.<name>]` from config.toml.
- `env -u XAI_API_KEY` prefix to use OAuth models.

---

## 4. Reading the REAL tool-call count (the metric)

After a run, find the session dir and count `tool_started`:
```bash
python3 - <<'PY'
import json, os, re
from collections import Counter
base = "$WORKSPACE/.grok/sessions"
cwd_enc = None
for d in os.listdir(base):                          # url-encoded cwd, e.g. %2Ftmp%2Fgrokbench
    if d.startswith("%2F"): cwd_enc = d
sdir = os.path.join(base, cwd_enc)
sid = max((f for f in os.listdir(sdir) if os.path.isdir(os.path.join(sdir,f))),
          key=lambda f: os.path.getmtime(os.path.join(sdir,f)))   # newest session
ev = os.path.join(sdir, sid, "events.jsonl")
names = []
def find(o):
    if isinstance(o, dict):
        if "tool_name" in o: return o["tool_name"]
        for v in o.values():
            r = find(v)
            if r: return r
    elif isinstance(o, list):
        for v in o:
            r = find(v)
            if r: return r
for line in open(ev, errors="replace"):
    if '"tool_started"' in line:
        try: names.append(find(json.loads(line)) or "?")
        except: pass
print(sid, "->", len(names), "tool calls:", dict(Counter(names)))
PY
```
Same session dir also holds: `system_prompt.txt` (exact injected prompt),
`chat_history.jsonl` (canonical messages), `updates.jsonl` (full ACP stream).
The `-p` stdout's `{"type":"end","sessionId":…}` line also gives the session id.

---

## 5. PROXY CAPTURE + external-model routing

grok talks **plain HTTP** to a custom `base_url` → no TLS/mitm needed.

```bash
# 1. start the logging proxy (this skill dir)
PORT=8899 UPSTREAM=https://api.x.ai LOG=/tmp/grok-transport.jsonl \
  setsid nohup python3 .claude/skills/grok-build-bench/grok-build-proxy.py \
  > /tmp/grok-proxy.log 2>&1 < /dev/null &
sleep 2

# 2. back up config, add a captured model
cp .grok/config.toml /tmp/grok-config.bak 2>/dev/null || true
cat >> .grok/config.toml <<'TOML'

[model.captured]
base_url = "http://127.0.0.1:8899/v1"
env_key  = "XAI_API_KEY"
model    = "grok-build-0.1"
TOML

# 3. run — transport lands in /tmp/grok-transport.jsonl
cd /tmp/grokbench   # any workspace with files
grok -p "List the files and say in one sentence what this is." -m captured --always-approve --output-format plain

# 4. ALWAYS restore config
cp /tmp/grok-config.bak .grok/config.toml 2>/dev/null || \
  sed -i '/\[model.captured\]/,/^model = /d' .grok/config.toml
pkill -f grok-build-proxy.py
```

**Config semantics:** `[model.<header>]` header = picker name; `model` field = id
sent to API (omit → header name sent); `env_key` references an env var (no secret
on disk) or `api_key = "..."` inline. Precedence: `[model.*]` > env vars >
built-in; per-model `[model.<name>]` wins; global defaults under `[models]`.

**CAPTURE ALL THREE WIRE DIALECTS.** grok-build is dialect-polyglot per model:
`api_backend = "chat_completions"` (DEFAULT when omitted — why past captures saw
/v1/chat/completions) | `"responses"` (native grok-4.5 backend, encrypted-content
reasoning) | `"messages"` (Anthropic dialect; structured output via a synthetic
StructuredOutput TOOL because a native schema blocks tool use there). Optional
`auth_scheme = "x_api_key"` flips Bearer→x-api-key. Three entries at one proxy:

```toml
[model.cap-cc]
base_url = "http://127.0.0.1:8899/v1"
env_key  = "XAI_API_KEY"
model    = "grok-build-0.1"          # api_backend omitted = chat_completions

[model.cap-resp]
base_url = "http://127.0.0.1:8899/v1"
env_key  = "XAI_API_KEY"
model    = "grok-4.5"
api_backend = "responses"

[model.cap-msg]
base_url = "http://127.0.0.1:8899"   # /v1/messages appended by the client
env_key  = "XAI_API_KEY"
model    = "grok-code-fast-1"
api_backend = "messages"
extra_headers = { "anthropic-version" = "2023-06-01" }
```

Then `grok -p "..." -m cap-cc|cap-resp|cap-msg --always-approve` per dialect.
(ModelEntryConfig.api_backend: xai-grok-shell/src/agent/config.rs:3890-3923; docs
xai-grok-pager/docs/user-guide/11-custom-models.md:84,200-209. Verify the exact
base_url path-join per backend from a first capture — the proxy log shows the
path each dialect hits.)

**External models:** point `base_url`/`model`/`env_key` at ANY OpenAI-compatible
endpoint — `https://api.openai.com/v1`, `https://api.together.xyz/v1`,
`http://localhost:11434/v1` (ollama), the omniclaude ai-proxy, etc. That's how you
run non-xAI models *through grok-build's harness* (same run loop + tools, foreign
model). Set `UPSTREAM` on the proxy to match if you also want the capture.

**What you capture** (`/tmp/grok-transport.jsonl`, REQUEST/RESPONSE records):
- `POST /v1/chat/completions` (OpenAI format), body = `model, messages, tools`
  (26 for grok-build), `stream:true`, `stream_options`.
- Headers: `Authorization: Bearer xai-…`, `x-grok-client-mode`,
  `x-grok-client-version`, `x-grok-client-identifier: grok-shell`,
  `x-grok-{user,conv,req,session,agent}-id`, `x-grok-model-override`,
  `x-grok-turn-idx`, `user-agent: grok-shell/<ver> …`.
- **api.x.ai OpenAI-compat models** (`curl https://api.x.ai/v1/models`):
  grok-4.20-*, grok-4.3, grok-4.5, **grok-build-0.1**, grok-imagine-*.
  (grok-code-fast-1 is the /v1/messages Anthropic-dialect path, not here.)

---

## 6. Bench mode (grok-build as ground-truth control)

Purpose: is a discrepancy our-harness-specific or model-intrinsic? Run the SAME
verifiable task in grok-build vs our harness vs a control model.

1. **Task:** deterministic + multi-step + verifiable (cortex-bench rule 5). Build a
   small controlled workspace so ground truth is exact:
   ```bash
   mkdir -p /tmp/grokbench/reports /tmp/grokbench/src
   printf '<html><body>ETF report</body></html>\n' > /tmp/grokbench/reports/a.html
   printf 'export function main(){return "hi";}\n'  > /tmp/grokbench/src/index.ts
   printf '# Project\nDemo.\n' > /tmp/grokbench/README.md
   ```
2. **Run** (pin model, n≥2, `cd` into the workspace):
   `grok -p "<TASK>" -m grok-build --always-approve --output-format streaming-json`
   (use the 0.1.212 binary for `grok-build`; 0.2.117 for `grok-4.5`).
3. **Metrics:** tool calls (§4 from events.jsonl), wall-clock, converged?
   (`"stopReason":"EndTurn"` + non-empty text), answer correctness vs the real files.
4. **Compare** to the omniclaude-v4 `/v1/messages` run (metadata.toolCallIterations)
   and the browser CORTEX. **Ledger** the deltas.

**Reference numbers (2026-07-31, "demonstrate efficient file-tool use" task):**

| model | harness | tool calls | time |
|---|---|---|---|
| grok-code-fast-1 | browser CORTEX | 19/36 | 2m16s |
| grok-code-fast-1 | omniclaude-v4 | 50(cap)/8 | 275s/59s |
| **grok-build-0.1** | **real grok-build 0.1.212** | **20/18** | 25s/18s |
| grok-4.5 | real grok-build 0.2.117 | 10 | 26s |
| deepseek-v4-flash | omniclaude-v4 | 2-3 | 20-38s |

Read: grok-code-fast/grok-build-0.1 is a grep-heavy explorer in EVERY harness incl.
xAI's own (~18-36 calls) → **model disposition, not a harness bug**; grok-build is
~5× faster at similar counts (lean 12.5K prompt, uncapped loop) → xAI's harness pays
less per round. Even xAI dropped that tier: 0.2.117's agentic model is grok-4.5.

---

## 7. OSS source analysis (supersedes reverse-engineering)

```bash
git clone --depth 1 https://github.com/xai-org/grok-build /tmp/grok-build-oss
```
- **System prompt (authoritative):**
  `crates/codegen/xai-grok-agent/templates/prompt.md` (MiniJinja —
  `${{ system_prompt_label }}`, `is_non_interactive` branch; opens with
  `<action_safety>`). Also `apply_patch_prompt.md`, `subagent_prompt.md`.
- **Run loop:** `crates/codegen/xai-grok-shell/src/session/acp_session_impl/run_loop.rs`
  (~2.2k lines) + `turn_end.rs`. **Compaction:** `crates/common/xai-grok-compaction/`.
- **26 tools:** `crates/codegen/xai-grok-agent/src/`.
- **KEY DESIGN FINDING:** grep across crates for `max_iterations|loop.?guard` →
  only compaction/byte budgets, **no hard tool-iteration cap**. xAI runs the loop
  UNCAPPED + relies on compaction + model self-stop; our harnesses bound with
  MAX_TOOL_ITERATIONS=50 + loop detection + progress brake. Candidate to study.
- **High-value next work:** diff OSS `prompt.md` + 26 tool defs against
  omniclaude-v4 SYSTEM_PROMPT/WORK_QUALITY and browser CORTEX SYSTEM_PROMPT —
  harvest steering/tool-shaping we lack; study the uncapped-loop+compaction design.

---

## 8. Cleanup checklist
- `pkill -f grok-build-proxy.py` (and any `grok -p` / `grok login`).
- Restore `.grok/config.toml` from `/tmp/grok-config.bak` (or sed-delete the block).
- `/tmp/grokbench` + `/tmp/grok-build-oss` are throwaway (recreate as needed).
- Persist any new capture to `grok-captures/<date>/` (transport jsonl + a full
  first-request body + tool-name list), like `grok-captures/2026-07-31/`.
