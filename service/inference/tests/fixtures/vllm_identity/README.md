# Official vLLM identity fixture

The three files listed in [provenance.json](provenance.json) are byte-for-byte extracts from the official `vllm-0.8.5.post1+cu118-cp38-abi3-manylinux1_x86_64.whl`, SHA256 `a593a2e5f455b0e47bf297ea31153dad9c2b2c44ddb13e194ba0a247e597e34a`.

[Version source](vllm/_version.py) sets module `__version__` to `0.8.5.post1`; [version loader](vllm/version.py) imports it. Distribution [METADATA](vllm-0.8.5.post1+cu118.dist-info/METADATA) instead contains `0.8.5.post1+cu118`. The CPU test executes those real version modules and resolves the real distribution metadata with `importlib.metadata`.

The package root, native argument class, engine factory, tokenizer and generation engine remain explicit CPU seams. This fixture does not import the entire Linux native package, initialize CUDA or construct a real model. It corrects the previous hand-written fake module version that concealed the startup defect. A separate authorized Linux CPU import and real GPU run remain necessary.
