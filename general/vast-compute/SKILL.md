---
name: vast-compute
description: How WE use Vast.ai — the three job shapes (bench executor VM fleet, training/eval GPU jobs, one-off compute jobs), the shared box lifecycle rules (rent, right-size, provision, self-reaper + reboot cron, TTL, teardown, cost quoting), every trap hit (kvm key injection, destroy prompt, GPU-error boxes, stuck 'created', reused-IP host keys, repl-side watchers dying, /tmp and workspace quotas, pip lazy deps), and the reusable scripts. Load for ANY Vast rent/run/teardown, any "run this somewhere with more resources", or any cost question about boxes. The vendor CLI reference is the `vastai` skill; the bench executor internals are `harbor-bench`; GPU training on spot is `spot-gpu-compute`.
---

# vast-compute — our Vast.ai operations (verified 2026-09-12 → 09-20)

## 0. Which skill for what
| need | skill |
|---|---|
| CLI syntax, query language, copy/ssh commands | `vastai` (vendor reference) |
| TB2.1/TB4.0 bench fleet on kvm VMs: adapter, supervisor, stores, adjudication | `harbor-bench` (DELTAs 09-12c, 09-18, 09-19) |
| LoRA/eval GPU jobs on reclaimable spot pods, HF-Space→pod porting, reclaim-resume | `spot-gpu-compute` |
| shared lifecycle rules + one-off compute jobs (this file) | `vast-compute` |

## 1. The three job shapes
1. **Bench executor fleet** (harbor-bench): `docker.io/vastai/kvm:ubuntu_terminal --disk 200 --ssh --direct`, non-Taiwan offers ≥64 vCPU
   (`vms_enabled=true cpu_cores_effective>=64 cpu_ram>=96 disk_space>=200 rentable=true direct_port_count>=1 reliability>0.95 dph_total<1.5`),
   the VM reports ~61 vCPU inside a 64 offer (a 128 offer also showed 64); right-size 16 vCPU/lane → launchers export
   `TB2_VCPU_AUTOSCALE=1 TB2_MIN_VCPU_PER_LANE=15` (4 lanes). One store per box. `.bench/vm/provision-and-launch.sh <iid> <env> <launch.sh> <tag>`
   ships `.bench.env` (HF, DeepSeek, VAST keys), bootstrap, launcher, `self-reaper.sh`, installs the `@reboot` cron. $0.7–1.5/h per box.
2. **Training / eval GPU jobs** (spot-gpu-compute): interruptible pods, checkpoint-to-hub + resume; re-verify prices before spend.
3. **One-off compute jobs** (new 09-20): `.bench/vm/vast-job.sh <tag> <offer|query> <image> "<pip pkgs>" '<import check>' '<run cmd>' '<results glob>' <inputs…>`
   — docker image with the framework preinstalled (e.g. `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`), cheapest small-GPU box
   (`cpu_cores_effective>=8 cpu_ram>=16 disk_space>=40 rentable=true direct_port_count>=1 reliability>0.95 dph_total<0.3 gpu_ram>=8`
   ≈ $0.05–0.07/h), inputs scp'd, pip install, a REAL import check (the class you will use, not the package), run, results copied to
   `.bench/vm/jobs/<tag>/`, destroy ONLY on rc=0 + results present; a TTL self-destroy is armed on the box first. First use: the
   GLiNER 2.5 zero-shot pass over the 262 judge states (`.bench/jev/gliner-run.py`).

## 2. Lifecycle rules (all learned the expensive way)
- **Quote instance-hours at launch** (arms × wall hours × $/h); host cost is the bench cost, tokens are secondary. Vast credit auto-tops-up
  from the card ($5→$10), so the visible balance reads as a constant drain — turn auto-top-up OFF when spend must stop.
- **Teardown must live ON the box.** Every repl-side watcher (Monitor tasks, `setsid nohup` reapers) died with each Claude Code restart.
  `self-reaper.sh <iid> <ttl_h>`: DELETE `https://console.vast.ai/api/v0/instances/<iid>/` (Bearer `VAST_API_KEY`) when the run's
  processes are gone for 3 min after a 20-min grace, or at the TTL. Verified: six f1/e6 boxes destroyed themselves.
- **Host reboots kill the run AND the reaper** (cb, 09-19: idle 2.25 h). `@reboot /root/reboot-relaunch.sh` (wipe stale bench dirs →
  re-run the launch script → restart the reaper) is installed by the provisioner. Same-store relaunch resumes (banked rows skipped).
- **Launchers run in a detached tmux session ON THE REPL**, never from the agent's shell:
  `tmux new-session -d -s <tag> "cd $WORKSPACE && <env> bash .bench/vm/<launcher>.sh > .bench/vm/logs/<log> 2>&1"`.
  Rent → boot → provision is the only repl-dependent phase; `setsid nohup` / `&` from a Bash tool call dies with the Claude Code session
  (09-27: the dc1 rerun launcher died mid-smoke overnight; nothing rented, ~11 h lost). tmux survives a session end, NOT a repl restart,
  so after a restart run `vastai show instances` and destroy any box whose provision log has no "self-reaper armed" line.
  The box is repl-independent from `self-reaper armed` + `LAUNCH-DONE` onward. (Same rule, one line, in harbor-bench §rent-on-condition.)
- **Size the TTL ≥ 2× the estimate.** 31 TB4.0 tasks × 8-h budgets on 4 lanes ran ~2 tasks/h/box (~15–20 h), not 9.
- **Destroy per arm at completion**, never at fleet completion (`tb4e6-all-monitor.sh` folds destroy-at-29/29 in as a backup).
- **Never edit a script while a detached copy runs** (bash reads incrementally). Never `pkill -f '<pattern>'` from a command line that
  itself contains the pattern: bracket it (`superviso[r]`) and keep kill and restart in SEPARATE ssh calls.

## 3. Traps (each cost real time or money)
| trap | signature | fix |
|---|---|---|
| kvm boxes reject every ssh key when several account keys exist | "Permission denied (publickey)" | provisioner detaches foreign keys from the instance and reboots once (`provision-and-launch.sh`) |
| `vastai destroy instance` PROMPTS | Bash call hangs 120 s | `yes \| vastai destroy instance <iid>` |
| box dies at boot "GPU error, unable to start instance" | `actual_status created`, `cur_state stopped` | destroy, re-rent on a different machine_id (exclude it in the search) |
| box goes `exited` right after rent (09-27, offer 52007071) | provisioner loops 40 min waiting for `running` | kill the provisioner by PID, `yes \| vastai destroy instance <iid>`, relaunch with the offer in `LAUNCH_EXCLUDE_OFFERS` |
| box stuck in `created` for 25+ min with `cur_state running` | provisioner FATAL after its 15-min wait | destroy + re-rent; do not wait |
| reused public IP:port shows "REMOTE HOST IDENTIFICATION HAS CHANGED" | ssh warning | harmless with StrictHostKeyChecking=no; use `-o UserKnownHostsFile=/dev/null` |
| the VM sees a SLICE of the offer's cores (192→23, 128→64) | `nproc` inside | the bootstrap vCPU gate + autoscale decides lanes; read `nproc` in the provision log |
| repl `/tmp` is capped ~5 GB (canon store holds 4.4 GB); workspace quota ~51 GB | EDQUOT on pip/torch installs | never install torch locally; run the job on a box (`vast-job.sh`) |
| Vast auto-attaches tmux (`ssh_tmux`) on every ssh login for some images (python:3.12-bookworm, 10-18) | non-tty ssh commands: "open terminal failed: not a terminal"; scp "Connection closed"; `ssh 'true'` still exits 0 | create `~/.no_auto_tmux` by typing into the tty session (`printf 'touch ~/.no_auto_tmux\nexit\n' \| ssh -tt …`); `vast-job.sh` does this automatically when a plain command fails |
| pip lazy imports (gliner2 needed transformers, sentencepiece, protobuf, peft, accelerate) | `import gliner2` passes, `from gliner2 import GLiNER2` fails | the import check must exercise the class you use; never destroy the box before results exist |
| `docker.io/vastai/kvm:ubuntu_terminal` lacks compose v2 / buildx; apt wedges on unquoted `/etc/environment` | harbor trials die in ~2 s | bootstrap installs compose + buildx and quotes `/etc/environment` (harbor-bench DELTA 09-12c) |

## 4. Files
`.bench/vm/provision-and-launch.sh`, `bootstrap-executor.sh`, `self-reaper.sh`, `reboot-relaunch.sh` (generated per box), `launch-<arm>.sh`,
`tb4*-vm-monitor.sh` / `tb4e6-all-monitor.sh` (repl-side convenience), `tb4e6-adjudicate.py`, `vast-job.sh`, `executor-<tag>-{iid,ssh}.txt`,
`jobs/<tag>.log`. Vast key: secret `VAST_AI_API_KEY` (bridge) / `~/.config/vastai/vast_api_key`.

## 5. Cost references (measured)
e6 cell: 6 × 64-vCPU boxes × 7.5–11.5 h ≈ $54 host + $47 tokens. f1 full run: 4 boxes × 9.5–21 h ≈ $52 + $45 tokens. One-off GLiNER job:
RTX 3060 box $0.055/h, ~20 min. Two boxes died at boot across the week (≈$2 total).

## DELTA 2026-09-21 — the self-reaper's idle rule destroys a box you are maintaining
- Rule (a) of `.bench/vm/self-reaper.sh` destroys the instance after 3 consecutive minutes with no `tb2-durable-supervisor` process (past a
  20-min boot grace). Killing the supervisors ON PURPOSE — to swap stores, upgrade the in-VM driver and reboot, or pause a cell — trips it:
  09-21 it destroyed the GPU box mid driver-595 apt run (51865908) and the r176 box while its cell was being repinned (51933091), ~$0.60 lost
  plus two re-provisions. STRUCTURE: `touch /root/reaper-hold` before any such maintenance (the reaper now treats the hold as "not idle"),
  `rm` it once the lanes are back; the TTL rule still applies. A relaunch-from-the-repl (provision-and-launch on an existing box) must set the
  hold first; go-595-style on-box scripts set it as their first line.
- `vastai show instance <iid>` prints `not found or no longer exists` for a destroyed box; `show instances` is the roster check — do it BEFORE
  ssh-ing "unreachable (rebooting?)" for more than ~10 min.
- **Launchers rent boxes — they MUST be single-instance (09-21, five E1 boxes rented at once).** A rent-on-condition script (wait for npm →
  `vastai create instance`) must `flock -n` a lock file as its first act and exit if held. Never conclude a detached launcher "died" from a
  filtered `pgrep` (the detached copies ran under the interactive bash and my `grep -v bash-interactive` hid them); check the launcher's own
  log marker or the lock. Detached processes from the tool shell DO survive; the `[N]+ Done` line is the wrapper, not the script. If duplicates
  did run: `vastai show instances` immediately, destroy every extra `created|loading` instance, kill the extra provisioners by their instance
  id in the cmdline, and keep exactly one.
- **Extending a running box's TTL** = restart its self-reaper with a new TTL (`setsid nohup bash /root/self-reaper.sh <iid> 30 &`; the TTL
  counts from the restart). Do the kill and the start in SEPARATE ssh calls, and kill with `ps | grep | awk` + `kill <pid>`, never `pkill -f`
  over ssh — 09-21 the pkill matched the ssh session's own `bash -c` string, killed it before the restart line ran, and both E1/E2 boxes sat
  without a reaper until the next check. Verify with `ps -eo pid,etime,args | grep self-reaper.sh` and the log's `up=0m` line.
- **Multi-slice kvm hosts (09-21 evening): only the FIRST kvm instance on a host booted; the 2nd–4th slices sat in `created`/`loading` or
  `exited` (5 of 7 slices across two hosts). Rent one box per host: launch sequentially and pass the previous rents' offer ids in
  `LAUNCH_EXCLUDE_OFFERS`; `LAUNCH_SKIP_NPM_WAIT=1` when the version is already on npm. A box still `loading` after 15 min will not boot — destroy and re-rent.

## DELTA 2026-09-24 — the f66 launch: parallel smokes, launcher-lock inheritance, and the repl /tmp-device stall
| trap | signature | fix (in structure) |
|---|---|---|
| 8 smoke gates in parallel on the repl | later starters FAIL `endturn_resolver event` (4/8), identical env passes solo | `launch-cell-when-ready.sh` serializes smokes via `flock .bench/vm/locks/smoke-slot.lock` |
| a failed smoke's children inherit the launcher's flock fd 9 | every retry prints "another launcher holds the lock" with no launcher alive; `/proc/locks` shows nothing | smoke child runs with `9>&-`; lock files live in `.bench/vm/locks/` (replace the file if it ever recurs) |
| /tmp device (/dev/vdc, also the /home/runner overlay) stalls | `ps` shows ssh/tee/git in `D` state (`ovl_write_iter`, `folio_wait_bit`); `timeout` cannot kill them; provisioner sits after "detached foreign key" | ssh/scp `-o UserKnownHostsFile=/dev/null`; launch logs, smoke dirs and locks on the WORKSPACE disk (`.bench/vm/{logs,smoke,locks}`); check `awk '$2 ~ /^D/'` before any launch. Hog on 09-24 = the canon-store watcher's session-start `git clone` into /tmp |
| `vastai destroy instance` prompts (no tty → "Aborted.", exit 0) | five "destroyed" boxes still billing | `yes \| vastai destroy instance <iid>` or REST `DELETE https://console.vast.ai/api/v0/instances/<iid>/` (Bearer key) → `{"success": true}` — verify with `vastai show instances` |
| REST `GET /api/v0/instances/` returned an empty list for our key | "count 0" while the CLI lists 3 running | roster check = `vastai show instances --raw` or per-id `GET /api/v0/instances/<iid>/`; never conclude a fleet is gone from the list endpoint |
Rule restated: the launch (smoke → rent → boot → provision → reaper) is the ONLY repl-dependent phase (~25 min/eighth serial-smoked; ~60 min for eight). Never start it
when the repl may die inside that window — an un-provisioned box has no self-reaper and bills until destroyed.

## DELTA 2026-09-26 — unattended-upgrades upgraded docker MID-RUN (MiMo pilot)
~30 min after boot the kvm image's unattended-upgrades ran and upgraded `docker.io` 24.0.7 → 29.1.3 while tasks were running. The new
CLIENT (API 1.52) cannot talk to the still-running OLD daemon (max 1.43): every `docker ps` fails → the supervisor's venue check banks
`venue_unready` for each new task (3 attempts, then `INCOMPLETE … missing`), and an in-flight task hangs past its budget. Signature:
`docker info` → "client version 1.52 is too new. Maximum supported API version is 1.43"; `/var/log/dpkg.log` shows the upgrade.
Fix (structure): `bootstrap-executor.sh` now stops + disables unattended-upgrades and the apt-daily timers, kills a running upgrade, and
`apt-mark hold`s docker/containerd on EVERY box before any work (it used to do this only on the GPU path). Recovery on a live box:
`touch /root/reaper-hold` → stop the upgrade services → kill the stuck supervisor + harbor by PID → `systemctl restart docker` (daemon
catches up to the new client) → relaunch the affected shards with the bootstrap env (done-sets skip finished tasks) → `rm /root/reaper-hold`.

## DELTA 2026-09-26b — bootstrap lines must survive `set -euo pipefail`; never re-provision a box whose provisioner is still running
- `bootstrap-executor.sh` runs under `set -euo pipefail`. A `pkill` that matches nothing exits 1 (the NORMAL case) and kills the bootstrap
  SILENTLY: the log ends at the last echo, 0 supervisors, and the self-reaper destroys the box 23 min later (MiMo r2/r3, twice, ~$0.70).
  Every best-effort call (`pkill`, `systemctl stop/disable/kill`, `apt-mark`) ends in `|| true`, patterns bracketed, `systemctl` calls
  `--no-block` + `timeout`. Replay a suspect step ON the box under `set -e` (`bash -s` with `set -euo pipefail` prepended) — a replay without
  `set -e` passes and proves nothing.
- Relaunch on an existing box = `touch /root/reaper-hold` → `provision-and-launch.sh <iid> <env> <launch> <tag>` → verify `sup=<lanes>` →
  `rm /root/reaper-hold`. BEFORE it: `ps` for `provision-and-launc[h]` / `launch-cell-when-read[y]` — a still-running original provisioner also
  launches, and the box ends with 2× supervisors (two writers per shard). Fix = kill supervisors + harbor by PID from a listing, `docker rm -f`
  the task containers, relaunch once (separate ssh calls). Resolve the ssh port live (`vastai show instance <iid> --raw` .ports) — the cached
  `executor-<tag>-ssh.txt` can be stale.

## DELTA 2026-10-20 — RESIDENTIAL EGRESS POOL (browser MCP) = a fourth job shape, run on the SAME STDB control plane
Design: `nexus-terminal/docs/research/vast-proxy-pool-design-2026-10-20.md` (§2 mapping, §3 data path, §7 gateway test). Facts from the 10-20 offer
survey: 64 CPU-only offers, $0.010–0.013/h, bandwidth UNMETERED on all, 49 distinct host IPs, 37 on ISP/telco ASNs (TELUS, AT&T, Verizon, O2/T-Mobile
CZ, Telefónica, Orange, HiNet, KDDI, Viettel, Magyar Telekom, Google Fiber), 2 datacenter, 25 unknown; `direct_port_count` 0 on all → tunnels go
through Vast's SSH gateway (`ssh5.vast.ai` mapped port); static_ip on 24/64; one host IP can back several offers (busy set = one slot per machine).
Classify egress by ASN org (Team Cymru whois port 43 — `dig` is absent on the repl; use a socket) at rent time; datacenter → fail + ban.
Vast ToS is silent on proxying ("careful and proper manner") — confirm before scaling past a pilot. Cap ~8 clients per box (reputation), TTL 24 h.
Gateway concurrency test (P3): sweep N tunnels × D in-flight streams, MB/s ± sd + p50/p99, warm-up, 3 repeats, one box vs spread, end-to-end vs
raw — the SpacetimeDB-benchmark method (clients × pipelining, Little's law); "in the pipe" (streams inside one SSH connection) beats "on the wire"
(a connection per request; the gateway handshake is the auth-path analogue that crashed our local STDB at concurrency 16).
- 10-20b: the pool's box side is `.bench/vm/bootstrap-proxy.sh` (sshd forwarding-only key `restrict,port-forwarding …` + an sshd_config.d drop-in, egress ip
  via ipify/ifconfig.me/icanhazip, ASN/org/country via `whois.cymru.com:43` over a python socket, keyword classifier → residential|isp|datacenter|unknown,
  TTL-only self-reaper = `/root/reaper-hold` held forever). Rig `.bench/proxy/stdb-proxy-pool.sh`; sweep `.bench/proxy/gateway-sweep.sh` (P3, live pool only).
- 10-20c TRAP: `cpu_ram` is **0 on every CPU-only offer** (`num_gpus=0`; 64/64 probed) — Vast reports RAM per GPU slice. Any `cpu_ram gte N` term
  empties a CPU-only search (the proxy-pool rig's first filter returned 0 offers for US/CA). Filter CPU-only boxes on `cpu_cores_effective`,
  `disk_space`, `inet_up`, `reliability`, `dph_total`, `vms_enabled`; read the VM's real memory with `free -m` inside once it boots.

- 10-20d 🔴 VAST HAS NO CPU-ONLY COMPUTE (vendor-validated): the search API's `resource_type` enum is `network_disk | disk | gpu`; every `num_gpus=0`
  "offer" is a DISK ask (`resource_type disk`, price = `instance.diskHour`, `cpu_ram 0`, `gpu_name N/A`) and `PUT /asks/<id>/` on it always returns
  `404/3603 no_such_ask` whatever the body. Always pass `resource_type: "gpu"` in a compute search (the web console does). Cheapest compute on a
  residential/ISP line = a fractional-GPU Docker offer (`gpu_frac` 0.125–0.5) at $0.03–0.09/h; `vms_enabled` offers are rare and dear (US 1 @ $1/h).
  `onstart` is capped at 4048 chars (docs quirks note) — ship bundles by URL (`.bench/proxy/stdb-proxy-pool.sh publish-bundle`), never embedded.
  A host_place `create_failed` ban (2 h, by machine_id) is OURS (10-05 rule) — `unban_vast_machine` lifts it; 32 lifted 10-20.
