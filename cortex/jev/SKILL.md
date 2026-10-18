---
name: jev
description: Everything we know and built around TypeSafe AI's Jev (System One typed-decision model) and its open replicas — the API shape and limits, our paired evaluation against the hidden grader (262 sessions), the Jev typed distiller, the classifier/decision-model plan (own-Jev bases, V2-P14 acceptor head), where it fits the harness/SPA/STDB stack, and the rules learned. Load before ANY Jev call, any "classifier/decision model/typed results" design, any distill or judge-evaluation work, or when the operator mentions Jev, SemIf, Luce, Laya, Verdict, Kev, NanoJev, system-one, or "mute yes/no LLM".
---

# jev — typed-decision models in the nexus stack

## 0. Facts (verified 2026-09-18/20)
- **Jev** (TypeSafe AI, released 2026-09-15): hosted, closed-weight "System One" model. `POST https://api.typesafe.ai/v1/systemone`, header
  `Authorization: Bearer $TYPESAFE_API_KEY`, body `{state: string|object|array, model: "jev-latest", questions: {name: {type, instructions, criteria?}}}`.
  Primitives: **choice** (≤255 options → choice, confidence, probabilities), **score** (2–10 ordered levels → score, probabilities, legend),
  **noul** (yes/no → probability, no separate confidence). All questions answered in one parallel pass; adding questions adds ~no latency.
  Limits (jev-1.13): 64K tokens/request, 32K for state + longest question; rate limits 250K tok/s, 1,200 RPM (dynamic). Price $0.042/M input,
  output free. Latency measured by us: median 0.34 s, p90 0.43 s. Errors: 401/422/429/529 (back off on 429/529).
- **Key location:** `TYPESAFE_API_KEY` in Replit Secrets → the session bridge `.claude/.replit-secrets.env` (`set -a; source …; set +a`).
  Never in `.env`. Operator has early access (waitlist cleared 09-18).
- **Jaggedness (vendor-documented):** literal reading ("answers the question you wrote"), cannot count or compare numbers/dates, degrades with
  indirection and with irrelevant state, not adversarially robust, P(noul) not guaranteed = 1−P(not). English-first. Keep math in code.
- **Not fine-tunable, not self-hostable; no open weights.** Same weights for every account; customization = instructions/criteria only.
  Also reachable via Vercel / Cloudflare / OpenRouter (`~typesafe/jev-latest`) / Netlify gateways.
- **ToS:** check TypeSafe terms before using Jev outputs as TRAINING labels for our own model; our own flash/pro is the safe labeler.

## 1. What we measured (primary sources; never re-derive from memory)
| item | where | headline |
|---|---|---|
| Paired eval: Jev "is this task done" vs the hidden TB4.0 grader, 262 sessions (stores t4z2/t4c/t4s/t4y/t4z), $0.023 | `omniclaude-v4/.cortex/research/jev-assessment-2026-09-18.md` §7; records `omniclaude-v4/.cortex/research/jev-eval-2026-09-18/` + HF `<hf-org>/jev-eval-2026-09-18` | AUC 0.716–0.718, Brier 0.152 (base-rate 0.166), **ECE 0.056–0.059 (calibrated)**, max `done` 0.65, next=investigate 211/262. Rerun reproduced within ±0.004 AUC (near-deterministic). |
| vs the LLM judge on the same 221 sessions | same §7 | judge accept: acc 0.665 / prec 0.346 / rec 0.540; Jev ≥0.3: 0.629 / 0.340 / 0.680; **judge AND Jev ≥0.3: prec 0.438, removes 24/51 false accepts for 6/27 true.** Verdict: a calibrated GATE on the judge, not a replacement; neither has the evidence (both read the agent's own final state). |
| Rich-state variant | same | unchanged (AUC 0.713–0.717) — the persisted `session.jsonl` holds pruned tool results, so "more state" did not add text. State-size question OPEN (needs `grader/` raw outputs). |
| Jev typed distill of the 100 failing f1 sessions, $0.011 | `omniclaude-v4/.cortex/bench/r-tb4-f1-curation-2026-09-19.md` §3; records `jev-eval-2026-09-18/jev-distill-f1.jsonl` | failure_mode: unverified_claim 43 / incomplete_gave_up 26 / verifier_mismatch 20 / misread_spec 6; `own_test_passed_wrong` 83/100; `gave_up_early` 96/100; `spec_ambiguous` 7/100; loop_thrash 0. Replaces the heuristic distiller's "unclassified" half. |
| GLiNER 2.5 zero-shot on the same 262 states (09-20, $0.06 Vast box; `jev-replicas-2026-09-20.md` §5, `.bench/jev/gliner-{run,score}.py`) | `jev-eval-2026-09-18/gliner-*.jsonl`, `gliner-score.txt` | base AUC 0.590/ECE 0.332, small 0.575/0.251, multi 0.550/0.087 vs Jev 0.716/0.056 — NOT a zero-shot judge; fine-tune base for the per-turn sensor only. Loader: `from gliner2.auto import AutoExtractor` (the `GLiNER2` class cannot load 2.5 boundary checkpoints); deps: transformers sentencepiece protobuf peft accelerate. |
| Own-Jev baseline: Qwen3.5-4B logit readout, zero training, same 262 states (09-20, $0.55 L4; `.bench/jev/ownjev-run.py`, Space `decide` endpoint in `omniclaude-v4/scripts/hf-space-template/app.py`) | `jev-replicas-2026-09-20.md` §6; `jev-eval-2026-09-18/ownjev-qwen35-4b.jsonl` + `ownjev-score.txt` | done AUC **0.728** (≥ Jev 0.716), verified 0.614, but ECE 0.291 / mean p 0.48 vs base rate 0.166 — discrimination parity, calibration 5× worse; Jev's edge is calibration (RLCD), not ranking. Free readout is fine for ranking/best-of-N; a threshold gate needs a Platt/temperature fit first. |
| E0 typed-chooser replay (09-21, $0.30; `.bench/jev/e0-replay.py`; 97 g1/g2 sessions + 759 commands) | `omniclaude-v4/.cortex/research/jev-e0-2026-09-21/results.md` | finish gate on lever-arm sessions AUC 0.638 / ECE 0.056 / 0 confident-wrong (claim + tool rows); a 1500-char raw-output tail does NOT help (0.603); the judge's opinion in the state makes Jev echo the judge (AUC 0.645, ECE 0.229) → the gate's state must never hold the decision it gates. Command-failure pre-run gate AUC 0.62 (ranker input only); literal repeat detection 0.98. |
| TypeSafe **System One adapter** (OSS, MIT, github.com/typesafe-ai/system-one-adapter-python v0.2.1 — same question interface, LLM backend; `OpenAIProvider(model, base_url=…)` reaches DeepSeek) on the same 262 states + questions (09-28, ~$8.9 for both; `.bench/jev/s1a-run.py`, venv needs `openai`; `.bench/jev/platt-cv.py`) | `jev-eval-2026-09-18/s1a-deepseek-{flash,pro}.jsonl` | done AUC: **flash 0.747** / pro 0.652 / Jev 0.716. ECE raw: flash 0.175 / pro 0.119 / Jev 0.056; after a 5-fold Platt refit on our labels: flash 0.027 / pro 0.067 / Jev 0.044 / own-Qwen 0.009. Verified question at chance for both (0.48). Median latency 22 s / 57 s vs 0.34 s; ~1.1–1.3M output tokens per 262 calls (reasoning) vs Jev $0.02. → An LLM backend is a usable NO-KEY fallback for the done gate only with a fitted calibration (never Jev's raw 0.3 threshold); too slow for per-turn use. The LLM "probabilities" are self-reported (`llm_answer_mode="probabilities"`), not token scores. (Scorer bug fixed 09-28: gliner-score mapped an exact 0.0 confidence to 0.5.) |
| Operating point | §7 | Jev is cautious on our evidence: usable threshold ≈ 0.3, not 0.5. Confident-wrong: 0 fails ≥0.9; 2 passes ≤0.1. |

## 2. Scripts (all pure stdlib + urllib; env HF_TOKEN + TYPESAFE_API_KEY)
- `.bench/jev/jev-eval-done.py <out.jsonl> <store>…` — per graded session: compact state (task instruction ≤7K chars, final agent message ≤4K,
  last N tool calls/results) → questions done/verified/next; joins the session's `endturn_resolver` verdicts; resumable (skips done keys).
  Env: `NTOOLS` (8), `RES_CHARS` (1500), `INSTR_CHARS` (7000). Scorer snippets live in the session record / the assessment §7.
- `.bench/jev/jev-distill.py <out.jsonl> <store>…` — failing sessions only; state += judge last verdict text + grader CTRF failed tests →
  failure_mode (choice) + 6 Nouls (judge_named_real_defect, agent_had_evidence, gave_up_early, own_test_passed_wrong, spec_ambiguous,
  fixable_with_more_turns). Imports the builder from jev-eval-done.py.
- Store readers they build on: `.bench/vm/tb4p3-read.py` (`rows()` = last done row per task from `results*.jsonl`).
- **Rule: outputs go to `omniclaude-v4/.cortex/research/…` or an HF dataset — NEVER the scratchpad** (a process restart wiped the first
  pass's raw records on 09-18; the rerun had to replace them).

## 3. Reports and designs (read in this order for a new session)
1. `omniclaude-v4/.cortex/research/jev-assessment-2026-09-18.md` — what Jev is, community patterns, stack fit ranked (§3), cost table,
   build-our-own (§5), recommendation (§6), paired eval (§7), **§8 "beyond classification: the mute yes/no oracle"** (12 harness patterns:
   per-turn perception bitmap, response-level speculative decoding / cascade acceptance, best-of-N with a free judge, bisection, streaming
   veto, 1 Hz supervisor, prefetch, memory selection, corpus labeling, twenty-questions extraction, tie-breaking, feature streams).
2. `omniclaude-v4/.cortex/research/jev-x-discourse-2026-09-18.md` — Grok X-search report (builds, numbers, criticisms, access).
3. `omniclaude-v4/.cortex/research/jev-replicas-2026-09-20.md` (+ `jev-replicas-x-discourse-2026-09-20.md`) — open-weight replicas:
   SemIf (frozen Qwen3.5-4B logit readout, 84.5% Jev agreement, MIT), Luce (Qwen3-4B LoRA, calibration loss = soft CE + Brier + NLL, Apache),
   AutoJev-SFT-27B (Qwen3.8-27B, Apache, self-reported > Jev), Verdict 2.0 / Laya (ModernBERT 150M/421M encoders, Apache, 20–30 ms),
   Kev (Qwen+LoRA+option-attention head, MIT), NanoJev (0.6B, license unconfirmed). "Jev = Qwen 27B" NOT substantiated (tokenizer 348/415
   closest, base unknown). simple-jev has NO license file — do not vendor. **§5 GLiNER 2.5** (Fastino, Apache, 74M/194M/287M DeBERTa encoders,
   4,096-word window, multi-task one pass, documented fine-tune, sigmoid scores, no ordinal Score): "closest open-source Jev" = same
   labels-in/scores-out shape; zero-shot Jev wins classification (0.91 vs 0.70 AG News, 0.87 vs 0.61 Banking77), fine-tuned GLiNER matches
   Jev in-distribution at ~7× lower latency; author: "Jev is a special case of GLiNER2". Best-supported encoder base for the PER-TURN SENSOR;
   zero-cost repl-CPU baseline on the 262 sessions proposed (`gliner-x-discourse-2026-09-20.md`).
4. `nexus-terminal/modules/database-ai/V2P14_JSPACE_TYPED_ACCEPTOR_DESIGN.md` — the Jev-shaped acceptor head inside speculative decoding,
   wired into j-space (route accept/verify/escalate + harness predicates; labels from JSVR/P12 artifacts + bench stores; E1–E5).
5. `omniclaude-v4/.cortex/bench/r-tb4-f1-curation-2026-09-19.md` — the corpus-level diagnosis the distiller produced (unverified claim +
   self-passing test + 85% budget unused; the judge often right and overridden by the gap-accept liveness cap) and the decisions-graph seed schema (§6).
6. The stack map of decision points (harness / STDB / SPA / financial / autoresearch) is in the assessment §3 and the 09-18 session record.
7a. External: Southbridge AI "Models Watching Models: Jev as an Agentic Observer" (Hrishi Olickel, 2026-09-19,
   southbridge.ai/blog/jev-watching-the-agents; 500 runs / 12 task families / 13,549 observations, $2.30): Jev as a READ-ONLY sentinel over
   event logs. Findings that bind us: (a) direct 1–100 progress percentages FAIL ("100, 100, 1" on repeat; Kalman smoothing made forecasts
   worse) — PHASE scoring (0–5: exploring/planning/building/checking/recovering/reporting) is stable → use score/phase levels, never numbers;
   (b) phase readings + runtime counters cut time/cost forecast error ~18% vs counters alone (ridge, family holdout 14.5%); Jev beat GLM-5.3
   Flash / DeepSeek V4 Flash / Haiku 4.5 on remaining-cost error at 444 ms / $0.035 per call; (c) security gate: 1.73% of 220K tool calls
   flagged, ~1% of decisions FLIP on retry, hex/python wrappers bypass it → "a gauntlet against honest mistakes, not hostile intent" (matches
   our E0 leg A 0.62 and the denylist-as-hard-floor rule); (d) "laziness / unjustified shortcut" labels disagree wildly across models (Jev 82,
   DeepSeek 10, Gemini 2, GLM 2 of 120) → our distill's `gave_up_early` labels need a second labeler; (e) full context stabilized their phase
   reading (Δ0.03 vs 0.64 event-only) — the opposite of our finish-gate E0 (more state hurt), different question types: right state per question.
7. Public comparison post (Claude Doc https://claude.ai/code/artifact/8a740f18-1d5f-47cb-828f-4b7648024668; markdown copy `omniclaude-v4/.cortex/research/jev-vs-llm-judge-post-2026-09-20.md`): "Jev vs LLM judge on 262 real agent sessions" — the answer to LangChain's 5-trace "Jev as a
   judge" post (https://x.com/langchain/status/2101454284927959080; 100% on 5 traces × 100 repeats vs human labels; repo danielgshea/jev-as-a-judge).

## 4. Rules learned (structure, not prose)
- In-harness Jev (4.120.0): `packages/core/src/training/jevGate.ts` (`jevNoul`, fail-open, 8 s timeout) + the R173b gap-hold gate
  `CORTEX_JUDGE_GAP_HOLD_JEV=off|shadow|gate` (`_MIN` 0.3) — the first typed result wired into control flow; the key ships via `.bench.env`
  → bootstrap → adapter → cortex-server env (TYPESAFE_API_KEY).
- Typed results must change CONTROL FLOW; the generator receives the consequence ("run c5 and c13 before finishing"), never the probability
  in prose (prompt clause ≠ enforcement; ENFORCE had 6% compliance).
- Negative knowledge > positive in this domain, delivered as gates. The judge's veto texts are the negative knowledge; bank them per task.
- Compact the state (<32K, no irrelevant output); write criteria concretely; no double negatives; keep counting/numeric comparison in code.
- Always report ECE/Brier + a confident-wrong count, not just accuracy; use the operating point the calibration shows (~0.3 here).
- Mechanism-engagement evidence for any Jev-gated lever = the event fields (predicate, probability, threshold, action taken).
- GATE INDEPENDENCE (E0, 09-21): never put the judge's verdict/plan (or any decision being gated) into Jev's state — it anchors and the AND-gate degenerates to the judge. Raw evidence helps only if it is the actual artifact/screen, not a tail of recent outputs.

## 5. Next experiments (in value-per-dollar order; none started; operator gates spend)
1. ~~Zero-train "own Jev"~~ DONE 09-20 (§1 row): AUC parity, calibration not. Next $0 step: Platt/temperature fit of the readout on the 262
   points (5-fold) → report ECE after calibration; then the readout becomes a usable threshold gate.
2. Per-turn bitmap replay over banked trajectories (which predicates predict the grader, how early). ~$1–5.
3. Harness levers (dark): `CORTEX_JUDGE_JEV_GATE` (confidence gate on judge accepts), EndTurn fan-out pre-judge feeding R170 INVESTIGATE,
   tool-risk classifier; STDB `router_prepass` swap (`agent_turn.rs` ~5574). Measure on the 13-task pool + the 29-task cell.
4. Own model: Luce-recipe LoRA (judge duties) + Verdict-recipe ModernBERT-base encoder (per-turn sensor, browser); then V2-P14 E1–E3.

## DELTA 2026-09-23 — where Jev measured well and where it did not (frame + ledger arcs)
- Whole-task doneness (E0 finish gate AUC 0.64; Southbridge phase/forecast leg D no pass signal) = weak. Typed per-line questions on concrete
  evidence = strong: R187b closes requirement-ledger lines from {requirement, writer attestation, harness check output} (smoke: 1–2 lines per
  finish at ~0.3 s); the pick-only chooser (R186) asks ONE question per option after the E2 replay showed the gate nouls changed 1.5% of actions.
- Author replay (R188, 97 E2 stuck turns): Jev preferred the author's option over the writer's 79% with full inputs vs 62% with truncated ones —
  Jev's answers track input quality, so fix inputs before reading Jev.
- Anchor note: the arc's "Terminus 2 26.8" target was a mis-attribution (AA = mini-swe-agent); see project-harness-arc-goal memory.

## 🔴 DELTA 2026-10-01 — the 262-state eval had NO tool evidence (read every Jev/CLM/GLiNER 262 number with this)
`jev-eval-done.py build_state()` read tool calls as flat `{id,name,input}`; nexus-cortex session files nest them under `toolUse`
(`{"type":"tool_use","toolUse":{id,name,input}}`). Every one of the 262 states therefore carried 8 empty recent_tool_calls (tool None,
no input, no result). The 0.716 / 0.728 / 0.686 / 0.59 "done" AUCs are TASK + FINAL MESSAGE ONLY baselines; "verified" (~0.61) could
never be answered. Fixed builder: `.bench/jev/clm-p2-build.py` (reads both shapes); rebuilt states at
`omniclaude-v4/.cortex/research/clm-p2-2026-10-01/eval-262.jsonl`. Any new state builder: assert recent_tool_calls have non-None tools.
Re-score 10-01 on the fixed states (`.bench/jev/jev-rescore-262.py`, $0.06, paired n=256): done AUC 0.723 → **0.746** (Δ +0.022, CI
[−0.033, +0.079], undetermined), verified 0.613 → **0.707** (Δ +0.094, CI [+0.023, +0.168], real), ECE 0.049 → 0.097. The headline Jev
reference is now 0.746 / 0.707 WITH tool evidence. Detail: CLM plan §6.

## DELTA 2026-10-01b — alternatives survey (read `omniclaude-v4/.cortex/research/jev-alternatives-2026-10-01.md` before choosing a base)
Decision Index 0.2.1 (HF Space multimodalart/jev-decision-index, 70 models, data/index-v0.2.1.json): Jev 57.1 / ECE 0.074; top open =
Surogate Rune 26B-A4B 56.5, Decider chat Gemma-4-31B 56.2, AutoJev-27B 54.9 (ECE 0.018); Decider 4B 39.2; **CLM-v0.1-8B rank 55/70,
6.9, ECE 0.32**. New 10-01: Cloudflare Clef 27B + Clef-Flash 9B (Apache, systemone-compatible) and autotrust/JEV-27B (Apache, detachable
adapter). Plan: retire CLM-8B as the Phase 2 base; zero-shot bake-off on the 256 fixed states, then fine-tune the winner that fits budget.



## 2026-10-01 — Phase 2 fine-tune plan
`omniclaude-v4/.cortex/research/clm-p2-2026-10-01/FINETUNE_PLAN.md` — cross-fit protocol (eval ⊂ corpus), 4 arms incl. small-vs-27B, pre-registered gates, ≈$12–18 likely.

## DELTA 2026-10-14 — Amos 1 (scira.ai) + Clef-omni; Decision Index 0.3.2 re-rank (read `omniclaude-v4/.cortex/research/amos-clef-update-2026-10-14.md`)
Amos 1 (mukaddamzaid, Apache-2.0): 27B (Qwen3.8-27B) / 9B (Qwen3.5-9B) / 2B / 0.5B, 128K ctx, noul/choice/score/multi/span/region, FREE
keyless hosted API (60 RPM) + `serve/` self-host (large 80 GB, medium 24 GB); vendor claims JevBench hard 84.7 vs Jev 74.1, typed-decisions
Brier 0.069, Clef 72.5 % on its own test. Not on the Decision Index FULL board yet. Clef/Clef-flash cards unchanged since 10-01; Clef-omni
(30B-A3B, audio/video) trails Clef on workflow evals. Decision Index 0.3.2 full ranks: Jev #12, RSI-Jev 27B #20, JEV-27B #37, Clef #43,
clef-flash #61 — general skill still does not predict our 256-state result. Next: bake off Amos large + medium SELF-HOSTED on the 256 states
(private data; ~$2) before any API use; the hosted endpoint would leak bench states to a third party.
**Bake-off RESULT 10-14 (self-hosted, $0.50, 256 states, Jev questions):** Amos 1 large done AUC **0.774** (+0.028 vs Jev, CI spans 0) /
verified **0.767** / ECE 0.30 → 0.050 after Platt / 3 confident-wrong / 1.55 s; Amos 1 medium 0.697 / 0.750 / ECE 0.43 → 0.046 / 0.48 s —
best open 27B (edges Clef 27B 0.767/0.761, parity by CI) and the best 9B "verified" signal. Table: amos-clef-update note §4. Harness:
`.bench/jev/bakeoff-amos-launch.sh` (BAKEOFF_MODELS must be QUOTED in the env file — unquoted ran the default list 10-14 and overwrote
two 10-01 result files in the dataset; restored from the local copies).

## DELTA 2026-10-15 — small-model bake-off (amos-mini/small, d1-3B, d1-omni-600M) + R261 attempt labels
Zero-shot on the 256 (note `omniclaude-v4/.cortex/research/bakeoff-small-decision-models-2026-10-15.md`): **amos-1-small 2.2B done 0.694 / verified
0.694** (= amos-medium 9B), amos-1-mini 0.5B 0.651 / ECE 0.039 raw (best calibration measured), d1-3B 0.641 (over-accepts; its Decision Index rank
does not transfer), d1-omni-600M 0.496 + OOM on long states (out). All CI-below Jev; 27B class still the bar. Fine-tune arms (FINETUNE_PLAN_B): G =
amos-small (own `loss_fn`/`pack`), E = d1-3B (CE at the yes/no slot via `render`/`readout_ids`), F = amos-mini (sensor; amended from d1-omni before
launch). TRAPS: a Tesla P40 box fails every current torch wheel (`compute_cap>=860` in every launcher); the bake-off box reads `/root/<tag>.iid`
(fixed-name lookup skipped self-destroy on 10-14); bank `*serve*.log`. CORPUS: R261 (10-15) put 185 restore-graded non-pick attempts + every
future attempt's full session into the lake (`harness~…__a<k>`) and STDB `bench_attempt_result` — the cleanest "done" labels we produce;
`clm-p2-build.py` must learn the `__a<k>` refs before the next corpus rebuild.


## DELTA 2026-10-16 — Phase 2b fine-tune (FINETUNE_PLAN_B) FAILED on both arms; read `clm-p2-2026-10-01/ft-b/RESULTS.md` before any retrain
amos-1-small LoRA: OOF AUC 0.586 vs own zero-shot 0.696 (Δ −0.11, CI [−0.20, −0.03]); d1-3B LoRA: 0.613 vs 0.639 (CI spans 0). Inner-split AUCs
0.72–0.77 on every fold of both arms vs 0.53–0.72 on held-out TASKS → the 6,195-example corpus teaches task-specific signal (cross-fit by task is
the right protocol; it exposed the overfit a random split would have hidden). Typed models for R260 stay Jev (0.746) / self-hosted Amos large
(0.774) zero-shot. Harness lessons banked in the plan's amendments 1–4: Amos probabilities depend on the FULL served question set in one case
(render all three bake-off questions, read q1); eval at the served context (30K), train capped at 6K; five smoke attempts of box plumbing
(driver/CUDA floors, uv timeout, HF download retries, streamed logs, final-push watchdog). ~$12 total on Vast boxes.
