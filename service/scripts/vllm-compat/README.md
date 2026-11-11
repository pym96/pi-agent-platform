# Isolated vLLM compatibility tooling (#21)

Product preflight tooling; opt-in only. It does not change the default Go/Pi/Transformers backend.

`lock.py LOCK WHEEL_DIRECTORY` checks the complete fixed-version official wheel closure, byte hashes, metadata and download bounds before installation. The xformers URL identifies its CUDA11.8 variant; its generic version alone is insufficient. No complete actual wheel closure has been produced by the November10 attempt yet.

`python -m unittest discover -s service/scripts/vllm-compat -v` exercises real CLI GO rejection, exact-owned CPU child cleanup, foreign-process preservation and wheel corruption/source rejection. Wheel fixtures and Docker adapters are synthetic CPU tests, never model compatibility evidence.

`launch.py --go EXTERNAL_JSON --go-sha256 HASH` is separately gated. It checks clean source, complete installed-file manifest, original model bytes, exact cached image, role/root ownership, fresh empty physical GPU0 twice ten seconds apart and single-use nonce. It requires an independent exact-CID watchdog readiness receipt before starting its single bounded offline process. Native timeout and watchdog share the absolute deadline; unknown native/cleanup outcomes remain failures. The manifest, source/probe/watch hashes, original model-manifest hash and physical UUID must be bound in a new Master GO. This launcher has CPU negative evidence only; actual container/CUDA compatibility remains unverified.

`smoke.py` performs one real offline generation, nonthinking greedy, BF16/context1024/TP1/eager/maxseq1/prefix cache off, at most16 tokens. It must run inside the read-only model/runtime container only after fresh precise GPU authorization. Parent code does not initialize CUDA first. The November10 attempt did not run it; November11 remains separately gated.

The independent Regulator's probes and logs remain outside this candidate. See [attempt evidence](../../../docs/evidence/vllm-compat-20261111/README.md). G0 requires actual Builder and independent Regulator generation; CPU tests/download metadata do not establish compatibility.

November11 uses roots `21-vllm-compat-20261111/{builder,regulator}`, projects `pi-vllm21-n11-b/r`, at most8CPU/24GiB per active container, absolute stop17:51:11Z and separate role start ceilings. A single new GO allows at most300seconds Builder or180seconds Regulator, within cumulative WorkOrder budgets. Importing the smoke probe has no runtime/model side effects; actual execution is protected by its main guard.

`native.py` computes the absolute engine timeout inside the container immediately before GNU timeout starts, leaving15seconds for cleanup; late or nonfinite deadlines reject before executing the model command. The independent watchdog uses the same earlier engine deadline. HOME/XDG/Triton/TorchInductor caches live under bounded `/tmp`, while weights/runtime/source are read-only.

`driver.py` is the SC-LOADER-N11-07 process-local selection module. It verifies the already projected native535.309.01 SHA, creates new private0700 links under container/tmp, then execs a fresh interpreter with that directory first in LD_LIBRARY_PATH. A non-init CDLL/maps gate requires the exact native path/hash before execing the original smoke in another fresh interpreter. Missing/mismatched bytes, unsafe directories, preload, wrong mappings or exec failure stop without a550 fallback. The new GO binds driver_sha256. No host/image driver symlinks, extra mounts, runtime wheels or default service paths change. CPU fixtures verify selection guards and fresh-process environment; actual loader selection and CUDA/model success require a new precise GPU GO. Runtime manifest8399 remains the unchanged152 environment produced under90b; corrected source is mapped separately.
