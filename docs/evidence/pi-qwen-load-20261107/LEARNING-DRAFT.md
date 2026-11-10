# 测量脚本怎样把推理服务锁住了

私有学习草稿，状态截至本轮 CPU 修复；真实负载结果另随执行记录补充。源记录：[#13 Activation](https://github.com/pym96/pi-agent-platform/issues/13#issuecomment-6700840007)、[CPU-ready Handoff](https://github.com/pym96/pi-agent-platform/issues/13#issuecomment-6701019072)、[集中修复 GO](https://github.com/pym96/pi-agent-platform/issues/13#issuecomment-6701071798)、[修复交接](https://github.com/pym96/pi-agent-platform/issues/13#issuecomment-6701153936)。运行源 a9e838ea90c59a0b43aa32c562efb0782fff1cad 与修复394e4f15a821ab969a104aae7f8803d3efd3ef72各自保留。

Human 希望用本地 Qwen 和 Pi 平台学习吞吐、排队与尾延迟，并提出显存和 Go 编排可能影响成本。Master 冻结两条链路、相同输入和有界预算。Builder 实现测量工具；独立 Regulator 设计故障反例。此稿记录 Agent 的工作，不能写成 Human 亲自独立实现。

推理后端原有一把串行锁。请求拿锁后启动生成任务，结束时先等待生成任务退出，再释放锁。Builder 为测量等待和执行时间加入显式开启的 trace 文件。最初只保护了最后一次 trace 写入，却让前面的 `await worker` 留在保护范围外。

Regulator 在第一个流结束时把 trace 目标变成目录。生成任务的收尾写入抛异常，`await worker` 把异常向上传递，释放锁的语句没有执行。Regulator 恢复文件后发第二个请求，得到503 queue_deadline；后端active为0、生成次数仍为1。这组证据把原因从“GPU仍忙”收敛到“软件保留了空闲槽的所有权”。

Builder 把取消、生成任务收尾和 trace 异常放进最外层 `try/finally`。服务仍等待生成任务退出后才释放槽。提前释放虽然能绕过泄漏，却会让尚在执行的生成任务与新请求重叠，改变原串行策略。修复后原反例第二个请求返回200，生成次数为2；第一请求的流错误仍保留，不能把恢复能力写成第一请求成功。

同轮还出现两个测量问题。Regulator 用持续 keepalive 证明，逐次 socket read 的超时会随读操作重置，超过整点截止约0.95秒；Builder 加入整个响应的截止关闭机制，原探针复跑超过截止约0.006秒，探针声明的系统调用/调度容差为0.1秒。这个容差只属于 CPU 故障探针，不是服务延迟承诺。

随后 CI2 的慢流测试失败。日志显示实际状态为 generator_drop。测试用了 rate100、count1，开放窗口只有10ms；Linux runner 还未准备好发送，窗口就结束了。测试没有进入它想验证的阻塞读路径。Builder 按 Master 窄修指令把该测试改成 rate1、drain0.2，并让滴流持续超过1.2秒。原 CI 失败保留；最终同 SHA CI 和独立复核仍是完成条件。

这些 CPU 结果支持收尾与测量契约的判断。GPU 吞吐、稳定 P95、4090 物理峰值和优化收益都需要实际曲线才能讨论。后续可让 Human 解释一条真实 trace：哪个状态拥有串行槽，哪个事件证明它已经释放，以及何种证据能区分显存压力、软件串行策略和客户端发送不足。

## X 草稿，未发布

给 Qwen 推理服务加 trace 时，Builder 把日志 I/O 异常留在了锁释放保护之外。独立复核把日志目标改成目录：第一个流失败，恢复日志后第二个请求仍503，而后端active已经是0。修复让 worker 收尾与异常传播都经过最外层 finally。原反例随后恢复，第一请求的错误仍保留。这里验证的是资源收尾；吞吐与 P95 要等真实负载证据。Human 提供项目目标，Agent 实现并独立复核。
