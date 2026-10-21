# 潘佳祥

**候选草稿·禁止投递**

上海｜13501632852｜pym66@outlook.com｜github.com/pym96

求职方向：推理服务 Infra 实习生

以流式服务、负载模型和执行边界为重点的候选定位。

## 项目经历

### Pi Agent Platform｜私有候选项目材料

Go / PostgreSQL / Pi / Docker Compose｜Agent协作实施的服务实验，非本人独立实现。

- hey固定并发、Vegeta固定目标速率：54轮共72600次请求均HTTP 200，分开核实际发送与完成率。

- 已提交事件经SSE游标重放；tail缓存可丢弃，旧游标回退SQL，慢写超时断连后可重连。

- 终态与事件同事务提交；单控制实例持锁，两个worker执行，事件读取与控制连接池分离。

- SSE在120s内24次采样均为10000在线订阅；断连后API观测回到0连接、11条goroutine。

测量边界：synthetic端点、单控制实例、最多两个执行者；HTTP history仅两行，非模型吞吐。

SSE仅一次120s采样逻辑订阅；含1000次计划重连、21次服务写失败，不代表TCP不中断或生产容量。

### Workspace Agent Harness

面向不确定Agent执行的Runtime、协议适配与可重算实验｜个人公开项目｜2026.08--至今

- 24个真实Trace上下文完成240-slot协议实验；Strict L3从93/120至一次repair后120/120。

- 五个failure-enriched上下文、四档输出上限共100次调用；L3为2/25→4/25→4/25→5/25。

- TUI从保留事件零模型/工具调用回放，取消只记一个终态；c2c9e33基线仓库测试116/116。

实验边界：固定语料、模型与时间窗；无repair含2048-token上限，不是provider普遍可靠性或任务成绩。

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
