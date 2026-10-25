# Opt-in Nginx configurations

`platform.conf` proxies one stateful Go controller. `lab.conf` round-robins two labelled stateless fixtures with a single worker. Both disable buffering and upstream retry. These private CPU profiles do not provide authentication, public deployment or GPU-aware scheduling.

Use the [bounded entry guide](../scripts/nginx-entry/README.md). The original default Compose file is unchanged.
