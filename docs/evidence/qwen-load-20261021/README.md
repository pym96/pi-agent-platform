# Qwen推理负载曲线｜Pi #7

状态：Builder已完成18轮正式真实模型矩阵及清理，候选待独立Regulator复核；不是独立accepted或简历披露批准。

[兼容与启动修正记录](compatibility-case.md)保留失败判断、原因与限制；[时序负向回归](parser-timing-tests.log)覆盖独立Regulator在准备期提出的矛盾时钟反例。

正式运行源码固定为`601918edd4198e32e6940fbab3e2d5a2ba6095b5`，config SHA256为`4e2fb31edbf480f7d74ddc6b42e09ab1bd9ef928642d11ac233a2a13b2274a67`；模型/GPU已于08:56:23Z停止。后分析代码`8c22f4a5893c8c3abbfe0381f025f63db7374276`按Master窄修复授权强化usage非空对象/128上限及明确图注；[16项测试](post-run-analysis-tests.log)通过，[一致性回执](analysis-comparison.json)确认325条实际记录、全部18份原summary和Rb/速率计划不变。原件、速率计划和执行身份保留。

[完整报告](REPORT.md)包含各rep吞吐、P50/P95/P99、n/缺失/失败分层和限制；[图表/CSV/JSON](results/README.md)可直接查看。[原件库存](raw-manifest.json)索引3472件/137352039bytes，完整server副本已逐件核对；[辅助边界采样](boundary-health-receipt.json)保留首轮边界缺失。[compare-analysis.py](compare-analysis.py)可复算执行源与后分析源。[私有博客/X草稿](private-writing-drafts.md)未发布。

合同：[WorkOrder #7](https://github.com/pym96/pi-agent-platform/issues/7)，Criteria1.1。实现入口：[实验脚本](../../../service/experiments/qwen-load-20261021/README.md)。现有Go/Pi业务与默认synthetic端点保持原状；本轮先测引擎直连。

选择：已有只读Qwen3-8B缓存，官方revision `b968826d9c46dd6066d109eabc6255188de91218`。候选引擎为固定CUDA12.1镜像中的PyTorch2.5.1 + 隔离Transformers4.51.3。其调度为**单个活动generate调用，FIFO等待，不做batching/前缀缓存**。这不能称为vLLM/continuous-batching容量。

GPU3在08:20Z后释放，两次间隔10秒检查通过后按既有授权启动。GPU2有无关计算任务；0/1未使用。实际单卡隔离、共享主机，[有效配置](effective-config.json)区分客户端seed/temperature元数据与后端实际greedy硬编码设置。

模型/语料/依赖/image锁已落盘。原始SSE、资源、失败、启动和清理原件位于本轮专属server目录与本地`~/.local/state/pi-agent-platform/qwen7-builder-20261021/server-mirror/`，详见manifest。[pre-run-lock](pre-run-lock.json)是启动前阶段冻结快照，stage字段不作当前状态。所有结果待独立复算，不晋升简历事实或Human掌握。

预登记：closed并发1/2/4/8/16/32各2rep；open速率由最大closed窗口完成数/45作0.5/1/1.5倍、精确half-up至0.001并下限0.01，各2rep。45秒半开发起/完成窗口，最多60秒drain；105秒后事件不纳入。TTFT覆盖所有有效非空首内容观测（另列成功/失败分母），E2E只覆盖完整成功；空delta、HTTP200、缺终态或损坏usage均不能算成功。实际prompt242tokens，输出上限128但按真实生成ID计数。
