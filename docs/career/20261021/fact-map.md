# 事实—句子—来源—贡献归属

本映射是候选编辑索引，不是事实账本，不晋升任何新事实。事实句的精确文本另见[claims.json](claims.json)，三版的使用清单也在该JSON。每份PDF的姓名/联系/教育/技能/公开输出对应B01/B02/E01/S01/S02/O01；岗位标题与一句定位摘要是Human要求下的求职目标，不是历史任职或能力认证。警示/页脚是交付状态说明，不是业绩主张。

## 来源定位

- F-*：[根事实账本的只读快照](source-snapshots/事实账本.md)，以ID检索；披露边界跟随同一条事实，不因改写消失。[现实版快照](source-snapshots/现实版.md)支持现行已批准表述。[风格与画像](source-snapshots/profile.md)仅作风格输入，其中C/未登记事实不能入稿。
- P01：[服务架构/恢复](../../../service/README.md)。P03：[store](../../../service/internal/store/store.go)、[executor](../../../service/internal/executor/executor.go)、[main](../../../service/cmd/service/main.go)。P04：[Compose](../../../service/compose.yaml)。均沿用accepted基线f1d172dda9e578cd1ff773363b14f03ff0a1d18d，候选未改业务。
- P02：[hey/Vegeta原报告](../../evidence/hey-vegeta-20261020.md)，Workload、Results、Resources及Attribution；原报告中的Builder候选措辞保留历史身份，最终accepted由P06证明。
- P05：[#1 accepted Verdict](https://github.com/pym96/pi-agent-platform/issues/1#issuecomment-6244826312)，ef176befbd63f0c89d57505b9ed5576a939401d7。P06：[#3 accepted Verdict](https://github.com/pym96/pi-agent-platform/issues/3#issuecomment-6291285634)，f1d172dda9e578cd1ff773363b14f03ff0a1d18d；不是Human独立实现或披露批准。
- DeepSeek/基础机制仅在[研究附件](research/README.md)与[来源清单](research/来源清单.md)，没有被写成简历经历或熟练技能。官方源码commit与硬件要求保持原研究身份。

## 逐句映射

| ID | PDF / Markdown中的事实句 | 支持来源 | 贡献归属 | 披露状态 |
| --- | --- | --- | --- | --- |
| B01 | 潘佳祥 | F-BASIC-01 | Human | 已批准A/B原子事实改写 |
| B02 | 上海｜13501632852｜pym66@outlook.com｜github.com/pym96 | F-BASIC-01/02 | Human | 已批准A/B原子事实改写 |
| E01 | 上海大学｜控制科学与工程｜硕士｜2025.09--2028.06｜GPA 3.76/4.00 | F-EDU-01；现实版教育栏 | Human | 已批准A/B原子事实改写 |
| S01 | 编程与工程：Python、C++、ROS1、Git、unittest、JSON/JSONL | F-SKILL-01 | Human有可归属产物；不外推熟练度 | 已批准A/B原子事实改写 |
| S02 | Agent：Agent Runtime、Tool Calling、JSON Schema、Trace、Evaluation | F-AGENT-04/08/12/13；现实版技能栏 | Human已批准项目事实范围 | 已批准A/B原子事实改写 |
| O01 | GitHub 个人非 Fork 仓库累计 100+ stars。 | F-SKILL-02；2026-08-26历史登记口径 | Human账号历史快照，不声称当日新核 | 已批准A/B原子事实改写 |
| P00 | Go / PostgreSQL / Pi / Docker Compose｜Agent协作实施的服务实验，非本人独立实现。 | P01/P02/P04/P05/P06 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| PL1 | 测量边界：synthetic端点、单控制实例、最多两个执行者；HTTP history仅两行，非模型吞吐。 | P01/P02 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| PL2 | SSE仅一次120s采样逻辑订阅；含1000次计划重连、21次服务写失败，不代表TCP不中断或生产容量。 | P02 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| P01a | PG保存任务与有序事件，幂等键区分重复提交；未知执行阻断会话，不自动重发模型请求。 | P01/P03/P05 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| P01b | 终态与事件同事务提交；单控制实例持锁，两个worker执行，事件读取与控制连接池分离。 | P01/P03/P05 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| P01c | Compose分离API、PG、Pi与负载端，合计4 CPU / 8 GiB硬配额；数据卷独立、端口仅loopback。 | P01/P02/P04 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| P02a | hey固定并发、Vegeta固定目标速率：54轮共72600次请求均HTTP 200，分开核实际发送与完成率。 | P02/P06 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| P02b | SSE在120s内24次采样均为10000在线订阅；断连后API观测回到0连接、11条goroutine。 | P02/P06 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| P01d | 已提交事件经SSE游标重放；tail缓存可丢弃，旧游标回退SQL，慢写超时断连后可重连。 | P01/P03/P05 | Human定目标/资源约束；Builder Agent实现/执行；Regulator独立复核；上游Pi/Go/PG/工具提供组件 | 新增Pi事实，项目已accepted；待Human逐句批准披露，禁止投递 |
| A00 | 面向不确定Agent执行的Runtime、协议适配与可重算实验｜个人公开项目｜2026.08--至今 | F-AGENT-01/04；现实版项目日期 | 已批准Human项目表述；不推导全部代码个人独立实现 | 已批准A/B原子事实改写 |
| A01 | 权限取Runtime、caller与Pack交集；evaluator在有界独立进程运行，错误不改写执行终态。 | F-AGENT-06/07 | Human已批准项目事实；不声称OS安全沙盒 | 已批准A/B原子事实改写 |
| A02 | 离线typed-history Adapter校验关联；事件化AgentLoop先验证动作，再写有序事件与唯一终态。 | F-AGENT-12/13 | Human已批准项目事实，非实时provider兼容声明 | 已批准A/B原子事实改写 |
| A03 | 24个真实Trace上下文完成240-slot协议实验；Strict L3从93/120至一次repair后120/120。 | F-AGENT-08/09 | Human已批准实验原子含义 | 已批准A/B原子事实改写 |
| A04 | 五个failure-enriched上下文、四档输出上限共100次调用；L3为2/25→4/25→4/25→5/25。 | F-AGENT-10/11 | Human已批准实验原子含义 | 已批准A/B原子事实改写 |
| A05 | TUI从保留事件零模型/工具调用回放，取消只记一个终态；c2c9e33基线仓库测试116/116。 | F-AGENT-14/15 | Human已批准软件行为事实，非LLM任务成功数 | 已批准A/B原子事实改写 |
| AL1 | 实验边界：固定语料、模型与时间窗；无repair含2048-token上限，不是provider普遍可靠性或任务成绩。 | F-AGENT-08/09/10/11 | Human已批准实验披露边界 | 已批准A/B原子事实改写 |
| R00 | RoboMaster自动瞄准与自主哨兵｜主要提交者｜2023.06--2024.07 | F-RM-01/02；现实版 | Human可归属Git identity，不声称队长或全部原创 | 已批准A/B原子事实改写 |
| R01 | Git identity覆盖MA_Sentry的179/188与MA_training的144/144提交；包含PnP、串口与ROS工程。 | F-RM-01/02 | Human可归属提交；不声称全部代码原创 | 已批准A/B原子事实改写 |

## 各版取舍

- 01平台可靠性Infra：以任务状态、失败恢复和受控负载为重点的候选定位。 使用事实ID：B01, B02, P00, P01a, P01b, P01c, P02a, P02b, PL1, PL2, A00, A01, A02, A05, R00, R01, E01, S01, S02, O01。
- 02推理服务Infra：以流式服务、负载模型和执行边界为重点的候选定位。 使用事实ID：B01, B02, P00, P02a, P01d, P01b, P02b, PL1, PL2, A00, A03, A04, A05, AL1, R00, R01, E01, S01, S02, O01。
- 03Agent应用开发：以执行契约、协议适配、Trace与实验有效性为重点的候选定位。 使用事实ID：B01, B02, A00, A02, A01, A03, A04, A05, AL1, P00, P01a, P01d, PL1, R00, R01, E01, S01, S02, O01。

## 贡献和追问边界

已批准Harness与RoboMaster表达沿用原账本，并不额外证明每行代码由本人独立实现。Pi由Human提出目标与资源约束，Master冻结工单，Builder Agent实现和运行，Regulator独立复核；上游Pi、Go/PG、hey/Vegeta各保留组件贡献。岗位对个人能力的判断需本人解释与操作证据，候选包不替代此步骤。

优先追问：为何unknown不重试、PG事务不能包住模型副作用；为何固定并发与固定目标速率不同；为何万级订阅不等于万级模型；为何2048-token ceiling限制repair对比的因果解释。具体学习动作在研究附件，不新增运行授权。

[返回候选包](README.md)
