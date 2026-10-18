---
name: candidate-model-onboarding
description: Onboard a new open-weight base model as a V2-P3 bake-off candidate — HF Space serving, harness card + tool-call parser, then the full cortex-bench suitability protocol (full-stack + lean-router + tool-stable-sampling) before accept/reject. Use whenever a new sub-4B model is proposed as a training/router/reasoner candidate for the nexus-cortex harness.
---

# Candidate Model Onboarding (HF Space serving + harness bench)

Battle-tested across Qwen3/3.5, SmolLM3, Phi-4-mini, LFM2.5 (350M/1.2B), MiniCPM5-1B
(2026-07-08 → 07-10). The goal: take a proposed open model → serve it → make it drivable
in the omniclaude-v4 harness → run the **full suitability protocol** → accept/reject with a
complete, defensible record. Feeds [[base-model-bakeoff-v2p3]], the V2-P3 SLOT_ROSTERS, and
the training pipeline.

**Related skills/memories:** `cortex` (drive the harness), `cortex-bench` (the methodology +
cardinal rules), `huggingface-spaces` (Space mechanics), [[hf-space-bench-server-bringup]]
(the original bring-up + the 4→5 tool-call families), [[base-model-bakeoff-v2p3]] (roster +
r-ledger), `feedback_test_models_first`.

---

## ⚑ THE CARDINAL LESSON (learned the hard way on MiniCPM5, 2026-07-10)

**Never reject a small candidate on ONE protocol.** MiniCPM5-1B scored **0/300 full-stack →
100/300 lean-router@0.9 → 250/300 lean-router@0.3** (tying the slot winner). A premature
reject after the first number would have discarded a genuinely good router. **Full protocol
coverage is mandatory before any accept/reject:**

1. **Drivability** — one single tool round-trip (proves plumbing).
2. **Chained tools** — a 2-step dependent task (proves multi-turn, non-streaming path).
3. **Full-stack bench** — 16k system prompt + all tool schemas (the reasoner protocol).
4. **Lean-router bench** — 307-byte persona, heavy builtins disabled (the r5 protocol).
5. **Sampling sweep** — if a lean run is unstable across *structurally identical* tasks,
   rerun near-greedy (temp 0.3, even 0.0). Format-fragile tool callers (Phi, MiniCPM5) only
   emit clean calls near-greedy; the vendor *chat* default (often 0.9) is wrong for tools.
   **BUT the relationship is NOT monotonic-down**: qwen3.5-2b (thinking model) scored 200/300
   at 0.6 vs 50/300 at 0.3 — thinking models can DEGRADE near-greedy. Sweep both directions;
   record the winning temp on the card (the card temp is the only sampling control).
   This lesson now also governs the BAKE-OFF eval: V2-P3 Lens A (`scoreHoldout`) takes
   `--temperature` (D20 — its old hardcoded 0.7 was an asymmetric sampling tax on
   format-fragile 1B candidates vs the frontier teacher); score at the temp production
   would use, and never compare scores across temps.

6. **MODE sweep (hybrid thinkers) — D28, learned the hard way on MiniCPM5:** if the template
   has Think/No-Think (enable_thinking / <think> control), the suitability protocol MUST run
   the tool-drivability + consume probes in BOTH modes before accept/reject or any training.
   MiniCPM5's entire V2-P3 program (6 arms) ran No-Think because the serve template default
   (ENABLE_THINKING=0) was never overridden — the base passes consume-grounding think-on
   UNTRAINED. Record the winning mode PER DUTY on the card (reflex duties may prefer No-Think
   for latency; agent duties think-on), and carry mode in every predictor tag thereafter.

A small model can be useless full-stack (drowns in context) yet excellent lean — that's a
**router-tier accept, lean-prompt duty**, not a reject. Only 0-across-all-protocols = reject.

---

**ARCHITECTURE HARD-GATE (2026-07-13, Needle):** the ENTIRE onboarding stack (unsloth LoRA train, AutoModelForCausalLM Gradio serve, hf-space card) assumes a PyTorch decoder-only causal LM with safetensors. A candidate whose config.json shows library_name:jax / model_type:custom / a non-*ForCausalLM architecture (e.g. Needle = SimpleAttentionNetwork, encoder-decoder, .pkl JAX weights, custom tokenizer) is NOT onboardable via the standard path — not LoRA-trainable, not template-servable. Such a model is at most an OFF-THE-SHELF eval (custom SDK Space + routerHoldout Lens-R, no training). CHECK config.json library_name + architectures FIRST — a JAX/custom arch is an immediate hold, before license/tool-format.

## Step 0 — research the model FIRST (before any GPU)

Verify from the HF model card + `config.json` + `generation_config.json` + `chat_template.jinja`:
- **License** (hard gate): apache-2.0/MIT ideal; note any commercial cap (LFM Open = $10M/yr).
- **Architecture** (`config.json` `architectures`): plain dense (LlamaForCausalLM, Qwen3) = easy.
  **Hybrid linear-attention / MoE / VLM** (Qwen3.5 `qwen3_5`, Gated-DeltaNet) = serving/fitting
  hazards — flag them.
- **Tool-call format** — grep `chat_template.jinja` for the emission block. This tells you which
  parser family you need (see Step 3). `curl -s -H "Authorization: Bearer $HF_TOKEN" \
  https://huggingface.co/<repo>/raw/main/chat_template.jinja`.
- **Vendor sampling** (`generation_config.json` temperature/top_p) — the STARTING point, not the
  tool-serving answer (see cardinal lesson #5).
- **`<think>`/enable_thinking** in the template → reasoning: true.

## Step 1 — serve it on a HF Space (the template already exists)

Template: `omniclaude-v4/scripts/hf-space-template/{app.py,requirements.txt,README.md}` — a
model-agnostic Gradio `/run(messages_json, tools_json, max_new_tokens, temperature)` server.

```bash
export PATH="$WORKSPACE/.local/bin:$PATH"
export HF_TOKEN="${HF_TOKEN:-$HUGGINGFACE_TOKEN}"
cd omniclaude-v4/scripts/hf-space-template
hf repo create <hf-org>/bench-<slug> --repo-type space --space-sdk gradio --private --exist-ok
hf upload <hf-org>/bench-<slug> . --repo-type space --exclude "app_vllm.py"
hf spaces variables add <hf-org>/bench-<slug> --env MODEL_ID=<repo>
hf spaces variables add <hf-org>/bench-<slug> --env ENABLE_THINKING=1   # if hybrid thinker
hf spaces variables add <hf-org>/bench-<slug> --env HF_HUB_ENABLE_HF_TRANSFER=1
hf spaces variables add <hf-org>/bench-<slug> --env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
hf spaces secrets   add <hf-org>/bench-<slug> --secrets "HF_TOKEN=$HF_TOKEN"
# TRUST_REMOTE_CODE=1 ONLY if the model needs it (Phi/SmolLM/Qwen do NOT; it broke Phi)
```

**Hardware:**
- **ZeroGPU (`zero-a10g`, free w/ PRO)** — shape discovery / a few calls. BUT: the harness JS
  `@gradio/client` does NOT apply the token to ZeroGPU quota (R59) → runs anonymous, ~2 calls
  then 500s. Fine for python-client probes; NOT for a bench.
- **`t4-small` ($0.40/hr)** — sub-1B at short (router) context.
- **`l4x1` ($0.80/hr, 24GB)** — REQUIRED at 16k prefill even for 1.08B models (full-attention
  activation spikes 3-7GB; T4 OOMs). Use L4 for the full-stack bench.
- **MUST make the Space PUBLIC** (`private:false`) — the harness `@gradio/client` fails on private
  Space metadata ("Space metadata could not be loaded"). All bench-* siblings are public.
- Readiness = **gradio `/config` returns 200**, NOT the container stage (stage lies during init).
  `--sleep-time 900` guard. Flip HW: `hf spaces settings <id> --hardware <hw>`; wait for
  `runtime.hardware.current` to actually equal the request (the flip triggers a rebuild).
- **PAUSE when done** (`hf spaces pause <id>`) — billing off, HW retained.

## Step 2 — shape probe (confirm the emitted tool-call format)

```python
# scratchpad probe via python gradio_client (token DOES apply here — unlike JS)
from gradio_client import Client; import json, os
c = Client("<hf-org>/bench-<slug>", token=os.environ["HF_TOKEN"], httpx_kwargs={"timeout":300})
tools=[{"type":"function","function":{"name":"get_weather","parameters":{"type":"object",
  "properties":{"city":{"type":"string"}},"required":["city"]}}}]
print(repr(c.predict(json.dumps([{"role":"user","content":"weather in Paris? use the tool"}]),
  json.dumps(tools), 512, 0.3, api_name="/run")[:1200]))
```
The raw emission tells you exactly which parser family (Step 3).

## Step 3 — harness card + tool-call parser (the only code you write)

**Card** — add one `SpaceModelSpec` to `omniclaude-v4/packages/core/src/models/cards/huggingface/
hf-space-models.ts` (env `HF_SPACE_ID_<SLUG>`, repo pin, reasoning, `defaultTemperature`). The
card default temp WINS over request temp (harness quirk) — so this is the tool-stability control.

**Parser** — `omniclaude-v4/packages/core/src/models/hfSpace/normalize.ts`. 6 families exist:
| Family | Marker | Models |
|---|---|---|
| Hermes-JSON | `<tool_call>{json}</tool_call>` | Qwen3, SmolLM3, granite-4.1 |
| Qwen3.5 XML | `<function=name><parameter=k>v</parameter></function>` (Nemotron variant: same, `<tool_call>`-wrapped) | Qwen3.5, arctic-awm, nemotron-3 |
| Phi token-array | `<\|tool_call\|>[{...}]` / bare `[{...}]` | Phi-4-mini |
| LFM pythonic | `<\|tool_call_start\|>[f(k=v)]<\|tool_call_end\|>` | LFM2.5 |
| MiniCPM5 XML-attr | `<function name="n"><param name="k">v</param></function>` (+CDATA, `<tool_sep>`) | MiniCPM5 |
| gemma-4 channel | `<\|tool_call>call:name{k:<\|"\|>v<\|"\|>}<tool_call\|>` (+`<\|channel>thought` → reasoning) | gemma-4-e2b |

If the new model matches one → done. If not → add a `parseX()` + a branch in `parseHFCompletion`
keyed on an **unambiguous marker** (MiniCPM5's `<function name="` vs Qwen3.5's `<function=` — order
matters). `<think>` reasoning extraction is already generic. **END_TOKENS**: check the probe for
leaking terminators — granite leaked `<|end_of_text|>`, gemma leaked `<turn|>`; add to the
END_TOKENS strip list in normalize.ts when a new one appears. Then:
`tsc --noEmit -p packages/core/tsconfig.json` → `npm run build` → smoke the parser on the REAL
probe emission (`node -e "import('./packages/core/dist/models/hfSpace/normalize.js')..."`).

## Step 4 — drive the harness (the two verification gates)

Boot the server with the card env in the REAL env (ESM reads `process.env` at module load):
```bash
cd omniclaude-v4/packages/server
PID=$(lsof -ti:4000); [ -n "$PID" ] && kill -9 $PID; sleep 1
HF_SPACE_ID_<SLUG>=<hf-org>/bench-<slug> HF_TOKEN="$HF_TOKEN" MENTORSHIP_ENABLED=false \
  setsid nohup node dist/index.js > /tmp/omniclaude-server.log 2>&1 < /dev/null &
for i in $(seq 1 25); do sleep 2; curl -sf http://localhost:4000/health >/dev/null && break; done
```
(For lean-router runs add `PROJECT_PATH=<router-profile> CORTEX_SYSTEM_PROMPT_FILE=<.../ROUTER_PROMPT.md>`.)

- **Gate A — single tool:** `cortex --new --quiet -m <card-id> "Use the Bash tool to run: expr 6 \* 7. Report the output."` → verify `Executing tool: Bash` in the log + correct answer.
- **Gate B — chained tools:** `"(1) Bash: printf hi > /tmp/t.txt  (2) Read /tmp/t.txt and report contents."` → verify BOTH tools execute in sequence. (Optional deep check: render the model's `chat_template.jinja` with a real 2nd-turn payload to confirm tool history is well-formed.)

## Step 5 — the bench matrix (cortex-bench discipline)

Two protocols, each `--runs 2`, PINNED model (never `auto`). Server drives the running :4000.
```bash
# Full-stack (reasoner protocol) — L4 hardware for 16k prefill
cortex autoresearch bench --task-set .cortex/bench/tasks/r2-hfspace-tasks.json \
  --experiment-tag r<N>-<slug> --runs 2 --split train --model <card-id>
# Lean-router — server booted with the router-profile; task set at
#   $WORKSPACE/.bench-hosting/router-profile/router-tasks.json
cortex autoresearch bench --task-set <router-tasks.json> \
  --experiment-tag r<N>-<slug>-router --runs 2 --split train --model <card-id>
```
**Bench-server state (2026-07-10 contamination incident): curl-driven benches MUST run
`CORTEX_MODE=stateless`** — a persistent orchestrator bleeds conversation across runs (gemma
"reproduced" an unguessable flag with ZERO tool calls because a prior run's answer was in
context). The `cortex` CLI still needs the persistent server (stateless → 503) — the two
drive modes need different server boots. Re-bench anything scored on a contaminated server.

**CONFOUND CHECKS (cardinal rule 4) before trusting any 0:**
- Space log for `CUDA out of memory` (→ bump HW) and `An error occurred` (transport).
- **Bench verifiers for version-drift** — hardcoded values (server version, file counts) rot;
  a perfect answer can score 0 on a stale verifier. Refresh to repo truth (don't weaken the check).
- If a lean run is split across identical tasks (100/0 on twins) → **sampling**, rerun at 0.3.

**Reference ranks (r3, lean = r5):** control 300 · qwen3.5-4B 250 · qwen3.5-0.8b/qwen3-1.7b 150
· qwen3-0.6b/lfm-1.2b-think 100 · lfm/smollm 50 · lfm-350m/phi 0 (full-stack). Lean router:
qwen3.5-0.8b 250 (winner), MiniCPM5 250@0.3, lfm-350m 0.

## Step 6 — record the verdict (rule 1: a ledger, not a pass/fail)

1. **Registry** `nexus-terminal/modules/database-ai/training/baseModelRegistry.ts` — one
   `BaseModelCandidate` (slot, license, toolCallFamily, sampling, minGpuAt16k, operatingIds,
   harnessCardId/env, notes with EVERY quirk + the score matrix). Record REJECTS too (Phi is
   in there) — the registry is the institutional memory. `tsx runBakeoff.ts --tag dryver` to
   confirm the roster loads.
2. **Roster** `v2p3/config.ts SLOT_ROSTERS` — add to `router`/`webgpu-reasoner` only if accepted.
3. **Ledger** `omniclaude-v4/.cortex/bench/r<N>-<slug>.md` — the score matrix + the disposition
   notes + confound history.
4. **Quarantine** — the operatingIds must be in `apprentice_models` (set_apprentice_model) before
   the model operates in-platform.
5. **PAUSE the Space.** Commit (explicit pathspec, no AI attribution): card+parser in omniclaude-v4,
   registry+roster in nexus-terminal.

## Known harness quirks this surfaces (backlog candidates)
- **R59** — JS `@gradio/client` token not applied to ZeroGPU quota (runs anonymous). Use dedicated HW.
- hf-space **card temp overrides request temp** → `bench --temperature` can't reach the Space; the card is the sampling control.
- Private Space → `@gradio/client` "metadata could not be loaded" → make public.
- `CORTEX_MODE=stateless` is curl-benchmarking ONLY — the `cortex` CLI needs the persistent server (stateless → 503).
- ESM: cards read `process.env` at module load → export card env into the REAL env before boot.

---

## DELTA 2026-07-22

- **Vocab-compatibility check is a REQUIRED onboarding step** for any candidate intended as a
  spec-decode draft or distill student: compare `config.vocab_size` (nested `text_config` on
  newer Qwen) against the intended verifier/teacher. Lesson: Qwen3-0.6B (151936) is INVALID
  under Qwen3.5-4B (248320); the whole Qwen3.5/3.6 family shares 248320.
- **Mode-labeled instruments everywhere** (D28): any bench/eval must record chat-template
  thinking mode AND temperature; raw-completion prompting of instruct models is a silent third
  mode — never do it unlabeled. Proxy-metric validity can FLIP between modes (acceptance↔F1:
  −0.22 nothink vs +0.57 think, spec-bench 0722).
- **CORRECTION (2026-07-23)**: Qwen3.5-2B WAS onboarded in the r12 wave (2026-07-10) — registry
  entry, `qwen3.5-2b-space` card, `<hf-org>/bench-qwen3-5-2b` Space, ledger
  `omniclaude-v4/.cortex/bench/r12-qwen3-5-2b.md`. LEAN-ROUTER protocol only: vanilla MARGINAL
  200/300 @0.6 (50/300 @0.3 — thinking models degrade near-greedy); khazarai distill variant
  300/300 wildcard-accept. Task #98's real remainder = the protocols r12 skipped: spec-decode
  draft agreement under the 4B verifier (riding the #79 v3 bench), full-stack bench, browser-tier
  q4 MLC hypothesis. Check the registry BEFORE claiming a candidate is un-onboarded.

## DELTA 2026-07-23 — sampling & gate-masking (the Qwen3.5-2B browser-check arc)

All four are variants of ONE rule: **the setup being present is NOT the measurement being valid —
read the TRACE, not the gate/flag/score.** (Operator caught each of these on Qwen3.5-2B.)

- **VENDOR PER-MODE SAMPLING IS LOAD-BEARING — temperature-only is a confound.** The model card's
  recommended sampling is PER MODE and includes more than temp. Qwen3.5: **think-on** `temp 0.6 /
  top_p 0.95 / presence_penalty 1.5`; **non-think** `temp 0.7 / top_p 0.8 / presence_penalty 1.5`.
  `presence_penalty≈1.5` is the one that SUPPRESSES rambling/overthinking/confabulation. A temp-only
  probe at 0.6 with `pp=0` made Qwen3.5-2B look like a weak reasoner (confabulated "Let's-Encrypt"
  authority into a grounding answer; overthought a 1-sentence def for 22.9s) — ALL of which vanished
  at `pp=1.5`. Before judging reasoning QUALITY, run the vendor per-mode sampling (grep the card:
  `temperature|top_p|presence_penalty|top_k`, and the "non-thinking mode: …" line). A weak-reasoning
  verdict at wrong sampling is not a model finding.
- **BINARY GATES MASK REASONING QUALITY — always inspect the trace.** A `3/3 PASS` can be SPURIOUS:
  a grounding gate `answer.includes("8443")` passes on a keyword that appears inside an UNCLOSED,
  TRUNCATED `<think>` block that never became an answer; a length gate passes on truncated meta-
  reasoning. Qwen3.5-2B think-on scored a fake "3/3" whose real value was 1/3 (only the tool task
  completed; the two non-tool "passes" never answered). Gates check "contains X" / "emitted a call",
  NOT grounding-purity, effort-proportionality, or convergence. Read the actual `<think>`/content.
- **CONFIG-PRESENT ≠ MEASUREMENT-VALID.** Setting `ENABLE_THINKING=1` on the serve Space is not proof
  the model reasoned — r13 recorded metrics-only (`outputTokens=0`, no traces), so "think-on" was an
  UNVERIFIED config claim. Verify the mode took effect FROM OUTPUT (visible think trace), not from the
  flag. Same for temp (card temp overrides request temp) and any env you set.
- **THINK-ON IS NOT UNIVERSALLY BETTER — some candidates serve better NON-THINKING (inverts D28).**
  D28's "agent duty = think-on" is a DEFAULT, not a law. Qwen3.5-2B at q4 OVERTHINKS catastrophically
  think-on (never converges on simple tasks — fills the token budget with meta-reasoning, truncates
  before answering; arXiv 2606.00206 quantized-overthinking), while its NON-thinking mode is fast +
  clean + correct. The vendor card even says it "operates in non-thinking mode by default." So: test
  BOTH modes at vendor sampling, read the traces, and record the winning mode PER DUTY — a candidate
  can be a fine draft/router/browser-non-thinking model AND a poor think-on reasoner.
- **Browser spike hygiene:** clean think-off must INJECT a closed empty `<think></think>` (force no
  reasoning), not merely omit the prime — Qwen3.5 thinks by default and leaks traces otherwise. Use
  the model's NATIVE tool format (registry `toolCallFamily`), not a guessed one (Qwen3.5 = qwen35-XML
  `<function=…>`, NOT Hermes `<tool_call>{json}</tool_call>` — instructing the wrong one → bare
  hallucinated names). web-llm's chat `tools` param is Hermes-models-ONLY → test tool-calling via raw
  completion. Worked example in `omniclaude-v4/.cortex/bench/r13-qwen3-5-2b-fullstack.md`.

## DELTA 2026-07-24 — HF Space JOB ops preflight (MANDATORY before any Space bring-up)

The jspace/jdistill saga (~$3 of silent-death rediscovery) produced a 10-rule preflight for ANY
job-at-boot Space — **read memory [[hf-space-job-ops-rules]] (or the v2p3-training-pipeline skill's
"HF SPACE JOB OPS" section) before creating or modifying a Space job.** Headlines: persist to a
DATASET repo never the Space's own repo (Space-repo uploads trigger a REBUILD that replaces the
container mid-run); keep-alive the app URL (sleep timer counts HTTP, not compute); pin
`python_version` in README when requirements pin wheels; `HF_HUB_ENABLE_HF_TRANSFER=0` for jobs
(Rust panics are uncatchable); verify `hf spaces variables ls` before restart; pre-download before
GPU work; `low_cpu_mem_usage` for monolith shards; daemon-thread CUDA init + autograd
multithreading off; checkpoint/merge-resume across boots.

## DELTA 2026-07-27 — mode is PER-ARTIFACT + the serving-alignment audit (khazarai-chat lessons)

- **NEVER transfer a mode verdict from the BASE to a DERIVED artifact.** The base Qwen3.5-2B
  onboarding concluded "browser-tier viable NON-thinking; think-on overthinks at q4" — correct for
  the base in the draft seat, WRONG for the khazarai distilled reasoner built on it: that artifact's
  TOOL-CALL reflex was trained downstream of think spans, so serving it no-think produced coherent
  chat with ZERO tool calls, while think-on fired real calls. Every distinct artifact (base, -SFT
  checkpoint, community distill, merged adapter) gets its own mode A/B on its own serving path
  before a duty is assigned. Mode is part of the instrument (D28) — at ARTIFACT granularity.
- **Onboarding now ends with the serving-alignment audit** (memory
  [[serving-alignment-audit-template]], 12 items) run against the artifact's ACTUAL serving path
  (WebGPU/browser if that's the deployment): training-template parity (fetch the artifact's
  chat_template from tokenizer_config and diff the serving renderer — a never-trained tool dialect
  = sloppy/empty calls), mode A/B, sampling completeness (near-greedy + no repetition penalty
  loops small q4 models), BOS/dialect, ctx/output budgets, structural loop-cap for ≤2B agents
  (one tool round per user message — they re-read tool RESULTS as new user requests).
- **Two degeneration classes — diagnose before prescribing** (adjudicated 2026-07-27 via the
  `webgpuEchoAB` paired instrument, n=6 production prompts, byte-identical arms):
  (a) **self-repetition loop** (repeats its OWN generated text) → frequency/presence penalties fix;
  (b) **prompt-copy policy** (copies PROMPT spans — backward-copy/instruction-echo) → penalties
  mathematically can't bite (they only tax repeated GENERATED tokens); it's a learned behavior,
  only training fixes it. A "repetitive" candidate must be classified (a) vs (b) before any
  sampling-config rescue attempt — instrument: `webgpuEchoAB` via nexus-sense MCP dispatch, or any
  paired same-engine A/B with penalties as the only variable.
- **Small-model system prompts:** no meta-instructions about interpreting the user (the model
  reasons about the instruction instead of the message — "answer the most recent message" caused
  universal deflection); concrete tool list + one explicit call example; never place a capability
  caveat adjacent to a tool name.

## ⚑ QUEUED CANDIDATES — check before onboarding anything new (added 2026-08-13)
Read memory `detllm-twil-candidates` FIRST. Queued: **TwiL-LM 3B** (webAI, HF; formal-logic; 65K ctx;
exact-format answering 52.0-vs-7.0 = the format-compliance trait our small candidates lack → strongest
fit is the JUDGE/VERIFIER apprentice slot; tool-call parsing unknown — the parser gate decides the
router slot; ⚠️ webAI Non-Commercial License v1.0 — internal training/eval OK, read before any serving).
Also **DetLLM** (int-only deterministic inference) as a SERVING-TECHNIQUE spike for candidate HF-Space
serving — deterministic evals collapse bench noise. Onboard TwiL-3B first (1.7B has only 8K ctx).
