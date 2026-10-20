---
name: nexus-rea
description: Reverse-engineer a shipped React/Next.js web app from its RUNTIME, not just its bundle — pre-load a React DevTools hook shim, walk the live fiber tree, bucket components by prop-key signature (minified names are useless, prop signatures are not), list the runtime-loaded chunks, then slice the bundle at the seams the runtime revealed. Extends leanrea (MIT, static CLI method) with a runtime layer that works three ways — plain Playwright with no server, the hosted nexus-browser MCP, or its sandbox relay for challenge-walled sites. Use for UI/command-suite research, competitor feature inventories, and "how does this React app actually work" questions. Read-only; public pages only.
metadata:
  version: "1.0"
  upstream: aicodeking/leanrea @ 09ba4aa0 (MIT) — static layer
  worked_example: Godel Terminal (app.godelterminal.com v4.6.8) → 64 window commands, 13 asset classes, the window registry shape, 2026-10-20
---

# nexus-rea — reverse engineering from the running React app down

leanrea says: skip the MCP, use the CLI tools you already have, slice the bundle. That is right for static targets and it is the first half of
this skill. The second half is what leanrea punts on ("for runtime behavior, use a headless browser with a network log"): a React app's truth is
in its **live fiber tree**, and a minified bundle only becomes legible once the runtime has told you which chunks loaded, which props flow,
and which `data-*` seams the app's own tests use. Runtime first, then static, then drive the UI for the authoritative lists.

## Rules
1. **Read-only, public pages, no accounts, no bypasses.** Challenge walls are crossed only where the site serves the page to any visitor.
2. **Seen vs inferred.** Every claim in the write-up is tagged: *seen* (a file, a response, a DOM read you can quote) or *inferred*.
3. **Bound the work.** One inventory call ≤ 6,000 fibers; the chunk slice is the runtime-loaded list, never the whole CDN; scratch under a
   quota-safe temp dir (`$TMPDIR/re/<name>`), delete when done.
4. **Prop signatures over names.** Production builds minify component names; `Object.keys(memoizedProps)` sorted is a stable signature that
   survives minification and groups the same component across the tree.
5. **Main world.** The hook, the fiber expandos (`__reactFiber$…`) and `window` globals live in the page's MAIN JavaScript world. Stealth
   drivers (Patchright) evaluate in an isolated world by default and see none of it — ask for the main world explicitly (below).
6. **Hydration timing.** Detect React after hydration, not at `load` (2–4 s on heavy SPAs); a probe that runs early reports no React.

## Layer A — static (leanrea)
Install leanrea beside this skill and follow its Router for bundles, binaries, apps, firmware. The two rows that matter for a web target:
- **Web bundle / minified JS** — find `sourceMappingURL`; if the map carries `sourcesContent`, dump the sources with `jq`; otherwise
  `rg`/`grep -o` the minified file for the strings the runtime handed you (route names, registry keys, enum values) and slice ±2 KB around each.
- **Website** — the HTML of a modern app is nonce'd loaders and nothing else; the chunk list must come from the runtime (Layer B), then
  `curl -sL` each chunk once into the scratch dir and slice there.

## Layer B — runtime (the part leanrea does not have)
Three ways to get a main-world evaluate against a page with the hook shim pre-loaded. All three run the same two files.

| path | when | how |
|---|---|---|
| **1. Plain Playwright, no server** | default; any public page without a bot wall | `scripts/react-inventory.py URL --wait 4 [--selector CSS]` — `context.add_init_script(react-hook-shim.js)` BEFORE the page, `page.evaluate(react-inventory.js)` after hydration, optional `bippy-lite.js` probe on one element. Needs `pip install playwright && python -m playwright install chromium` (or `--chromium /path`). |
| **2. nexus-browser MCP (hosted)** | you already drive sites through MCP, or want scan/grab/click with React data attached | `browse({url})` pre-loads the shim on every navigation. Then `evaluate({script: INVENTORY})`; on the **sandbox backend** add `mainWorld: true`. `grab({selector})` returns `componentName`, `componentStack`, `props` per element; `scan()` rows carry `componentName`; `detect_framework({budget:"high"})` (medium runs before hydration). Connect: `https://browser.spitfire-products.com/mcp` — a missing token auto-provisions a key on connect (free tier: 10 req/min, 10 min browser time/day). |
| **3. Sandbox relay (challenge-walled sites)** | Cloudflare/Turnstile pages where the stealth container must own the page | Through the MCP's `run_command`, drive the relay on `127.0.0.1:8222`: `POST /launch` → `POST /init_script {script: SHIM, applyNow:false}` → `POST /navigate {url}` → `POST /evaluate {script: INVENTORY, isolatedContext:false}`. Keep every call < 20 s (the exec session dies on longer ones); `destroy_sandbox` to recover. |

**What one inventory call returns** (`scripts/react-inventory.js`): hook state (shim present, renderers, roots, commit count), script and
chunk URLs from `performance.getEntriesByType('resource')`, the app's `data-*` attribute vocabulary with counts, `localStorage` keys, uppercase
panel titles, short uppercase buttons (a command bar), fibers visited, and the **top prop-key signatures** with counts.
**What the probe returns** (`scripts/bippy-lite.js`, `{selector}` or `{x,y}`): `componentName` (null on minified builds), `componentStack`,
`props`, `sourceLocation` (and a Next.js-resolved location when the dev overlay's resolver is present).

## Layer C — the workflow (proven on a Bloomberg-style web terminal, 2026-10-20)
1. **Runtime inventory first.** One evaluate: hook (1 root, ~3,700 commits), 30 runtime-loaded chunks (4.6 MB; the HTML carried only
   nonce'd loaders), the `data-*` vocabulary, `localStorage`, 6,000 fibers bucketed by prop signature.
2. **Seams from the app's own test ids.** `data-cy-active-window`, `data-cy-command-type`, `data-cy-command-toolbar`, `data-cy-terminal-input`,
   `data-cy-qm-cell` ×272, `data-column-key` ×21 → the window types open by default, the quote-monitor column model, the command input.
3. **Static slice at the seams.** `curl` the 30 chunks; `rg` for a string the UI showed (the HELP entry) → the registry object shape
   (`{type, status, title, shortcut, description, defaultWidth/Height, minWidth/Height, popoutEnabled, instanceLimit, isCompanyScoped, …}`)
   → 99 registry entries, the asset-class enum, pseudo-commands, the pinned toolbar, the terminal keybind — all *seen*.
4. **Drive the UI for the authoritative lists.** Type the app's own help command, read its tabs (getting started / keystrokes / commands).
5. **Write the gap table** against your own product: what they have, what you have, what to build, each row tagged seen/inferred.
Result: 64 window commands + 35 security-page sections, 13 asset classes, keystrokes, the window architecture from prop signatures
(`onCloseWindow, screenId, window, zindex`; linking groups `extantRelationships, includes, linkedTo, onLink`), 107 data fields, 8 recommendations.

## Report skeleton
`# <target> — UI / command-suite reverse engineering (date)` · 1. Method (which path, hook state, chunk count) · 2. Command grammar & keys
(seen) · 3. Window / component architecture (prop signatures; interpretation *inferred*) · 4. Registry / catalog (extracted JSON beside the
note) · 5. Data model (fields seen in props and responses) · 6. Gap table vs ours · 7. Recommendations · Appendix: inventory JSON, chunk list.

## Pitfalls (each cost real time)
- Isolated world → `hook.present:false` while the main world is full of React. Ask for the main world (`mainWorld:true` / `isolated_context=False`).
- A `medium` detection budget reports `react:false` on heavy SPAs (runs before hydration); use `high` or wait 2–4 s.
- `componentName` null everywhere = minified build, not a broken probe; switch to prop signatures and `data-*` seams.
- The HTML lists no chunks (nonce'd loaders): the chunk list exists only at runtime.
- A real DevTools hook on the page wins; the shim steps aside and the inventory still reads `hook.renderers`/roots through it.
- Init scripts must not patch `navigator`/runtime objects on stealth drivers (conflicts with their own patches).

## Files
`scripts/react-hook-shim.js` (pre-load; 2.6 KB) · `scripts/bippy-lite.js` (one-shot fiber probe; 10 KB) · `scripts/react-inventory.js`
(the inventory; 3.6 KB) · `scripts/react-inventory.py` (the no-server runner) · `THIRD_PARTY_NOTICES.md` (leanrea MIT; bippy naming).
