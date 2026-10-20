#!/bin/sh
# Run on the owned Linux host from service/, after syncing the frozen source.
set -eu
: "${RUN_ROOT:?}" "${NODE_ROOT:?}" "${GO_ROOT:?}" "${PRIOR_CACHE:?}"
mkdir -p "$RUN_ROOT/evidence" "$RUN_ROOT/cache" bin
df -Pk "$RUN_ROOT" > "$RUN_ROOT/evidence/disk.txt"
[ "$(df -Pk "$RUN_ROOT" | awk 'NR==2 {print $4}')" -ge 20971520 ]
ulimit -n > "$RUN_ROOT/evidence/host-nofile.txt"
docker run --rm --name pi-hv3-build --network none --cpus 1 --memory 1g \
 -v "$PWD:/source" -v "$RUN_ROOT/cache:/cache" -v "$PRIOR_CACHE:/prior:ro" \
 -v "$GO_ROOT:/go:ro" -v "$NODE_ROOT:/node:ro" \
 -e GOROOT=/go -e GOPATH=/cache/gopath -e GOCACHE=/cache/go-build \
 -e GOTOOLCHAIN=local -e GOENV=off -e CGO_ENABLED=0 -e GOMAXPROCS=1 \
 -e npm_config_cache=/cache/npm -e PATH=/node/bin:/go/bin:/usr/bin:/bin \
 -w /source --entrypoint /bin/sh \
 python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
 -c 'cp -a /prior/gopath /cache/; cp -a /prior/npm /cache/; go build -p 1 -trimpath -o bin/service ./cmd/service; go build -p 1 -trimpath -o bin/load ./cmd/load; npm ci --prefix pi --ignore-scripts --offline; go test -p 1 ./...'
