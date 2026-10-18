---
name: spot-gpu-compute
description: Choose and use a CHEAP spot / decentralized GPU market (Vast.ai, RunPod, Lium/SN51, io.net, Akash, NVIDIA DGX Lepton) instead of HF Spaces for sub-1B LoRA training / eval / inference — and PORT our durable-run apparatus onto it so reclaimable spot instances become a ~3x price win instead of a risk. Covers the market map + verified 2026 pricing, the durable-worker-formula fit (why WE can safely buy the cheapest reclaimable tier), the HF-Spaces→spot-pod porting recipe, the one-pod validation spike, and the data/payment-rail gates. Use when GPU cost matters, when picking where to run a training/eval arc, or when HF Space cost/OOM friction is the bottleneck. NOT for the CF nexus-cortex-sandbox container fleet (own Worker, session-routed — different beast).
triggers:
  - gpu cost
  - cheaper gpu
  - spot gpu
  - lium
  - vast.ai
  - runpod
  - rent a gpu
  - gpu marketplace
  - move off hf spaces
  - decentralized compute
---

# spot-gpu-compute — cheap reclaimable GPUs for our durable training/eval

The thesis in one line: **our durable-worker formula turns spot/reclaimable GPUs from a risk into a
~3x price cut.** A spot pod reclaim is the SAME event as an HF Space eviction, which our rig already
survives (store≠compute + D53 crash-resume). So we should deliberately buy the CHEAPEST reclaimable
tier and let resume-logic absorb reclaims — paying for SLA/"Secure" tiers WASTES the durability we
already built. This skill is how to pick a market and port onto it safely.

> Scope: sub-1B LoRA training/eval/inference (the S-series + P4 bake-off class; 24GB is enough,
> 48GB removes our OOM dance). NOT the TB2 CF `nexus-cortex-sandbox` fleet (own Worker + session
> routing — see harbor-bench). Sibling skills: `huggingface-spaces` (the lifecycle we're porting
> OFF), `v2p3-training-pipeline` (the run pattern), `harbor-bench` §📐 (the durable-worker formula).

## The market map (verified 2026-08; RE-VERIFY prices before spend — they move weekly)

Two tiers: **fiat brokers** (mature CLI, no token — the pragmatic default) vs **DePIN / crypto**
(cheapest headline, token-rail friction). For a 24GB LoRA run the target is a consumer 4090/3090 or
an L40S.

| Provider | Model | 4090 (24GB) | L40S/L40 (48GB) | H100 80GB | Rails | Notes |
|---|---|---|---|---|---|---|
| **Vast.ai** | P2P broker | **$0.29–0.35/hr** (spot from $0.13) | ~$0.40–0.80 | ~$1.49 | fiat | Maturest P2P; per-host reliability scores; per-second bill; **first spike target** |
| **RunPod** | community/secure | $0.34 community | ~$0.79 | ~$1.99–2.79 | fiat | Cleanest UX + real persistence tiers; Community=cheap/interruptible, Secure=SLA-ish |
| **Lium (SN51)** | Bittensor DePIN | 3090 $0.40 / 4090 $0.35 | **L40S $0.38 / L40 $0.33/GPU** | $1.75/GPU (8x) | TAO? verify | Cheapest L40S seen; DinD; hotkey providers; spot-reclaimable 88–100% rel |
| **TensorDock** | broker | competitive (unlisted) | — | — | fiat | Supplier-set prices |
| **io.net** | DePIN (1M+ GPUs) | $0.18–0.44 (spot from $0.01) | — | ~$1.47 | token | Huge supply, ~70% vs centralized; cluster deploy <2min; token friction |
| **Akash** | DePIN | ~$0.20 on-demand | — | $1.20–1.80 | AKT token | Compute-by-the-job; most mature DePIN; 60–70% vs AWS |
| **Prime Intellect** | aggregator | emerging | — | market | — | Early (no token yet); decentralized-TRAINING focus — WATCH for the W2S/distill arc |
| **NVIDIA DGX Lepton** | curated broker | n/a (datacenter parts) | — | ~$5/$2.91 on-dmd/spot | fiat/enterprise | NVIDIA's own MARKETPLACE (routes to neocloud partners, not NV metal); premium/curated tier — only for vetted H100/B200 at scale |
| **HF Spaces (baseline)** | managed | — (no 4090) | L40S ~$1.80 | — | fiat | a10g-small ~$1.05/hr; managed app lifecycle we're currently coupled to |

**Readings that drive the choice:**
- **~3x savings are real** for our workload: 4090 $0.29–0.35 vs a10g $1.05; **L40S $0.38 (Lium) vs
  $1.80 (HF)**. The **L40S is the standout** — 48GB kills the gradient-checkpointing OOM dance (the
  3072-tok × 248K-vocab-logit blow-up in s5_cont) → ~30% faster ON TOP of the cheaper rate.
- **Fiat brokers (Vast/RunPod) beat DePIN on friction for us** — same-ish price, no token, mature
  ssh/CLI. Lium's specific edge = cheap L40S; io.net/Akash = scale + deepest discount but token rails.
- **NVIDIA IS on-demand now (Lepton) but as a broker**, curated/premium, datacenter-GPU-tier — wrong
  tier for sub-1B. Signal, not a buy: even NVIDIA concluded the future is marketplace aggregation.
- **Prime Intellect** = watch for decentralized *training* specifically (closer to S-series than pod
  rental).

## Why WE can buy the cheapest reclaimable tier (the formula fit)

Map each spot risk to the durable-worker invariant (harbor-bench §📐) that already neutralizes it:
- **Pod reclaim mid-run** → same as HF eviction. `store≠compute`: results/logs/ckpts live in HF
  Datasets, NOT the pod disk. Reclaim loses nothing.
- **Refit-on-restart cost** → `resume-not-refit`: s5_cont already D53 crash-resumes from the highest
  step-named banked ckpt (`adapter-s{N}.bin` in OUT_REPO-ckpt). Fresh pod → relaunch → continues.
- **No SLA / provider churn** → `idempotent relauncher`: any session/cron re-provisions + relaunches.
- **No keep-alive/pause API** → UNNEEDED: pods bill only while UP, so the HF sleep-timer keep-alive
  dance + `pause_space` self-pause both disappear. `destroy` IS the self-pause; provisioning IS the
  wake. Simpler than HF, not harder.

Corollary: never pay for a "Secure"/on-demand SLA tier for a run our formula covers — that spends
money to buy reliability we manufacture in software.

## Porting recipe: HF Spaces → spot pod (what changes, what doesn't)

**Unchanged (the whole point — this IS the store≠compute test):** `s5_cont.py`, the HF Dataset store
(`shell-s5c1-logs` logs, `…-s7-adapter-ckpt` checkpoints, `shell-s3-queue` if queue-driven), the
[RESULT] battery format, HF_TOKEN + provider-key env, D53 resume logic.

**Changes (the compute control plane):**
| HF Spaces | Spot pod |
|---|---|
| Gradio app auto-runs on boot | `ssh` in, `python3 s5_cont.py` (or a boot script) manually / via cloud-init |
| HTTP keep-alive vs sleep timer | **gone** — pod bills while up; no keep-alive needed |
| `restart_space` / `pause_space` API | `<cli> destroy` = self-pause; re-`create` = wake |
| Space secrets UI | env vars on `create`, or scp a `.env` (never bake into image) |
| `get_space_runtime().stage` monitor | `<cli> instances` / ssh `pgrep` for liveness |
| relauncher = redeploy paused Space | relauncher = `<cli> create` fresh pod + relaunch cmd |

The queue-driven self-advancing pattern ports 1:1 — the queue is a Dataset, provider-agnostic. Only
the "am I alive / relaunch me" verbs swap from HF-API to pod-CLI.

## The one-pod validation spike (≈$1–2, ~2h — DO THIS before any migration)

Tests exactly one claim: **does the durable formula survive a provider swap?** Full plan:
`nexus-terminal/modules/database-ai/training/SPOT_GPU_SPIKE_PLAN.md`.

1. Provision ONE interruptible **Vast.ai 4090** (~$0.29–0.35/hr) — maturest CLI, fiat, apples-to-
   apples 24GB with a10g. (Lium L40S = spike-2 only after the port is proven.)
2. Port compute only: pod pulls `s5_cont.py`, reads/writes the SAME HF Datasets. Nothing store-side
   changes.
3. Run ONE eval-only checkpoint (`EVAL_ONLY_CKPT=adapter-s2725.bin`, `MAX_MINUTES=300`) → a [RESULT]
   battery directly comparable to a10g runs (double-serves a bake-off cell; dedup by the logs Dataset).
4. **Force a reclaim** at ~50%: destroy the pod, re-provision fresh, relaunch → confirm resume from
   the highest banked ckpt + clean finish. **THE load-bearing assertion** (a10g resume proven;
   cross-provider not).
5. Record to a decision note: actual $/hr, wall-time vs a10g, lossless-resume Y/N, port friction.

**Success** = battery completes + reclaim resumes clean + $/result ≤ a10g → validated lane for the
k=5 leaderboard run + future training arcs. **Fail** = needs the keep-alive/pause plane rebuilt AND
reclaim doesn't resume → stay on HF; friction not worth 3x.

## GATES before real spend (grounded, not skippable)
- **Payment rails:** Vast/RunPod = fiat/card (easy). Lium (SN51) = confirm fiat vs TAO. io.net/Akash
  = token (higher friction). Lepton = enterprise/fiat.
- **Data posture:** you're on a stranger's GPU. FINE for sterile open-weight training + public
  benchmarks (no private data; only ephemeral provider keys via env). NOT for user data / persistent
  secrets. Keep the CF TB2 fleet where it is.
- **Image match:** confirm the pod image's torch+CUDA match s5_cont's expectations or eat a
  cold-setup tax per pod (bake a known-good image once if going repeat).
- **Cost guards still apply** ([[feedback_gpu_cost_guards]]): state $ before spend, self-terminate at
  end, no auto-retry of failing runs, checkpoint long runs.

## Recommendation ranking (default path)
1. **Spike Vast.ai 4090** (fiat, mature, 24GB, per-second) — proves the port.
2. **Then Lium L40S** — best training lane if 48GB + $0.38 holds (drop checkpointing); verify TAO-vs-fiat.
3. **RunPod Community** — reliability-leaning fallback if reclaim churn ever hurts.
4. **HF Spaces stays** for anything needing the managed-app model until a spike proves the swap.
5. **CF container fleet (TB2) NOT a candidate** — own Worker + session routing (harbor-bench).
6. **Lepton / Akash / io.net** — only at datacenter-GPU scale or if a much larger base-model arc appears.

## Related
- Spike plan: `nexus-terminal/modules/database-ai/training/SPOT_GPU_SPIKE_PLAN.md`
- Durable-worker formula: `harbor-bench` skill §📐 · HF lifecycle being ported off: `huggingface-spaces` skill
- Run pattern + OOM/keep-alive lessons: `v2p3-training-pipeline` skill · Cost guards: [[feedback_gpu_cost_guards]], [[hf-space-job-ops-rules]]

## 🔬 LIVE VAST.AI SPIKE — proven mechanics + gotchas (2026-08-24, first real run)

Ran the eval-only s2700 battery on a Vast RTX 4090 to validate the port. Everything below is
hands-on, not planned. Reference: `scratchpad/vast-spike-relaunch.sh` (the ported invariant-5).

**CLI recipe that works (fully self-managed, zero user action):**
1. `pip install vastai` (v1.5.5). Key via `--api-key "$K"` per call, or `vastai set api-key`.
   Auth check: `vastai show user --raw` → 403 "requires login" = wrong/empty key; a JSON body with
   `credit` = good. NOTE `balance` and `credit` are DIFFERENT fields — `credit` is the spendable one
   (a funded account can show `balance:0, credit:10.0`).
2. **SSH key: register your OWN via API** — `vastai create ssh-key "$(cat id.pub)"` (no user paste!).
   `vastai show ssh-keys --raw` to verify. This is what makes the whole thing self-managed.
3. **Search:** `vastai search offers 'gpu_name=RTX_4090 num_gpus=1 rentable=true reliability>0.98
   disk_space>50 inet_down>300' -o 'dph+' --raw`. Sort by `dph_total`. `reliability2` is the live
   score. Prefer US geo for HF latency.
4. **Create:** `vastai create instance <OFFER> --image pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
   --disk 45 --ssh --label <lbl> --raw`. 🔴 **CHECK `success` in the response** — `success:false` with
   a `new_contract` means the host couldn't allocate (offer contended); the instance sits in
   `intended_status:stopped` forever. `vastai start` then returns "resources unavailable, state
   change queued." FIX: destroy + pick a DIFFERENT offer (availability is per-host and shifts). A
   good create returns `success:true` and reaches `actual_status:running` in ~30-60s.
5. **Destroy is INTERACTIVE** — `vastai destroy instance <id>` prompts "Are you sure?" → hangs a
   non-interactive shell. Use `yes | vastai destroy instance <id>`.
6. **SSH:** host/port from `vastai show instance <id> --raw` (`ssh_host`/`ssh_port`); user is `root`.
   `ssh -i key -p <port> -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@<host>`.
   First connect may warn "try again after a few seconds" — retry once.

**Port-friction found (the a10g HF Space bundles more than the .py files):**
- `import gradio` at module top crashes a pod without gradio — the Space app framework. STRIP it
  (`sed -i '/^import gradio as gr/d'`) since the UI code is unused when you call `run()` directly.
- The Space's entrypoint is a background `threading.Thread(target=queue_main)` + `demo.launch()` at
  module bottom — both run on import and `demo.launch()` BLOCKS. Make a launcher = `head -n <line
  before the thread>` + append `if __name__=='__main__': run()`, so importing defines functions and
  you drive `run()` directly (bypasses the HF-Space queue/self-restart/self-pause lifecycle — those
  are Space-API calls that no-op/fail on a pod anyway; that IS the control plane you're replacing).
- **Bundled DATA dirs travel too** — `interface-v1/` (tool schemas) sits next to the code and is NOT
  in the .py set; `scp -r` it. Grep the code for `os.path.join(HERE, ...)` / `open('<relative>')` to
  find every such asset BEFORE launching (each missing one = one crash-fix round trip).
- Sibling imports may live in a DIFFERENT repo dir (`shell-native/` here) than the main script
  (`bash-plus/`) — flatten them into one bundle dir; the script's `sys.path.insert(../sibling)` is
  then harmless.

**SECURITY — untrusted host, scoped-credential problem. ⚠️ DEMOTED SECTION (operator-directed
2026-08-26): this was the SPIKE-1/2-ERA option list and it repeatedly confused later setups.
Current doctrine: the HF STORAGE BUCKET (connection 44615, [[vast-hf-bucket-standing-config]])
is THE PRIMARY DATA PLANE — zero HF credentials on the pod for any data transfer. The options
below survive ONLY as (i) the REPO-BANKING exception and (ii) a data-plane BACKUP of last
resort:**
- HF does NOT expose token-minting via API (the `/api/users/access-tokens/new` endpoint 404s) — you
  CANNOT mint a fine-grained token programmatically.
- **Repo-banking exception (the one legitimate current use):** the bucket fronts buckets, not git
  repos, so s5-style runs still export the workspace HF_TOKEN in the SSH SESSION ENV ONLY for the
  small run-state/ckpt/adapter repo writes (inherited by setsid; never in `--env`/`--onstart`
  which Vast PERSISTS; never written to pod disk). This is a banking leg, NOT a transfer method.
- **Data-plane BACKUP ONLY (early-trial method, superseded by the bucket):** token-over-SSH bulk
  transfers (spike-1/2 style scp/hf_hub_download) may be used if the bucket connection is broken —
  caveats: broad token lives in pod RAM on a stranger's GPU for the run's whole life; every leg is
  hand-rolled (no --schedule auto-banking, hash-verify everything); destroy the pod after; rotate
  if the run was long. Do NOT plan new work on this path.
- (Historical option (c), the zero-token monkeypatch shim: correct but fragile — superseded by the
  bucket for data; only relevant again if full zero-credential repo banking is ever built.)

**DURABILITY — invariant 5 ported to Vast (`vast-spike-relaunch.sh`):** idempotent relauncher that
(1) no-ops if the battery is already banked to HF (checks logs for the RUN_TAG + a real `general`
RESULT), (2) finds the pod by `--label`, (3) relaunches the run if the process died on a live pod,
(4) PROVISIONS A FRESH POD + full cold setup (deps + bundle + scp interface-v1) + relaunch if the pod
was reclaimed. Arm a watchdog Monitor running it every ~5min (quiet while `ALIVE + run alive`). The
run is detached (`setsid nohup`) so it already survives session death; the watchdog adds
eviction-resilience = the HF durability parity. 🔴 EVAL-ONLY has NO mid-battery checkpoint, so a
reclaim RE-RUNS the whole battery (idempotent, dedup by HF logs) — true D53 mid-run resume needs a
TRAINING run banking step-checkpoints (spike-2 shape). store≠compute holds either way: the pod
carries no state that matters; the result lands in the HF Dataset.

## ✅ SPIKE-2 (2026-08-24): MID-RUN RECLAIM RESUME PROVEN — the formula fully survives the swap
Short sandbox TRAINING run on a UK 4090 → destroyed MID-TRAINING at step 200 (forced reclaim) →
fresh pod on a DIFFERENT host (Japan) + same durable setup script → **`[resume] from step 200`**,
trained forward, banked step 300 to the HF store. Bank→die→re-provision→resume→continue closed
cross-provider for ~$0.25. Both spikes total ~$0.55.
**Standing ops hardening (all in `.bench/`, NEVER the /tmp scratchpad — the reaper ate the SSH key
AND a launcher mid-arc):**
- `vast-deadman.sh` — session-independent detached repl process; destroys ANY account instance
  older than 100min, exits when the account is empty. MANDATORY whenever a pod exists: Vast pods
  have NO self-pause and bill until destroyed; a session crash without this = runaway spend. Wake
  protocol: check `ps aux | grep vast-deadman` + `vastai show instances` for orphans FIRST.
- **Save `instance_api_key` AT CREATE** (`.bench/keys/vast_instance_key`) — it appears ONLY in the
  create response, never retrievable later; enables on-pod self-destruct (the cleaner dead-man).
- Durable SSH keypair `keys/vast_spike`; `vastai attach ssh <id> "<pub>"` adds a key to a RUNNING
  instance (~1 min propagation) — keys registered before create are injected automatically.
- Sandbox-repo rule for test TRAINING runs: point OUT_REPO/LOGS_REPO at throwaway repos — a test
  run pushing to the real ckpt/logs repos would clobber run-state and the artifact bank.

**Training-on-spot design notes (from spike-2):**
- **Probe/bank cadence IS the durability knob.** A reclaim costs at most one bank interval of work
  (spike-2: ≤100 steps ≈ ~5 min GPU). Cheaper/flakier hosts justify tighter banking; the cost of a
  bank is one HF push (~seconds). Tune `N_PROBE`/probe-every-N to the host's reliability score —
  don't pay for reliability with money when you can pay with checkpoint frequency.
- **Resume trigger fires on run-state, not step-named banks.** The plain path (run-state `step` +
  `adapter.bin`) is sufficient for cross-provider resume — step-named `adapter-s{N}.bin` banks are
  the belt (D53 prefers them when present) but their absence does not block the test or the resume.
- **🔴 The session SCRATCHPAD is NOT durable even INTRA-session** — the /tmp reaper deleted the SSH
  private key and a launcher script MID-ARC while both were in active use. EVERYTHING ops-critical
  (keys, launchers, dead-man, rosters) lives in workspace (`.bench/`), full stop. Scratchpad is for
  transient clones/artifacts only — anything a relauncher or future wake needs must survive /tmp.
- **Timing the reclaim test**: with MAX_MINUTES short, destroy the pod IMMEDIATELY after a bank
  lands — waiting for "one more bank" can let the run finish before the reclaim, voiding the test.

**NEW (2026-08-06, NOT yet used by us): Vast ↔ HF Storage Bucket Cloud Connections.** Vast added
Hugging Face **Storage Buckets** (the new Xet-backed bucket product at huggingface.co/storage — NOT
the git Dataset/Model repos our formula banks to) as an account-level Cloud Connection: attach in
Vast settings, instances pull datasets/checkpoints from the bucket and push results back via cloud
sync (same system as S3/Dropbox/Backblaze/GDrive; main docs page still stale — announced via
blog/X). Spike-1/2 predated our awareness and hand-rolled transfers (scp + hf_hub_download with the
token SSH-delivered). **Why evaluate (spike-3 candidate):** (a) credential posture — token lives in
Vast's connection store, never transits the untrusted host's env (fixes our main compromise; use a
bucket-scoped credential); (b) potentially faster Xet transfers for checkpoints + a native
push-back banking leg. **Blocker to verify first:** whether the connection fronts only the bucket
product or also git repos — our resume machinery is repo-native, so bucket-only means adding a
bucket leg to the store topology (bank ckpts to bucket AND repo, or migrate the ckpt bank).

## 📦 OFFICIAL `vastai` SKILL INSTALLED (2026-08-24) — use it for CLI mechanics
`npx skills add vast-ai/vast-cli --skill vastai` → `.agents/skills/vastai/` (registered; also ships
as a Claude Code/Codex/Cursor plugin). THIS skill stays the strategy/durability layer; the official
one is the CLI reference. **Upgrades over our hand-rolled recipe (adopt these):**
- `vastai destroy instance <id> -y` — native non-interactive (retire the `yes |` hack); batch form
  `destroy instances <id1> <id2> -y`.
- `vastai copy local:./x <id>:/workspace/` — native file transfer both directions + instance↔instance
  + `s3.<connection-id>` cloud-connection endpoints; `vastai cloud copy --transfer "Instance To
  Cloud"` — the HF Storage Bucket connection (added in UI settings) rides this same connection-id
  mechanism. No scp needed for data (SSH still for exec).
- Search: `-o 'dlperf_usd-'` (perf-per-DOLLAR sort beats naive dph+) + `verified=true
  direct_port_count>=1` filters; image `@vastai-automatic-tag` picks the right CUDA tag.
- `--label` at create + `show instances --label X` — native fleet filtering (our relauncher greps
  client-side); `vastai recycle instance <id>` = destroy+recreate in one verb.
- **Official confirmation of our contended-host lesson**: `actual_status` ∈ {exited, unknown,
  offline} NEVER reaches running — timeout + destroy + retry a DIFFERENT offer (disk charges accrue
  while you wait).
- **🔴 DEAD-MAN NUANCE — `stopped` instances still bill STORAGE.** Interruptible/outbid instances go
  to `stopped` (not destroyed) and keep charging storage. A dead-man must DESTROY by age, not just
  check "running" (ours destroys any listed instance by age — correct; keep it that way).
- Volumes exist (`--create-volume/--link-volume`, `V.<id>:` copy endpoints) — persistent storage
  across instances; an alternative store leg to re-uploading per pod (still prefer the HF store as
  source of truth; volumes are a cache).
- On-image agent affordance: Vast's own images ship a `vast-capabilities` command + agent guide —
  prefer Vast-templated images when driving via agent so the box self-describes.

**🔴 STANDING CONFIG (operator-confirmed 2026-08-26): the token + Vast connection are scoped to
`<hf-org>/spike3-bucket` ONLY.** A new bucket = a new operator mint/connect cycle (VETOED —
"I don't want to go through this cycle again"). ALWAYS reuse `spike3-bucket` with per-project
prefixes (`p4c2/…`). Full standing config + repl-side API calls: memory
`vast-hf-bucket-standing-config`. Vast key env = `VAST_AI_API_KEY` (not VAST_API_KEY).

**✅ SPIKE-3 (2026-08-24): the Vast↔HF-Bucket connection WORKS — zero-token-on-host proven.**
Bidirectional hash-verified transfers with NO HF credential on the pod (scoped HFAK creds live in
Vast's connection store). Setup: fine-grained token (bucket-scoped, no spend perms) → "Generate S3
credentials" in the token dropdown (HFAK id + ONE-TIME secret) → Vast Cloud Connections with BARE
namespace ("<hf-org>"). 🔴 TRAP: `--src /bucket/dir` (leading slash + directory) transfers NOTHING
but still reports "Cloud Copy Operation Complete" — use `bucket/dir` (no slash) and ALWAYS
hash-verify arrival; the Complete status is not evidence. `--schedule HOURLY/DAILY` exists = native
auto-banking leg candidate. Gap: connection fronts BUCKETS not git repos — heavy artifacts can ride
the bucket while run-state/results stay repo-side. Full detail: SPOT_GPU_SPIKE_PLAN.md spike-3.

## 🔴 DELTA 2026-08-26 — the P4-C2 false-start: three self-inflicted failures, all skill-documented
Launched a 3-pod training arc WITHOUT re-reading this skill; every failure was already written here.
1. **Bare `pytorch/pytorch` image** → torch 2.2.1 → `pip -U transformers` breaks the env →
   AutoModelForCausalLM ImportError on ALL pods. The recipe PINS
   `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` (every successful spike create used it).
2. **Raw s5_cont.py launched** (module-bottom thread+demo.launch on import) and **bundle missing
   the shell-native/ siblings** — both in the port-friction list above.
3. **Declared "training" off a model-download progress bar.** RULE: a run is alive only when the
   log shows a training/probe STEP; "Fetching N files" is setup. Verify the step before reporting.
Also: quote-mangling through nested ssh-string layers — verify remote python with
`python3 -m py_compile <f>` (no inner quotes), and NEVER let an unasserted `str.replace` patch a
launcher (it no-ops silently; grep the file bytes after every patch).
The transcript-reconstructed canonical recipe now lives at `.bench/P4C2_VAST_RECIPE.md` — load IT
+ this skill before ANY Vast launch. Cost of the lesson: ~$0.26 credit, ~90 min, three dead pods.

## DELTA 2026-08-26b — training-pod ops proven live (the s11 pilot; details recipe §4b + v2p3 skill)
- **Multi-boot sup loop = the Vast analog of HF's queue self-restart** (a capped s5-style run
  needs N resume boots; a single setsid invocation parks after MAX_MINUTES). Pod-side
  `sup-<run>.sh`: re-invoke until the run's REAL completion marker; token exported in the SSH
  session env and inherited by setsid — NEVER written into the sup script (spike-2 posture).
  Completion markers must be robust to PARTIAL output (the s11 sup false-completed on a
  truncated eval battery — key on a full-run denominator, not line presence).
- **Costume rules hold INSIDE ssh remote commands**: a remote `pkill -f <literal>` matches the
  remote wrapper shell (exit 255, silent) — bracket patterns on pods too; remote polls need
  `</dev/null` (ssh drains stdin from while-read loops — already in the skill; re-bitten).
- **Deadman relaunches use ABSOLUTE paths** (a relative `>> .bench/…` redirect after `&`
  failed on cwd once) and are sized to the WHOLE multi-boot arc, not one boot — D53 resume
  makes even a deadman destroy lossless, so err long (~1500min) rather than shooting a
  healthy run.
- **Repl restarts kill deadman+timers silently while the POD keeps billing** — post-restart
  triage always: `pgrep -f "vast-deadma[n]"` + `vastai show instances` (duration field = age)
  BEFORE anything else.
