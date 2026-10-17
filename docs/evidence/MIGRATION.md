# Independent repository migration — #1 Criteria1.1

Human corrected the repository boundary: the Pi platform belongs in its own repository, while Pan is complete. Master created `pym96/pi-agent-platform`; Builder relocated only the experimental service and its relevant evidence. Pan #142/PR143 were closed without acceptance or merge. This migration is not a technical performance improvement.

## Source and history

- New independent bootstrap: `f8b5a0bef391b2bd861e4321fb8b6f6738373bfa`.
- Source snapshot: Pan `381947df33783c89773601793b1d8f7a17668e59`, archived as `archival/pi142-pre-repo-split-20261017`.
- Original measured implementation: Pan `aa1d1afcfb4c822e9082da4b4372f4ea824d8906`.
- `platform/pi-service/` → `service/`; `docs/evidence/pi-service/` → `docs/evidence/`.
- No Pan Git ancestry, Runtime, TUI, workbench, resumes or governance history is imported. Original MIT contributor attribution is retained.

[File-level mapping](migration-map.json) records old/new hashes, modes and reasons. Go module/import namespace changes to `github.com/pym96/pi-agent-platform/service`; npm project name changes, with the dependency lock/integrities preserved. Compose becomes `pi-platform-1`, using localhost ports18151/18152 and new volumes. Diagnostic scripts use those same independent names. Agent/executor/store/cache algorithms are not redesigned. Historical synthetic fixture labels and advisory-lock constants remain; PostgreSQL is a fresh independently owned database.

## Evidence boundary

The historical13-run matrix remains under its original source SHA, task IDs and paths. The old manifest is byte-identical. [Historical report](REPORT.md) is labelled and only adjusts repository links. These are inherited source measurements, not fresh independent-repository results and not a previous accepted verdict. No13-run rerun is implied.

New migration validation is small and synthetic: clean dependency installation/build, Go checks, actual Pi submission/two-turn history/SSE replay and owned restart/fault probes. Its new source SHA, raw outputs and cleanup evidence are separate in [migration-manifest.json](migration-manifest.json). Validation is pending completion in this candidate preparation; independent acceptance is not claimed.

## Ownership and setup

Server ownership is a fresh `pi-agent-platform/experiments/1` root. Node/Go distributions and public dependency caches may be copied from existing installations into this owned root; containers mount only the new root, not a Pan checkout. No old volumes/history are reused. [Root README](../../README.md) and [service instructions](../../service/README.md) provide standalone Linux installation and stop commands. Existing Pan artifacts and the unrelated ComfyUI service are preserved. No paid model calls, GPU work, global Docker/toolchain changes or public service.
