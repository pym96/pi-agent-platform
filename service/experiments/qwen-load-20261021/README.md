# Qwen真实推理实验（opt-in）

WorkOrder：[Pi #7](https://github.com/pym96/pi-agent-platform/issues/7)。只运行实验脚本，不改变现有服务或默认回归。

- `measure.py`：保存逐请求及原始SSE行，严格区分完成、partial、timeout和发生器drop。
- `matrix.py`：串行closed1/2/4/8/16/32×2，再冻结Rb衍生的open速率×2；各45秒发起窗口/最多60秒drain。
- `report.py`：直接从原件复算nearest-rank分位数并输出CSV/JSON/PNG/SVG。
- `test_measure.py`：测量语义负向检查。
- `transformers_server.py`：只有明确选用fallback时运行；单个活动generate调用、FIFO锁等待，无batching或前缀缓存；不称作vLLM容量。
- `freeze.py` / `inventory.py`：CPU锁定完整模型/实际依赖版本、语料与文件哈希。
- `launch.sh`：仅Master阶段B激活后启动；两次空闲检查、固定UUID/镜像与硬资源上限。
- `observe.py`：采样GPU与容器资源，发现同卡无关计算或到期时只停本轮自有容器。

环境/模型/语料/运行代码身份须先冻结。结果状态及全部证据见[本轮Evidence](../../../docs/evidence/qwen-load-20261021/README.md)。
