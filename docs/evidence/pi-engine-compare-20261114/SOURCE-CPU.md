# Local source CPU checks (Builder evidence)

Not an independent Verdict, actual Linux3.10 run, sourceCI or model result.

- Comparison harness: 21 tests,0 failures/errors/skips/expected failures. Includes real local HTTP with the accepted app and injected native-engine seam, complete raw SSE/native/drain replay, deletion of a raw failed-slot artifact, absolute-deadline unsent drops, plan and guard negatives. The repair adds a complete18-slot pilot through the production replay CLI and an actual TFStreamer partial-failure/recovery chain; source4efa's original19-test result remains in preserved v2 receipts.
- Complete inference suite: 71 tests,0 failures/errors/skips/xfail reports. The two new TF observation tests compare off/on generation parameters and stream, and retain original generation_failure with truthful failed observation.
- Unchanged serving suite: 17 tests,0 failures/errors/skips; unchanged compatibility suite: 16 tests,0 failures/errors/skips.
- Local interpreter: existing Python3.14/aiohttp3.12.15/pytest8.4.2; dependencies were read-only and nothing installed. Actual3.10 is explicitly required by the new CI step and future independent Linux stage; local green does not substitute for it.
- Standard plot smoke: existing system Python3.9.6/matplotlib3.9.0 produced standalone SVGs from the explicitly labelled injected CPU HTTP fixture, with task-owned font cache. These are not GPU curves or performance results.
- 27 recorded TDD/verification slices preserve their raw failures and fixes externally, including the independent-review findings. Raw Builder manifest SHA256 `f78883220b6496d89688c21b7f2d2cb57b4067e30829b0e953463c1ff4afa562`; the Master external SOURCE Handoff binds its path/complete source SHA. R private probe source stays outside candidate.

Only the default-off TF observation, new measurement/control tools, related tests, allowed CI additions and navigation differ from accepted base. App/vLLM/default entry/GoPi/compose/legacy guards and historical Evidence remain unchanged. Server/model/native/POST/CI/push consumption by this Builder is0; the separately recorded R static preflight1 second remains in the global new28 ledger. Runtime8399's original `size` rows and legacy `bytes` rows are normalized without dropping files; full actual cached closure remains a future scoped CPU check.
