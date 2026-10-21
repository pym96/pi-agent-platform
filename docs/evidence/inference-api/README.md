# Inference API QA — Pi #9

Builder candidate, not an independent acceptance. [WorkOrder and subsequent Verdict](https://github.com/pym96/pi-agent-platform/issues/9). Execution source: `47d174af53efb4f29deca836355aa09a266df93f`; final evidence commit changes only this evidence directory. [Reproduction](../../../service/inference/README.md).

| Check | Observed result |
|---|---|
| macOS Python 3.14.0, pytest 8.4.2, actual HTTP | 49 passed, 0 skipped/errors/failures |
| Linux Python 3.10.12, same source, actual HTTP | 49 passed, 0 skipped/errors/failures |
| Seeded invalid-request status changed 400 → 200 | pytest exit 1; restored bytes exit 0 |
| Existing frozen #7 measurement-parser regression | 16 passed |
| Real GPU model generation | Not started by Builder; independent Stage B pending |

[Manifest](manifest.json) hashes every retained raw artifact under `~/.local/state/pi-agent-platform/inference9-20261021`. Local/Linux directories contain JUnit, pytest logs, raw request/response bodies, fixture backend lifecycle and cleanup records. `source-identity.json` binds all copied Linux module files to executed source bytes; the Linux test directory is a copied source tree, not a Git checkout. Final review must use a fresh clean candidate checkout. `linux-wheel-manifest.json` and both freeze files record complete installed dependency identity, including conditional Python 3.10 packages. `readiness.json` records full existing model/dependency manifest verification (33/2349 files, no mismatches), exact image, and two idle GPU observations; it is preparation evidence, not launch authorization or a future availability guarantee.

No owned server service/container was started. Tests create temporary loopback listeners and verify their closure in fixture finalizers, including deliberate assertion failure. Server retained only the isolated venv/source/evidence directory under the authorized #9 root. No global package, driver, model or Docker configuration was changed. Old #7 files are unchanged.

## Failure and decision record

The first HTTP test failed because the new app module did not yet exist; the vertical slice then passed before invalid/fault coverage was added. A deliberately defective status implementation later made the public pytest tests fail, and restoration passed. Both logs and defective source are retained rather than presenting only green output.

Linux preparation initially failed because system Python lacked ensurepip. Installing global packages would violate scope, so the Builder bootstrapped only the isolated venv from wheels. Cross-platform wheel download on Python 3.14 omitted Python 3.10 conditional dependencies; the first Linux import exposed missing exceptiongroup, then the reviewed bundle added exceptiongroup/tomli/async-timeout/typing_extensions. An initial rsync also lacked its destination parent; the parent was created within the owned directory and the copy retried. These were environment preparation failures, not model/API evidence. Full wheel hashes and final resolved versions make the correction reproducible.

Human selected the target and budget; Master fixed the API and resource contract; Builder implemented the adapter/tests and gathered Stage A evidence. Independent Regulator supplies adversarial probes and any real-model receipt. No claim of Human independently implementing this code, no new throughput/quality claim, and no automatic resume fact promotion.

## Stage B handoff

Builder calls: zero. Proposed independent run: exact final candidate SHA, config `service/inference/config/server.json`, existing pinned image/model/dependencies, GPU3 only, new `pi-inference9-model`, loopback18179. `launch.sh` requires fresh bound deadline/guard receipt, repeats all checks, and monitors only its owned container. Regulator may run `smoke.py --requests 3` with at most six total generation attempts, no retries, each <=128 new tokens, concurrency one. Model envelope6CPU/28GiB, client2CPU/4GiB, total GPU lifetime<=30min including startup. Record all attempts and stop receipt. Real smoke remains pending until its own raw evidence and Verdict; this document does not imply it passed.

Limits: scripted CPU tokens are fixture values, not tokenizer measurements. Cancellation tests prove cooperative behavior, not arbitrary native-code termination. This is a narrow private streaming contract, not complete OpenAI compatibility or public authentication. A successful smoke would establish functional completion only, not model quality or a production SLA.
