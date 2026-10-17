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

New migration validation is small and synthetic: clean dependency installation/build, Go checks, actual Pi submission/two-turn history/SSE replay and owned restart/fault probes. Its new source SHA, raw outputs and cleanup evidence are separate in [migration-manifest.json](migration-manifest.json). Executed migration source: `0c6db070bccc87f7fd7b0780c93d112d93a36512`. All29 server source files matched this commit before cleanup. Independent acceptance is not claimed.

Fresh checks passed: offline clean npm installation; capped Go build; local race checks; actual PostgreSQL integration in a separate empty test database; actual Pi two-turn/context, duplicate/conflicting-key and SSE replay smoke; restart interruption/history; slow-consumer write deadline; terminal-persistence fault rollback/fail-stop/recovery. The provider-failure probe uses a deliberate synthetic endpoint error, not a paid provider.

A separate100-connection/10.001s check used one subscribed session, two offered/completed tasks and two maximum executors. All100 connections established and remained healthy; each observed all22 durable session events (2200 subscriber deliveries), with zero missing IDs, duplicates or regressions. This is a migration smoke, not a new C10K result. Normal idle stack limits total3 CPU/7 GiB; generator or build/test slot adds at most1 CPU/1 GiB. SSH/control observations remain outside container limits.

Owned services were stopped at03:24 UTC2026-10-17; new and historical volumes retained, unrelated ComfyUI stayed running. No model requests or GPU work were billed. Public Node22.23.3 and Go1.24.13 distributions were independently copied into the new root; no `pan-env` or Pan checkout is required.

One read-only evidence query initially referenced nonexistent `session_id`; correcting it to `events.session` produced the receipt. No task was rerun or data changed for this diagnostic mistake. Startup health polling also retained a transient connection reset before readiness.

## Ownership and setup

Server ownership is a fresh `pi-agent-platform/experiments/1` root. Node/Go distributions and public dependency caches may be copied from existing installations into this owned root; containers mount only the new root, not a Pan checkout. No old volumes/history are reused. [Root README](../../README.md) and [service instructions](../../service/README.md) provide standalone Linux installation and stop commands. Existing Pan artifacts and the unrelated ComfyUI service are preserved. No paid model calls, GPU work, global Docker/toolchain changes or public service.
