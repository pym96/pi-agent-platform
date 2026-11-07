# Pi #13 load measurement (Product, opt-in)

`load.py point` records complete lifecycle, never treating HTTP 202 as inference completion. Paths: direct strict model SSE or platform task POST→SSE→durable history. Closed workers wait for terminal. Open arrivals use absolute offsets, max-inflight32, explicit lag/drop and bounded drain. No automatic retries.

`python3 -m unittest discover -s service/scripts/pi-qwen-load -v` exercises actual HTTP/CLI behavior. Synthetic-only `--max-inflight 2` makes generator saturation testable; real workloads require32. `load.py recompute --out DIR --anchor EXTERNAL_SHA256` verifies sealed original frames and ledger agreement before statistics. No-content/terminal censoring remains unknown; usage comes from native terminal, not chunks. P95 uses nearest rank and is exploratory at20 planned samples.

`campaign.py --stage pilot` runs platform3, captures full actual mapped payload, then direct3 identical replay. Last two direct terminal durations define Rb. `--stage freeze --pilot PILOT` creates the complete immutable12-point formal plan before its separate Master GO. `--stage formal --plan FROZEN_PLAN` executes it; unrun rows remain with reasons. CSV and SVG are derived artifacts, not physical GPU capacity or SLO evidence.

`launch.py --go EXTERNAL_JSON` checks exact source/config/binary/launcher/watch identities, two fresh GPU0-empty observations and preexisting project exclusion. A separately started foreground `watch.py` must precede model startup. Native inference deadline and max-attempts remain enforced. Existing serialized execution/queue2s/generation30s/Pi45s/Go60s policies remain unchanged. Collectors never bypass final owned cleanup. Images/models/deps/SDK are read-only cached dependencies; server new files stay in the approved #13 root. The supplied compose is opt-in only.

`LOAD_TRACE` adds model-local payload/queue/execute spans only when set. Clock domains remain distinct. First-request cold state, all pilot calls, collector overhead, failures and actual output lengths must be reported separately. Hey/Vegeta HTTP controls do not measure durable platform completion.
