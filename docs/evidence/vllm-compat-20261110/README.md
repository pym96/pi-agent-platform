# Pi #21 November10 isolated compatibility attempt

Builder candidate only; G0 has not passed. This attempt currently lacks a complete wheel closure, installed runtime/pip-check/import identity and actual Builder/Regulator GPU generation. No inference performance, project fact, resume fact, public content or independent acceptance is claimed.

Baseline: accepted main `65c9f61cc4955bcfb5a8bfc761e087d98acdae96`. Human sets direction; Builder implements this opt-in preparation; a separate Regulator independently checks source and negative cases. Default inference code is unchanged.

Builder inspected the cached server image as `sha256:08619d6d884b3b456661f883a4e4420bd85a81aee560a86f7f26021b75dd6229`, Python3.10.12. Its missing `ensurepip` was handled with `venv --without-pip` and a SHA256-verified official pip25.0.1 wheel. No shared packages were changed. Preparation had no GPU device request and explicitly empty CUDA visibility/NVIDIA void, 10 CPU/32GiB, no new image pull.

The first official vLLM wheel download was slow; at15:09:25Z its temporary partial was90,477,223bytes including pip temporary metadata. It had not reached dependency resolution/installation. The one authorized alternate local route probe used the identical official URL, Range0–2097151 and a2MiB maximum: HTTP206,2,097,152bytes in3.813797seconds,549,885bytes/second. It did not justify a complete closure transfer within the unchanged15:23:36Z prep cutoff. No third route or implicit retry was attempted.

The initial source test failed because the launcher did not exist, then passed after implementation. Five CPU tests currently pass with zero skips: missing GO, eight malformed/expired identity cases, actual CPU sleeper terminated by the independent deadline watcher, foreign nonce preserved, and sealed synthetic wheels rejecting corruption/untrusted source. These do not substitute for actual runtime testing. Independent R probe originals are external and are not committed here.

Representative decision: a package version does not identify CUDA ABI. `xformers0.0.29.post2` has a generic wheel filename, so its CUDA11.8 official URL and actual bytes must be locked. The official cu118 index advertises SHA256 `1f58e453c27a861d5e4b099b37a58f33f4dc231e6b47ea79e3591d84e48e49a4`; that is source metadata, not a downloaded-artifact or runtime compatibility observation. The incomplete initial resolver command used extra-index version selection and was never allowed to install an ambiguous closure.

Raw preparation, partial-byte accounting and exact stop receipts will be preserved before handoff. No candidate CI push or model GO has occurred.

[Actual Builder strict CPU receipts](cpu/README.md). The wheel guard additionally evaluates Linux/Python3.10 active transitive requirements, version specifiers and requested extras; an actual missing-transitive fixture was rejected after independent review exposed the first subset-only check. Source-only CI is separately gated and cannot authorize GPU without the actual full runtime.
