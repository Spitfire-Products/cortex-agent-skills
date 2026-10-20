#!/usr/bin/env python3
"""ccv — Claude Code Variables scanner/ledger (drives BOTH skills: claude-code-variables and claude-code-experiments).

Kinds tracked (all read from the installed Claude Code binary + the GrowthBook cache in .claude.json):
  flag     remote feature flags (`tengu_*` read through k()/Gr()/Fn()/g_()/hz()/ld()/xP()/$n()/servedTrue(...))
  env      environment variables (typed env getter table `NAME:()=>x` + direct `process.env.NAME` reads)
  setting  settings.json keys (zod schema keys with .describe(), `hs("key")` reads, `ft().key` reads)
  event    telemetry event names (`tengu_*` used only as log-event names) — tracked for completeness, auto-summarised

Ledger model (APPEND-ONLY): data/inventory.jsonl is the event log (added / deprecated / restored / value_changed / investigated /
scan). data/state.json is the MATERIALISED view rebuilt from scans + ledger. reference/*.md are GENERATED — never hand-edit them.

Sub-commands:
  check            fast path for the SessionStart hook: version + cache compare; cache diff inline; background `update` on a
                   version change; prints a one-line notice (and the pending-investigation count) as JSON for the hook
  update           full scan of the binary + cache → diff → ledger → state → regenerate both skills' reference files
  mark NAME ...    record an investigation result for an item (--kind --category --summary --confidence)
  regen            regenerate reference files from state (no scan)
  status           print counts and the pending list
  seed-tsv FILE    import an existing classification TSV (flag or env map) as investigated summaries (one-time bootstrap)

Env: CCV_BINARY (override binary path), CCV_CONFIG_JSON (override .claude.json path), CCV_LOG (log path).
"""
import json, os, re, sys, time, glob, hashlib, subprocess, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)                                   # .claude/skills/claude-code-variables
SKILLS_ROOT = os.path.dirname(SKILL)
EXP_SKILL = os.path.join(SKILLS_ROOT, "claude-code-experiments")
DATA = os.path.join(SKILL, "data"); REF = os.path.join(SKILL, "reference")
EXP_DATA = os.path.join(EXP_SKILL, "data"); EXP_REF = os.path.join(EXP_SKILL, "reference")
LEDGER = os.path.join(DATA, "inventory.jsonl"); STATE = os.path.join(DATA, "state.json")
EXP_LEDGER = os.path.join(EXP_DATA, "experiments.jsonl"); EXP_STATE = os.path.join(EXP_DATA, "state.json")
NOTICE = os.path.join(REF, "NOTICE.md")
# CHANGELOG (2026-10-20, operator): the public Claude Code changelog names new variables/flags/settings as they ship and describes
# behaviour the binary scan can only hint at. It is tracked beside the binary scan: cached raw file, append-only entry ledger, a
# generated reference, and an UNTRIAGED queue the agent turns into library candidates (library/CANDIDATES.md, hand-curated).
CHANGELOG_URL = os.environ.get("CCV_CHANGELOG_URL", "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md")
CL_CACHE = os.path.join(DATA, "changelog.md"); CL_STATE = os.path.join(DATA, "changelog-state.json")
CL_LEDGER = os.path.join(DATA, "changelog.jsonl"); CL_REF = os.path.join(REF, "changelog.md")
CANDIDATES = os.path.join(os.path.dirname(REF), "library", "CANDIDATES.md")
CL_KEYWORDS = ("tool", "hook", "agent", "subagent", "memory", "compact", "context", "cache", "sandbox", "permission", "mcp", "effort",
               "thinking", "prompt", "skill", "plugin", "session", "resume", "diff", "bash", "worktree", "checkpoint", "rewind", "transcript",
               "token", "model", "stream", "retry", "timeout", "background", "monitor", "cron", "schedule", "auto mode", "auto-mode", "env", "setting")
LOG = os.environ.get("CCV_LOG", "/tmp/claude-code-variables.log")
CONFIG_JSON = os.environ.get("CCV_CONFIG_JSON") or os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~"), ".claude.json")
if not os.path.isfile(CONFIG_JSON):
    for cand in ["$WORKSPACE/.claude.json", os.path.expanduser("~/.claude.json")]:
        if os.path.isfile(cand): CONFIG_JSON = cand; break
PT = datetime.timezone(datetime.timedelta(hours=-7), "PT")  # display only; ledger stores UTC ISO

FLAG_GETTERS = {"k", "Gr", "Fn", "g_", "hz", "ld", "xP", "$n", "c1", "rC"}  # c1 = dynamic config (async), rC = k alias
EVENT_LOGGERS = {"i", "js", "jT", "ePt", "e", "rC"}
ENV_PREFIXES = ("CLAUDE", "DISABLE", "ANTHROPIC", "MCP_", "MAX_THINKING", "BASH_", "API_TIMEOUT", "ENABLE_", "FORCE_", "IS_DEMO", "DO_NOT_TRACK", "FALLBACK_")


def now_iso(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def now_pt(): return datetime.datetime.now(PT).strftime("%Y-%m-%d %I:%M %p PT")
def log(msg):
    try:
        with open(LOG, "a") as f: f.write(f"{now_iso()} {msg}\n")
    except Exception: pass
def jload(p, default):
    try: return json.load(open(p))
    except Exception: return default
def jdump(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"; json.dump(obj, open(tmp, "w"), indent=1, sort_keys=True); os.replace(tmp, p)
def append(path, rec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f: f.write(json.dumps(rec, sort_keys=True) + "\n")
def snippet(b, i, before=220, after=300):
    return b[max(0, i - before):i + after].decode("utf-8", "replace").replace("\n", " ").replace("\t", " ")


# ----------------------------------------------------------------------------------------------------------------- binary
def binary_path():
    p = os.environ.get("CCV_BINARY")
    if p and os.path.isfile(p): return os.path.realpath(p)
    for cand in ["claude"]:
        try:
            out = subprocess.run(["bash", "-lc", f"command -v {cand}"], capture_output=True, text=True, timeout=10).stdout.strip()
            if out: return os.path.realpath(out)
        except Exception: pass
    return None


def binary_version(path):
    """Fast: package.json next to the npm install; fallback: VERSION:"x.y.z" literal inside the binary."""
    if not path: return None
    d = path
    for _ in range(4):
        d = os.path.dirname(d)
        pj = os.path.join(d, "package.json")
        if os.path.isfile(pj):
            try:
                v = json.load(open(pj)).get("version")
                if v: return v
            except Exception: pass
    try:
        b = open(path, "rb").read()
        m = re.search(rb'VERSION:"(\d+\.\d+\.\d+[^"]*)"', b)
        if m: return m.group(1).decode()
    except Exception: pass
    return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""): h.update(chunk)
    return h.hexdigest()


def scan_binary(path):
    """Returns {kind: {name: item}} with item = {default, desc, sites, snippet, getters}."""
    b = open(path, "rb").read()
    items = {"flag": {}, "env": {}, "setting": {}, "event": {}}
    # --- tengu_* lookups: flag getters vs event loggers
    uses = collections.defaultdict(lambda: {"getters": collections.Counter(), "defaults": set(), "pos": None, "sites": 0})
    for m in re.finditer(rb'([A-Za-z_$][\w$]{0,3})\(\s*"(tengu[_-][a-z0-9_-]+)"\s*(,([^()]{0,80}?))?\)', b):  # hyphenated names = dynamic configs / off-switches
        fn = m.group(1).decode(); name = m.group(2).decode(); dflt = (m.group(4) or b"").decode("utf-8", "replace")
        u = uses[name]; u["getters"][fn] += 1; u["sites"] += 1
        if fn in FLAG_GETTERS:
            u["defaults"].add(dflt)
            if u["pos"] is None: u["pos"] = m.start()
        elif u["pos"] is None and fn in EVENT_LOGGERS: u["pos"] = m.start()
    for name, u in uses.items():
        is_flag = any(g in FLAG_GETTERS for g in u["getters"])
        kind = "flag" if is_flag else "event"
        items[kind][name] = {"default": "/".join(sorted(u["defaults"]))[:60] if is_flag else "", "desc": "",
                             "sites": u["sites"], "snippet": snippet(b, u["pos"]) if u["pos"] is not None else "",
                             "getters": ",".join(sorted(u["getters"]))}
    # servedTrue("tengu_x") kill-switch readers
    for m in re.finditer(rb'servedTrue\("(tengu_[a-z0-9_]+)"\)', b):
        n = m.group(1).decode()
        if n not in items["flag"]:
            items["flag"][n] = {"default": "false", "desc": "", "sites": 1, "snippet": snippet(b, m.start()), "getters": "servedTrue"}
    # names held in a variable and looked up indirectly: var X="tengu_x"; k(X, dflt)  (e.g. tengu_amber_tally, tengu_lantern_wick_*)
    # — found 2026-10-12 as a scanner gap. ONLY JS assignments `ident="tengu_x"` count: the Bun string table also holds every
    # tengu_* literal (telemetry event names included), so a looser pattern added 1,575 false rows on 2026-10-12.
    for m in re.finditer(rb'[\w$]=\s*"(tengu_[a-z0-9_]+)"\s*[,;]', b):
        n = m.group(1).decode()
        if n in items["flag"] or n in items["event"]: continue
        items["flag"][n] = {"default": "", "desc": "", "sites": 1, "snippet": snippet(b, m.start()), "getters": "indirect"}
    # --- env vars: typed getter table + direct process.env reads
    table = {}
    for m in re.finditer(rb'\b((?:CLAUDE_CODE|CLAUDE|DISABLE|ANTHROPIC)_[A-Z0-9_]{3,70}):\(\)=>([A-Za-z_$][\w$]{0,5})[,}]', b):
        table.setdefault(m.group(1).decode(), m.start())
    sites = collections.defaultdict(lambda: {"n": 0, "pos": None})
    for m in re.finditer(rb'(?:(?<![\w$])[\w$]{1,3}\.|process\.env\.)((?:' + "|".join(re.escape(p) for p in ENV_PREFIXES).encode() + rb')[A-Z0-9_]{2,70})\b(?!:\(\)=>)', b):
        n = m.group(1).decode(); s = sites[n]; s["n"] += 1
        if s["pos"] is None: s["pos"] = m.start()
    for n in set(table) | set(sites):
        pos = sites[n]["pos"] if n in sites else table.get(n)
        items["env"][n] = {"default": "", "desc": "", "sites": sites[n]["n"] if n in sites else 0,
                           "snippet": snippet(b, pos) if pos is not None else "", "getters": "env-table" if n in table else "process.env"}
    # --- settings keys: schema describe() + hs() + ft().x
    for m in re.finditer(rb'([a-zA-Z][A-Za-z0-9_]{1,60}):\(\)=>([^,;{}]{0,260}?)\.describe\("((?:[^"\\]|\\.){3,600})"\)', b):
        k = m.group(1).decode()
        if k not in items["setting"]:
            items["setting"][k] = {"default": "", "desc": m.group(3).decode("utf-8", "replace").replace("\\n", " "), "sites": 1,
                                   "snippet": snippet(b, m.start(), 80, 420), "getters": "schema"}
    for m in re.finditer(rb'\bhs\("([a-zA-Z][A-Za-z0-9_]{1,60})"(,([^()]{0,40}?))?\)', b):
        k = m.group(1).decode(); it = items["setting"].setdefault(k, {"default": "", "desc": "", "sites": 0, "snippet": snippet(b, m.start()), "getters": ""})
        it["sites"] += 1; it["getters"] = ",".join(sorted(set(filter(None, it["getters"].split(","))) | {"hs"}))
        if m.group(3) and not it["default"]: it["default"] = m.group(3).decode("utf-8", "replace")[:40]
    for m in re.finditer(rb'\bft\(\)\??\.([a-zA-Z][A-Za-z0-9_]{1,60})\b', b):
        k = m.group(1).decode()
        if k in ("parse", "safeParse", "optional", "describe", "default"): continue  # a zod schema object is also named ft() somewhere
        it = items["setting"].setdefault(k, {"default": "", "desc": "", "sites": 0, "snippet": snippet(b, m.start()), "getters": ""})
        it["sites"] += 1; it["getters"] = ",".join(sorted(set(filter(None, it["getters"].split(","))) | {"ft"}))
    return items


# ----------------------------------------------------------------------------------------------------------------- cache
def read_cache(path=CONFIG_JSON):
    d = jload(path, {})
    return {"at": d.get("cachedGrowthBookFeaturesAt"), "growthbook": d.get("cachedGrowthBookFeatures") or {},
            "statsig": d.get("cachedStatsigGates") or {}, "experiments": d.get("cachedExperimentData") or {},
            "experiment_features": d.get("cachedExperimentFeatures") or [], "dynamic": d.get("cachedDynamicConfigs") or {}}


def served_for(name, cache):
    if name in cache["experiments"]:
        e = cache["experiments"][name]; return {"source": "experiment", "value": e.get("value"), "experiment": e.get("experimentId"), "variation": e.get("variationId")}
    if name in cache["growthbook"]: return {"source": "growthbook", "value": cache["growthbook"][name]}
    if name in cache["statsig"]: return {"source": "statsig", "value": cache["statsig"][name]}
    if name in cache["dynamic"]: return {"source": "dynamic", "value": cache["dynamic"][name]}
    return None


# ----------------------------------------------------------------------------------------------------------------- state
def load_state(): return jload(STATE, {"items": {}, "last_scanned_version": None, "cache_at": None, "binary_sha256": None, "last_scan_at": None, "served_only": {}})
def key(kind, name): return f"{kind}:{name}"


def apply_scan(state, items, version, sha, cache):
    """Diff scan vs state → ledger events; returns summary dict."""
    ts = now_iso(); added = []; deprecated = []; restored = []
    seen = set()
    for kind, names in items.items():
        for name, it in names.items():
            k = key(kind, name); seen.add(k); cur = state["items"].get(k)
            served = served_for(name, cache) if kind == "flag" else None
            if cur is None:
                auto = (kind == "event") or (kind == "setting" and bool(it["desc"]))
                rec = {"kind": kind, "name": name, "status": "auto" if auto else "new", "first_seen_version": version, "last_seen_version": version,
                       "first_seen_at": ts, "last_seen_at": ts, "default": it["default"], "desc": it["desc"], "sites": it["sites"], "snippet": it["snippet"],
                       "getters": it["getters"], "served": served, "category": ("telemetry-event" if kind == "event" else ("setting" if auto else "")),
                       "summary": (("telemetry event name (logged, not a flag)") if kind == "event" else (it["desc"] if auto else "")),
                       "confidence": "high" if auto else "", "investigated_at": ts if auto else "", "investigated_by": "auto" if auto else ""}
                state["items"][k] = rec; added.append(k)
                append(LEDGER, {"ts": ts, "version": version, "kind": kind, "name": name, "event": "added", "status": rec["status"], "default": it["default"], "desc": it["desc"][:200]})
            else:
                if cur.get("status") == "deprecated":
                    cur["status"] = "new" if not cur.get("summary") else "investigated"; cur.pop("deprecated_version", None); restored.append(k)
                    append(LEDGER, {"ts": ts, "version": version, "kind": kind, "name": name, "event": "restored"})
                if cur.get("default") != it["default"] and it["default"]:
                    append(LEDGER, {"ts": ts, "version": version, "kind": kind, "name": name, "event": "default_changed", "from": cur.get("default"), "to": it["default"]})
                    cur["default"] = it["default"]
                if it["desc"] and cur.get("desc") != it["desc"]: cur["desc"] = it["desc"]
                cur["last_seen_version"] = version; cur["last_seen_at"] = ts; cur["sites"] = it["sites"]; cur["getters"] = it["getters"]
                if it["snippet"]: cur["snippet"] = it["snippet"]
                if kind == "flag": cur["served"] = served
    for k, cur in state["items"].items():
        if k not in seen and cur.get("status") != "deprecated":
            cur["status"] = "deprecated"; cur["deprecated_version"] = version; cur["deprecated_at"] = ts; deprecated.append(k)
            append(LEDGER, {"ts": ts, "version": version, "kind": cur["kind"], "name": cur["name"], "event": "deprecated", "last_seen_version": cur.get("last_seen_version")})
    # served names the binary does not read (other versions) — kept as a side list, not items
    binflags = set(items["flag"]) | set(items["event"])
    state["served_only"] = {n: (cache["growthbook"].get(n) if n in cache["growthbook"] else cache["statsig"].get(n)) for n in sorted((set(cache["growthbook"]) | set(cache["statsig"])) - binflags)}
    state["last_scanned_version"] = version; state["binary_sha256"] = sha; state["last_scan_at"] = ts; state["cache_at"] = cache["at"]
    append(LEDGER, {"ts": ts, "version": version, "event": "scan", "added": len(added), "deprecated": len(deprecated), "restored": len(restored),
                    "counts": {k: len(v) for k, v in items.items()}})
    return {"added": added, "deprecated": deprecated, "restored": restored}


def apply_cache(state, cache, version=None):
    """Served-value diff for flags (cheap; runs every session start). Returns list of changes."""
    ts = now_iso(); changes = []
    if cache["at"] is None or cache["at"] == state.get("cache_at"): return changes
    for k, cur in state["items"].items():
        if cur["kind"] != "flag": continue
        new = served_for(cur["name"], cache); old = cur.get("served")
        if json.dumps(new, sort_keys=True) != json.dumps(old, sort_keys=True):
            cur["served"] = new; changes.append((cur["name"], old, new))
            append(LEDGER, {"ts": ts, "version": version or state.get("last_scanned_version"), "kind": "flag", "name": cur["name"], "event": "value_changed", "from": old, "to": new})
    state["cache_at"] = cache["at"]
    return changes


# ------------------------------------------------------------------------------------------------------------ experiments
def load_exp_state(): return jload(EXP_STATE, {"experiments": {}, "cache_at": None})


def apply_experiments(exp, cache, version, source="live", at=None):
    """Active = in cachedExperimentData now; an experiment that disappears becomes past. at = cache timestamp (ms)."""
    ts = now_iso(); at = at or cache["at"]; changes = []
    live = {}
    for feat, e in cache["experiments"].items():
        if not isinstance(e, dict) or not e.get("experimentId"): continue
        live.setdefault(e["experimentId"], {"features": {}, "variationId": e.get("variationId")})
        live[e["experimentId"]]["features"][feat] = e.get("value")
    for eid, info in live.items():
        cur = exp["experiments"].get(eid)
        if cur is None:
            cur = {"experimentId": eid, "status": "active", "features": info["features"], "variationId": info["variationId"], "first_seen_at": ts,
                   "first_seen_cache_at": at, "first_seen_version": version, "last_seen_at": ts, "last_seen_cache_at": at, "last_seen_version": version, "history": []}
            exp["experiments"][eid] = cur; changes.append(("new", eid))
            append(EXP_LEDGER, {"ts": ts, "version": version, "event": "experiment_started", "experimentId": eid, "variationId": info["variationId"], "features": info["features"], "source": source})
        else:
            if cur.get("status") != "active":
                cur["status"] = "active"; changes.append(("resumed", eid)); append(EXP_LEDGER, {"ts": ts, "version": version, "event": "experiment_resumed", "experimentId": eid})
            if cur.get("variationId") != info["variationId"] or json.dumps(cur.get("features"), sort_keys=True) != json.dumps(info["features"], sort_keys=True):
                cur["history"].append({"at": cur.get("last_seen_cache_at"), "variationId": cur.get("variationId"), "features": cur.get("features")})
                append(EXP_LEDGER, {"ts": ts, "version": version, "event": "experiment_changed", "experimentId": eid, "from": {"variationId": cur.get("variationId")}, "to": {"variationId": info["variationId"], "features": info["features"]}})
                cur["variationId"] = info["variationId"]; cur["features"] = info["features"]; changes.append(("changed", eid))
            cur["last_seen_at"] = ts; cur["last_seen_cache_at"] = at; cur["last_seen_version"] = version
    if source == "live":
        for eid, cur in exp["experiments"].items():
            if eid not in live and cur.get("status") == "active":
                cur["status"] = "past"; cur["ended_at"] = ts; cur["ended_cache_at"] = at; changes.append(("ended", eid))
                append(EXP_LEDGER, {"ts": ts, "version": version, "event": "experiment_ended", "experimentId": eid, "last_variationId": cur.get("variationId")})
        exp["cache_at"] = at
    return changes


def seed_experiment_history(exp, version):
    """One-time: walk .claude.json.backup.* (oldest first) so experiments seen only in backups become 'past'."""
    cfg_dir = os.path.dirname(CONFIG_JSON)
    backups = sorted(glob.glob(os.path.join(cfg_dir, ".claude", "backups", ".claude.json.backup.*")) + glob.glob(os.path.join(cfg_dir, "backups", ".claude.json.backup.*")),
                     key=lambda p: int(re.findall(r"(\d+)$", p)[0]) if re.findall(r"(\d+)$", p) else 0)
    n = 0
    for p in backups:
        d = jload(p, {})
        if not d.get("cachedExperimentData"): continue
        c = {"at": d.get("cachedGrowthBookFeaturesAt"), "experiments": d["cachedExperimentData"], "growthbook": {}, "statsig": {}, "dynamic": {}, "experiment_features": []}
        apply_experiments(exp, c, version, source=f"backup:{os.path.basename(p)}", at=c["at"]); n += 1
    return n


# ---------------------------------------------------------------------------------------------------------------- regen
def fmt_served(s):
    if not s: return "—"
    v = json.dumps(s.get("value"))[:70]
    return f"{v} ({s['source']}{': ' + s['experiment'] if s.get('experiment') else ''})"
def esc(s): return str(s).replace("|", "\\|").replace("\n", " ")
def ms_to_pt(ms):
    try: return datetime.datetime.fromtimestamp(ms / 1000, PT).strftime("%Y-%m-%d %I:%M %p PT")
    except Exception: return str(ms)


def _vtuple(v):
    try: return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    except Exception: return (0,)

def fetch_changelog(timeout=30):
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(CHANGELOG_URL, headers={"User-Agent": "ccv/1"}), timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        log(f"changelog fetch failed: {e}"); return None

def parse_changelog(text):
    """'## <version>' headings, '- ' bullets (continuation lines joined). Returns {version: [bullets]} in file order."""
    out = {}; cur = None
    for ln in text.splitlines():
        m = re.match(r"^##\s+v?(\d+\.\d+\.\d+\S*)", ln)
        if m: cur = m.group(1); out.setdefault(cur, []); continue
        if cur is None: continue
        if re.match(r"^\s*[-*]\s+", ln): out[cur].append(re.sub(r"^\s*[-*]\s+", "", ln).strip())
        elif ln.strip() and out[cur] and ln.startswith("  "): out[cur][-1] += " " + ln.strip()
    return out

_LINK_RX = {}
def link_items(bullet, state):
    """Inventory items (env/setting/flag) named verbatim in a bullet — one compiled alternation over all names, memoised per bullet."""
    sid = id(state)
    if sid not in _LINK_RX:
        by = {}
        for k, it in state.get("items", {}).items():
            n = it.get("name") or k.split(":", 1)[-1]
            if len(n) >= 6: by.setdefault(n, k)
        names = sorted(by, key=len, reverse=True)
        rx = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(n) for n in names) + r")(?![A-Za-z0-9_])") if names else None
        _LINK_RX[sid] = (rx, by, {})
    rx, by, memo = _LINK_RX[sid]
    if bullet in memo: return memo[bullet]
    out = sorted({by[m.group(1)] for m in rx.finditer(bullet)}) if rx else []
    memo[bullet] = out; return out

def cl_tags(bullet):
    b = bullet.lower(); return [k for k in CL_KEYWORDS if k in b]

def load_cl_state(): return jload(CL_STATE, {"versions": {}, "fetched_at": None, "source": None})

def apply_changelog(cl, parsed, state, source):
    """Append new (version, bullet) pairs to the changelog ledger; new versions start UNTRIAGED. Returns (new_versions, new_bullets)."""
    ts = now_iso(); new_v = []; new_b = 0
    for ver, bullets in parsed.items():
        rec = cl["versions"].setdefault(ver, {"bullets": [], "first_seen": ts, "triaged": False, "triaged_at": None})
        seen = set(rec["bullets"])
        fresh = [b for b in bullets if b not in seen]
        if fresh:
            if not rec["bullets"]: new_v.append(ver)
            for b in fresh:
                rec["bullets"].append(b); new_b += 1
                append(CL_LEDGER, {"event": "changelog_entry", "version": ver, "bullet": b, "linked": link_items(b, state), "tags": cl_tags(b), "at": ts})
    cl["fetched_at"] = ts; cl["source"] = source
    return new_v, new_b

def regen_changelog(cl, state, installed=None, keep=40):
    hdr = f"<!-- GENERATED by scripts/ccv.py changelog — do not hand-edit. Fetched {cl.get('fetched_at')} from {cl.get('source')}; installed binary {installed}. -->"
    vers = sorted(cl["versions"], key=_vtuple, reverse=True)
    untriaged = [v for v in vers if not cl["versions"][v].get("triaged")]
    out = [hdr, f"# Claude Code changelog — {len(vers)} versions tracked, {len(untriaged)} UNTRIAGED for library candidates\n",
           "Triage = read each untriaged version's bullets (tagged ones first), add anything the nexus-cortex harness should adopt or answer to "
           "`library/CANDIDATES.md` (what it is · harness analog or gap · where it lands · status), then record it:\n",
           "```\npython3 .claude/skills/claude-code-variables/scripts/ccv.py changelog-triaged <version> [<version> …]\n```\n"]
    if untriaged:
        out.append("## UNTRIAGED\n")
        for v in untriaged:
            rec = cl["versions"][v]; tagged = [b for b in rec["bullets"] if cl_tags(b)]
            mark = " (installed)" if installed and _vtuple(v) == _vtuple(installed) else (" (newer than installed)" if installed and _vtuple(v) > _vtuple(installed) else "")
            out.append(f"### {v}{mark} — {len(rec['bullets'])} entries, {len(tagged)} tagged · first seen {rec['first_seen'][:10]}\n")
            for b in rec["bullets"]:
                tags = cl_tags(b); linked = link_items(b, state)
                if not tags and not linked: continue
                out.append(f"- {esc(b)}" + (f"  ⟶ linked: {', '.join('`'+l+'`' for l in linked)}" if linked else "") + (f"  [{', '.join(tags[:4])}]" if tags else ""))
            out.append("")
    out.append(f"## All tracked versions (newest {keep}; the full cache is `data/changelog.md`)\n")
    for v in vers[:keep]:
        rec = cl["versions"][v]
        out.append(f"### {v} — {len(rec['bullets'])} entries · {'triaged ' + str(rec.get('triaged_at'))[:10] if rec.get('triaged') else 'UNTRIAGED'}\n")
        for b in rec["bullets"]:
            linked = link_items(b, state)
            out.append(f"- {esc(b)}" + (f"  ⟶ `{'`, `'.join(linked)}`" if linked else ""))
        out.append("")
    os.makedirs(REF, exist_ok=True); open(CL_REF, "w").write("\n".join(out) + "\n")
    return untriaged

def cmd_changelog(args):
    """Fetch (or --file <path>) the public changelog, ledger new entries, regenerate reference/changelog.md and the NOTICE line."""
    state = load_state(); exp = load_exp_state(); cl = load_cl_state(); path = binary_path(); installed = binary_version(path) if path else None
    if "--file" in args:
        src = args[args.index("--file") + 1]; text = open(src, encoding="utf-8", errors="replace").read()
    else:
        src = CHANGELOG_URL; text = fetch_changelog()
        if text is None:
            print("ccv changelog: fetch failed (offline?) — cached copy unchanged", file=sys.stderr); return 2
    os.makedirs(DATA, exist_ok=True); open(CL_CACHE, "w").write(text)
    parsed = parse_changelog(text)
    if not parsed: print("ccv changelog: parsed 0 versions — format changed?", file=sys.stderr); return 3
    new_v, new_b = apply_changelog(cl, parsed, state, src)
    jdump(CL_STATE, cl); untriaged = regen_changelog(cl, state, installed); regen(state, exp)
    msg = f"changelog: {len(parsed)} versions parsed, +{len(new_v)} new version(s) ({', '.join(new_v[:6])}{'…' if len(new_v) > 6 else ''}), +{new_b} entries; untriaged: {len(untriaged)}"
    log(msg); print(msg); return 0

def cmd_changelog_triaged(args):
    cl = load_cl_state(); ts = now_iso(); done = []
    by = args[args.index("--by") + 1] if "--by" in args else "agent"
    vers = [a for a in args if not a.startswith("--") and a != by]
    if "--before" in args:   # baseline: every tracked version older than <ver> (pre-ledger history nobody will triage)
        cut = _vtuple(args[args.index("--before") + 1]); vers += [v for v in cl["versions"] if _vtuple(v) < cut]
    for v in vers:
        if v in cl["versions"] and not cl["versions"][v].get("triaged"):
            cl["versions"][v]["triaged"] = True; cl["versions"][v]["triaged_at"] = ts; cl["versions"][v]["triaged_by"] = by; done.append(v)
            append(CL_LEDGER, {"event": "changelog_triaged", "version": v, "at": ts, "by": by})
    jdump(CL_STATE, cl); state = load_state(); exp = load_exp_state(); path = binary_path()
    regen_changelog(cl, state, binary_version(path) if path else None); regen(state, exp)
    print(f"changelog-triaged: {', '.join(done) or 'nothing matched'}"); return 0

def regen(state, exp):
    os.makedirs(REF, exist_ok=True); os.makedirs(EXP_REF, exist_ok=True)
    items = state["items"].values()
    by_kind = collections.defaultdict(list)
    for it in items: by_kind[it["kind"]].append(it)
    pending = sorted([it for it in items if it["status"] == "new"], key=lambda x: (x["kind"], x["name"]))
    dep = sorted([it for it in items if it["status"] == "deprecated"], key=lambda x: (x["kind"], x["name"]))
    hdr = (f"<!-- GENERATED by scripts/ccv.py — do not hand-edit. Binary {state.get('last_scanned_version')} scanned {state.get('last_scan_at')} UTC; "
           f"cache fetched {ms_to_pt(state.get('cache_at')) if state.get('cache_at') else '—'}. -->\n")
    # INDEX
    counts = {k: collections.Counter(i["status"] for i in v) for k, v in by_kind.items()}
    idx = [hdr, "# Claude Code variables — index\n", f"Binary version: **{state.get('last_scanned_version')}** · last scan {state.get('last_scan_at')} UTC · pending investigation: **{len(pending)}** · deprecated: {len(dep)}\n",
           "| kind | total | new (uninvestigated) | investigated | auto | deprecated | file |", "|---|---|---|---|---|---|---|"]
    for k, f in [("flag", "flags.md"), ("env", "env-vars.md"), ("setting", "settings.md"), ("event", "events.md")]:
        c = counts.get(k, {}); idx.append(f"| {k} | {sum(c.values())} | {c.get('new',0)} | {c.get('investigated',0)} | {c.get('auto',0)} | {c.get('deprecated',0)} | `reference/{f}` |")
    idx.append(f"\nServed-but-not-read-by-this-build flag names: {len(state.get('served_only', {}))} (`reference/served-only.md`). Deprecated list: `reference/deprecated.md`. Pending: `reference/NOTICE.md`.\n")
    open(os.path.join(REF, "INDEX.md"), "w").write("\n".join(idx) + "\n")
    # per-kind tables (active = not deprecated)
    def table(kind, path, title, cols):
        rows = sorted([i for i in by_kind.get(kind, []) if i["status"] != "deprecated"], key=lambda x: (x.get("category") or "zz", x["name"]))
        out = [hdr, f"# {title} ({len(rows)})\n", "Status: `new` = appeared in the binary and nobody has investigated it yet (see NOTICE.md); `investigated` = summarised by an agent/operator; `auto` = summary taken from the binary's own schema text or it is a telemetry event name.\n"]
        cur = None
        for i in rows:
            if (i.get("category") or "uncategorised") != cur:
                cur = i.get("category") or "uncategorised"; out.append(f"\n## {cur}\n"); out.append("| " + " | ".join(c[0] for c in cols) + " |"); out.append("|" + "---|" * len(cols))
            out.append("| " + " | ".join(esc(c[1](i)) for c in cols) + " |")
        open(os.path.join(REF, path), "w").write("\n".join(out) + "\n")
    table("flag", "flags.md", "Remote flags (GrowthBook / Statsig / experiments)",
          [("flag", lambda i: f"`{i['name']}`"), ("status", lambda i: i["status"]), ("code default", lambda i: f"`{i['default']}`" if i["default"] else "—"), ("served now", lambda i: fmt_served(i.get("served"))),
           ("summary", lambda i: i.get("summary") or ""), ("conf", lambda i: i.get("confidence") or ""), ("seen", lambda i: f"{i['first_seen_version']}→{i['last_seen_version']}")])
    table("env", "env-vars.md", "Environment variables",
          [("variable", lambda i: f"`{i['name']}`"), ("status", lambda i: i["status"]), ("read via", lambda i: i.get("getters", "")), ("sites", lambda i: i.get("sites", 0)),
           ("summary", lambda i: i.get("summary") or ""), ("conf", lambda i: i.get("confidence") or ""), ("seen", lambda i: f"{i['first_seen_version']}→{i['last_seen_version']}")])
    table("setting", "settings.md", "settings.json keys",
          [("key", lambda i: f"`{i['name']}`"), ("status", lambda i: i["status"]), ("read via", lambda i: i.get("getters", "")), ("default", lambda i: f"`{i['default']}`" if i["default"] else "—"),
           ("description / summary", lambda i: i.get("summary") or i.get("desc") or ""), ("seen", lambda i: f"{i['first_seen_version']}→{i['last_seen_version']}")])
    table("event", "events.md", "Telemetry event names (not flags)",
          [("event", lambda i: f"`{i['name']}`"), ("sites", lambda i: i.get("sites", 0)), ("seen", lambda i: f"{i['first_seen_version']}→{i['last_seen_version']}")])
    # deprecated
    out = [hdr, f"# Deprecated items ({len(dep)})\n", "Items that were read by an earlier scanned binary and are absent from the current one. They stay here forever (append-only); if a later build reads them again they move back and the ledger records `restored`.\n",
           "| kind | name | last seen in | deprecated at | last summary |", "|---|---|---|---|---|"]
    for i in dep: out.append(f"| {i['kind']} | `{i['name']}` | {i.get('last_seen_version')} | {i.get('deprecated_version')} ({i.get('deprecated_at','')[:10]}) | {esc(i.get('summary') or i.get('desc') or '')} |")
    open(os.path.join(REF, "deprecated.md"), "w").write("\n".join(out) + "\n")
    # served-only
    so = state.get("served_only", {})
    out = [hdr, f"# Served-only flag names ({len(so)})\n", "Present in the GrowthBook/Statsig cache (served to every CLI version) but with no lookup in the scanned binary — they belong to newer or older builds. Name = served value.\n", "```"]
    out += [f"{n} = {json.dumps(v)[:100]}" for n, v in so.items()]; out.append("```")
    open(os.path.join(REF, "served-only.md"), "w").write("\n".join(out) + "\n")
    # NOTICE
    out = [hdr, f"# NOTICE — {len(pending)} item(s) pending investigation\n"]
    if pending:
        out.append("Each appeared in the scanned binary without a summary. Investigate from the snippet (and the binary if needed), then record it:\n")
        out.append("```\npython3 .claude/skills/claude-code-variables/scripts/ccv.py mark <NAME> --kind <flag|env|setting> --category <cat> --summary \"<≤25 words>\" --confidence <high|med|low>\n```\n")
        for i in pending:
            out.append(f"## {i['kind']} `{i['name']}`  (first seen {i['first_seen_version']}, {i['first_seen_at'][:10]})\n")
            if i.get("default"): out.append(f"- code default: `{i['default']}`")
            if i.get("served"): out.append(f"- served now: {fmt_served(i['served'])}")
            if i.get("desc"): out.append(f"- schema text: {i['desc']}")
            out.append(f"- read via: {i.get('getters','')} · sites: {i.get('sites',0)}")
            out.append(f"- snippet: `{esc(i.get('snippet',''))[:500]}`\n")
    else: out.append("Nothing pending. The next binary version that adds an item will list it here and the SessionStart hook will say so.\n")
    try:
        cl = load_cl_state(); unt = sorted([v for v, r in cl["versions"].items() if not r.get("triaged")], key=_vtuple, reverse=True)
        out.append(f"\n# CHANGELOG — {len(unt)} version(s) untriaged for library candidates\n")
        if unt: out.append(f"Versions: {', '.join(unt[:12])}{'…' if len(unt) > 12 else ''}. Read `reference/changelog.md` (UNTRIAGED section, tagged bullets first), "
                           "add candidates to `library/CANDIDATES.md`, then `ccv.py changelog-triaged <version>`. Last fetch: " + str(cl.get("fetched_at")) + "\n")
        else: out.append("Every tracked version is triaged. The hook refreshes the changelog daily and on a binary change.\n")
    except Exception: pass
    open(NOTICE, "w").write("\n".join(out) + "\n")
    # experiments
    acts = sorted([e for e in exp["experiments"].values() if e["status"] == "active"], key=lambda e: e["experimentId"])
    past = sorted([e for e in exp["experiments"].values() if e["status"] == "past"], key=lambda e: e.get("ended_at") or "", reverse=True)
    cand = sorted([i for i in by_kind.get("flag", []) if i["status"] != "deprecated" and not i.get("served")], key=lambda i: i["name"])
    flag_summary = {i["name"]: i.get("summary") or "" for i in by_kind.get("flag", [])}
    out = [hdr, "# Claude Code experiments\n",
           "**Active** = present in `cachedExperimentData` of `.claude.json` at the last check (this install is enrolled; `variationId` 0 is normally control). "
           "**Past** = seen in an earlier cache/backup, absent now. **Candidates (\"future\")** = flags this binary reads for which NOTHING is served yet — the code default applies; "
           "they are the only forward-looking signal available (an experiment is not enumerable from the binary: enrollment arrives in the remote-eval payload). Each flag links to its row in the variables skill.\n",
           f"## Active ({len(acts)})\n", "| experiment | variation | feature flag(s) → value | since (cache) | affects (variables-skill summary) |", "|---|---|---|---|---|"]
    for e in acts:
        feats = "<br>".join(f"`{f}` → `{json.dumps(v)[:60]}`" for f, v in e["features"].items())
        aff = "<br>".join(esc(flag_summary.get(f, "")) for f in e["features"])
        out.append(f"| `{e['experimentId']}` | {e.get('variationId')} | {feats} | {ms_to_pt(e.get('first_seen_cache_at')) if e.get('first_seen_cache_at') else e.get('first_seen_at','')[:10]} | {aff} |")
    out += [f"\n## Past ({len(past)})\n", "| experiment | last variation | feature flag(s) | first seen | ended |", "|---|---|---|---|---|"]
    for e in past: out.append(f"| `{e['experimentId']}` | {e.get('variationId')} | {', '.join(f'`{f}`' for f in e['features'])} | {ms_to_pt(e.get('first_seen_cache_at')) if e.get('first_seen_cache_at') else ''} | {ms_to_pt(e.get('ended_cache_at')) if e.get('ended_cache_at') else e.get('ended_at','')[:10]} |")
    out += [f"\n## Candidates — flags read by the binary with nothing served ({len(cand)})\n", "| flag | code default | summary | first seen |", "|---|---|---|---|"]
    for i in cand: out.append(f"| `{i['name']}` | `{i['default']}` | {esc(i.get('summary') or '')} | {i['first_seen_version']} |")
    open(os.path.join(EXP_REF, "experiments.md"), "w").write("\n".join(out) + "\n")


# ------------------------------------------------------------------------------------------------------------- commands
def cmd_update(args):
    path = binary_path()
    if not path: print("ccv: claude binary not found", file=sys.stderr); return 2
    version = binary_version(path) or "unknown"; sha = sha256(path)
    log(f"update: binary={path} version={version}")
    items = scan_binary(path); cache = read_cache()
    state = load_state(); exp = load_exp_state()
    first = state.get("last_scanned_version") is None
    # ANOMALY GUARD (2026-10-12): a scanner-regex mistake once produced +1,575 false "added" rows in one step. A real version bump
    # adds tens of items, not hundreds. Refuse to touch the ledger when the delta is implausible unless --force is given.
    if not first and "--force" not in args:
        existing = {k for k, v in state["items"].items() if v.get("status") != "deprecated"}
        incoming = {key(kd, n) for kd, names in items.items() for n in names}
        added_n = len(incoming - existing); gone_n = len(existing - incoming)
        if added_n > max(60, 0.25 * len(existing)) or gone_n > max(60, 0.25 * len(existing)):
            msg = (f"SCAN ANOMALY {version}: would add {added_n} and deprecate {gone_n} of {len(existing)} items — refusing to write the ledger. "
                   f"Inspect the scanner (scripts/ccv.py scan_binary) and re-run with `update --force` only if the delta is real.")
            log(msg); print(msg, file=sys.stderr)
            try:
                os.makedirs(REF, exist_ok=True); open(os.path.join(REF, "SCAN-ANOMALY.md"), "w").write(f"# {msg}\n\nsample added: {sorted(incoming - existing)[:40]}\n\nsample gone: {sorted(existing - incoming)[:40]}\n")
            except Exception: pass
            return 3
    summ = apply_scan(state, items, version, sha, cache)
    if first: n = seed_experiment_history(exp, version); log(f"seeded experiments from {n} backups")
    apply_experiments(exp, cache, version)
    jdump(STATE, state); jdump(EXP_STATE, exp); regen(state, exp)
    pend = sum(1 for i in state["items"].values() if i["status"] == "new")
    msg = f"scan {version}: +{len(summ['added'])} added, {len(summ['deprecated'])} deprecated, {len(summ['restored'])} restored; pending investigation: {pend}"
    log(msg); print(msg)
    try: cmd_changelog([])
    except Exception as e: log(f"changelog refresh after update failed: {e}")
    return 0


def cmd_check(args):
    """Hook fast path. Prints JSON {notice, pending, version, changed}."""
    state = load_state(); exp = load_exp_state(); path = binary_path(); version = binary_version(path) if path else None
    notes = []; changed = False
    if state.get("last_scanned_version") is None:
        notes.append("claude-code-variables has never been seeded — run `python3 .claude/skills/claude-code-variables/scripts/ccv.py update`.")
    elif version and version != state["last_scanned_version"]:
        changed = True
        if "--no-spawn" not in args:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), "update"], stdout=open(LOG, "a"), stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        notes.append(f"CLAUDE CODE BINARY CHANGED {state['last_scanned_version']} → {version}: the variables/experiments scan is running in the background (~1 min, log {LOG}); new items will appear in reference/NOTICE.md and be announced at the next session start.")
    cache = read_cache()
    if state.get("last_scanned_version") is not None:
        vc = apply_cache(state, cache, version); ec = apply_experiments(exp, cache, version)
        if vc or ec:
            jdump(STATE, state); jdump(EXP_STATE, exp); regen(state, exp)
            if vc: notes.append(f"{len(vc)} remote flag value(s) changed since last session: " + ", ".join(f"{n}: {json.dumps(o and o.get('value'))[:30]}→{json.dumps(w and w.get('value'))[:30]}" for n, o, w in vc[:6]) + (" …" if len(vc) > 6 else ""))
            if ec: notes.append("experiments changed: " + ", ".join(f"{a} {e}" for a, e in ec) + " (see claude-code-experiments/reference/experiments.md)")
    try:
        cl = load_cl_state(); stale = True
        if cl.get("fetched_at"):
            age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.strptime(cl["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).total_seconds()
            stale = age > 86400 or changed
        if stale and "--no-spawn" not in args:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), "changelog"], stdout=open(LOG, "a"), stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        unt = [v for v, r in cl.get("versions", {}).items() if not r.get("triaged")]
        if unt: notes.append(f"{len(unt)} Claude Code changelog version(s) untriaged for library candidates (newest {sorted(unt, key=_vtuple)[-1]}): see reference/changelog.md + library/CANDIDATES.md.")
    except Exception: pass
    pending = [i for i in state["items"].values() if i["status"] == "new"]
    if pending:
        kinds = collections.Counter(i["kind"] for i in pending)
        notes.append(f"{len(pending)} Claude Code item(s) await investigation ({', '.join(f'{v} {k}' for k, v in kinds.items())}): load skill `claude-code-variables`, read reference/NOTICE.md, summarise each and record it with `ccv.py mark`, then tell the operator what they are.")
    out = {"version": version, "last_scanned_version": state.get("last_scanned_version"), "changed": changed, "pending": len(pending), "notice": " ".join(notes)}
    print(json.dumps(out)); return 0


def cmd_mark(args):
    if not args: print("usage: mark NAME --kind K --category C --summary S [--confidence high|med|low] [--by who]"); return 2
    name = args[0]; opt = {}
    i = 1
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args): opt[args[i][2:]] = args[i + 1]; i += 2
        else: i += 1
    state = load_state(); exp = load_exp_state()
    cands = [k for k, v in state["items"].items() if v["name"] == name and (not opt.get("kind") or v["kind"] == opt["kind"])]
    if not cands: print(f"ccv: no item named {name}" + (f" of kind {opt['kind']}" if opt.get("kind") else "")); return 1
    if len(cands) > 1: print(f"ccv: ambiguous ({', '.join(cands)}); pass --kind"); return 1
    it = state["items"][cands[0]]; ts = now_iso()
    it["status"] = "investigated" if it["status"] != "deprecated" else "deprecated"
    it["category"] = opt.get("category", it.get("category", "")); it["summary"] = opt.get("summary", it.get("summary", ""))
    it["confidence"] = opt.get("confidence", it.get("confidence", "med")); it["investigated_at"] = ts; it["investigated_by"] = opt.get("by", "agent")
    append(LEDGER, {"ts": ts, "version": state.get("last_scanned_version"), "kind": it["kind"], "name": name, "event": "investigated", "category": it["category"], "summary": it["summary"], "confidence": it["confidence"], "by": it["investigated_by"]})
    jdump(STATE, state); regen(state, exp); print(f"marked {cands[0]} investigated"); return 0


def cmd_seed_tsv(args):
    """Import the 2026-10-12 research TSVs: flags-map (flag) or env map (env). Columns detected by header."""
    if not args: print("usage: seed-tsv FILE"); return 2
    import csv
    rows = list(csv.DictReader(open(args[0]), delimiter="\t")); state = load_state(); exp = load_exp_state(); ts = now_iso(); n = 0
    for r in rows:
        name = r.get("flag") or r.get("var"); kind = "flag" if r.get("flag") else "env"
        it = state["items"].get(key(kind, name))
        if not it or it["status"] not in ("new",): continue
        it["status"] = "investigated"; it["category"] = r.get("category", ""); it["summary"] = r.get("what_it_gates") or r.get("what_it_does") or ""
        it["confidence"] = r.get("confidence", "med"); it["investigated_at"] = ts; it["investigated_by"] = f"reader-pass 2026-10-12 ({os.path.basename(args[0])})"
        it["evidence"] = r.get("evidence", "")
        append(LEDGER, {"ts": ts, "version": state.get("last_scanned_version"), "kind": kind, "name": name, "event": "investigated", "category": it["category"], "summary": it["summary"][:200], "confidence": it["confidence"], "by": it["investigated_by"]}); n += 1
    jdump(STATE, state); regen(state, exp); print(f"seeded {n} items from {args[0]}"); return 0


def cmd_status(args):
    state = load_state(); exp = load_exp_state()
    c = collections.Counter((i["kind"], i["status"]) for i in state["items"].values())
    print(f"binary {state.get('last_scanned_version')} scanned {state.get('last_scan_at')}; cache {ms_to_pt(state.get('cache_at')) if state.get('cache_at') else '—'}")
    for k in ("flag", "env", "setting", "event"): print(f"  {k:8} " + "  ".join(f"{s}={c.get((k, s), 0)}" for s in ("new", "investigated", "auto", "deprecated")))
    e = collections.Counter(x["status"] for x in exp["experiments"].values()); print(f"  experiments active={e.get('active',0)} past={e.get('past',0)}")
    pend = [i for i in state["items"].values() if i["status"] == "new"]
    if pend: print("  pending:", ", ".join(f"{i['kind']}:{i['name']}" for i in pend[:40]) + (" …" if len(pend) > 40 else ""))
    return 0


def cmd_regen(args):
    state = load_state(); exp = load_exp_state(); regen(state, exp); print("regenerated"); return 0


def locked(fn):
    """Several Claude Code sessions share this workspace and all run the SessionStart hook; serialise ledger/state writers."""
    def run(args):
        import fcntl
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, ".lock"), "w") as lk:
            try: fcntl.flock(lk, fcntl.LOCK_EX)
            except Exception: pass
            return fn(args)
    return run


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"; rest = sys.argv[2:]
    table = {"update": locked(cmd_update), "check": locked(cmd_check), "mark": locked(cmd_mark), "regen": locked(cmd_regen), "status": cmd_status, "changelog": locked(cmd_changelog), "changelog-triaged": locked(cmd_changelog_triaged), "seed-tsv": locked(cmd_seed_tsv)}
    sys.exit(table.get(cmd, cmd_status)(rest))
