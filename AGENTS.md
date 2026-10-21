# Project workflow

Master defines scope and integrates; Builder submits workorder/<issue>-candidate; independent Regulator reviews the exact remote SHA in a clean worktree. Never self-accept or push main as Builder.

Use issue-linked WorkOrder → Handoff → Verdict. Preserve failed experiments and distinguish synthetic load, connections, sessions and concurrent model execution. Only accepted candidate SHA may land through a recorded PR without changing its identity. Main must not be force-pushed or deleted.

This repository is independent of Pan-agent. Do not edit or resume the completed Pan product as part of this work. No real-model requests, training, GPU allocation, public deployment, or shared-server global changes without explicit scope.

## Agent skills

Engineering skills use [issue tracker](docs/agents/issue-tracker.md), [triage labels](docs/agents/triage-labels.md), and [domain navigation](docs/agents/domain.md). Apply TDD for behavioral changes and codebase-design for module boundaries; these links do not grant additional execution authority.
