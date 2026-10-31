# Pi #12 E2E1.1 Stage A candidate report

Builder candidate only. No independent acceptance or new real GPU0 model execution. Base main870575fe697dbc71c7a4ed13ce3c1d76fdb28fed; necessary #12 code was transplanted from archived, unaccepted4944bd96e733966f5ea42f668d78bca6fd5494a2. The old GPU3 GO has expired. Human authorized the new loop and physical GPU0; the Master controls any new exact-SHA/config/deadline GO.

## Local CPU observations

Two precommit runs use actual Pi1.3.0, local Go1.27.1/Node26.7.0/Python3.14/PostgreSQL14.18. Their run.json correctly records the870575 HEAD plus worktree_dirty=true: these are preparation runs, not exact-final-source CI. Each run executes seven Go tests with-count=1/-race against a new dedicated empty database,13 actual SDK JUnit testcases, six measurement tests, five public required-entry tests and50 inference pytest cases, then five durable tasks. Three complete, two intentionally interrupt after stream error/context rejection. All required top-level suites have positive count and zero skips/expected failures; nested negative probes intentionally invoke native skip/xfail/empty runners and require rejection. CPU second run adds one synthetic device-reader test. Cleanup receipts report all owned child processes and local PG stopped.

No Docker daemon was started. The authorized SSH connection closes before authentication; current server resources are unknown. Local CPU cannot stand in for Linux Docker/NG or real-GPU runs. The workflow will execute actual current Nginx platform/lab/strict suites without its12-point load matrix, and preserve its own exact-SHA receipts.

The sealed run anchors are:

- cpu-run01: f06f6639c17ffae72d909c67d087f7ba672926dbb9f61ee87a4bf9a21444afc1,67 files.
- cpu-run02: d0a886486486d09742b2f791b89a1f97cf69c2160411c989b0022082c67f7534,69 files.

Native API binary, local PG data and private Pi working directory are omitted from this candidate receipt copy; logs/raw model bridge/client/Go trace/PG events, tool versions, suite machine results and cleanup are retained. No timing from these synthetic runs establishes GPU throughput or P95.

## Behavioral failures preserved

required-expectedfailure-red.log shows the old measurement wrapper accepting a native successful runner with one expected failure. The narrow counter fix makes the same probe green. required-pytest-xpass-red.log shows a nonstrict XPASS producing JUnit pass/exit0; the required-only plugin now rejects actual xfail/XPASS reports. SDK gating uses native testcase events/mandatory names rather than substring matching. The public required-entry probes also reject native Node skip/todo, zero tests, unittest skip/unexpectedSuccess, absent/wrong external digest, altered file and extra inventory.

gpu-relabel-red.log shows that changing historical GPU3 run labels/config digest could previously remain green. The new analyzer requires actual device command receipts plus source/config/model inspect associations; the same copied historical run now fails. Device-reader positive/mismatch tests use synthetic metadata explicitly, never pretend they ran NVIDIA hardware. Fresh real GPU0 capture and independent negative tests remain necessary.

The external watchdog now attempts stopping previously verified owned IDs even if a later diagnostic refresh fails, and handles SIGTERM through its cleanup. Its live server behavior remains unexecuted in this window. It never stops unverified foreign objects.

## Preserved identities and remaining gates

The703 manifest-listed old #12 originals plus their manifest (704 tracked files) remain byte-identical and historical. The974 manifest-listed Nginx originals plus their manifest (975 tracked files) and accepted Nginx scripts/config/compose/workflow remain byte-identical; the combined protected NG source+evidence set contains991 tracked paths. Preservation receipts identify those sets separately.

Stage B preparation requires server reconnect, current resource/device/port/disk checks, CPU UID1001 write probe under the real client limits, frozen source/config/build and a new Master GO. New projects pi-e2e12-1031-b/r use only host physicalGPU0 UUID GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead, CUDA_VISIBLE_DEVICES=0 and fresh volumes. Each new stack is capped at three attempts; there is no warmup/retry. Historical B3/R0 and502seconds remain in the shared budget. This report does not claim real-GPU execution, final CI success, accepted Verdict or completion of the project.
