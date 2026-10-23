# Private draft: Pi said “done”, but the upstream usage was missing

Human's next step was concrete: connect the existing Go/Pi task platform to local Qwen before measuring high load. The existing worker treated a Pi result as completed. That seemed plausible because Pi already owned the model protocol.

The independent reviewer challenged that assumption. The Builder ran actual Pi1.3.0 against a CPU endpoint that returned text, a stop marker and DONE, but no usage. Pi produced a result and filled usage with zeros. Accepting that result would have hidden a broken exchange behind a valid-looking task terminal.

The Builder added a Qwen-only bridge that checks the original upstream stream. It forwards text while generation proceeds and releases the final markers after valid finish, usage, DONE and EOF. Go records completed only after the whole Pi response passes validation and the terminal transaction succeeds. The PostgreSQL completed event gives clients a durable terminal distinct from provisional Pi output.

A small positive test uncovered a separate SDK assumption. Pi's simple request helper reserves4096 tokens before estimating output room. Registering our1024-token experimental context reduced the request to one output token. The Builder used the SDK's public explicit-stream interface, keeping the real context declaration and the backend's exact tokenizer check. This avoids inflating the advertised context just to satisfy an estimator.

The CPU chain now checks context restoration, idempotent submission and SSE reconnect. A deliberate missing-DONE bug makes the required entry fail. These checks establish protocol behavior; GPU throughput and latency still need a separately bound real run.

Human chose the learning problem; Master scoped the experiment; the Builder implemented this candidate; the Regulator's challenge exposed the usage risk. The upstream SDK and inference libraries supply their implementations. Publication is not authorized, and this draft awaits independent candidate review.

Sources: [original actual wire](initial-sdk-wire-red.json), [case record](compatibility-case.md), [WorkOrder12](https://github.com/pym96/pi-agent-platform/issues/12). Final candidate SHA and real-stage receipts will be added through the handoff rather than invented here.

## X draft (unpublished)

While connecting a durable Pi task platform to local Qwen, our CPU probe found Pi1.3.0 could emit a result with zero-filled usage when upstream usage was absent. The candidate now checks raw finish/usage/DONE before success, while forwarding text as it arrives. CPU protocol evidence so far; no GPU performance claim. Built with Agent assistance; independent review pending.
