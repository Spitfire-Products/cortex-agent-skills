# cortex-agent-skills

The agent skills we rely on daily, mirrored from the workspace where they are maintained (this repo is the
published copy; edits happen at the source and land here through `scripts/deploy-cortex-agent-skills.sh`). Each skill is a
directory with a `SKILL.md` (frontmatter: `name`, `description`) plus any references or scripts it carries. Paths inside the skills
that pointed at the author's machine are written as `$WORKSPACE`; private store names as `<hf-org>/`.

## Using a skill

Copy a skill directory into your project's `.claude/skills/`, `.agents/skills/` or `.cortex/skills/` (nexus-cortex loads
`.agents/skills` then `.cortex/skills`). Claude Code and nexus-cortex discover it by its frontmatter `name`.

## general

Agent skills that stand on their own: research discipline, session/memory hygiene, team orchestration, cloud compute, vendor references.

| skill | description |
|---|---|
| [`assemble-agents`](general/assemble-agents/SKILL.md) | Fetch specialized agents from the VoltAgent repository. Searches across categories, presents top 5 matches, and waits for user approval before adding to .claude/agents/. |
| [`assemble-plugins`](general/assemble-plugins/SKILL.md) | Search the official Claude Code marketplace (claude-plugins-official) for plugins matching capability gaps. Uses plugin CLI to list and search, presents top 5 matches for user approval. |
| [`assemble-skills`](general/assemble-skills/SKILL.md) | Query the skills.sh registry for skills matching identified capability gaps. Presents top 3 HIGHLY RELEVANT matches only, waits for user approval before installation. Be conservative - only suggest skills that are clearl |
| [`best-of-n`](general/best-of-n/SKILL.md) | Implement one task N ways in parallel and keep only the best candidate. Spawns N varied subagents (distinct strategy, model, temperature) in isolated git worktrees, judges every candidate against the SAME criteria, and a |
| [`canon-store`](general/canon-store/SKILL.md) | Operate the CANON STORE — the canonical, provider-neutral, lossless memory + context-retrieval rail that captures THIS workspace's Claude Code sessions (and every harness's) as append-only JSONL in a git repo. Load this  |
| [`claude-code-experiments`](general/claude-code-experiments/SKILL.md) | Active, past and candidate A/B experiments that Anthropic runs on this Claude Code install (GrowthBook experiment enrollments cached in .claude.json — experimentId, variationId, the feature flags and values each one driv |
| [`claude-code-variables`](general/claude-code-variables/SKILL.md) | Master reference of EVERY knob Claude Code reads — remote feature flags (GrowthBook tengu_* / Statsig gates / experiment features), environment variables, settings.json keys, and telemetry event names — for the installed |
| [`execute`](general/execute/SKILL.md) | Orchestrate an agent team to execute the user's task. Checks for agent teams support, presents pre-execution review, spawns teammates, and coordinates execution. Falls back to subagents if agent teams unavailable. |
| [`grounded-research`](general/grounded-research/SKILL.md) | Active-discovery + map-before-assert research discipline. Invoke BEFORE answering any cross-cutting "who calls X / which path / how does this flow" question, before fixing or deploying against an assumed code path, or wh |
| [`huggingface-spaces`](general/huggingface-spaces/SKILL.md) | Build, deploy, and maintain applications on Hugging Face Spaces — Gradio / Docker / Static SDKs, ZeroGPU and dedicated hardware, model loading, debugging, buckets, inference providers, community grants. Use whenever the  |
| [`leanrea`](general/leanrea/SKILL.md) — third-party: aicodeking/leanrea @ 09ba4aa0 (MIT, LICENSE kept); local Linux/quota notes appended to SKILL.md | Reverse engineer shipped software with plain local CLI tools, no MCP needed. Covers Electron/JS bundles, native Mach-O/ELF/PE, Go/Rust/.NET/Flutter/WASM binaries, APKs, SQLite, pcaps, firmware and websites. Use to explai |
| [`nexus-rea`](general/nexus-rea/SKILL.md) — our evolution of leanrea (attributed, MIT notice kept): runtime React layer — hook shim pre-load, fiber probe, prop-signature inventory; three paths (plain Playwright / nexus-browser MCP / sandbox relay) | Reverse-engineer a shipped React/Next.js web app from its RUNTIME, not just its bundle — pre-load a React DevTools hook shim, walk the live fiber tree, bucket components by prop-key signature (minified names are useless, |
| [`pdf-documents`](general/pdf-documents/SKILL.md) | Create rich PDF documents (reports, blueprints, posters, banners) from HTML and read/deconstruct existing PDFs for agent consumption. Covers page sizes, print CSS, SVG charts, scaled output, and lossless PDF-to-HTML conv |
| [`pm-wake-loop`](general/pm-wake-loop/SKILL.md) | The WAKE PROTOCOL for a PM agent resuming a long-horizon mission after sleep — orient from the mission ledger, rehydrate memory cheap-to-deep, heal the worker fleet with idempotent relaunchers, adjudicate newly banked re |
| [`resume-analyst`](general/resume-analyst/SKILL.md) | Analyze, improve, and create professional resumes and CVs. Use when the user needs help with resume review, ATS optimization, content improvement, or creating a new resume from scratch. |
| [`resume-session`](general/resume-session/SKILL.md) | Build and maintain the RESUME MEMORY — the one file a fresh context (post-compaction, new session, or a different agent) reads first to recover the FULL scope of a long session with no context loss — plus the project che |
| [`scope`](general/scope/SKILL.md) | Analyze project structure, architecture, tech stack, and existing Claude Code configuration. Use when starting the dream-team workflow to understand the codebase context. |
| [`spacetimedb-cli`](general/spacetimedb-cli/SKILL.md) | SpacetimeDB CLI reference for initializing projects, building modules, publishing databases, querying data, and managing servers |
| [`spacetimedb-concepts`](general/spacetimedb-concepts/SKILL.md) | Understand SpacetimeDB architecture and core concepts. Use when learning SpacetimeDB or making architectural decisions. |
| [`spacetimedb-csharp`](general/spacetimedb-csharp/SKILL.md) | Build C# modules and Unity clients for SpacetimeDB. Covers server-side module development and client SDK integration. |
| [`spacetimedb-rust`](general/spacetimedb-rust/SKILL.md) | Develop SpacetimeDB server modules in Rust. Use when writing reducers, tables, or module logic. |
| [`spacetimedb-typescript`](general/spacetimedb-typescript/SKILL.md) | Build TypeScript clients for SpacetimeDB. Use when connecting to SpacetimeDB from web apps, Node.js, Deno, Bun, or other JavaScript runtimes. |
| [`spot-gpu-compute`](general/spot-gpu-compute/SKILL.md) | Choose and use a CHEAP spot / decentralized GPU market (Vast.ai, RunPod, Lium/SN51, io.net, Akash, NVIDIA DGX Lepton) instead of HF Spaces for sub-1B LoRA training / eval / inference — and PORT our durable-run apparatus  |
| [`team-plan`](general/team-plan/SKILL.md) | Analyze task requirements and identify talent gaps. Compares needed expertise against available resources to determine if assembly and training phases are required. |
| [`train`](general/train/SKILL.md) | Auto-generate custom agents and skills for remaining capability gaps after assembly. Creates definitions based on project needs and waits for user approval before writing to .claude/. |
| [`vast-compute`](general/vast-compute/SKILL.md) | How WE use Vast.ai — the three job shapes (bench executor VM fleet, training/eval GPU jobs, one-off compute jobs), the shared box lifecycle rules (rent, right-size, provision, self-reaper + reboot cron, TTL, teardown, co |
| [`vastai`](general/vastai/SKILL.md) | Vast.ai CLI to manage GPU instances, volumes, serverless endpoints, and billing. |

## cortex

Skills specific to the nexus-cortex harness (the npm `nexus-cortex` product), its benches and its training arc.

| skill | description |
|---|---|
| [`autoresearch`](cortex/autoresearch/SKILL.md) | The playbook for an agent tasked with acting as the AUTO-RESEARCH PM — investigate, write a measurable experiment plan, delegate to N varied subagents (or relay to the cortex harness), and arbitrate the holdout-verified  |
| [`candidate-model-onboarding`](cortex/candidate-model-onboarding/SKILL.md) | Onboard a new open-weight base model as a V2-P3 bake-off candidate — HF Space serving, harness card + tool-call parser, then the full cortex-bench suitability protocol (full-stack + lean-router + tool-stable-sampling) be |
| [`cortex`](cortex/cortex/SKILL.md) (alias: nexus-cortex-harness) | Operate the nexus-cortex HARNESS (the omniclaude-v4 monorepo — `cortex` CLI, headless server on :4000, 31 tools, agent teams, PR pipeline, benchmarking). This is the npm `nexus-cortex` product. NOT the Nexus Terminal COR |
| [`cortex-bench`](cortex/cortex-bench/SKILL.md) | Multi-model parallel benchmark methodology for finding harness deficiencies and driving autoresearch-style recursive self-improvement of the CORTEX harness itself. Cross-provider comparison with ground-truth control. EVE |
| [`cortex-shipped`](cortex/cortex-shipped/SKILL.md) — the sanitized variant that ships inside the npm package | Dispatch tasks to the Nexus Cortex server for parallel testing, evaluation, and agent-to-agent workflows. |
| [`cortex-subagent`](cortex/cortex-subagent/SKILL.md) | Drive Nexus Cortex headlessly as a full autonomous SUB-AGENT from your own agent harness — configure it, prompt it, budget it, and verify its output. Use when another agent/harness (not a human at a TUI) should delegate  |
| [`cortex-tool-development`](cortex/cortex-tool-development/SKILL.md) | Develop and WIRE a new tool into the nexus-cortex harness (omniclaude-v4) end-to-end — where tools are DEFINED (Base vs Addon registries → ToolFactory), where they EXECUTE (the 3 dispatch paths: executor vs orchestrator- |
| [`docx`](cortex/docx/SKILL.md) | Create, read, and edit Word documents (.docx). Use whenever the deliverable is a Word document, or the user asks to open/modify/extract from an existing .docx — reports, letters, templated documents, doc-to-PDF conversio |
| [`grok-build-bench`](cortex/grok-build-bench/SKILL.md) | Drive xAI's real grok-build CLI (the `grok` / grok-shell agent) headless — to (a) proxy-capture its exact transport (headers + OpenAI /v1/chat/completions JSON), (b) benchmark models in xAI's own harness as a ground-trut |
| [`harbor-bench`](cortex/harbor-bench/SKILL.md) | Run a PUBLIC agentic benchmark (Terminal-Bench 2.0 via the Harbor framework) against the hosted nexus-cortex harness, durably, and read the results honestly. Covers the Harbor installed-agent ADAPTER (the "A1 arm"), the  |
| [`herdr`](cortex/herdr/SKILL.md) | Control Herdr, the terminal workspace server nexus-cortex is running inside (HERDR_ENV=1): inspect neighboring panes/agents, run long-lived processes in sibling panes and read/wait on them, start helper agents. Use when  |
| [`jev`](cortex/jev/SKILL.md) | Everything we know and built around TypeSafe AI's Jev (System One typed-decision model) and its open replicas — the API shape and limits, our paired evaluation against the hidden grader (262 sessions), the Jev typed dist |
| [`pptx`](cortex/pptx/SKILL.md) | Create, read, and edit PowerPoint presentations (.pptx). Use whenever the deliverable is a slide deck — building presentations from content or data, editing existing decks, extracting slide text, or deck-to-PDF conversio |
| [`stdb-bench`](cortex/stdb-bench/SKILL.md) | Operate the STDB BENCH CONTROL PLANE — the `nexus-nexus-cortex` SpacetimeDB module that places, keeps alive, heals, budgets, gates, reaps and completes a Harbor/TB2.1 lane fleet with NOTHING running on the repl. Covers t |
| [`v2p3-training-pipeline`](cortex/v2p3-training-pipeline/SKILL.md) | Operate the V2-P3 base-model bake-off — train LoRA adapters on candidate bases per slot, eval each on its SLOT-APPROPRIATE lenses, gate vs baseline, pick the smallest base clearing the gate. The runbook + full defect led |
| [`verify-work`](cortex/verify-work/SKILL.md) | Verify completed work with an independent, skeptical subagent before calling it done. Spawns a verifier that reviews the diff, runs the build and tests, and tries to REFUTE the claimed result rather than confirm it. Use  |
| [`xlsx`](cortex/xlsx/SKILL.md) | Create, read, edit, and clean spreadsheets (.xlsx, .csv, .tsv). Use whenever a spreadsheet file is the primary input or output — adding columns/formulas, formatting, charting, cleaning messy tabular data, converting betw |
