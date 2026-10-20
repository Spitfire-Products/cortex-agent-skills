# Inventory

Every skill directory found in the workspace and what happened to it.

## Exported

| category | skill | source | size |
|---|---|---|---|
| cortex | `autoresearch` | `.agents/skills/autoresearch` | 30 KB |
| cortex | `candidate-model-onboarding` | `.claude/skills/candidate-model-onboarding` | 22 KB |
| cortex | `cortex` | `.agents/skills/nexus-cortex-harness` | 70 KB |
| cortex | `cortex-bench` | `.agents/skills/cortex-bench` | 49 KB |
| cortex | `cortex-shipped` | `omniclaude-v4/.cortex/skills/cortex` | 48 KB |
| cortex | `cortex-subagent` | `omniclaude-v4/.cortex/skills/cortex-subagent` | 7 KB |
| cortex | `cortex-tool-development` | `.claude/skills/cortex-tool-development` | 24 KB |
| cortex | `docx` | `omniclaude-v4/.cortex/skills/docx` | 3 KB |
| cortex | `grok-build-bench` | `.claude/skills/grok-build-bench` | 16 KB |
| cortex | `harbor-bench` | `.claude/skills/harbor-bench` | 268 KB |
| cortex | `herdr` | `omniclaude-v4/.cortex/skills/herdr` | 16 KB |
| cortex | `jev` | `.claude/skills/jev` | 27 KB |
| cortex | `pptx` | `omniclaude-v4/.cortex/skills/pptx` | 4 KB |
| cortex | `stdb-bench` | `.claude/skills/stdb-bench` | 43 KB |
| cortex | `v2p3-training-pipeline` | `.claude/skills/v2p3-training-pipeline` | 76 KB |
| cortex | `verify-work` | `omniclaude-v4/.cortex/skills/verify-work` | 3 KB |
| cortex | `xlsx` | `omniclaude-v4/.cortex/skills/xlsx` | 4 KB |
| general | `assemble-agents` | `.claude/skills/assemble-agents` | 7 KB |
| general | `assemble-plugins` | `.claude/skills/assemble-plugins` | 3 KB |
| general | `assemble-skills` | `.claude/skills/assemble-skills` | 9 KB |
| general | `best-of-n` | `omniclaude-v4/.cortex/skills/best-of-n` | 3 KB |
| general | `canon-store` | `.claude/skills/canon-store` | 17 KB |
| general | `claude-code-experiments` | `.claude/skills/claude-code-experiments` | 83 KB |
| general | `claude-code-variables` | `.claude/skills/claude-code-variables` | 10062 KB |
| general | `execute` | `.claude/skills/execute` | 9 KB |
| general | `grounded-research` | `.claude/skills/grounded-research` | 3 KB |
| general | `huggingface-spaces` | `.claude/skills/huggingface-spaces` | 91 KB |
| general | `leanrea` | `.claude/skills/leanrea` | 16 KB |
| general | `nexus-rea` | `.claude/skills/nexus-rea` | 28 KB |
| general | `pdf-documents` | `omniclaude-v4/.cortex/skills/pdf-documents` | 105 KB |
| general | `pm-wake-loop` | `.claude/skills/pm-wake-loop` | 4 KB |
| general | `resume-analyst` | `omniclaude-v4/.cortex/skills/resume-analyst` | 12 KB |
| general | `resume-session` | `.claude/skills/resume-session` | 15 KB |
| general | `scope` | `.claude/skills/scope` | 4 KB |
| general | `spacetimedb-cli` | `.agents/skills/spacetimedb-cli` | 7 KB |
| general | `spacetimedb-concepts` | `.agents/skills/spacetimedb-concepts` | 20 KB |
| general | `spacetimedb-csharp` | `.agents/skills/spacetimedb-csharp` | 15 KB |
| general | `spacetimedb-rust` | `.agents/skills/spacetimedb-rust` | 36 KB |
| general | `spacetimedb-typescript` | `.agents/skills/spacetimedb-typescript` | 25 KB |
| general | `spot-gpu-compute` | `.claude/skills/spot-gpu-compute` | 25 KB |
| general | `team-plan` | `.claude/skills/team-plan` | 5 KB |
| general | `train` | `.claude/skills/train` | 8 KB |
| general | `vast-compute` | `.claude/skills/vast-compute` | 16 KB |
| general | `vastai` | `.agents/skills/vastai` | 1025 KB |

## Held back (not exported until approved)

| skill | source | reason |
|---|---|---|
| `nexus-sense` | `nexus-terminal/.agents/skills/nexus-sense` | Nexus Terminal product internals (proprietary) |
| `nexus-terminal-cortex` | `nexus-terminal/.agents/skills/nexus-terminal-cortex` | Nexus Terminal product internals (proprietary) |
| `browser-cortex-bench` | `nexus-terminal/.agents/skills/browser-cortex-bench` | Nexus Terminal product internals (proprietary) |
| `hosted-cortex-driving` | `nexus-terminal/.agents/skills/hosted-cortex-driving` | documents admin routes of the hosted service |
| `npc-swarm` | `.claude/skills/npc-swarm` | Nexus Terminal product internals (proprietary) |
| `npc-swarm-provisioning` | `nexus-terminal/skills/npc-swarm-provisioning` | Nexus Terminal product internals (proprietary) |
| `nexus-resource-catalog` | `.agents/skills/nexus-resource-catalog` | workspace-specific index of private resources |

## Excluded sources (third-party or copies)

| path | why |
|---|---|
| `.grok/skills/{docx,pptx,xlsx}` | Anthropic document skills, proprietary license (LICENSE.txt) — not ours to republish |
| `.grok/skills/{check,help,create-skill}` | grok-build's own skills (xAI) |
| `.grok/bundled/*` | grok-build bundled skills (xAI) |
| `.local/secondary_skills/*` | Replit-provided sample skills |
| `.claude/plugins/**` | plugin marketplaces (third-party) |
| `aidenybai/**` | vendored upstream repos |
| `.cache/pkg/**, .bench-hosting/**, .claude/worktrees/**, **/.cortex/builtin/**, *-extracted/**` | caches, worktree copies, mirrors |
