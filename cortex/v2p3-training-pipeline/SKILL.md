---
name: v2p3-training-pipeline
description: Operate the V2-P3 base-model bake-off — train LoRA adapters on candidate bases per slot, eval each on its SLOT-APPROPRIATE lenses, gate vs baseline, pick the smallest base clearing the gate. The runbook + full defect ledger (D1-D20) + GPU cost guards so you never re-thrash the config issues. Use for any V2-P3 bake-off / apprentice-training-pipeline run.
---

# V2-P3 Base-Model Bake-off — Operational Runbook

Trains LoRA adapters on N candidate bases per slot (router / reasoner / own-inference),
evals each on its slot-appropriate lenses, gates vs a baseline, picks the SMALLEST base
clearing its gate. Feeds the SHADOW→INTERN→APPRENTICE→JOURNEYMAN(3 tracks)→MASTER ladder.
Companion skills: `candidate-model-onboarding` (add a NEW base to the roster), `cortex` /
`cortex-bench` (drive the harness), `huggingface-spaces`. Detail memory:
[[base-model-bakeoff-v2p3]], [[decision-capture-layer]], [[jspace-jlens-distillation]].

**Cardinal ethos (proven this program): BAKE ONE ARM FIRST.** A one-arm pilot
(`--candidate <slug>`) found 12 pipeline defects for ~$0.35 GPU before the full matrix. Never
fire all N arms on an unproven pipeline.


**★★★ SETTLED FINDINGS (2026-07-14, post-D28 — the program's load-bearing conclusions):**
- **TWO DUTIES compete for 1B capacity** → separate LoRA adapters on ONE frozen base (adapter-library = cheap per-duty MoE, caller picks duty).
- **TURN-PRED SOLVED**: R24 beats untrained base +0.0392 (ε=0) AND teacher +0.0122 (No-Think t0.0). Deployable MASTER; promote to INTERN shadow next.
- **AGENT was a MODE BUG (D28), not capacity**: all R19-R24 ran ENABLE_THINKING=0. Untrained base THINK-ON @t0.3 sweeps the agent suite (D22/consume/Lens B 100%). No-Think SFT DAMAGED invocation reflex (temp-scrambled) but dual-mode Lens D = NO j-space eviction (representations intact, sampling pathway perturbed). Agent slot: serve base think-on; R25 = careful polish not rescue; 2B RETIRED for agent duty.


## Files (all under `nexus-terminal/modules/database-ai/training/`)
| File | Role |
|---|---|
| `v2p3/runBakeoff.ts` | orchestrator; phases `pack\|train\|register\|evalA\|evalB\|gate\|decide` |
| `v2p3/config.ts` | `SLOT_ROSTERS`, `CORPUS_MIXTURE`, `LORA_RECIPE`, `HUB`, `INCUMBENT` |
| `baseModelRegistry.ts` | candidate cards (arch/license/tool-family/sampling/VRAM/quirks) |
| `packCorpus.ts` | corpus builder (router + reasoner .jsonl); `--mixture`, `--min-outcome`, holdout split |
| `scoreHoldout.ts` / `gradeApprentice.ts` | **reasoner** Lens A (next-turn F1) + paired gate |
| `routerHoldout.ts` / `gradeRouter.ts` | **router** Lens R (AST match) + dual gate |
| `v2p3/train-space/train_lora.py` | the GPU trainer (runs ON the HF Space) |
| `gradeStats.ts` | shared bootstrap-CI + FWER gate (`pairedGate`, `graduate`) |

## Spaces / repos / baseline (<hf-org> HF org)
- **Trainer**: `<hf-org>/v2p3-trainer` — runs `train_lora.py` at boot from env vars. a10g-small
  for router/1B; **l4x1 for reasoner or 16k prefill** (1B OOMs T4 at 16k). PAUSE after each phase.
  **COST GUARDS (2026-07-10, both built in — verify before ANY run):** (a) the job SELF-PAUSES
  the Space on completion/failure (`app.py _self_pause` → `HfApi().pause_space(SPACE_ID)`);
  (b) checkpoints push to the ADAPTER_REPO hub every `SAVE_STEPS` (default 60,
  `hub_strategy="checkpoint"` → `last-checkpoint/`) and `_prefetch_resume()` resumes on boot —
  a container recycle (~1.5h runtime window) costs ~5min reload, not the run.
- **Serve**: `<hf-org>/v2p3-serve` — the model-agnostic template (`omniclaude-v4/scripts/hf-space-template/`,
  now with **peft+bitsandbytes** so it loads ADAPTER repos directly). Swap `MODEL_ID` per adapter.
  **Must be PUBLIC** (private → `@gradio/client` "metadata could not be loaded"). t4-small. PAUSE after eval.
- **Base bench**: `<hf-org>/bench-<slug>` (from candidate-model-onboarding).
- **Corpus**: `<hf-org>/v2p3-corpus-<tag>` (train split only — holdout NEVER uploaded).
- **Adapters**: `<hf-org>/v2p3-<tag>-<slug>`. **Done signal = trainer SELF-PAUSE + ROOT `adapter_model.safetensors`** — NOT a tree grep: checkpoint-to-hub pushes `last-checkpoint/adapter_model.safetensors` from step 60, so file-presence fires ~8% into training (run-r13.sh has the correct `wait_selfpause` + root-file check).
- **HARD PREREQUISITES (enforced, 2026-07-12)**: `scoreHoldout` + `routerHoldout` EXIT 2 without `--temperature` (no default). Rows carry `eval_temperature` (`record_turn_prediction_v2`; legacy reducer kept for deployed live surfaces — their rows are None). `gradeApprentice` + `gradeRouter` REFUSE to pair rows at mixed temps, and refuse temp-stamped-vs-legacy or all-legacy pairings without `--allow-legacy-temp` (only for historical 0.7/0.3-era re-grades you KNOW share the instrument). The gate cannot silently compare two instruments anymore — a wrong setup now fails loudly BEFORE spend, not quietly after.
- **PER-CANDIDATE EVAL TEMP (D20 corollary)**: eval temperature is a PER-CANDIDATE property set BEFORE the run, pulled from `baseModelRegistry.sampling.temperature` (each candidate's onboarding-swept value — MiniCPM5/LFM2.5 0.3, Qwen thinking family 0.6, Phi 0.0; thinking models can DEGRADE near-greedy, sweep both directions). `runBakeoff` passes it to scoreHoldout + routerHoldout automatically; manual eval invocations MUST pass `--temperature <registry value>`. The deployable unit is model+sampling config — candidates in the same bake-off legitimately eval at different temps, and the teacher runs at ITS deployment temp. Registry tuples with minP/repetitionPenalty are only partially honored by the serve Space (temperature only) — at greedy, missing repetition-penalty can loop small models.
- **Distill-teacher (the high-value-row arm) = REASONING model, from `v2p3/config.ts DISTILL_TEACHER`** (default deepseek-v4-pro; workflow/orchestration classes → claude-sonnet-4-5). Non-reasoning teachers transfer ~nothing at this student scale (arXiv:2607.08268, verified). Distinct from the GATE baseline below — never conflate the two roles.
- **Teacher baseline** (reasoner gate): **`deepseek-v4-flash` PINNED** via `https://api.deepseek.com/v1`, `predictor='teacher'`. (`deepseek-chat` is a DEPRECATED alias that today redirects to v4-flash — verified live 2026-07-12; never ride the alias, a silent repoint would move the gate baseline. `deepseek-v4-pro` is the pro tier — panel-probed for bar sensitivity, see D20.)
- **Router profile** (lean persona + tasks + fixtures for evalB/router): `$WORKSPACE/.bench-hosting/router-profile/`
  (`.cortex/ROUTER_PROMPT.md`, `router-tasks.json`, `data/{alpha,beta}.json,flag.txt`).
- **Eval transport**: PROXY-FREE — `training/hfSpaceTransport.ts` calls the serve Space's gradio REST
  directly and reuses the harness 6-family parser (incl. gemma-4 channel) (`omniclaude-v4/packages/core/dist/models/hfSpace/normalize.js`).
  `routerHoldout`/`scoreHoldout` take `--space <hf-org>/v2p3-serve`. The old localhost `oai_proxy.py`
  (:8100) is LEGACY (still works via `--base-url`, but the harness got a native `hf-space` transport
  in 40c173722 and the eval scripts now go direct — do NOT reintroduce the proxy).

## Run commands
```bash
export PATH="$WORKSPACE/.local/bin:$PATH"
export GLIBC_TUNABLES=glibc.rtld.optional_static_tls=65536
export HF_TOKEN="${HF_TOKEN:-$HUGGINGFACE_TOKEN}"
export CORPUS_DEID_SALT="$(head -c16 /dev/urandom | base64)"   # per-run random; pack needs it
cd nexus-terminal/modules/database-ai/training

# DRY plan (no GPU): omit --go
npx tsx v2p3/runBakeoff.ts --tag <tag>
# ONE-ARM PILOT (do this first): all phases for one candidate
npx tsx v2p3/runBakeoff.ts --tag <tag> --candidate <slug> --phase <p> --go
# FULL MATRIX: minus --candidate
npx tsx v2p3/runBakeoff.ts --tag <tag> --go
# per-phase re-run (checkpointed in v2p3/runs/<tag>/, so completed phases skip):
#   --phase pack | train | register | evalA | evalB | gate | decide
```
Env knobs: `EVAL_LIMIT` (points/arm, 0=full ~566), `EVAL_CONCURRENCY` (default 6),
`CORPUS_MIXTURE`, `CORTEX_MIN_OUTCOME`. Eval endpoint = `--space` (direct, preferred) or
`--base-url`/`LOCAL_MODEL_BASE_URL` (OpenAI-compat: API teachers, LM Studio, legacy proxy).
Standalone run scripts (checkpointed): **`v2p3/runs/run-r13.sh` is the CURRENT template**
(ETL→pack→upload-verify→train→self-pause done-signal→D17 serve→Lens A→gate; trap touches serve
ONLY). run-r11.sh/run-r11b-reasoner.sh are historical — r11b's wait_adapter tree-grep now
false-fires on the step-60 checkpoint push.

## Per-slot evals — CRITICAL, don't mismeasure (D10)
A router is a routing COMPONENT (call right tool+args, STOP). A reasoner is a general agentic
COMPLETER. **They need different lenses — a perfect router scores 0 on a task-completion verifier.**

| Slot | Lenses | Gate |
|---|---|---|
| **router** | **Lens R** = `routerHoldout.ts` (single-turn AST tool+args match, partial credit) + Lens C (WebGPU) | `gradeRouter.ts` — **beats base (CI-low>0) AND clears floor (≥0.7)**; baseline = BASE model (no teacher-router) |
**RUN/EVAL/J-SPACE FOOTGUNS (2026-07-13, unrecorded-till-now):**
- **DRIVE GRADUATES ONLY VIA THEIR ONBOARDED CARD (D25 methodology incident, 2026-07-13).** The generic `hf-space` card has NO defaultTemperature (env HF_SPACE_TEMPERATURE only) → the transport falls through to 0.7 = the D20 sampling tax re-committed; the onboarded card (`minicpm5-1b-space`) carries the swept 0.3. AND `CORTEX_SYSTEM_PROMPT_FILE`/`PROJECT_PATH` are read by OrchestratorFactory IN THE SERVER PROCESS at boot — passing them on the CLI/bench invocation does NOTHING (you silently run the full-stack prompt = MiniCPM5-class known-0/300). Correct drive shape: serve adapter → boot server with `HF_SPACE_ID_<SLUG>=<serve-space> HF_SPACE_EXPECT_MODEL_<SLUG>=<adapter-repo> MENTORSHIP_ENABLED=false PROJECT_PATH=<profile> CORTEX_SYSTEM_PROMPT_FILE=<prompt>` → `cortex --new --quiet -m <card-id>` → cortex-bench throttling confound scan. `v2p3/d25-gate.sh` is the reference implementation. An 0/6 measured on the wrong card is NOT a model result.
- **HOLDOUT SIZE DRIFTS WITH THE LAKE.** Holdout = session-hash (mod 10 == 0), so ingesting new sessions ADDS holdout points: 566 (pre-07-12-ingest) → 727 (post). R19 was scored @566, R20/R21 @727 → raw avgMatchScore/modelZeros% are on DIFFERENT denominators, NOT directly comparable. The GATE meanDelta IS comparable (pairs on session:turn vs teacher@t00 → ~650 paired for all), but **before declaring a cross-run CHAMPION, RE-SCORE every contender AND the teacher on the CURRENT holdout** (pin `--holdout-now` to reproduce). Don't compare R19@566 zeros% to R21@727 zeros% naively.
- **TEACHER BASELINE must be re-scored on the grown holdout too** — `teacher@t00` currently caps pairing at ~650. For full pairing on the 727 holdout, re-score `teacher@t00` (deepseek-v4-flash @t0.0 @512-tok — the 64-tok default TRUNCATES its greedy preamble → 667/668 zeros, D20 artifact).
- **EVAL-SCRIPT EXIT-TRAP PAUSE RACE:** `trap 'pause serve' EXIT` fires when the script is KILLED (session restart) MID-SCORING → pauses the serve space → all remaining points infraFail → 0 scored. **Pause serve only AFTER scoring completes, never in a bare EXIT trap** (run-r20-eval2.sh is the clean pattern; the derived recovery scripts had this bug, cost R20 two attempts).
- **--distill-file / --system-prompt-file rows BYPASS packCorpus.eligible() consent filter** (pushed to reasonerLines pre-filtered). The GENERATOR (distillTargets/systemPromptLayer) must enforce consent itself — they do (own eligible()), but any new layer-file generator MUST too.
- **J-SPACE probe quirks:** (1) `FIT_N` MUST match across runs to compare presence scores (calibration used 60); (2) fit base+ALL adapters in ONE probe run (comparable lenses from the same base fit) — ADAPTER_ID is comma-separated; (3) a10g REQUIRED (t4 stalls on the backward); STANDARD-ARCH only (MiniCPM5 dense-Llama OK, hybrid Qwen3.5 fails); (4) `gradeJSpace --adapter <KEY>` where KEY is the SHORT readout name = adapter id with `v2p3-` and `-minicpm5-1b-reasoner` STRIPPED (e.g. `r20-distill`, `r19-infosft`), NOT the full id; (5) runid = `mmdd-hhmm`; latest jspace-*.json auto-picked unless `--runid`; (6) preservation metric is presence-by-ANY-token (forgiving) — a token displaced from top-20 still "present" via a weaker cluster synonym.
- **INFOSFT / DISTILL_LOSS / FORMAT_AUGMENT persist as trainer-Space env vars** — any run wanting them OFF must SET them off explicitly (they don't reset between runs).

**D28 + THE MODE DOCTRINE (2026-07-14, operator-caught — read before ANY MiniCPM5/hybrid-thinker run):**
MiniCPM5-1B is a hybrid Think/No-Think model; the serve template defaults `ENABLE_THINKING=0`
and `train_lora.py` rendered without `enable_thinking` — so ALL of R19-R24 (training AND every
eval/gate/probe) ran No-Think. Decisive probe: the UNTRAINED base, THINK=1 @t0.3/1024tok,
performs the full agent loop perfectly incl. consume-grounding ("port 8443" read FROM the
result) — the exact behavior four arms failed to train in. The 1B-capacity/dissociation
conclusions are SUSPECT until re-measured. Doctrine going forward:
- **Mode is part of the instrument, like temperature (D20).** Predictor tags carry it:
  `r23@t03-think` vs `r23@t03`. NEVER pair/compare across modes; the existing ledger IS the
  No-Think table — think-on scores form a NEW league table beside it.
- **Per-DUTY production modes:** turn-pred/reflex duty = No-Think (latency; R24's teacher-beat
  is internally valid there and STANDS). Agent/tool duty = Think-ON (the base's tool-use edge
  lives there per its own model card).
- **Training renders MUST match the duty mode** (train_lora: pass enable_thinking to
  apply_chat_template per-arm; a think-on eval of a No-Think-trained adapter measures
  fine-tune damage to think circuitry, not raw ability — label it as such).
- **Re-gate order: BASE first, think-on, full agent suite** (D22 + consume probe + Lens B
  lean-router, temp swept BOTH directions per the thinking-model rule) — if the base clears
  untrained, the agent slot needs polish (vocabulary/format), not rescue, and R25 is designed
  accordingly. Then champions (R23/R24) think-on as the damage-check.
- Thinking consumes output tokens: probes/evals need max_tokens >=1024 or the answer starves
  (the same budget trap as the reasoning-judge and teacher-truncation defects).

**R25 SPEC (the conclusive last 1B attempt — design locked 2026-07-14, fire order AFTER the D28 think-on base re-gate):**
Two arms, per-duty (the dissociation doctrine):
- **R25-agent (think-ON train + eval, NEW league table):** base = candidate-compare
  `MiniCPM5-1B` release vs **`-SFT` pre-OPD checkpoint** (OPD packed the release; the SFT
  checkpoint may take new skills with less eviction). Method changes (Sleep, arXiv:2606.03979):
  (1) **freeze-and-stack** — new skill trains in a NEW adapter composed over the FROZEN prior
  (train_lora: load prior adapter frozen, train fresh LoRA on top) instead of overwriting;
  (2) **rank sweep r16 vs r64/α128** (Sleep runs r64; adapter capacity is a paper-backed
  eviction suspect); (3) **UltraData-SFT-2605 replay slice** (~10-15% mass) against forgetting;
  (4) chat_bot mass CAPPED for this arm (R24 lesson); (5) layers: grounded-consume + CORTEX
  invocation + doc-grounded (docs-in-system-prompt → doc-grounded action). Gates: D22 +
  consume probe + Lens B lean-router, all think-on @swept temp, tags `@tXX-think`.
- **R25-turnpred (No-Think, only if chasing margin):** R24 lineage + replay slice; R24 already
  MASTER-bar — this arm is optional polish.
- **R26+ data upgrade (Sleep REM):** importance-scored selection over the lake/failure stream
  (gradient-scored dream selection analog) instead of ingest-everything packing.
If R25-agent STILL dissociates/fails consume with think-on + freeze-stack + r64 + replay →
the 1B capacity conclusion is EARNED; move agent slot to 2B (qwen3.5-2b control arm) with a
clean conscience. SPS (arXiv:2607.01218) = pretraining-only, candidate-watch (lil-lab/sps).

**FREEZE-AND-STACK IMPLEMENTATION (Sleep NREM in LoRA form — for R25-agent train_lora.py):**
The eviction/damage from R19-R24 came from OVERWRITING one adapter surface. Instead compose
a NEW adapter over the FROZEN prior so old skill is immutable and only new params learn:
```python
from peft import PeftModel, LoraConfig, get_peft_model
base = AutoModelForCausalLM.from_pretrained(BASE, ...)          # or the -SFT checkpoint
if PRIOR_ADAPTER:                                               # stack over a graduated arm
    base = PeftModel.from_pretrained(base, PRIOR_ADAPTER, is_trainable=False)  # FROZEN
    base = base.merge_and_unload()                             # bake prior in, then fresh LoRA on top
model = get_peft_model(base, LoraConfig(r=RANK, lora_alpha=ALPHA, ...))  # only THIS trains
```
Env: `PRIOR_ADAPTER_REPO` (empty = train fresh on base), `LORA_RANK`/`LORA_ALPHA` (sweep 16/32 vs 64/128).
Render MUST match duty mode: `apply_chat_template(..., enable_thinking=(DUTY=='agent'))`. Replay:
mix a `UltraData-SFT-2605` slice (~10-15% mass) into the corpus against forgetting. Verify the
frozen-prior grads are zero (only new-LoRA params in optimizer) before spending GPU.

**★ R25a CONCLUDED (2026-07-16) — THE AGENT-DUTY RULE: DO NOT SFT THE AGENT DUTY AT 1B.**
Arm A (r16/α32, think-on corpus w/ on-policy harvested think spans, declared-menu rendering) was the
best-constructed arm of the program and STILL failed the pre-registered exit: A/B menu-selection
adapter 9/12 vs base 8/12 (base near-ceiling — declared-menu descriptions suffice; vocab "graft"
adds ~nothing) while the d25 harness gate REGRESSED (base PASS reads-file→8443; adapter FAIL, zero
tool calls). D28 thesis confirmed twice: the base's native think-on agency is the asset and SFT
subtracts from it. **AGENT DUTY DEPLOY = untrained base, think-on, t0.3, via the onboarded card +
ENABLE_THINKING=1.** Arm B (r64) deliberately NOT fired — regression-without-gain is not a capacity
symptom. Future agent-arm research (not need): the -SFT pre-OPD checkpoint as graft base. Turn-pred
duty unaffected (R24 = MASTER, No-Think t0.0 — separate adapter, separate mode, separate table).
- **D29 (fixed):** packer emitted `thinking`; template renders only `reasoning_content` → all lake
  thinking silently dropped from training text in every prior run. Packer now dual-emits; train_lora
  has a fallback. PROBE THE TEMPLATE with real rows before any new pack (D26/D29 family).
- **D30:** enable_thinking is generation-prompt-ONLY (no-op at train render). Targets must carry
  real think spans (on-policy harvest, STaR rejection-sampling — harvest-space/) or you teach
  skip-thinking to a think-served model.
- **D31 — GLIBC_TUNABLES POISONS NODE:** the Rust/spacetime static-TLS tunable EINVALs node
  pthread_create (noise + degraded pool; tainted a gate verdict). NEVER export it globally in a
  script that runs node/tsx/cortex — scope to spacetime/cargo calls; strip with `env -u
  GLIBC_TUNABLES` at node launch sites (d25-gate.sh pattern).
- **Harvest infra (reusable):** <hf-org>/v2p3-harvest = batch job-at-boot Space (self-pause +
  chunk-resume + FAIL-FAST chunk-0 guards: spans==0 or acceptance<30% aborts in ~15min). FOOTGUN:
  job-in-a-thread looks IDLE to HF → sleep-timer fires mid-job (set --sleep-time 86400 + monitor
  keep-alive ping). Serve-space serial driving costs ~4x the batched job.

**LENS D CALIBRATED + D22 BEHAVIORAL GATE (2026-07-13):** Lens D presence is NECESSARY BUT NOT SUFFICIENT — R20 passed Lens A (token-F1) AND Lens D (j-space instruction_frame restored 0.273→1.00) while STILL behaviorally failing to invoke tools under an instructional system prompt (D22). **ALWAYS run the D22 BEHAVIORAL GATE (`v2p3/d22-gate.py`): serve + tool-loop bisect, MUST emit a real tool call under a router-style system prompt, not fabricate.** Add it to every reasoner eval (wired in run-r21.sh). The corpus root cause: ZERO system-role rows → `systemPromptLayer.ts` wraps real tool-calling turns with 8 varied instructional sys prompts (real tool call = target), merged via `packCorpus --system-prompt-file` (layer=system_prompt). R-ledger: R19 graduated (-0.0103, format 7.8%z), R20 distill graduated (-0.0099, 1.1%z best-ever, Lens D pass), NEITHER beats teacher (ε=0); R21 = R20 recipe + system_prompt layer (D22 fix). Serve un-pause = `curl POST https://huggingface.co/api/spaces/<owner>/<space>/restart?factory=false` (plain `hf spaces restart` does NOT wake a PAUSED space). Champion = R20 (deployment) / R21 (if D22-PASS = first drivable).

**LENS D — j-space capability-preservation (V2-P13, added 2026-07-12; ADVISORY until calibrated on 2-3 arms):** `runBakeoff --phase lensD` (reasoner-tier arms only) drives `<hf-org>/jspace-probe` (job-at-boot, self-pauses, ~$0.5/arm, ~27min: fits a Jacobian lens on BASE and base+adapter, 6 probes incl. the production turn-pred prompt) → `gradeJSpace.ts` verifies the base's CRITICAL working-memory clusters survived fine-tuning (mid-late-layer presence ratio ≥0.5): `error_detection` on the bug probe (the strongest sub-1B j-space signature — R19 EVICTED it despite passing Lens A = the motivating regression) + `instruction_frame` on the tool-loop probe (its removal = the D22 answer-fabrication signature); `dialogue_machinery` on turn-pred = installation check (informational). N/A if the BASE never held a cluster (min-base 0.2). `--enforce` flips advisory→hard gate. Clusters/probes: `gradeJSpace.ts JSPACE_CLUSTERS` + `jspace-probe/app.py PROBES`. Standard-arch bases only (hybrid linear-attn backward impractical); fit n=60 = demo-grade, treat clusters not tokens.

| **reasoner** | **Lens A** = `scoreHoldout.ts` (next-turn F1) + **Lens B** = evalB (task-completion bench) + Lens C | `gradeApprentice.ts` — paired vs TEACHER (deepseek), **NON-INFERIORITY ε=0.03** (operator decision 2026-07-11: apprentice replaces teacher calls at ~zero cost, so the bar is "within ε", shift-transform permutation test; `--epsilon 0` = strict superiority, which MASTER graduation keeps; router gate unchanged = must BEAT base) |

Run router evals: `routerHoldout --predictor <adapter> --space <hf-org>/v2p3-serve --model <adapter-repo>`
for BOTH the adapter AND the base → `gradeRouter --candidate <adapter> --baseline <base>`.

## The serving chain (evalA / evalB / router) — PROXY-FREE
1. `hf spaces variables add v2p3-serve --env MODEL_ID=<adapterRepo>` + `hf spaces restart` → wait
   `/config` returns **200** (NOT container stage — stage lies during init).
2. **evalA / routerHoldout**: `--space <hf-org>/v2p3-serve` (direct gradio REST via
   `hfSpaceTransport.ts`; no local server). Legacy `--base-url` path kept for LM Studio/API teachers.
3. **evalB additionally needs a HARNESS server on :4000** (the bench does NOT auto-start it — that
   was a live `fetch failed`): boot from `omniclaude-v4/packages/server` with
   `HF_SPACE_ID=<serve> HF_SPACE_REASONING=true PROJECT_PATH=<router-profile> CORTEX_SYSTEM_PROMPT_FILE=<…/ROUTER_PROMPT.md> setsid nohup node dist/index.js &` — the harness's NATIVE hf-space
   transport (no proxy), then confirm the `hf-space` card is registered (`/models`).
4. PAUSE serve + kill :4000 (by PORT: `lsof -ti:4000`) when done.

**⚠ STDB /sql OPTION DECODE (cost an hour, 2026-07-11): `Some = [0, value]`, `None = [1, []]`
(array form; dict form `{some:v}/{none:[]}` also appears).** An inverted ad-hoc decoder read
1,852 present r2_refs as ZERO and triggered phantom write-path debugging. NEVER hand-roll it —
copy `un()` from scoreHoldout.ts (handles both forms), and when a count looks impossible,
print ONE RAW row before trusting the decoder.

**⚠ SHELL FOOTGUN (cost a whole night, 2026-07-10): NEVER `pkill -f <literal>` where the literal
appears in the SAME command's text** — pkill matches the wrapping shell's own cmdline and kills it
(exit 144, no output, files never written). This fabricated false "environment constraints"
(120s cap / netns isolation / bg-reaping) that were all artifacts. Kill by PORT (`lsof -ti:PORT`)
or bracket-escape the pattern (`pkill -f "[o]ai_proxy"`). Also: post-compaction, RELOAD this skill
+ check the session transcript BEFORE debugging "broken" infra that worked pre-compaction.

## THE 19-DEFECT LEDGER — all FIXED (never rediscover these)
| # | Symptom | Fix |
|---|---|---|
| **D1** | unsloth `DownloadStallError` (hybrid-VLM snapshots, even w/ `HF_HUB_DISABLE_XET=1`) | retried `snapshot_download` PREFETCH before the unsloth import (`train_lora.py`) |
| **D2** | whole-repo `load_dataset` pyarrow schema clash + trains BOTH corpora | `CORPUS_FILE` per slot (router→`router-corpus.jsonl`, reasoner→`reasoner-corpus.jsonl`), set by runBakeoff |
| **D3** | 4-bit adapter unservable (`bitsandbytes` missing) | added to the serve template requirements |
| **D4/R60** | recorder wrote turn-METADATA into `selected_args_json`, not tool args → fine-tune emits garbage | `CortexOrchestrator.ts` records first-tool + real args (**published nexus-cortex 4.47.4**); historical re-derived in `exportHarnessRouterSamples.ts` from `.cortex/sessions/<id>.jsonl` (`block.toolUse.{name,input}`) |
| **D5** | `record_turn_prediction` 400 (bare-string Option; missing `prefill_provenance`) | sum-type encoding `{some}/{none}` + 11th arg `{some:'none'}` (`scoreHoldout.ts`) |
| **D6** | evalA serial (~1 pt/min) + no `--limit` → days × 8 arms | concurrency pool + `--limit`/`--concurrency` (env `EVAL_LIMIT`/`EVAL_CONCURRENCY`); runBakeoff passes them |
| **D7** | gate verdict null — no incumbent baseline predictions | score the TEACHER: `scoreHoldout --predictor teacher --model deepseek-v4-flash --base-url https://api.deepseek.com/v1 --api-key-env DEEPSEEK_API_KEY` |
| **D8** | `scoreHoldout` silently DROPS unparseable predictions → survivorship bias (5%-answerer passes) | model-failure (text, no prediction) records `match_score=0`; infra-null still dropped (confound) |
| **D9** | evalB was a STUB (flag, no invocation) | implemented in `phaseEval`: `cortex autoresearch bench --split holdout --model hf-space` on the served adapter |
| **D10** | router graded by the reasoner's task-completion verifier → perfect router scores 0 | per-slot evals — router suite `routerHoldout`+`gradeRouter` (above) |
| **D11** | reasoner corpus `load_dataset` fails pyarrow (nested/variable multi-turn schema) → blocks ALL reasoner arms | `train_lora.py` loads JSONL MANUALLY (`hf_hub_download`+json), renders via chat template with per-row try/except, `Dataset.from_dict({text,weight})` |
| **D12** | `CORPUS_MIXTURE` cosmetic (logged, never applied) → reasoner corpus ~95% NPC-chat after fanout | `packCorpus.applyMixture` scales `meta.weight` to hit target MASS per layer + `train_lora` `WeightedRandomSampler`; runBakeoff passes `--mixture`; ratio bumped `general=0.7` |
| **D13** | `routerHoldout.sql()` called `spacetime sql … --json` — flag doesn't exist (CLI v2) → instant crash misread as a "hang" | HTTP `POST /v1/database/<module>/sql` w/ CLI token (scoreHoldout's pattern) + array-form Option unwrap |
| **D14** | routerHoldout only parsed the 5 NATIVE tool-call families, but router fine-tunes emit the CORPUS TARGET format `{"tool":X,"args":Y}` → a corpus-faithful router scores 0 | `parseCorpusToolJson` (balanced-brace outer object, string-encoded args, one-level wrapper unwrap) tried after the native parser |
| **D15** | npc fanout stores `decision_data` VERBATIM in `selected_args_json` ("parsing deferred to pack time" by design) but the packer never unwrapped → training targets carried `result_preview`/score metadata (model hallucinates them) + eval expected-args matched wrapper keys. 1036/1338 router rows | `routerArgs.unwrapRouterArgs` shared by `packCorpus` (bare-args OBJECT targets) + `routerHoldout` (bare expected args). Reducer untouched (fix-at-read is the designed seam) |
| **D16** | `wait_adapter` timeout (90min) < actual train time (~3h reasoner) → wait "fails", eval phase proceeds against a Space still serving the BASE → adapter scores are silently base scores; the exit trap then PAUSED the mid-run trainer (lost the GPU spend) | wait budget is a per-run PARAMETER sized to the corpus (run-r11b), timeout = HARD ABORT of the eval (never proceed), and no side-effecting cleanup on the wait path |
| **D17** | nothing verified WHICH model the serve Space actually loaded → an eval can silently score the wrong model (D16's failure was only caught this way) | serve template prepends `[MODEL=<repo>]` to completions; `serveModel()`/run scripts probe once after `/config` 200 and ASSERT the header matches the requested repo before any eval |
| **D18** | R11 reasoner fine-tune LOST the strict `SUMMARY:`/`PREDICTION:` format (emitted `**PREDICTION**:` markdown → 101/120 Lens A zeros, coherent content). NOT an eval bug: the strict regex is the PRODUCTION contract (`turnPrediction.ts` browser twin parses apprentice output with the same regex — a lenient eval would hide a deployability regression). Teacher also loses 102/566 to format | Fix at the CORPUS: `packCorpus` emits a **meta_task layer** — per train-split session, ≤8 consecutive-turn pairs → (exact production prompt → strict-format target, ground-truth next user turn as prediction); `CORPUS_MIXTURE` gains `meta_task=0.10`. Contract now in ONE shared module `turnPredictionContract.ts` (scoreHoldout imports it; keep the browser twin in lockstep). Raw text IS recorded on parse-miss (`prediction \|\| out.slice(0,2000)`) → lenient re-scores are free offline DIAGNOSTICS, never the gate |
| **D19** | fine-tunes EMIT harness scaffolding: literal `</system-reminder>` tokens, memorized reminder text as final answers, transcript-replay loops in harness-shaped contexts (r13-agentic-probe: lean routing INTACT, loop control broken; full-stack hallucinates repo work) — corpus rendered transcripts VERBATIM incl. `<system-reminder>` blocks + tool furniture | `stripScaffolding()` at the `scrub()` choke point in packCorpus (whole blocks: system-reminder/task-notification/local-command-caveat; unwrap command tags; drop dangling halves) — every packed path covered incl. historical rows, no re-ingest. Verified on full pack: zero literal tags; prose MENTIONS of the words + grep-pattern args legitimately survive |
| **D20** | Eval TEMP mismatched deployment: `scoreHoldout` hardcoded 0.7 for a machine-parsed structured-output task while onboarding PROVED format-fragile 1B bases need near-greedy (MiniCPM5 100/300@0.9 → 250/300@0.3). Asymmetric tax: frontier teacher robust at 0.7, 1B candidate pays a zero-cliff (off-format draw → whole point 0) → depressed mean AND inflated CI (the binding constraint: half-width ~0.008 at n=566) — LR-sweep ranking (12.0/13.8/17.2% zeros at 1e-4/2e-4/4e-4) was substantially THIS tax | `scoreHoldout --temperature` + `--max-tokens` (default 0.7 = old instrument preserved); measurement condition carried in the predictor tag (`r18@t02`) so regimes can't silently pair. **NEVER compare scores across temps — a temp change is a NEW league table, both sides re-scored** (`runs/run-rescore-t.sh`: mini-sweep {0.0,0.2,0.3} → 4-teacher panel → full re-score + gates). Gate semantic: measure at the temp production would USE (near-greedy for a structured contract) |

Non-numbered but load-bearing: **SFT outcome floor** (`packCorpus --min-outcome 0.5`; drop confirmed-failures from imitation, keep null=unknown, failures→DPO later). **stale-Monitor race** (killing a worker doesn't disarm its Monitor's side-effecting cleanup branch → key watchers to the CURRENT pid). **`CORTEX_MODE=stateless` is curl-benchmarking ONLY** (the CLI needs the persistent server → 503). **ESM env-at-module-load** (export card env BEFORE booting the harness server). **`--candidate` train-phase RESTARTS the trainer** (sets env+restart before poll) → re-pause after any checkpoint rerun.

## Corpus pipeline (lake → training rows)
- **Reasoner corpus** = `reasoner_training_samples` (STDB) + `session_transcripts` (STDB), packed as multi-turn ChatML.
- **Router corpus** = `router_training_samples` (STDB), packed as `(input → tool+args)`.
- **npc_decisions fanout**: FORWARD is auto (`record_npc_decision:51 → upsert_training_sample_for_decision` on every new decision — no manual curation). BACKFILL the backlog: `spacetime call nexus-nexus-cortex backfill_fanout_decisions -- <limit>` repeatedly until drained (idempotent). chat_response→reasoner, tool_call(with context)→router; context-less skipped (guard). Ran this → reasoner 0→12,634, router 392→1,410.
- **Router args** come from the harness cortex-samples (`exportHarnessRouterSamples.ts --go` → `ingest_router_samples_batch` reducer; re-derives real args from sessions). Run after any recorder change.
- **Mixture**: `general=0.63/workspace=0.27/meta_task=0.10` (agentic Claude-Code = target skill; NPC-chat = diversity; meta_task = D18 format anchors — production turn-pred prompt to strict SUMMARY:/PREDICTION: target with ground-truth next user turn, cap `min(64,max(8,pairs/6))` per session; only multi-turn MAIN sessions yield pairs — 93% of lake sessions are single-row subagent trajectories by design). Weight-based, enforced.
- **Format augmentation (R16 lever, KAT-Coder arXiv 2607.05471 [[kat-coder-v25-techniques]])**:
  `packCorpus --format-augment <nativeFrac>` (env FORMAT_AUGMENT; default 1=off) renders a
  fraction of sessions' tool calls in NON-native surface forms (hermes-json / xml-attr /
  corpus-json) via `formatAugment.ts` — deterministic per-session (FNV hash), whole-trajectory
  consistent. Targets the R13/R14 harness-context collapse (model overfits ONE tool surface →
  degenerate `<tool name=` under a different framing). Uses the format specs we already own.
  meta_task anchors + D19 scrub untouched (anchors are a strict-format deployment contract, not
  interface overfit). Watch the AGENTIC probes, NOT Lens A (format ≠ next-turn F1).
- **R2 full-fidelity tier (ACTIVE since 2026-07-11)**: oversized turns (>1.5KB args / >2KB
  results inline caps) push their complete blob (full text + thinking + untruncated tool
  trajectories) to nexus-r2-storage at ingest; the row carries `r2_ref`; packCorpus re-joins
  at pack time via the TOKEN-GATED `GET /training/transcripts/<hash>.json` route (blobs are
  sharing:private — the public /file route 404s them BY DESIGN; that read route was the
  missing half for weeks and every earlier pack silently trained on truncated previews).
  Token: `TRAINING_INGEST_TOKEN` — worker secret + GH repo secret + `~/.claude/.etl-env`
  (600 perms, sourced by claude-etl-ingest.sh AND needed in env for any pack that should
  hydrate). Worker caps blobs at 256KB (larger = skipped, inline preview stands).
  **Pack-quality check: the summary's `r2Hydrated` count — 0 on a lake with refs means the
  token is missing from env or the route broke.** First validated pack: r2Hydrated=895,
  reasoner corpus +29% (35.3→45.4MB).
- **Lake maintenance**: `purge_session_transcripts(session_ref)` (admin-gated reducer) removes
  a session's rows (synthetic probes, mis-ingests). NOTE the SFT outcome floor (`--min-outcome`)
  reads `outcome_score` which transcript rows DON'T have — their `quality_weight` feeds the
  training WEIGHT instead (a low-quality transcript row is downweighted, not dropped).
- **Holdout split**: reasoner = session-hash mod 10; router = sample_id-hash mod 10. TRAIN split packed+uploaded; HOLDOUT recomputed from STDB by the evals (never uploaded — V2-P0 isolation).

## GPU / billing discipline (learned expensive — ~$10 lost 2026-07-10, [[feedback_gpu_cost_guards]])
- **Both trainer cost guards MUST be verified live before any run** (self-pause on job end +
  checkpoint-to-hub/resume — see the Trainer bullet above). NEVER restart a run longer than the
  ~1.5h recycle window without checkpoint+resume in place.
- **NO auto-retry of a failing GPU run.** When the operator is cost-sensitive: state the estimated
  $ and get an explicit go first. The $10 loss = 4 restarts of an uncheckpointed 3h run.
- NEVER couple a GPU job to the session lifetime (exit traps / Monitors that pause a MID-RUN
  trainer kill the spend — D16's trap did exactly this). Cleanup on the wait path must be
  side-effect-free; the JOB pauses its own Space.
- PAUSE the trainer + serve Spaces after EVERY phase. Verify stage via API (`/api/spaces/<id>/runtime`
  → `stage`+`hardware.current`), and audit ALL org spaces, not just the ones you touched.
- Rough prices: a10g-small ≈ $1/hr, t4-small $0.40/hr, l4x1 $0.80/hr. A router arm ≈ $0.05 train;
  the MiniCPM5 reasoner arm ≈ $1.50–3 (1–2 epochs, now recycle-safe).
- STDB: a 12K-row `packCorpus` takes >2 min via CLI — run with a long timeout / in background.

## HF SPACE JOB OPS — the 10-rule preflight (2026-07-24 jspace/jdistill saga, ~$3 of rediscovery)
Full detail: memory [[hf-space-job-ops-rules]]. Reference impls: `training/jdistill-arm/app.py`,
`training/jspace-probe/app.py`. Run this checklist on EVERY new/modified Space job:
1. **⚠ PERSIST TO A DATASET REPO, NEVER THE SPACE'S OWN REPO** — Space-repo uploads commit →
   queue a REBUILD → the rebuild REPLACES THE CONTAINER MID-RUN (silent delayed death; the saga's
   mystery post-persist kills). Logs/checkpoints/lens-caches → `<OUT_REPO>-logs` dataset. Reads
   from the Space repo are safe.
2. **Sleep timer counts HTTP traffic, not compute** — watchdogs keep-alive the APP URL
   (`curl <url>/config`) every cycle; `--sleep-time` ≥ job length regardless.
3. **Pin `python_version: "3.10"` in README frontmatter** when using version-pinned wheels (fresh
   Spaces default to newest Python → cp310 wheels rejected). `short_description` ≤60 chars or the
   README upload is REJECTED (leaving stale config silently). Proven GDN stack: torch 2.10.0+cu130
   + prebuilt causal-conv1d cu13torch2.10 + flash-linear-attention (zero source compile).
4. **`HF_HUB_ENABLE_HF_TRANSFER=0` for jobs** — hf_transfer failures are Rust PANICS (uncatchable,
   silent process death); use `snapshot_download` + retry loop (resumable, retries make progress).
5. **Pre-download ALL models BEFORE any GPU work** (fail-fast: download death = 2 idle min, not
   15 fitted min); exhausted retries → raise with a clear next-step message.
6. **`low_cpu_mem_usage=True, device_map={"":0}`** for monolithic-shard from_pretrained (default
   path ≈ 2× file size in HOST RAM → OOM-kill SIGKILL, no log line).
7. **Daemon-thread CUDA**: `torch.cuda.init()` + warmup + `torch.autograd.set_multithreading_
   enabled(False)` ('terminate called without an active exception' otherwise).
8. **jlens**: jacobians = layers 0..N-2 (clamp layer lists); fit BEFORE LoRA attach (fit freezes
   base params); FIT-ONCE-CACHE the jacobian dicts to the logs dataset (~$0.5/refit).
9. **`hf spaces variables add` restarts per-var and can silently fail** — set all, then VERIFY
   with `variables ls` BEFORE restarting (a mid-way boot gets a partial env → wrong-mode run).
10. **Wake PAUSED with `restart?factory=false`**; readiness = `/config` 200 not stage; design
    checkpoint/merge-resume across boots (stable RUN_ID + skip-completed) so restarts = resume.

## KNOWN-OPEN (before a TRUSTWORTHY full 8-arm matrix)
1. ✅ DONE (2026-07-10): per-slot eval+gate dispatch in runBakeoff (router→routerHoldout adapter+base via serveModel()+gradeRouter; reasoner→scoreHoldout+gradeApprentice; evalB per-slot task-sets).
2. ✅ DONE: serveModel()/pauseServe() automate the base-model pairing serve.
3. **More agentic (general) data** — 0.7 mass from few unique general rows MEMORIZES them; keep running the Claude-Code ETL (`scripts/claude-etl-ingest.sh`, +592 rows 2026-07-10) before each pack.
4. ◐ router-suite E2E: smoke-verified (limit 3-8, found D13-D15); full-scale first run = R11's eval phase.
   R11 router half DONE (adapter Lens R 0.106 vs base 0.136 → honest discard; checkpoints recorded).
5. R11-R17 CLOSED, **R18 (LR=4e-4) IN FLIGHT** (2026-07-12). Full-holdout league: R15/LR2e-4
   **-0.0304 = champion, 0.0004 outside ε** · R17/1e-4 -0.0324 · R13 -0.0329 · R14 -0.0349 ·
   R16/format-aug -0.0394 (format-aug HURT at 1B — rejected). Resume state + decision tree in
   [[base-model-bakeoff-v2p3]] RESUME-NOW block; next levers ranked in [[v2p3-next-levers-arxiv]]
   (InfoSFT token-weighting is next if the LR lever closes). run-r15/r17/r18 scripts reuse the
   UPLOADED corpus via the artifact-size gate (skip re-pack) = the controlled-A/B pattern.
6. DONE (2026-07-11): nexus-cortex **4.48.0 PUBLISHED** (tool-route verifier + gemma4 parser live on npm) — router Lens B unblocked on a stock install (cortex --version >= 4.48 passes the runBakeoff guard).

## What "success" → next (the ladder, incl. the research tracks)
Bake-off picks the slot winner (smallest base clearing ITS gate). Winner → SHADOW→INTERN→APPRENTICE→
duty-tracks→MASTER. **Track A/P12 (dSpark/DeepSpec speculative serving) attaches right after V2-P3**
(apprentice-as-draft → accept/reject = free DPO pairs). **Track B/P13 (j-space distillation +
agreement gate + recursive chaperone) attaches at INTERN, REASONER tier only** (routers are below the
~2B j-space floor). Failures → DPO stream (never SFT). See [[jspace-jlens-distillation]], [[dspark-vs-mentorship-training]].

---

## DELTA 2026-07-19→22 — production serving epoch + bench doctrine (read before any pipeline work)

**Ledger**: D21–D39 now PUBLIC in `public_proof_deficiencies` (canonical text:
`training/seedDeficiencyLedger.ts`; D26/D27 intentionally absent — writeups too thin). Highlights
future agents MUST know: D28 (mode is part of the instrument), D31 (mlc toolchain needs
`apache-tvm-ffi==0.1.10` EXACTLY), D32 (web-llm raw completions omit BOS — prepend literal `<s>`;
"garbage weights" was this), D33 (STDB table subscriptions created before connect are permanently
inert — fixed at factory), D38 (multi-adapter probe publishes key per graded adapter).

**Duty-instrument map (FINAL, D28 doctrine)**: turn-pred duty = No-Think t0.0 via R24 adapter
(`<hf-org>/v2p3-r24-grounded-minicpm5-1b-reasoner`, MASTER); agent duty = UNTRAINED BASE
think-on t0.3 (R25a trained arm REJECTED — SFT subtracts; R26+ = research). Never cross-compare
modes or temps; every result row carries its instrument.

**WebGPU production serving (task #86 DONE, live)**: own MLC conversion via
`<hf-org>/mlc-convert` Docker Space (cpu-basic, ADAPTER_REPO env = LoRA pre-merge;
`webgpu-serving/convert/`); artifacts `<hf-org>/minicpm5-1b-q4f16-MLC` (base, public) +
`...r24-merged-MLC` (public). Registry = `services/webgpu/WebGPUServingService.ts WEBGPU_MODELS`.
INTERN shadow LIVE fleet-wide (turn-pred default ON, opt-out): three-score rows
(match/agreement/summary_agreement) in `turn_predictions`; `<model>@live` scoreboard rows in
`turn_prediction_stats` (DBAI EVALS); serving configurator = DBTRAINER→CONTROL. First production
read (n=5): R24 = 100% echo-class failures (backward-copy/context-echo/instruction-echo) —
harness-corpus graduation did NOT transfer; R26 lever #1 = train on the exact production
`buildTurnPredictionPrompt` template (shadow rows are harvesting it).

**Probe/bench Space OPERATIONAL LAWS**: (1) results persist to a DATASET repo
(`<hf-org>/spec-bench-results` pattern) — uploading to the Space's OWN repo REBUILDS the
running Space (restart-loop); (2) check for UNGRADED result JSONs in probe repos before any
GPU re-run (`gradeJSpace --sweep` now auto-grades daily via claude-etl-ingest.sh); (3)
`jspace-probe` has QUANT_ARM env (base-q4 bnb-nf4 arm; quant probe verdict: browser q4 tier
CLEAN — instruction_frame preservation 1.00).

**P12 §1b bench (spec-bench/, results in <hf-org>/spec-bench-results)**: KEY RESULT —
acceptance↔F1 proxy validity SPLITS BY MODE: r=−0.22 nothink (FAIL) vs +0.567 think (PASS;
self-4bit 0.715) → OSD-as-graduation-signal valid THINK-ONLY (= agent duty). Think-span is the
lowest-acceptance segment (0.72) = JSVR headroom. Batch-30 throughput PENALIZES spec decode
(−16%); batch-1 latency = +29% (quant-self, K=5 untuned). VOCAB LAW: Qwen3 (151936) ≠ Qwen3.5/3.6
(248320) — 3.5/3.6 one family, any internal pairing legal; ALWAYS vocab-check pairs. vLLM
qwen3_5-draft spec loading BROKEN upstream (arm A timing blocked). Spec homes:
`V2P12_SPECULATIVE_SERVING_SPEC.md` §7 (OSD) §8 (acceptance instrument) §9 (JSVR) §10 (quant
axis incl. quantized-self-as-draft); plan `P12_S1B_EXPERIMENT_PLAN.md`. Paper anchor: arXiv
2606.00206 (quant → overthinking at high-entropy positions; fp verifier prunes it).

**Roster**: Qwen3.5-2B exists, UN-onboarded (task #98 — draft/browser/reasoner hypotheses);
9B = teacher-tier option; official Qwen SAEs for 3.5-{2B,9B,27B,35B} (V2-P13 comparator basis
candidate). No small Qwen3.6 exists.

## DELTA 2026-07-27 — serving-alignment audit + echo-theory adjudication (khazarai-chat thrash → template)

**SERVING-ALIGNMENT AUDIT (operator-ratified, MANDATORY before first-serving/shadowing ANY artifact
— and before blaming the model for a live failure).** Full 12-item checklist: memory
[[serving-alignment-audit-template]]. Every item was a real defect found serially on 2026-07-26
bringing up khazarai-2B chat. Headlines:
1. **Template parity** — serving render must match the artifact's TRAINING chat_template verbatim
   (fetch from tokenizer_config, diff; 3 conflicting tool dialects = sloppy/empty calls).
2. **Mode is PER-ARTIFACT, not per-family** — the base Qwen3.5-2B onboarding verdict (serve
   no-think) did NOT transfer to the khazarai DISTILLED artifact: its tool-call reflex lives in the
   trained think pathway (no-think = coherent chat, ZERO tool calls; think-on = calls fire).
   Live-A/B the mode on the artifact itself before serving a duty.
3. **Near-greedy + no repetition penalty loops small q4 models** (chat duty now carries
   fp0.6/pp0.3; other duties' instruments untouched — D20).
4. **Small-model prompts: NO meta-instructions** (the model reasons about the instruction instead
   of the message); concrete tool list + explicit call example; no capability caveats next to a
   tool name (made it refuse to OPEN the News window).
5. **Loop control is STRUCTURAL at ≤2B** (R13): one tool round per user message — the follow-up
   round offers no tools (WebGPUTransport), else the model re-reads tool RESULTS as new user
   requests and spirals.
6. **HMR does NOT hot-swap orchestrator/transport singletons** — hard refresh before judging any
   serving edit; add the diag breadcrumb (`__webgpuChatDiag` pattern) BEFORE iterating.

**ECHO-THEORY ADJUDICATION (2026-07-27) — R24's live echo is a LEARNED COPY POLICY, not a serving
artifact.** Instrument: `webgpuEchoAB` MCP-dispatch tool (browser-side, nexus-sense
TOOL_EXECUTORS) + `predictTurn(model, prompt, overrides?)` penalty knobs — replays real production
prompts (rebuilt via shared `buildTurnPredictionPrompt` from session_transcripts) through an MLC
artifact twice on the SAME engine: arm A = incumbent instrument, arm B = +penalties. Verdict n=6:
echo-class 6/6 BOTH arms, 5/6 byte-identical — **penalties can't fix prompt-copying** (fp/pp only
tax repeated GENERATED tokens; copied prompt spans are never penalized). Distinguish the TWO
degeneration classes: (a) self-repetition loop → penalties fix; (b) prompt-copy policy →
model-level, only training fixes. R24 condemnation STANDS; turnpred instrument unchanged; r26
(prod-template corpus) is the lever and its live shadow is well-posed.

**r26 state (2026-07-27):** trained+graduated (0.107 ε=0.03) → mlc-convert (~5min; WATCH the Space
env-persistence footgun — leftover `WASM_SRC=skip` nearly shipped a wasm-less artifact; set AND
`variables ls`-verify every var per run) → **P5 probe PASS** (delta 2.1/2.0 vs margin 12, max 39<40,
zero leaks) → public → registered `<hf-org>/minicpm5-1b-r26-merged-MLC` in WEBGPU_MODELS →
deployed. **P5 is PER-ADAPTER — a prior adapter's pass does NOT transfer; artifact stays PRIVATE
until ITS probe passes** (browser shadow needs public, so P5 blocks shadow). Live-shadow vs R24
accrues in turn_prediction_stats as the operator browses; compare in DBAI→EVALS.

## DELTA 2026-07-27b — trainer DPO-path defect chain (khazarai fresh-LoRA DPO bring-up; each cost a run to find)
1. **train_lora.py ran the ENTIRE SFT setup at MODULE LEVEL** (unsloth load_base + get_peft_model +
   corpus render) BEFORE the TRAIN_MODE branch — so TRAIN_MODE=dpo still executed the unsloth SFT
   build first, and any patch placed inside the dpo branch was DEAD CODE until it. Two GPU runs
   (~$0.20) died there on the Qwen3.5 hybrid arch. FIXED: build wrapped in `TRAIN_MODE != "dpo"`;
   **map a script's MODULE-LEVEL flow before patching a branch** (map-before-assert applies to
   Python module top-level, not just call graphs).
2. **TRAIN_BACKEND=hf** (dpo only): plain transformers+bnb+peft load path — unsloth import is
   SKIPPED entirely for dpo+hf (its loader chokes on non-Llama arches; its IMPORT hard-crashes
   CPU boxes "You need a GPU", so CPU diagnostic runs need the guard too). Default 'unsloth'
   unchanged = MiniCPM5 SFT path untouched. `DPO_INIT_ADAPTER` now OPTIONAL: empty = fresh LoRA
   on the bare base (same rank/alpha/targets as SFT path).
3. **Guarding module imports orphans branch deps** — the dpo branch used module-level
   `Dataset`/`hf_hub_download`; after the guard they were SFT-only → NameError. Any branch that
   can now run standalone needs its OWN imports (AST-check the branch, not just py_compile).
4. **trl's DPOTrainer imports `mergekit`** (current Space-resolved trl) — missing dep = RuntimeError
   at `from trl import DPOTrainer`. In requirements now.
5. **RUN-LOG PERSISTENCE IS PERMANENT INFRA** (job-ops rule 11): app.py uploads the FULL run log to
   dataset `<hf-org>/v2p3-trainer-logs` BEFORE self-pausing — without it, both early failures
   were BLIND (the container's log dies at pause; waking a job-at-boot Space to read logs = an
   accidental retry). Never bring up a job Space without it.
6. **Smoke runs use a SEPARATE ADAPTER_REPO** (`…-smoke`) — the full run's done-signal is
   root adapter presence; a smoke push to the real repo would false-fire it. `MAX_STEPS=8` env
   (DPOConfig max_steps) = the ~$0.05 arch/deps gate BEFORE any full arm — ALWAYS smoke a new
   backend/arch combination first (the 2026-07-27 lesson, twice).
7. **requirements.txt: never pin a transformers floor alongside unsloth** — pip conflict risk
   would take down the WORKING SFT stack; add deps additively and let the smoke reveal version
   gaps as named tracebacks.

## ⚑ BEFORE ANY NEW BAKE-OFF ROUND — check the operator-sourced leads (added 2026-08-13)
Read memory `detllm-twil-candidates` FIRST. It queues unevaluated items that change this pipeline's
design space: **W2S-OPD** (arxiv 2607.26246 — weak-to-strong on-policy distillation; REMOVES the
strong-teacher assumption from the V2-P4→P5 apprentice arc: contrast-pair logit arithmetic + reverse-KL
on student rollouts; contrastive-hints = cheapest instantiation, GPU-guard-friendly), **Bennett
weakest-hypothesis** (arxiv 2301.12987 — weakness beats simplicity/MDL for generalization; weight
held-out BREADTH over diff-brevity in keep/discard scoring), **TwiL-LM 3B** (formal-logic candidate,
exact-format 52-vs-7 → judge/verifier slot; ⚠️ non-commercial license), **DetLLM** (bit-identical
int-only inference → deterministic evals for the verifiable-record north-star). Fold applicable ones
into the round design or explicitly note why deferred.


## DELTA 2026-08-14/15 — W2S-OPD adjudicated + shell-native slot + three new instrument rules (D40-D45 PUBLIC)

**Ledger**: D40-D45 now PUBLIC in `public_proof_deficiencies` (canonical text:
`training/seedDeficiencyLedger.ts`; 43 rows total). The ⚑ operator-sourced-leads item
**W2S-OPD is ADJUDICATED — REPLICATED NULL, program closed** (5 attempts ~$16):
contrast-hint distillation has real per-item force with ZERO net direction (D41 —
122/500 flips each way, 0 net, same-boot). Any future contrast-objective proposal must
explain why it would beat this measured null. Lens-fusion (attempt-5, LAMBDA_J
directionality prior) returned NULL too (+1/500, §1h) — the program is FULLY CLOSED, both hooks. Bennett breadth = SHIPPED (4.60.0).
DetLLM = license-blocked (contact draft ready); its interim mitigation is now doctrine:

**★ SAME-BOOT INSTRUMENT RULE (D40 — joins D20 temperature + D28 mode as the third
instrument doctrine):** evals that will be COMPARED must run in the SAME boot on the SAME
instance. Measured: cross-instance greedy decode flips ~3/150 borderline items with zero
weight change; in-boot base-vs-base at n=500 flips ZERO. Baselines are re-scored in-boot
(adapter-off/on via `disable_adapter()`), never carried across restarts. The shell-native
Space apps (`training/shell-native/s1_app.py`) are the reference implementation.

**SHELL-NATIVE SLOT (spec: `SHELL_NATIVE_SLOT_SPEC.md` §8-8e — the S1.x series):**
bash-as-a-language for sub-1B; S2 in flight. Its transferable findings:
- **D42 template collapse**: templated synthetic SFT at 0.8B memorizes command SHAPES
  (loss →0.0003 = the tell) and goes BELOW base on held-out; real-source episodes broke it.
- **D43 mixed-mean early stop**: a loss-stop window must accumulate ONLY the guarded
  family's loss — interleaved general data masks the target family's memorization.
- **D44 hidden-binding eval defect**: eval tasks must state every parameter the gold binds
  (EVAL_CONCRETE suffix pattern); perfect-model simulations CANNOT catch underspecification
  — only real-generation replay can. (Eval-side only; training phrasing stays natural.)
- **D45 proportion seesaw**: one-epoch SFT generalization tracks family proportions;
  BALANCE_FAMILIES parity interleave (minority with replacement) lifted both holdout axes.
  Adopted for S2 with TRAIN_SEED multi-seed replication (both env-plumbed in s1_app.py).

## DELTA 2026-08-15b — S2 stage-B verdict (GATE FAIL, seesaw at scale) + D46/D47 (45 rows PUBLIC)
**S2 stage-B (train-v7 15,281 → parity 17,718, seed 7): seen +55 · held −6 (COLLAPSE below
base) · realheld +9.** Gate (held ≥+2) FAILED → stage-C seeds NOT fired; recipe change is an
operator discussion (spec §8f options: per-family loss floors / synthetic exposure cap /
held-role rethink with a no-regression bar / §8c continued-pretrain fallback). Best overall
artifact remains shell-s18-adapter (+2/+11).
- **D46 (extends D43 — the masking lesson RECURSES):** a loss stop scoped to the guarded
  family still masks collapse when that family is itself a mixture — synthetic members
  floored at ~1e-4 while real members held 0.1-1.5 and the family mean never crossed the
  threshold. A mean over ANY mixture cannot detect member collapse: watch the MINIMUM
  member family, or drop each family from the mix when its own mean floors.
- **D47 (joins D44 in the eval-defect class):** the jailed executor's strict UTF-8 decode
  crashed the eval on legitimate binary stdout (curl gzip body) — fixed with
  errors='replace' in `gen_transcripts.run()` (both arms decode identically, comparisons
  stable). When real-world content enters a corpus, the eval apparatus must be binary-safe.
- MAX_MINUTES sizing note: 17,718 parity examples did NOT fit 150 min on a10g (84% of one
  epoch); the push-adapter-before-eval + run-state guards turned the overrun into two cheap
  eval-only resumes instead of a lost run (same-boot rule preserved — both arms on the
  resumed boot).

## DELTA 2026-08-16 — S2 corpus verification closed (D48/D49; 47 rows PUBLIC)
- **D48 adversarial twins**: mined-gold verification needs the second twin varied on TIME
  (-1h utime incl. directories), ENVIRONMENT (nested root + sibling population), and
  NETWORK (dead HTTP proxy — kills live-socket luck). Gold replay 40/40, assert never
  lowered. Reference impl: build_s16_corpus.probe_stable + run_s2_chain.sh.
- **D49 cross-engine divergence**: GNU-verified corpus diverges 47.2%/33.1% on just-bash
  (the browser serving engine) → `jsbash` fourth dialect bucket + engine-matched golds
  rule; help/man + curl axes are jb-incompatible (S0_CORPUS_NOTES §9).
- S2 TRAINING state: bracket complete (spec §8h), GPU stopped, operator decision pending
  (half-corpus ablation / realheld-primary regate / continued-pretrain / ship s18).

## DELTA 2026-08-16b — S2/S3 CLOSED: CPT recipe + four new doctrines (D50-D53; 51 rows PUBLIC)
**Program state**: shell-native S-series COMPLETE. Winner recipe = **CPT-then-SFT**: 40min
raw-prose next-token pretrain (cpt-raw-v1, 4.1MB tldr+help text) → S2h SFT (BALANCE_FAMILIES
parity, CORPUS_FRACTION=0.5, shell-mean LOSS_STOP=0.02). Three-seed replication: realheld
+14/+9/+9 (mean +10.7) · held −1/0/+15 (no-regression ×3; s23's +15 = program best).
**Artifact: <hf-org>/shell-s3cpt-s23-adapter.** Spec §8f-9b is the canonical run record.
- **D50 — the absorption ceiling is per-RUN (cumulative), not per-epoch.** Rotating
  stratified half-samples across epochs collapses synthetic-held identically to full
  exposure. Past the ceiling (≈9k parity examples @0.8B), change recipe CLASS (CPT), not
  the sampling schedule. Localize a suspected ceiling with a half-corpus ablation FIRST.
- **D51 — n=40 gate buckets are noise readers**: measured ±5..±16 item seed spread on the
  same recipe. Gates need multi-seed MEANS + no-regression floors; size buckets so the
  expected effect exceeds the MEASURED seed spread (run 3 identical-config seeds once to
  measure it).
- **D52 — CPT-then-SFT**: raw domain prose absorbs surface forms without spending the SFT
  absorption budget. Implementation invariants: CPT needs its own resumable step counter
  (pt_step — a restart must reload the CPT-ed adapter or SFT starts from raw weights), and
  a wall-clock cap must RESUME, never mark train_done (silent multi-phase truncation).
- **D53 — the training host drives its own run QUEUE** (queue.json in a dataset: next
  incomplete run → verify [RESULT] emitted → mark complete → self-restart → self-pause when
  empty; restart cap 8; append seeds by editing the file). Driver sessions are passive
  readers — 4+ session deaths absorbed, zero dropped spend. ⚠️ inactivity-SLEEP is a
  separate kill vector from crashes: set sleep_time=86400 explicitly or the queue stalls.
- **NEXT SESSION (operator-directed): CPT-corpus-scaling RISK BRIEF before any GPU** — see
  [[session-resume-2026-08-15]] item 0b for the full spec (drift risk, 2-point dose curve,
  man-page license analysis, size-vs-minutes confound, D51 gate discipline). Serving
  graduation rides the EXISTING WebGPU shadow pipeline (WebGPUServingService +
  apprentice_models; same path as khazarai-2B).

**Telemetry discipline (gap found 2026-08-16, backfilled):** the S1→S3 arc ran entirely on
HF datasets + spec docs and never wrote `training_runs` STDB rows — DBTRAINER's run history
silently stopped at r24 until a 20-run backfill (`seedShellNativeRuns.ts`, idempotent).
STANDING RULE: when reading a verdict off the queue, ALSO `upsert_training_run` (admin
reducer, nexus-nexus-cortex) — the ledger covers lessons, but the windows show RUNS.

## DELTA 2026-08-17 — S4 dose curve REGRESSION: D54 (52 rows PUBLIC)

- **D54 — at a fixed pretraining time budget, corpus EXPOSURES beat corpus SIZE.**
  Scaling the CPT corpus 4MB→14MB (in-domain tldr/help → + manuals/books/real scripts)
  at the same 40min cut realheld mean +10.7 → +7.0 with the program's widest seed
  spread (0/+15/+6): v1 got ~10 passes, v2 got ~0.4 — repetition of tightly in-domain
  prose IS the dose. Corollary: before scaling any CPT corpus, compute passes-per-token
  at the budget; if it drops below ~1, you are trading signal for coverage.
- **Instrument: the guarded general-drift probe worked** (n=20 non-shell exact-match,
  additive bucket, try/except so it can never kill a run) — clean +2 across all seeds,
  cleanly separating "signal dilution" from "capability erosion" as the failure mode.
- **Process: pre-registered gates paid off.** Thresholds (adopt/null/regression) were
  written into the brief BEFORE launch; the regression call took zero deliberation and
  zero motivated reasoning. Standard practice for any dose-curve or scaling run.
- Untested axis left open: PRETRAIN_MINUTES on the SMALL corpus (time-dose, not
  size-dose). Canonical: SHELL_NATIVE_SLOT_SPEC.md §9c + training/CPT_SCALING_BRIEF.md §5.

## DELTA 2026-08-17b — graduation/serving + lens-channel wiring quirks (all hit live today)

- **merge_lora.py arch probe is now ARCH-AGNOSTIC** (deployed to <hf-org>/mlc-convert):
  the old sanity check hardcoded `model.model.layers[0].self_attn.q_proj` (MiniCPM5-era) and
  CRASHED on Qwen3.5 hybrid layers (`Qwen3_5DecoderLayer` has no self_attn on linear-attn
  layers). Now diffs full state_dicts (max |delta| over shared tensors — also a stronger
  check). Any future per-layer probe on hybrid arches must discover attributes, not assume.
- **Qwen3.5-family MLC graduation is weights-only**: `WASM_SRC=skip` + a
  `prebuiltLibFrom: 'Qwen3.5-0.8B-q4f16_1-MLC'` WEBGPU_MODELS entry (web-llm's own
  prebuilt lib; wasm is weight-independent for same arch/quant/ctx). No compile step.
  Converter env recipe for an adapter graduation: ADAPTER_REPO + BASE_MODEL + MERGED_REPO
  (private) + OUT_REPO + QUANT=q4f16_1 + CTX=4096 + CONV_TEMPLATE=chatml + WASM_SRC=skip;
  Space is cpu-basic (≈free) and self-pauses. convert.log lands IN the OUT_REPO.
- **Fitted-lens artifact TRUTH (supersedes stale references)**: the jdistill raw-dict
  lenses (`jlens-student.pt` 0.8B d1024 / `jlens-teacher.pt` khazarai-2B d2048) live in
  dataset **<hf-org>/v2p13-jlens** (persisted 2026-08-17 from the rebuild-mutable
  jdistill Space cache). The `<hf-org>/v2p13-jdistill-logs` repo id referenced in
  w2s-pilot code NEVER EXISTED — that 404 silently killed the July jspace capture.
  TWO incompatible lens formats: Format A = `JacobianLens.save` (`jlens.pt`+`jlens.json`,
  load via from_pretrained; only export = MiniCPM5 r26 prodtmpl) vs Format B = raw
  `{int layer: [d,d]} torch.save` dict (jdistill cache). jspace_capture v2 loads BOTH
  (JSPACE_LENS_{FILE,FORMAT,REPO_TYPE}) and carries a **d_model guard** — a
  wrong-width lens now refuses loudly instead of fail-open dying silently (the July
  channel was dead for 3 weeks from exactly that: MiniCPM5 lens vs khazarai serving).
- **Fail-open needs a health surface**: two silent-death classes in one audit (d_model
  mismatch swallowed; trails dataset never created because the flush threshold [20] was
  never reached on a low-traffic Space — now env `JSPACE_FLUSH_EVERY`, default 5).
  Rule: any fail-open capture path MUST emit a visible health line per boot.
- **J-space LIVE channel exists** (JSPACE_STATE_CHANNEL_PLAN.md §S4-LIVE): serve-side
  capture pushes per-turn lens summaries to STDB `jspace_stream` (writer-token gated,
  owner-scoped `my_jspace_stream` view; JSPACE window LIVE tab renders). Payload band
  env `JSPACE_LAYERS` (default 10,14,17,20,22 ≈6KB/turn).
- **S5 (bash-plus minimal-agent executor) is the successor program**: runbook =
  `modules/database-ai/training/BASH_PLUS_SPEC.md`. Pinned interface artifacts
  (`training/bash-plus/interface-v1/`, hashed manifest = future serve gate; schemas
  EXTRACTED from the live harness registry, never hand-written) + tool-call episode
  emitter (`gen_toolcall_episodes.py`, 5 families, execution-verified). Before P4:
  validate Read/Edit/Write RESULT FRAMING against real harness transcripts — framing
  is part of the pinned interface. Serving doctrine from the anchoring program:
  interface dependence is a FEATURE when we own the serving surface — train-time and
  serve-time interface byte-identical, enforced by the manifest hash.

## DELTA 2026-08-18 — D55/D56 (wire-level positive control; result-framing byte-fidelity) + R63 taint note

- **D55 — WIRE-LEVEL POSITIVE CONTROL (joins D40/D20/D28 as the fourth instrument doctrine):**
  an A/B whose arms differ only via config levers must prove the difference reaches the
  OUTBOUND REQUEST BYTES (per-arm payload-size/content probe, e.g. the harness DEBUG_PAYLOAD
  sysMsg-bytes line) before any verdict is read. /proc-environ "env-verified" is NOT delivery:
  the P6/P6b prompt-mass sweeps compared byte-identical arms for 84 runs and produced a fake
  twice-replicated winner. Root cause was harness R63: since R28f (2026-05-16) the omniclaude-v4
  chat/completions + hf-space request builder DROPPED the entire static system prompt
  (PreparedRequest.systemMessage never consumed) — see omniclaude-v4-harness-deficiencies R63.
  **TAINT: any harness-driven (server/cortex-CLI) eval of an hf-space/deepseek/openai-chat model
  between 05-16 and 08-18 that depended on system-prompt content (CORTEX_SYSTEM_PROMPT_FILE,
  PROJECT_PATH docs, router prompts on the evalB path) ran PROMPTLESS.** D25's full-stack-prompt
  0/300 attribution is suspect (the temp fix landed same-pass and may have been the whole
  effect). Direct-transport evals (scoreHoldout/routerHoldout via hfSpaceTransport.ts) are
  UNAFFECTED (they build their own requests).
- **D56 — RESULT-FRAMING BYTE-FIDELITY**: the train/serve byte-identity rule covers TOOL-RESULT
  FRAMING, not just prompts+schemas. The S5 P3 emitter framed 4/4 tools unfaithfully (foreign
  success strings, fabricated exit shapes, relative paths the harness rejects, zero coverage of
  the Read verbatim-reminder preamble). Validation method = transcripts + executor-source
  byte-diff (BEFORE GPU). Fixed 2026-08-18: gen_toolcall_episodes.py now byte-copies executor
  templates, adds edit-miss/read-miss negative families, and interface-v1/result-framing.json
  is IN the manifest hash (content_sha256 61edbe78…) — framing drift now forces an interface
  bump. S5 P4's "validate framing first" gate is CLEARED.

## DELTA 2026-08-18b — P6 program CLOSED: family prompt shape + long-work budget doctrine
- **P6f/P6g verdict (long real-work tasks, pro+flash)**: corpus-at-lift (defer) FAILED the
  pre-registered gate on both models (pro +15% cost/output-even; flash output +31%
  REVERSED + costlier). **DeepSeek FAMILY shape = bash-edit door + boot-observation
  minimal prompt (B), short AND long scale.** Shipped as defaults in nexus-cortex 4.66.0:
  R63 delivery default-ON + card `promptPreset: 'boot-minimal'` both deepseek cards.
- **Long-work budget profile doctrine PROVEN**: 150/60 turned pro's t1 bug-hunt from 0/4
  (old 15/50 regime: fabrications, cap-deaths) to 4/4 real targeted fixes at 86-99 calls.
  Honesty clause verified live at the cap ("FILES CHANGED: none", no fabrication).
- **R66** joins the mined-by-bench ledger: unbounded ShellTool stream accumulation =
  whole-server crash on runaway output; bounded head+tail fix, 300MB repro.
- Instrument rules exercised: D55 wire control per arm (sysMsg bytes), session-summed
  true tokens (R64 usage defect), grep-"429"-in-byte-counts = known false-positive class
  in confound scans of DEBUG_PAYLOAD logs.

## DELTA 2026-08-24 — P4-C1 continuous-run: crystallization is RECURRENT + the durable-run pattern (D60-D62)
The P4-C1 pilot (s5_cont.py: continuous CPT->SFT on ONE AdamW + probe-every-100 + per-probe
banked ckpts + best-on-probe harvest, EPOCHS=2) rewrote the multiedit-crystallization story
AND hardened the durable-run doctrine.

- **D60 (eval/ship identity) VALIDATED at scale — the harvest is load-bearing.** Best-on-probe
  = s1300 (multiedit 8/8) auto-pushed as the artifact regardless of endpoint. Full battery on
  s1300: **multiedit 0->29/30 (+29)**, toolseen 30/30 (+3), realheld 3/30 (FLAT — weak spot;
  precursor beat it 7/30), general 15->13/20 (-2 mild forgetting). Recipe DECISIVELY works on
  its target; realheld generalization + forgetting are the open axes.
- **D61 CRYSTALLIZATION IS RECURRENT, not a one-shot lottery.** Curve: 0/8 to s1200 -> 8/8
  plateau s1300-1350 -> decay -> EXTINCT 0/8 for ~1150 steps (s1525-2650) -> RE-EMERGES to
  8/8 at s2700-2725 -> collapses -> rising 7/8 at the s2826 endpoint. TWO ceiling plateaus
  ~1400 steps apart, matching ~75-100-step lifetimes. The continuous-optimizer trajectory
  REVISITS the capability ridge on a long cycle. ⇒ ENDPOINT EVALS ARE A COIN FLIP on where the
  oscillation lands (original s7 ended in a trough = "destroyed"; P4-C1 ended on a rise). Only
  whole-run dense probes + best-on-probe harvest make the outcome deterministic. Probe grid MUST
  cover the ENTIRE run, not just the first-epoch window. "Train past 1 epoch" = PARTIALLY
  rehabilitated (epoch 2 destroyed plateau 1 but grew plateau 2).
- **D62 checkpoint bake-off pattern** (eval which wave is best): EVAL_ONLY_CKPT=adapter-s{N}.bin
  in s5_cont.py loads a banked ckpt, runs ONLY the full battery, NEVER push_to_hub (assert the
  push sits inside the train_done-guarded block so eval-only skips it). Multi-ckpt = N queue runs.

**🔴 THE DURABLE CRASH-RESISTANT RUN PATTERN (canonical — use for ANY GPU run now):**
1. **Queue-driven self-advancing Space** (`shell-s3-queue` apparatus): queue.json runs[] +
   completed[] + restarts{}; run -> mark complete -> self-restart -> next -> self-pause at
   queue-done. Survived 5+ session deaths across P4-C1 + bake-off. Sessions are PASSIVE readers.
2. **Bank EVERY checkpoint step-named** (`adapter-s{N}.bin` to OUT_REPO-ckpt) + **D53 crash-resume**:
   on boot, scan -ckpt for the highest banked step and resume from it (a crash/OOM/eviction/sleep
   continues, never refits). Run-state (pt_step/step/best_probe) in a resumable JSON.
3. **Results/logs to a DATASET, never the Space repo** (Space-repo upload = REBUILD mid-run = silent
   death; hf-space-job-ops rule 1). Per-run log keyed by runid so queue runs don't collide.
4. **Keep-alive the app URL** (root + /config every ~4-5 min): the HTTP sleep timer counts traffic
   NOT compute, so a compute-only run SLEEPS mid-run (killed P4-C1 once — resumed from s2225 ckpt,
   <=25 steps lost). Set sleep_time >= run length AND hammer the URL.
5. **Self-pause on end** (HfApi.pause_space) + no-auto-retry (cost guard). Redeploy the app ONLY
   when the Space is PAUSED (upload rebuilds + kills a running job).

**🔴 WORKSPACE-QUOTA FREEZE (EDQUOT) — recurred 2026-08-24, cost the local layer.** Monitors that
fresh-clone HF Datasets every N min MUST `rm -rf` the clone after reading — un-cleaned clones filled
the ~51-52G workspace quota, and at EDQUOT NO local command runs (the tool can't open its own
output file under /tmp/claude-*). Symptom: every Bash call returns `EDQUOT ... open '.../tasks/*.output'`.
Fix needs the USER's shell (deletion works at quota): reclaim `$HOME/.cache/uv`,
`.cache/huggingface/hub`, `.claude/projects/*/tool-results/`, and disposable /tmp clones. Remote
work (Spaces, containers, Datasets) is UNAFFECTED — only local observability freezes. [[workspace-storage-quota-ceiling]]
Prevent: self-cleaning polls; never leave two monitors double-cloning the same Datasets (split-brain
doubles the churn — kill the stale monitor when re-arming).

**🔴 HF 402 CREDITS-EXHAUSTED SIGNATURE (2026-08-24):** when pre-paid GPU credits run out MID-QUEUE,
it presents as: run crashes EARLY with NO log persisted → queue self-restart FAILS → Space PAUSED with
completed=[] — looks exactly like an app bug. Diagnose in one step: `restart_space` from the API and
read the error — `402 Payment Required` = billing, not code. The durable queue parks losslessly; a
top-up + one restart resumes at the same run. Check the balance BEFORE diagnosing any early-crash-no-log
pattern, and size top-ups for the whole planned arc (mid-run stalls waste adjudication time even though
they lose no data).

## DELTA 2026-08-26 — Vast spot lane is a FIRST-CLASS training venue; the standing bucket config
The P4-C2 multi-seed commission runs on Vast (validated ~3x cheaper than HF Spaces; spikes 1-3
proven — see spot-gpu-compute skill). **Read `.bench/P4C2_VAST_RECIPE.md` + the
`vast-hf-bucket-standing-config` memory BEFORE any Vast run — do NOT re-derive the transfer
plane** (that re-derivation cycle burned two sessions and operator patience):
- **Data plane = HF Storage Bucket `<hf-org>/spike3-bucket` via Vast Cloud Connection 44615**
  (`vast-hf-spike-3`). Token + connection are scoped to THIS bucket only (operator-confirmed);
  a new bucket = an operator re-mint/re-connect cycle they have vetoed. REUSE with per-project
  prefixes (`p4c2/…`). Pod carries ZERO HF creds for data; repl seeds via `batch_bucket_files`,
  pods pull via `vastai cloud copy --connection 44615` (`bucket/dir` — NO leading slash;
  hash-verify both sides).
- Repo-side banking (run-state/ckpts/adapter — the D53 resume rail) is git-repo-native and the
  bucket cannot front it: the SETTLED posture is the workspace HF_TOKEN over SSH FOR THE
  BANKING LEG ONLY (launcher fallback `${HF_TOKEN_P4C2:-$HF_TOKEN}`; SSH-session env, never
  on pod disk). 🔴 NEVER ask the operator to mint a token — operator-vetoed 2026-08-26.
  ⚠️ For DATA transfers token-over-SSH is DEMOTED to backup-of-last-resort (spike-2
  early-trial method) — the bucket is the primary data plane, full stop.
- Vast key env = `VAST_AI_API_KEY`; pinned image `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`;
  dead-man MANDATORY when any pod exists (`.bench/vast-deadman.sh`, destroys by AGE incl.
  `stopped`); BAKE ONE ARM FIRST applies to pods exactly as to Spaces.

**P4-C2 s11 pilot lessons (2026-08-26 — each cost a real incident; all fixed in
`.bench/p4c2-vast-launch.sh` + recipe §4b):**
- 🔴 **STAGED ENV DEFECTS PROPAGATE — ground-truth the env against the PREDECESSOR RUN'S
  LOG, never against staging.** The parked queue entries AND the launcher both lacked
  `PRETRAIN_FILE` (first launch ran SFT-only = wrong experiment, killed at $0.04). The
  authority was P4-C1's own log (`[cpt] 2376 blocks; budget 40.0min` in
  <hf-org>/shell-s5c1-logs — note: LOGS_REPO names do NOT always follow `<OUT>-logs`).
  VERIFY the `[cpt]` line live before believing any launch of a CPT recipe.
- 🔴 **A MAX_MINUTES cap mid-EVAL emits PARTIAL `[RESULT]` lines** (`trained=0/0` = bucket
  never ran, NOT zero passes) — any completion check keyed on `[RESULT general]` presence
  false-fires; key on the DENOMINATOR (`trained=N/20`). Eval-resume is proven: relaunch →
  "[resume] training already done — straight to eval".
- **Multi-boot is the venue's job**: HF queue self-restarts capped runs; on Vast the
  launcher's pod-side sup loop does it (re-invoke until the denominator marker; token
  env-only, never on pod disk). Dead-man sized to the WHOLE arc (~1500min), not one boot.
- **Telemetry row AT LAUNCH** (`telemetry.ts run <tag> … running`), updated at verdict —
  and at every arc close, AUDIT the training_runs table tail against the program timeline
  (P4-C1 + the whole P4 audit had NO rows until backfilled 08-26; second occurrence of the
  S1→S3 gap class). Deficiency ledger current through D61.
- **Battery order** toolseen→multiedit→realheld→general; realheld-via-tools is its own
  instrument (first-Bash-of-rollout in a fresh twin — never compare to S3 NL→command rows).
- **The pkill/pgrep costume rules apply INSIDE ssh remote commands too** — `pkill -f
  s5_run` in a remote compound killed its own remote shell (exit 255); bracket patterns
  (`s5_ru[n]`) everywhere, including on pods.

## DELTA 2026-08-24b — BAKE-OFF VERDICT (D63): wave-2 peak strictly dominates; no new skills across waves
Full-battery bake-off of 4 checkpoints (durable queue, eval-only mode, all complete, Space self-paused):
| ckpt | multiedit | toolseen | realheld | general |
|---|---|---|---|---|
| s1300 (wave-1 peak, SHIPPED) | 29/30 | 30/30 | 3/30 | 13/20 |
| **s2700 (wave-2 peak)** | **30/30** | 30/30 | 3/30 | **14/20** |
| s2725 (wave-2 decay) | 27/30 | 30/30 | 5/30 | 14/20 |
| s2826 (endpoint, rising) | 25/30 | 30/30 | 4/30 | 14/20 |

- **D63a — no new skills in later waves**: toolseen at ceiling everywhere; realheld wobbles 3-5/30
  (noise at n=30); general 13-14. The re-emergent plateau re-crystallizes the SAME skill.
- **D63b — wave-2 uniformly retains general better** (14 vs 13 across all three wave-2 cells — small
  but consistent): later-wave crystallization costs slightly less forgetting.
- **D63c — s2700 STRICTLY DOMINATES the shipped s1300** (multiedit 30>29, general 14>13, rest tied).
  Harvest-at-peak policy CONFIRMED, but the probe-driven auto-harvest picked wave-1's peak when
  wave-2's was better ⇒ harvest rule upgrade: at run end, bake-off ALL 8/8-probe plateau peaks with
  the full battery and ship the dominator — the probe (n=8 multiedit) can't see the general/realheld
  axes that separate equal-probe peaks.
- **D63d — multiedit tracks oscillation phase exactly** (peak 30 → decay 27 → rebuilding 25):
  the probe curve is a faithful phase indicator; only the BATTERY ranks equal-phase candidates.
- Ops notes: one zombie-Space incident mid-queue (RUNNING + queue-thread dead 2.5h, no log, restarts
  frozen — restart_space resumed losslessly); MAX_MINUTES 150 capped s1300's first attempt (realheld
  2/16, general 0/0) — 300 completed it; queue survived the operator 402 top-up + 5 restarts total.


## DELTA 2026-10-18 — runtime-invariance (swap) diagnostic is on the graduation checklist
Source: @Sauers_ thread (x.com/sauers_/status/2111696312026677658; `research/x-thread-sauers-2111696312026677658.txt`): last-two-layer SFT
teaches a model to detect activation probes / Trainer-vs-vLLM from fp-ordering fingerprints alone. Our apprentices are last-layers-SFT'd with
Lens D / J-lens hooks present — the same recipe. Procedure + pass rule: `V2P4_INTERN_SPEC.md §8.1`. Rules: gates run in the SERVING runtime;
probe topology identical across graded/ungraded runs (buffer-write probe preferred); spec-decode acceptance measured under the engine's batched
verify, not eager one-token decode. A FAIL is fixed by retraining the last layers across randomized runtimes/kernel configs.
