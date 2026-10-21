# 潘佳祥

**候选草稿·禁止投递**

上海｜13501632852｜pym66@outlook.com｜github.com/pym96

求职方向：平台可靠性 Infra 实习生

以任务状态、失败恢复和受控负载为重点的候选定位。

## 项目经历

### Pi Agent Platform｜私有候选项目材料

Go / PostgreSQL / Pi / Docker Compose｜Agent协作实施的服务实验，非本人独立实现。

- PG保存任务与有序事件，幂等键区分重复提交；未知执行阻断会话，不自动重发模型请求。

- 终态与事件同事务提交；单控制实例持锁，两个worker执行，事件读取与控制连接池分离。

- Compose分离API、PG、Pi与负载端，合计4 CPU / 8 GiB硬配额；数据卷独立、端口仅loopback。

- hey固定并发、Vegeta固定目标速率：54轮共72600次请求均HTTP 200，分开核实际发送与完成率。

- SSE在120s内24次采样均为10000在线订阅；断连后API观测回到0连接、11条goroutine。

测量边界：synthetic端点、单控制实例、最多两个执行者；HTTP history仅两行，非模型吞吐。

SSE仅一次120s采样逻辑订阅；含1000次计划重连、21次服务写失败，不代表TCP不中断或生产容量。

### Workspace Agent Harness

面向不确定Agent执行的Runtime、协议适配与可重算实验｜个人公开项目｜2026.08--至今

- 权限取Runtime、caller与Pack交集；evaluator在有界独立进程运行，错误不改写执行终态。

- 离线typed-history Adapter校验关联；事件化AgentLoop先验证动作，再写有序事件与唯一终态。

- TUI从保留事件零模型/工具调用回放，取消只记一个终态；c2c9e33基线仓库测试116/116。

### RoboMaster

RoboMaster自动瞄准与自主哨兵｜主要提交者｜2023.06--2024.07

- Git identity覆盖MA_Sentry的179/188与MA_training的144/144提交；包含PnP、串口与ROS工程。

## 教育背景

上海大学｜控制科学与工程｜硕士｜2025.09--2028.06｜GPA 3.76/4.00

## 技能

编程与工程：Python、C++、ROS1、Git、unittest、JSON/JSONL

Agent：Agent Runtime、Tool Calling、JSON Schema、Trace、Evaluation

## 公开输出

GitHub 个人非 Fork 仓库累计 100+ stars。

新增Pi项目句子待本人披露批准；本稿仅供内部评审。
