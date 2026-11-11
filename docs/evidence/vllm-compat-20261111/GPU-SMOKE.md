# Nov11 双侧 GPU smoke（最终 Verdict 待完成）

Builder 在原物理GPU0、driver535.309.01、原Qwen3-8B snapshot和完整152运行时上完成一次真实生成：31个输入token、16个输出token，文本为`1,2,3,4,5,6,7,8,`，finish_reason为length。该结果只覆盖固定BF16/TP1/eager/context1024/maxseq1/prefixoff/greedy配置，不是吞吐、C10K、并发容量或模型质量结果。独立Regulator也已完成自己的实际生成，最终完整SHA Handoff/CI/独立G0 Verdict仍待完成。

## 失败、诊断和修正分别保留

[首次GPU原件](gpu-smoke01-summary.json)在90b源码下于CUDA初始化报Error804，模型构造失败、generate未调用；其13.581239770秒设备生命周期计入成本。CPU导入和pipcheck没有覆盖真正的CUDA驱动调用。

[单独授权的非初始化诊断](loader01-summary.json)只调用CDLL并读maps/文件摘要。正常设备投射同时提供原生535与compat550，但通用libcuda.so.1链接和实际映射选中了550.54.15，其摘要与compat包相同。原生535.309.01文件已在同容器，摘要与宿主机一致；此时没有调用CUDA API，也没有证明修正后能运行。

修正模块验证已经投射的535精确摘要，在容器私有/tmp下建立0700库选择目录，再启动新解释器使glibc从进程启动时读取受控LD_LIBRARY_PATH。非初始化门核对实际映射后，再exec新的原模型进程。没有改宿主机/镜像的链接、共享驱动、安装环境或模型。新增模块、launcher和测试的执行身份见[源码/运行时映射](source-execution-map.v3.json)。

第一次源码修复0e41仍有tuple模型摘要键及deleted-map漏检，被R实际预检打回，没有单独成为远端候选HEAD或CI目标；它作为后续d803的祖先保留在Git历史中。Builder补red再修到d803；R独立负向及[CI3](CI-SOURCE.json)通过后才获新GPU GO。旧失败和测试记录在外部冻结包保留。

## 本次原生结果与限制

[完整B结果](gpu-smoke02-summary.json)、[输入/配置](gpu-smoke02-input.json)、[原生输出](gpu-smoke02-generation.json)、[driver门](gpu-smoke02-driver-selection.json)、[原始日志](gpu-smoke02-native.log)共同绑定source d803和原运行时8399。运行时由90b生产的身份保持不变，没有为了新source SHA重写安装清单。实际日志显示V1、uni执行路径、FlashAttention、原模型五个权重分片加载、engine ready及非空生成。本次没有再出现804。

日志中的tokenizer fork、IP/Gloo loopback和FlashInfer不可用警告完整保留。独立R读取官方wheel源码后确认greedy分支在top-k/p之前返回torch.argmax；FlashInfer构造期警告不等于改用其他引擎或CPU回退。这是源码分支与实际greedy配置的限定解释，不冒逐kernel追踪。KV缓存容量及日志中的理论并发值也不作为实测服务容量。

缓存基底确实没有C编译器/Python.h，宿主机只读库存发现工具与头文件；本次没有安装、复制或投射它们，固定路径仍完成生成。这个观察不能推广到任意Triton/JIT路径。

## 清理和成本

本次设备生命周期18.713252219秒，native/outer均0、watch0，精确自有容器停止/删除成功。12:16:04.401Z只读终核确认自有容器0、原GPU0无计算PID、6MiB/0util，Builder明确释放。首次失败、无初始化诊断和本次成功合计33.486328255秒，实际生成调用1；[成本账](preparation-cost.json)保留逐次成本及不同历史工单的分账。

原CPU依赖/安装/源码准备在12:11:11截止前停止；之后只执行新的精确GPU GO及本地Evidence整理。Regulator也完成一次31输入/16输出token生成，设备18.630552432秒，独立观察CUDA11.8、V1 uni、RTX4090及父进程CUDA初始化标志false；[报告引用](independent-r-result.json)保留完整限定。双方设备合计52.116880687秒，各1次生成。R的原生执行与清理均早于原截止，但只读archive取回开始晚7.378839秒，单列限制而不抹去。最终独立Verdict尚未给出，本文不宣布G0接受，不晋升项目/简历事实。博客/X正文保持在候选外的私有原件中，[候选指针](PRIVATE-DRAFTS.md)不包含正文。
