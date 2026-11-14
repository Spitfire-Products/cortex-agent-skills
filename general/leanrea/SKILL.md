---
name: leanrea
description: Reverse engineer shipped software with plain local CLI tools, no MCP needed. Covers Electron/JS bundles, native Mach-O/ELF/PE, Go/Rust/.NET/Flutter/WASM binaries, APKs, SQLite, pcaps, firmware and websites. Use to explain how a feature works, extract versions/deps, compare builds, or rebuild a feature.
---

# leanrea: fast path

You already know these tools. This file only lists the fastest command for each target, and the traps.

## Rules
- Work on a copy (`cp -c` on APFS is instant). Put each extraction in a new dir under `$TMPDIR/re/<name>`. Reuse an extraction if one exists.
- Route by `file -b T` and the magic bytes first. Run the cheapest inventory next. Only then decompile or read code.
- `rg` skips hidden and ignored files, and bundlers hide code (Electron: `.webpack/`, `.vite/`). Always search extracted trees with `rg -uu`.
- Never `cat` a big or minified file. Slice it: `rg -o '.{0,200}NEEDLE.{0,200}' F | head`. Dump a disassembly once to a file, then grep that file.
- Batch independent probes into ONE shell call with `;` and `echo '--- name'` markers (quoted: zsh expands a bare `==x`). Cap every output with `head` or `-m`.
- Answer from evidence. In the answer, mark each claim as **seen** (cite file:offset, or a symbol/string) or **inferred**. A fact you did not find is **unknown**, not "absent". Static reading is not observed execution.
- A missing tool is not a blocker. Use the fallback in the same row, or `brew install <x>` if the user allows it.
- Turns cost more than bytes. Aim for 2–4 tool calls: one batched recon call, one or two targeted slices, then answer. Stop when every item you were asked has evidence. Do not re-verify what you already saw.

## First move: one call each, paste and run
Native (Mach-O):
```sh
T=./bin; D=$TMPDIR/re/$(basename $T); mkdir -p $D; file $T; lipo -info $T; otool -L $T; echo '--- EXPORTS'; nm -gU $T | head -150; echo '--- IMPORTS'; nm -u $T | rg -v '^__Z|napi_' | tr '\n' ' '; echo; echo '--- STRINGS'; strings -a -n 6 $T | rg -v '^[_$.]' | head -400; otool -tV $T > $D/dis.txt; echo '--- FUNCS'; rg '^[_a-zA-Z].*:$' $D/dis.txt | rg -v '^_?_?Z?N?St3' | head -150
```
Then read one function: `awk '/^FUNC_LABEL:$/{p=1;next} p&&/^[_a-zA-Z].*:$/{exit} p' $D/dis.txt | rg 'bl|b\.|cmp|literal|mov\s+w2'`.

Electron:
```sh
A=./app.asar; X=$TMPDIR/re/asar; rm -rf $X; npx -y @electron/asar extract $A $X && jq '{name,version,main}' $X/package.json; find $X -path '*/node_modules' -prune -o -type f \( -name '*.js' -o -name '*.node' \) -print | head -60; ls ${A}.unpacked/node_modules 2>/dev/null; rg -uu -l --glob '!node_modules' 'exposeInMainWorld' $X
```
Then slice the needle across the bundle: `rg -uu -o --glob '!node_modules' '.{0,250}NEEDLE.{0,250}' $X | head -20`.

Go: `go version -m T` alone usually answers the question.

## Router
| Target (detect) | Fastest path |
|---|---|
| Electron app (`*.app/Contents/Resources/app.asar`) | `npx -y @electron/asar extract app.asar X` (also see `app.asar.unpacked/` for `.node` addons). Entry point: `jq .main X/package.json`. Surface: `rg -n -o '.{0,120}(ipcMain\.(handle|handleOnce|on|once)|ipcRenderer\.(invoke|send|sendSync|on)|contextBridge\.exposeIn(Main|Isolated)World|webPreferences|preload:|nodeIntegration|contextIsolation|sandbox|\.node\b).{0,160}' -uu X --glob '!node_modules'`. App-specific IPC wrappers often hide the channels, so also run `rg -uu -o '"[a-z]+:[a-z0-9:-]+"' X/<main> \| sort -u`. Fuses: `npx -y @electron/fuses read --app A.app`. |
| Web bundle / minified JS | Find `sourceMappingURL`. If the map has `sourcesContent`, dump the sources: `jq -r '.sources[]'`. For webpack, grep the module ids, then slice around the hit. For pretty-print: `npx -y prettier --parser babel F > F.pretty.js`, then read with line ranges. |
| Hermes / bytenode / V8 snapshot | Hermes magic is `c6 1f bc 03` (`index.android.bundle`): use `hermes-dec` / `hbc-decompiler`. `.jsc` (bytenode) cannot be decompiled: use strings and runtime hooks. |
| Mach-O (`file`: Mach-O) | `lipo -info` (thin first: `lipo -thin arm64 -o T1 T`). Then: `otool -L` (libs); `xcrun dyld_info -exports -imports`; `nm -gU` (exports) / `nm -u` (imports = the capability map); `strings -a -n 6`; `otool -l \| rg -A3 'LC_(RPATH\|BUILD_VERSION)'`; `codesign -d --entitlements :- T`; `otool -ov` (ObjC classes/methods); `xcrun swift-demangle --compact`. |
| Native code logic | `otool -tV T > $D/dis.txt` (or `llvm-objdump -d --no-show-raw-insn -C`). Find the function: `rg -n '^_?.*Name.*:$'`. Read the call/string trail: `awk '/^FUNC:/{p=1} p&&/^[_a-zA-Z].*:$/&&!/FUNC/{exit} p' dis.txt \| rg 'bl\|call\|literal\|cmp'`. otool labels string literals and stubs inline, which is often enough. Only for real pseudocode: Ghidra `analyzeHeadless $D p -import T -postScript DecompileAll.java -deleteProject` or `r2 -qc 'aaa; pdc @ sym.X' T`. |
| ELF / PE | `readelf -hlSW`, `readelf -dW` (NEEDED), `nm -D --defined-only`, `objdump -d -M intel`. PE: `objdump -x`, `pefile`/`wrestool` for resources. checksec: `pwn checksec`. |
| Go (`__go_buildinfo`, `.go.buildinfo`) | `go version -m T` gives the toolchain, path, mod, deps and build flags in one call. Without Go: `strings -a T \| rg -m1 -A200 'Go buildinf' `. Symbols survive stripping: `go tool nm T \| rg main\.`. |
| Rust | Deps (cargo-auditable): `cargo audit bin T`, or extract `.dep-v0` / `__DATA,.dep-v0` and zlib-inflate it. Compiler: `strings -a T \| rg -o '/rustc/[0-9a-f]{40}' \| sort -u`. Crates from paths: `strings -a T \| rg -o '[a-z0-9_-]+-[0-9]+\.[0-9]+\.[0-9]+/src' \| sort -u`. |
| .NET (`file`: Mono/.Net) | `ilspycmd -p -o X T.dll` (install: `dotnet tool install -g ilspycmd`), then `rg`. P/Invoke: `rg DllImport X`. NativeAOT/IL2CPP are native: use the native rows. |
| Android APK | `jadx -d X --show-bad-code a.apk` then `rg`. Resources/manifest only: `apktool d --no-src -o X a.apk`. Quick look: `unzip -l a.apk`. `lib/*/libflutter.so` means Flutter (Dart AOT: `blutter`); `libhermes.so` means React Native (Hermes row). |
| Flutter snapshot hash | In `libapp.so`, find magic `f5 f5 dc dc`; the 32 hex chars at +20 are the snapshot hash. Map it to a Dart version. |
| WASM | `wasm-objdump -x`, `wasm2wat`, `wasm-decompile` (WABT). |
| SQLite | Copy the db, plus the `-wal` file if present. `sqlite3 'file:C?mode=ro' '.schema'`, then `SELECT * FROM t LIMIT 20`. |
| plist / nib / car | `plutil -p F`. Info.plist holds the bundle id, URL schemes and privacy strings. Asset catalogs: `assetutil --info Assets.car`. |
| pcap / HAR | `tshark -r C -q -z conv,tcp`; `tshark -r C -T fields -e dns.qry.name -e tls.handshake.extensions_server_name -e http.request.full_uri \| sort -u`. HAR: `jq -r '.log.entries[].request \| .method+" "+.url'`. |
| Firmware | `binwalk -e F` or `unblob -e X F`. Then route each extracted binary through this table. |
| Website | `curl -sL URL` for the HTML and script srcs, then fetch the JS and slice it. For runtime behavior, use a headless browser with a network log (Playwright `page.on('request')`) or Chrome `--remote-debugging-port`. |
| Running app / runtime | macOS: `lldb -p PID`, `dtrace`/`fs_usage`/`log stream --predicate 'process=="X"'`. Electron main: `--inspect` (only if the RunAsNode/inspect fuses allow it). Android: `adb logcat`, `frida -U -f pkg -l hook.js`. |

## Speed patterns
- Strings and imports first. On a small binary, `nm -u` + `strings` + the export list usually answer "what does it do" with no disassembly.
- To find who uses a string: get its address from `otool -tV` "literal pool for" comments, or `rg -n 'literal pool for: "X'`. Then find the enclosing function label above that line.
- A C++ name in a `bl` target already tells you the protocol (for example `getpeereid`, `write`, `std::hash`). Read the call sequence, not every instruction.
- For JS, go from the native/JS boundary inward: find the native call, then its caller class, then the IPC registration, then the renderer/preload.
- Comparing versions: diff the inventories (`nm`, the module list, `go version -m`) before you diff any code.
- Rebuilding: write the minimal reimplementation, then test it against the original (same inputs, same outputs).

## Install (only on request)
`brew install jadx apktool radare2 binwalk wabt wireshark ghidra` · `npm i -g @electron/asar` · `dotnet tool install -g ilspycmd` · `cargo install cargo-audit`.

---
## Local notes for THIS workspace (appended 2026-10-19; everything above is upstream aicodeking/leanrea @ 09ba4aa0, MIT — see LICENSE)
- Linux box, not macOS: use the **ELF / PE** row (`readelf -hlSW`, `readelf -dW`, `nm -D --defined-only`, `objdump -d -M intel`) where the
  first-move block says `otool`/`lipo`/`codesign`; no `brew` — tools come from the Nix runtime path or `npx -y`.
- Scratch dirs: `/tmp` is quota-capped at 5 GiB (the canon store fills it) — put `$TMPDIR/re/<name>` under
  `$WORKSPACE/.bench/tmp-smoke/re/<name>` for anything over a few hundred MB. `cp -c` is APFS; here `cp --reflink=auto` (btrfs) is instant.
- Big binaries: a 200+ MB Bun executable (Claude Code `claude.exe`) interleaves a string table with JS chunks — one Python pass with
  `re.finditer` over the decoded bytes beats repeated `rg`; the `claude-code-variables` skill already does this for flags/env.
- Memory: run any whole-binary pass through `scripts/oom-box.sh --max 3G -- …` (8 GB VM, no swap; see skill `replit-management` §8).
- Already-mapped targets (don't redo): the Replit supervisor stack (pid0/pid1/pid2), the `replit` CLI, pid2's `/mnt/pid2/*.cjs` bundles,
  the viktor SQLite index — all in skill `replit-management`. `go version -m` works here (Go toolchain present).

---
## VM disk images / guest filesystems (appended 2026-11-05, macbook; proven on a suspended Parallels Win7 VM)
Read a guest FS **without booting the VM and without hypervisor tooling**: the pure-python Fox-IT `dissect` stack parses the
container, the partition table and the filesystem directly, read-only. Works where the vendor tools refuse — Parallels Mounter
and `prl_disk_tool` both reject a SUSPENDED VM's disk; `dissect` does not care. Pure python → runs on old hosts (Big Sur
py3.12 verified; no compile).
```sh
python3 -m pip install dissect.hypervisor dissect.volume dissect.ntfs   # + dissect.extfs/xfs/vmfs as needed
```
```python
from pathlib import Path
from dissect.hypervisor.disk.hdd import HDD          # Parallels; also: .vmdk VMDK, .vhdx VHDX, .qcow2 QCOW2
from dissect.volume.disk import Disk                  # MBR/GPT
from dissect.ntfs import NTFS
hdd = HDD(Path(".../VM.pvm/HardDisk-0.hdd"))          # the .hdd BUNDLE dir (DiskDescriptor.xml + .hds), not the .hds
fs = NTFS(Disk(hdd.open()).partitions[1].open())      # [0] is usually System Reserved on Windows
rec = fs.mft.get("Program Files/Vendor")              # path lookup from root
rec.listdir()                                         # dict name -> entry; keys are the names
with fs.mft.get(f"{path}/{name}").open() as f: ...    # stream file content (chunked read for big files)
```
Traps (cost an iteration each): `listdir()` values are IndexEntry objects with NO `.name` — iterate the dict KEYS and
`fs.mft.get(full_path)` each child for reliable `is_dir()` / `size()` / `open()`. Skip the 8.3 alias names (`FOO~1.LUA`) or
you copy everything twice. `DiskDescriptor.xml` in the .hdd bundle gives size/encryption/suspend state before you start.
Windows layout recall: user content under both `Program Files*` AND `Users/<u>/AppData/{Roaming,Local}`; `Documents and
Settings` is a junction (may not resolve — use `Users/`). Sweep for artifacts by extension with a bounded-depth recursive
walk rather than a full-MFT pass on 8 GB hosts.

## Defunct-vendor source hunting (appended 2026-11-07, macbook; proven on the Gehtsoft/Indicore SDK)
When a vendor's download site is dead and you need headers/bundles/grammars, run these in cost order:
1. `gh api orgs/<org>/repos` then `git/trees/<ref>?recursive=1` per repo — grep whole trees with zero clones.
2. PRs survive deleted forks: `pulls?state=all` names the real engineers; `pulls/N/files --paginate` manifests
   let you diff "what a PR added" vs current master to spot content deleted since (or confirm nothing hidden).
3. Wayback CDX (`/cdx/search/cdx?url=<domain>&matchType=domain&collapse=urlkey`) rate-limits hard — sleep
   20-30s, retry once, treat EMPTY output as a rate-limit not a no-capture until a clean query confirms.
4. Cloudflare-walled legacy hosts: curl fails even with a browser UA (JS challenge) and curl INSIDE the
   browser sandbox fails too (clearance is per-client) — only the sandbox's real `browse()` page passes;
   then `extract_links`/`get_content`. One session, close it.
5. `gh api search/code -f q='"DistinctiveClassName" extension:h'` settles "does any public copy exist" in one call.
6. **Sample ASSETS are ground truth**: mobile samples' `assets/`/`Resources/` data files carried the exact
   HDR/DAT file grammar the engine's own ini described ambiguously (named `t1` interval vs our guessed "1" —
   two failed runs). Sweep bundled sample data BEFORE guessing any file grammar.
7. No public headers anywhere ⇒ reconstruct: sample-code usage + `c++filt` on the .so dynamic table +
   typed MSVC exports of the Windows sibling DLL; check `.comment` (GCC era) to size the ABI effort first.
Worked example + full source map: market-research/re/gehtsoft-sources.md.

## Live traffic of a running app (appended 2026-11-13, workspace; DRAFT — finalize after the Sun 11-15 Trading Station capture)
Goal: see where a running desktop app gets its data — which hosts, which connections stay open, how often messages arrive, how late
they are — then hand the capture to the pcap row above for analysis. Static first: extract every URL/host from the binaries
(`strings -el`/`strings` + a URL regex over each DLL/EXE/.so; worked example market-research/public-endpoints.txt, 41 TS binaries) so
live hosts can be mapped to the component that names them.
**Scope rules (hard):** your own software on your own machine; read the vendor's terms before any decryption; trading/banking apps
ONLY on a demo login for anything beyond tier 1; captures stay on the capturing machine (never mailed, uploaded or committed);
never type, log or store a credential for someone else.
**Tier 1 — passive capture (no decryption, no credential exposure). Start here; it answers most questions.**
- Pick the interface the app's traffic crosses. A VM guest: capture on the HOST's virtual interface (Parallels shared network
  shows as a `bridge`/`vnic` interface; list with `ifconfig`, confirm with a test ping from the guest). `sudo tcpdump -i <if> -w
  cap.pcap 'not port 22'` (or Wireshark, same filter); note the guest IP to filter later.
- Sync clocks FIRST (`sntp -sS time.apple.com` on macOS; `w32tm /resync` in Windows) and log the host↔guest offset before and after.
- Read it: `tshark -r cap.pcap -q -z conv,tcp` (long-lived conversations = streams), `-T fields -e frame.time_epoch -e ip.dst
  -e tls.handshake.extensions_server_name` (which host each connection is), then per long-lived connection the packet
  inter-arrival times and sizes (`-Y 'tcp.stream==N' -T fields -e frame.time_delta_displayed -e tcp.len`) → rate per stream,
  p50/p95 gaps, burst pattern. Map each SNI host to the static endpoint list.
**Tier 2 — intercepting proxy (decrypts; ONLY if tier 1 cannot answer the protocol question, ONLY on a demo login).**
- mitmproxy/mitmdump on the host, the app pointed at it (system proxy in the guest, or transparent mode); trust mitmproxy's CA in
  the guest's ROOT store (Windows: `certutil -addstore root mitmproxy-ca-cert.cer`) — remove it when done.
- Filter the sign-on exchange OUT of the saved flows (a mitmdump `-s` script that drops auth/SSO/token URLs and Authorization /
  Cookie headers before writing); assume a raw flow file contains secrets and keep it local.
- Pinning check: if the app refuses to connect (or the proxy logs TLS handshake failures only for the app's hosts) the client pins
  certificates — STOP; tier 1 is the answer. Do not patch the binary to defeat pinning.
**Timing / delay study:** delay = receive time (NTP-synced capture clock) − the source's own timestamp in the message (tier 2, or
any timestamp visible in clear text); without a source timestamp, report cadence only (rate, inter-arrival), and lead/lag
against a second recorded source of the same instrument.
TODO after the Sunday run: the real interface name on the macbook's Parallels, the TS hosts/ports seen, whether TS honours the
system proxy, whether it pins, the measured quote cadence per pair — replace this TODO with what was proven.
