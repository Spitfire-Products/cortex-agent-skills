---
name: cortex-tool-development
description: Develop and WIRE a new tool into the nexus-cortex harness (omniclaude-v4) end-to-end — where tools are DEFINED (Base vs Addon registries → ToolFactory), where they EXECUTE (the 3 dispatch paths: executor vs orchestrator-dispatched), how they get INTO the request (deferred-loading + anchor-lift + post-filter append), the canonical 3-orthogonal-layer round-trip (naming ⊥ schema ⊥ transport), and forced tool_choice (gateway shapes, transport splats, all providers). Use whenever adding, removing, gating, or wiring a tool, a tool parameter, or tool_choice in the harness. ⚠️ ENTIRELY dependent on map-before-assert + active discovery + grounded codebase research — every file:line here is a POINTER to verify NOW, never a fact to trust blind. NOT for browser-CORTEX tools (nexus-sense) and NOT for MCP-server tools.
triggers:
  - add a tool
  - wire a tool
  - tool development
  - tool_choice
  - register a tool
  - tool dispatch
---

# cortex-tool-development — build & wire a harness tool

Adding a tool to the nexus-cortex harness is NOT "write a function." A tool touches a
definition registry, an execution path, an inclusion filter, a naming round-trip, and N
per-provider transports. Miss one and the tool is invisible, un-callable, or silently
stripped — with no error. This skill is the map. **The map is only as good as your
verification of it against the code as it is RIGHT NOW.**

## 0. 🔴 THE PREREQUISITE — this whole skill rides on grounded research

**Load the `grounded-research` skill first, and obey it here above all else.** Every file
path and line number below is a POINTER to a moving target, not a fact:

- **Line numbers DRIFT.** This harness is edited constantly; `CortexOrchestrator.ts` alone is
  8000+ lines. A line number in this skill (or in any spec) is stale the moment someone edits
  above it. **Always re-grep for the CURRENT site** before editing — anchor edits on unique
  surrounding text, never on a line number.
- **MAP before you assert.** "Where is this tool dispatched / included / named?" is a
  cross-cutting question spanning registries, the orchestrator, the gateway, and APIClient.
  That is a MAPPING task (an Explore agent or an exhaustive multi-form grep), not one narrow
  grep. A scoped match answers "does this string appear here?", never "is this the only/right
  path?"
- **VERIFY the flow with ground truth, not inference.** The decisive test that a tool is wired
  is not "the code looks right" — it is running it: `toolFactory.getTool('YourTool')` returns
  the def (a 5-line node script against the built dist), `tsc --noEmit` after every edit, a
  DEBUG_PAYLOAD probe that the tool is actually in the request the model sees. This session's
  AskForAdvice wiring was proven with exactly those, after the "it's registered so it must
  work" assumption was wrong (standard-tier tools get stripped — see §4).
- **The source-of-truth doc for the tool system** is `omniclaude-v4/docs/
  MENTORSHIP_ASK_FOR_ADVICE_SPEC.md §12` (grounded file:line map, written by reading the code).
  Read it, then RE-VERIFY its anchors before acting on them.

If you cannot cite a claim to a file:line you read THIS session, it is an assumption — label
it and go verify. Do not edit, gate, or ship against an unverified premise.

## 1. The mental model — three orthogonal axes + a definition/execution split

A tool is described by INDEPENDENT concerns; conflating them is the #1 confusion:

**Definition ≠ Execution.**
- **Definition** (`packages/core/src/tools/`): what the tool IS — name, description, schema,
  category, discoveryTier. Carries NO code for base tools.
- **Execution** (`packages/executors/`): what the tool DOES — a `BaseTool` subclass mapped by
  NAME in the `ExecutorRegistry`.

**Three orthogonal `ModelConfig` keys (the "canonical system"):**
- `tools.namingConvention` (`snake_case`|`PascalCase`) → `ToolNamingHandler` at the GATEWAY.
- `tools.adapter` → the schema-shape adapter (`AdapterRegistry`) — shapes the TOOLS array.
- `api.pattern` → the `APIClient` transport (body-builder + endpoint).

Naming, schema, and transport are decided SEPARATELY. tool_choice keys off `api.pattern`
(transport), NOT the schema adapter — it is a body-level control.

## 2. Where tools are DEFINED — registries → ToolFactory

Verify current anchors with:
```bash
grep -rn "class BaseToolRegistry\|BASE_TOOLS\|class AddonToolRegistry" packages/core/src/tools/registries/
grep -n "getTool\|baseToolRegistry\|addonToolRegistry" packages/core/src/tools/ToolFactory.ts
```
- **`registries/BaseToolRegistry.ts`** — IMMUTABLE static `CanonicalToolDefinition[]`
  (`{name, description, schema, category, discoveryTier, metadata}`). A built-in tool is a new
  entry here. Base tools carry NO implementation.
- **`registries/AddonToolRegistry.ts`** — MUTABLE, dynamic tools that DO carry
  `implementation:{language,code,dependencies}` (run via sandbox/artifact executors). Use only
  for on-the-fly/user-authored tools, not built-ins.
- **`ToolFactory.ts` (singleton `toolFactory`)** — unifies base ∪ addon (base precedence),
  `getTool(name)`, `applyToolProfile()`. **Every model-facing surface funnels through here** —
  so `toolFactory.getTool('YourTool')` returning the def is the ground-truth wiring check.
- `types/CanonicalTool.ts` — `ExecutionEnvironment = client | sandbox` ONLY (there is NO
  'server'; server-side tools dispatch by NAME, they don't set this field).

## 3. Where tools EXECUTE — the 3 dispatch paths (pick the RIGHT one)

Verify: `grep -n "executeToolCalls\|isContextManagement\|executorRegistry.execute\|mcp" packages/core/src/orchestrator/CortexOrchestrator.ts`

Three paths in the orchestrator's tool loop:
1. **Name-switch (orchestrator-dispatched)** — a branch in the orchestrator that runs the tool
   inline WITH orchestrator state (`this.helperMiddleware`, session state, the decision store).
2. **MCP** — `server__tool` names routed to the MCP client.
3. **ExecutorRegistry** — `execute(name, params, signal)` → a `BaseTool` subclass in
   `packages/executors`. **Executors receive ONLY `ExecutorConfig` — NO helperMiddleware / no
   orchestrator state.**

🔴 **THE DECISION:** does your tool need orchestrator state (a helper-model call, session
counters, the decision store, the render pipeline)? → it MUST be **orchestrator-dispatched
(path 1)**, because path-3 executors structurally cannot reach that state. Pure/self-contained
(fs, shell, string transform)? → an **executor (path 3)**. (AskForAdvice is path 1 because the
mentor call needs `helperMiddleware` + thrash state; ShellTool/EditTool are path 3.)

Whichever path: add the name to the unknown-tool guard too, or the loop rejects it.

## 4. How a tool gets INTO the request — inclusion is the SILENT killer

**A registered, dispatchable tool that never reaches the model is the most common failure, and
it throws NO error.** Verify the filter order NOW:
```bash
grep -n "getFilteredTools\|applyAnchorIfArmed\|ensureStructuredOutputTool\|enableDeferredToolLoading" packages/core/src/orchestrator/CortexOrchestrator.ts
grep -n "ENABLE_DEFERRED_TOOL_LOADING\|ENABLE_PTC" packages/core/src/config/SettingsSchema.ts
```
Per-request filter order (verify the current lines):
1. **Deferred filter** (`ENABLE_DEFERRED_TOOL_LOADING` default `'true'`): keeps ESSENTIAL +
   recently-used tools only. **🔴 This STRIPS standard-tier tools** — so setting
   `discoveryTier:'standard'` does NOT make your tool present. This is the trap that made
   AskForAdvice invisible until fixed.
2. **Anchor** (`applyAnchorIfArmed`, e.g. {Bash,Edit} on turn 1, no-op once lifted).
3. **Post-filter append** — the REAL inclusion lever. Tools appended HERE survive the deferred
   filter and the anchor. Pattern: `ensureStructuredOutputTool` (a request-scoped
   `ensureXTool(toolsToUse)` helper, gated, idempotent, appended after the filter+anchor).

**⇒ To make a tool reliably present:** append it post-filter with a gated `ensureYourTool`
helper — do NOT rely on `discoveryTier` or on SearchTools discovery (a model mid-task can't
afford a discovery round-trip). Add the append in BOTH the streaming and non-streaming assembly
regions (§7 duplication rule).

**🔴 The config that gates your tool (`ENABLE_DEFERRED_TOOL_LOADING`, `ENABLE_PTC`, …) is SOURCED FROM
THE ENV CHAIN — verify the LIVE value, never assume the code default is what runs.** `bootstrapEnv`
(`packages/core/src/config/SettingsLoader.ts`, called by every entry point) layers, highest→lowest:
`.env.local` → real `process.env` (injected; base .env never clobbers it) → `cwd/.env` → `packageRoot/.env`
(install dir, user-editable, presides over global) → `~/.cortex/.env` (hidden global). First-wins; a blank
`KEY=` = unset. On EVERY startup it also SEEDS both `~/.cortex/.env` and `packageRoot/.env` from the shipped
`.env.example` when missing (regenerate a deleted one; never clobber an edited one). **Consequence for tool
work:** the harbor bench inherits `ENABLE_DEFERRED_TOOL_LOADING=true` from `~/.cortex/.env` (seeded from
`.env.example`) — so the "winning" config is DEFERRED-loaded (~15 essential tools), NOT the full ~51-tool
catalog. That is exactly WHY a standard-tier tool gets stripped and the post-filter append above is
mandatory. Read the real `.env` (or a DEBUG_PAYLOAD tool count); the code default is not proof of the live value.

## 5. The naming round-trip — canonical PascalCase ⊥ wire snake_case

- **Canonical = PascalCase** everywhere in YOUR code: registry, dispatch `switch`, storage,
  docs (sibling of `AskUserQuestion`, `SearchTools`).
- **Wire = per `tools.namingConvention`** (deepseek/OpenAI = snake_case → `your_tool`).
- `GatewayTranslationLayer.prepareRequest` applies naming (canonical→wire) BEFORE the schema
  adapter; `convertResponse` reverse-names tool_use back to PascalCase so the orchestrator
  ALWAYS sees canonical. ⇒ your dispatch branch checks `toolUse.name === 'YourTool'`
  (PascalCase); the wire/probe uses `your_tool`. The normalizer is
  `name.toLowerCase().replace(/[_-]/g,'')` — collisions after that get deduped (first wins).

## 6. Forced tool_choice — the complete guide (build one for ANY scenario)

Forcing the model to call a specific tool for one turn is a general capability, not a one-off — future
use cases will want it (a mandatory attestation, a required classifier/router call, a safety gate, a
structured-output extractor, a "you MUST use tool X now" backstop). This section is the COMPLETE recipe,
distilled from getting the AskForAdvice v2 heed-backstop actually working on DeepSeek — where a
compile-clean, "code-complete" forced choice was **totally inert** until FIVE distinct things were fixed.
Every step below was a real reward-0 / ignored-choice before the fix. Build a new forced choice by walking
all six sub-steps; skip one and the model silently ignores the force with NO error.

### 6.1 The round-trip — gateway SHAPES, transport SPLATS
🔴 **The schema translation belongs at the GATEWAY, not the transport** (operator doctrine: "the gateway
translator translates canonical→provider schemas"). One normalized choice fans out to every provider shape:
- Pass a CANONICAL, NORMALIZED choice into `GatewayTranslationLayer.prepareRequest`'s options —
  `{type:'tool', name:'YourTool'}` (PascalCase, `type` ∈ `auto|required|tool`).
- The gateway does BOTH translations: naming (canonical→wire via `ToolNamingHandler.convertName`) THEN
  schema shape via `orchestrator/toolChoiceTranslation.ts translateToolChoice(normalized, apiPattern)` →
  the provider-shaped `{key, value}` stored on `PreparedRequest.toolChoice`. Shapes per `api.pattern`:
  chat `tool_choice:{type:function,function:{name}}` (OpenAI/DeepSeek/xAI-chat), messages `{type:'tool',name}`
  (Anthropic/xAI-messages), Responses flat `{type:function,name}`, google REST snake `tool_config`
  (functionCallingConfig ANY + allowedFunctionNames), google SDK camelCase `toolConfig`.
- `APIClient` is a DUMB SPLAT: `body[request.toolChoice.key] = request.toolChoice.value` at each
  tool-attach site — NO per-provider logic in the transport.
- **Coverage is per `api.pattern`, and EVERY dispatched pattern needs a splat site.** Verify:
  `grep -n "applyToolChoice\|\.tools = request.tools\|toolChoice" packages/core/src/orchestrator/APIClient.ts`
  then cross-check against the dispatch switch cases. hf-space is the known structural exception (Gradio
  `/run` has no tool_choice slot). tool_choice is body-level, per-request → NOT part of the cached
  tool/prefix → **cache-safe** (setting it never busts the prompt cache).

### 6.2 Arm it at EVERY request-assembly site the trigger can fire (bug #1 + #2)
The force is only as good as WHERE you attach the `toolChoice` option in the turn loop:
- **Both stream AND non-stream, AND both the INITIAL and CONTINUATION `prepareRequest` sites** — typically
  4 call-sites (§7 stream⊥non-stream duplication). Attaching only to the initial request is the classic
  dead-force: a condition that develops mid-turn (thrash, N failures, turn-count) is IMPOSSIBLE on the
  initial request (the loop is at turn 0, the failing window empty) — so the force never arms. Grep the
  resolver name; expect ~4 hits; wire all of them.
- **Feed the trigger detector the RIGHT counter.** The loop's tool-call iteration (`toolCallIteration`) is
  NOT the per-user-message turn counter (`this.turnNumber`, which is constant within a message). A detector
  gated on a floor of tool calls will never fire if handed the wrong counter. Pass the tool-call iteration;
  initial sites pass `0`.

### 6.3 The forced tool must be PRESENT — and ALONE (bug #4)
Two inclusion interactions, both silent killers:
- **Present:** the forced tool must survive the tool-inclusion pipeline (§4 — deferred filter, anchor,
  post-filter append). Forcing a tool that the deferred filter stripped = the model has no such tool to
  call = the force is meaningless. Make the forced tool essential-tier or post-filter-appended.
- **Alone:** when forcing, restrict the tools array to ONLY the forced tool. With the FULL catalog present,
  providers (DeepSeek observed 2026-08-29) IGNORE the named choice and call some other available tool. The
  gateway filters `tools` to the forced canonical name BEFORE naming-conversion when a `type:'tool'` choice
  is set.

### 6.4 🔴 Provider quirks that silently DEFEAT a forced choice (the checklist — bugs #3 + #5 + sacred paths)
A byte-correct-looking request can still be ignored. Walk this per provider you force on:
- **DeepSeek (chat/completions) + thinking mode → HTTP 400** ("Thinking mode does not support this
  tool_choice"). DeepSeek v4 is a HYBRID reasoning model, thinking ON by default. Send
  `chatRequest.thinking = { type: 'disabled' }` (OpenAI format) when a tool_choice is forced on deepseek.
  🔴 Dropping `reasoning_effort` is NOT enough — you must disable thinking explicitly.
- **🔴🔴 SUPERSEDING FINDING (2026-08-30): DeepSeek IGNORES forced tool_choice whenever the history holds
  ANY prior tool_call — regardless of `parallel_tool_calls` (absent OR false), top_p, thinking, or even
  `tool_choice:"required"`, and even when the tools array contains ONLY the forced tool (it echoes a tool
  that isn't in the array).** Bisect-mapped: 0 prior tool_calls = choice honored; ≥1 = history tool echoed.
  The earlier "#5 parallel_tool_calls was the root cause" attribution was their NONDETERMINISM flipping one
  replay — keep `parallel_tool_calls=false` when forcing (harmless, correct semantics) but DO NOT trust it
  as a fix. ⇒ **Forced tool_choice on DeepSeek is structurally unreliable mid-conversation** — any mechanism
  that needs a guaranteed tool call mid-task (exactly when triggers like thrash fire) must NOT depend on it.
  The robust pattern: if the tool is orchestrator-dispatched, have the ORCHESTRATOR invoke it directly and
  deliver the output through the tool-result system-reminder channel (which provably works) — see the
  auto-consult (CORTEX_MENTOR_AUTO) worked example.
- **The full catalog defeats the named choice** → restrict tools (6.3).
- **The xAI messages interleaved-thinking path is SACRED** — a forced choice (or any new body key) on that
  path must be ADDITIVE and gated behind before/after grok canary probes; never disturb the thinking
  round-trip ([[feedback_xai_interleaved_sacred]]).
- **Google HTTP vs SDK casing** — REST `generateContent` = snake `tool_config`; `@google/genai` SDK = camel
  `toolConfig`. One translator, two shapes; don't hand-roll the camelCase in the transport.

### 6.5 🔴 Validate END-TO-END with a seeded trigger + literal-request replay (never trust green tsc)
A forced choice that COMPILES and looks right in the code is a coin-flip between "works" and "5 hidden bugs"
— only a live run distinguishes them. The method that ended the v2 hunt:
1. **Seed the trigger deterministically** (a real model won't thrash/fail on cue): e.g. seed the state the
   detector reads (`.cortex/decisions.jsonl` failure window + `CORTEX_THRASH_MIN_TURNS=1`), set the env gate
   on, drive a real failing task, watch DEBUG for the forced tool actually being CALLED + its executor firing.
2. **When the request "looks correct" but the model ignores the choice:** dump the LITERAL outbound request
   body the harness built (`console.error('[BODY]'+JSON.stringify(chatRequest))` at the real send site —
   `require('fs')` fails silently in the ESM dist, use console), replay it VERBATIM via curl (reproduce the
   wrong behavior), then BISECT fields — remove one at a time until the choice is honored. That is exactly
   how `parallel_tool_calls` was isolated. Inference over the code would never have found it.
3. `tsc --noEmit` after every edit; the pure translator (`translateToolChoice`) gets unit tests per provider.

### 6.6 Ship it DARK behind one master gate
Gate the whole mechanism behind a single env flag (default off) + the trigger condition, so it ships
inactive and activates by config (the v2 model: `CORTEX_MENTOR_FORCE`). Key property to PRESERVE and VERIFY:
every provider fix in 6.4 keys off the PRESENCE of a forced `toolChoice` — so when the resolver returns
`undefined` (gate off), the choice is unset and behavior is byte-identical to pre-force (e.g. `parallel_tool_calls`
falls back to its original value, tools stay the full catalog, thinking stays on). Confirm the sole producer
of a forced choice is your gated resolver (grep every `toolChoice:` arg to `prepareRequest`) so nothing else
trips the fixes. Then a publish is dark: on npm, off in prod, one flag from active.

**Worked episode (provenance):** AskForAdvice v2 — the five fixes above, found by seeded-thrash validation +
literal-replay bisection, shipped dark in nexus-cortex 4.86.0. Contrast: the EndTurn Stage-4 verifier was ALSO
gated-off + green-tsc but turned out ALREADY complete (0 bugs) — same live-seeded validation, opposite finding;
that's the whole point of 6.5. Full story: [[session-resume-2026-08-29]]; source-of-truth map:
`omniclaude-v4/docs/MENTORSHIP_ASK_FOR_ADVICE_SPEC.md` §13.

## 7. 🔴 THE GOTCHAS LEDGER (each cost real time)

- **STREAM ⊥ NON-STREAM DUPLICATION.** Assembly, dispatch, and the turn loop are ALL duplicated
  across a streaming and a non-streaming path. **Every edit goes in BOTH** (inclusion append,
  dispatch branch, forced-choice arming) or it silently works in only one mode. Grep the symbol;
  expect ~2 hits; edit both.
- **`this`-less closures.** Some transport body-builders run inside a closure where `this` is
  not the class instance (e.g. a streaming generator) → `this.helper(...)` is a TS error
  (`'this' implicitly has type 'any'`). Inline the module-level function there instead.
- **Line-number drift.** Never trust a line number from a doc/spec/memory — re-grep. Anchor
  edits on unique surrounding text.
- **The SACRED xAI interleaved-thinking path.** tool_choice / new body keys on the xAI
  `messages` path must be ADDITIVE (do not disturb the thinking round-trip); gate any real
  change behind before/after grok canary probes ([[feedback_xai_interleaved_sacred]]).
- **Google HTTP vs SDK casing.** `generateContent` (REST) is snake_case; `google-sdk`/
  `google-genai` (@google/genai) config is camelCase. One translator, two shapes — don't
  hand-roll the camelCase in the transport.
- **executionEnvironment is client|sandbox ONLY** — omit it for server-dispatched tools
  (setting 'server' is a typecheck error).
- **The unknown-tool guard.** A dispatch branch without a matching guard entry gets rejected
  before it runs.

## 8. TDD + verification discipline (obey the repo rules)

- 🔴 **NEVER run the full vitest suite** (it has crashed the repl). SCOPED single-file only:
  `timeout 180 npx vitest run <ONE file> --no-coverage`.
- **`tsc --noEmit` after EVERY edit** — it is the cheap guardrail that catches the this-less
  closure, the interface mismatch, the wrong arg.
- **Ground-truth the wiring, don't infer it:** a node one-liner importing the built dist and
  calling `toolFactory.getTool('YourTool')`; a DEBUG_PAYLOAD probe that the tool is in the
  request; a scoped test that the dispatch/inclusion/naming behaves. (§0.)
- **Unit-test the pure pieces** (a translator, a detector, a store method) in isolation.
- Follow TDD where practical; verify the CHANGED code's test file no-keys green BEFORE any
  publish ([[feedback-preflight-before-publish]]).

## 9. THE 6-STEP WIRING CHECKLIST (map each step to code you READ)

1. **DEFINE** — add the `CanonicalToolDefinition` to `BaseToolRegistry` (PascalCase name, schema,
   category, discoveryTier, metadata). Verify `toolFactory.getTool('YourTool')` resolves.
2. **PICK THE DISPATCH PATH** — needs orchestrator state? → orchestrator-dispatch (path 1) with a
   branch + guard entry, in BOTH stream & non-stream loops. Else → an executor in
   `packages/executors` + registration.
3. **INCLUDE** — a gated, idempotent `ensureYourTool(toolsToUse)` appended POST-filter (after the
   deferred filter + anchor), in BOTH assembly regions. Do not rely on discoveryTier.
4. **NAME** — nothing to do if you used PascalCase canonically; confirm the wire form via a probe
   and that your dispatch checks PascalCase.
5. **(optional) FORCE** — if the tool needs forcing: a normalized `toolChoice` option on
   `prepareRequest` (gateway shapes via `translateToolChoice`), splatted in the transport at every
   `api.pattern` site; arm it in the turn loop behind an env gate.
6. **VERIFY** — `tsc` clean; scoped tests green; ground-truth getTool + DEBUG_PAYLOAD; then a real
   run confirms the tool APPEARS and is CALLED. Record the grounded file:line map in the spec/doc
   so the next person doesn't re-derive it.

## 10. Worked example — AskForAdvice (this session, the canonical case)
Definition in `BaseToolRegistry` (PascalCase, standard tier) → orchestrator-dispatched (path 1,
because the mentor call needs `helperMiddleware` + `DecisionStore` thrash state) → included via
`ensureAskForAdviceTool` post-filter in both assembly regions (tier alone left it invisible) →
forced via `translateToolChoice` at the gateway + a dumb splat across all `api.pattern` transports
+ armed on `resolveThrashState` behind `CORTEX_MENTOR_FORCE`. Every one of those steps was FIRST a
grounded map (spec §12), verified file:line, before a line was edited — and the one step done on
assumption (tier ⇒ present) was the one that was wrong. That is the whole lesson: map, verify, then
wire.


## 🔴 Companion lesson — sub-flag PREREQUISITE gates (from the EndTurn verifier, 2026-08-29)
(The forced-tool_choice knowledge that used to live here is now the full §6 guide.) One extra lesson from
the sibling episode — the EndTurn Stage-4 verifier: a mechanism can have MULTIPLE env flags in a dependency
chain. `CORTEX_ENDTURN_REQUIREMENTS` (and even `CORTEX_ENDTURN_INTEGRITY`) are INERT without
`CORTEX_ENDTURN_GATE=true`, because Stages 4/5 run INSIDE the EndTurn-call handler and the EndTurn tool is
filter-stripped when the gate is off. ⇒ before concluding "flag X = active," trace X's PREREQUISITE gate: a
sub-flag whose enabling code only runs downstream of a master gate does nothing on its own. (This is the
inverse of the §6.6 dark-ship property: verify not just that the master gate turns the feature ON, but that
each sub-flag actually reaches live code once the master is on.)