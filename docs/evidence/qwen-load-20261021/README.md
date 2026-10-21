# Qwen推理负载曲线｜Pi #7

状态：Builder准备阶段；尚无正式GPU运行、性能曲线或独立Verdict。

合同：[WorkOrder #7](https://github.com/pym96/pi-agent-platform/issues/7)，Criteria1.1。实现入口：[实验脚本](../../../service/experiments/qwen-load-20261021/README.md)。现有Go/Pi业务与默认synthetic端点保持原状；本轮先测引擎直连。

选择：已有只读Qwen3-8B缓存，官方revision `b968826d9c46dd6066d109eabc6255188de91218`。候选引擎为固定CUDA12.1镜像中的PyTorch2.5.1 + 隔离Transformers4.51.3。其调度为**单个活动generate调用，FIFO等待，不做batching/前缀缓存**。这不能称为vLLM/continuous-batching容量。

已有GPU2/3正在运行无关任务；GPU0/1虽空闲，阶段B仍须获准UUID与二次空闲检查。硬件共享背景负载会保留，不能把单卡隔离写成整机独占。

模型与语料/依赖准备文件将在锁版时进入本目录；正式运行原始SSE、资源观测、失败和清理回执按manifest索引。原件位于本轮专属server目录与本地 `~/.local/state/pi-agent-platform/qwen7-builder-20261021/`。冻结代码后追加报告不改变执行代码身份。所有结果待独立Regulator复算，不晋升简历事实或Human掌握。

预登记：closed并发1/2/4/8/16/32各2rep；open速率由最大closed窗口完成数/45作0.5/1/1.5倍、精确half-up至0.001并下限0.01，各2rep。45秒半开发起/完成窗口，最多60秒drain；105秒后事件不纳入。TTFT覆盖所有有效非空首内容观测（另列成功/失败分母），E2E只覆盖完整成功；空delta、HTTP200、缺终态或损坏usage均不能算成功。实际prompt242tokens，输出上限128但按真实生成ID计数。
