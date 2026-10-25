# Pi #15：私有 Nginx 入口与分流实验

状态：Builder 候选自检通过，待独立 Regulator。Issue15，Criteria NG1.1；最终候选完整SHA、draft PR和同SHA CI回执以外部Handoff绑定，本文不自授accepted。

## 结果与边界

本轮新增显式可选的 Nginx → 单 Go 控制器入口，保留原默认 Compose 与 PostgreSQL singleton。实际平台链路使用锁版Pi1.3.0和确定性synthetic model；独立lab的两个后端只是无状态fixture。未调用GPU、Qwen或付费模型，未运行公网服务和C10K测试。

完整server执行源码为 `ae0764d140cc2d8b6a089e77eb90d6cc2214b1cb`，run-06；其后候选仅补Evidence、导航、静态图注和main同路径CPU CI触发，不改本次测量算法或平台运行配置。Nginx/Go/Pi/测量入口与config在此执行身份冻结；最终同SHA CPU CI另作复核。Nginx1.28.0官方镜像执行身份 `nginx@sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284`；实际effective config、版本、镜像和Docker inspect原件均保留。

run-06原件清单SHA256：`2e3f1890170d1f9c4e4343feb0014572bb06ae909f9baba67550081732198ad9`。

## 完整CPU与协议自检

- Go：5个实际测试通过，包含专属新空库上的TestDurableAdmissionAndRecovery；`-race -count=1`，零测试级skip。两个无测试文件包的包级skip另列，不能替代必需测试。
- 基线inference全部CPU pytest：49通过，零skip；[原始summary](raw/run-06/inference/summary.json)。
- 新测量/回执单测：8通过，覆盖未成功分母、零成功undefined、额外回执拒绝、nanosecond时间、Go必需PG/空测试、hey调度规则及少一条仍missing。
- 实际SDK平台：3通过。代理新任务、跨直连/代理同key身份、冲突409、持久历史逐字段、SSE完整事件与Last-Event-ID重连、边界输入、客户端断开后durable任务完成、synthetic失败interrupted/后续429均有HTTP/SSE原件。
- 第二控制器非零singleton拒绝；拒绝前后所有task/event/session快照相同，第一实例继续healthy。
- lab：4通过。12个顺序请求覆盖A/B并严格交替；收件ID守恒；完整marker到达后才独立release，原件顺序marker→release→terminal；POST已接收后断响应仅收件一次且返回502；故障503、恢复和截断可见。

平台SSE持续开放，客户端按截止事件停止读取，不等EOF。断开订阅不代表取消任务。独立R仍需在干净候选补缓冲、POST重复、游标、原件删条/重复/零成功等负向；Builder的自检不是最终Verdict。

## 预登记HTTP矩阵

| 工具 | 路径 | 负载 | 配置意图 / 安排 / 收件 | HTTP成功 / 错误 | 完成 req/s | P95 ms |
|---|---|---:|---:|---:|---:|---:|
| hey | direct | 1 | 300 / 300 / 300 | 300 / 0 | 5376.34 | 0.200 |
| hey | direct | 8 | 300 / 296 / 296 | 296 / 0 | 13333.33 | 1.000 |
| hey | direct | 32 | 300 / 288 / 288 | 288 / 0 | 6889.95 | 30.400 |
| hey | proxy | 1 | 300 / 300 / 300 | 300 / 0 | 2544.53 | 0.500 |
| hey | proxy | 8 | 300 / 296 / 296 | 296 / 0 | 6563.19 | 1.600 |
| hey | proxy | 32 | 300 / 288 / 288 | 288 / 0 | 6471.91 | 24.000 |
| vegeta | direct | 10 | 100 / 100 / 100 | 100 / 0 | 10.10 | 1.340 |
| vegeta | direct | 25 | 250 / 250 / 250 | 250 / 0 | 25.10 | 1.148 |
| vegeta | direct | 50 | 500 / 500 / 500 | 500 / 0 | 50.10 | 0.882 |
| vegeta | proxy | 10 | 100 / 100 / 100 | 100 / 0 | 10.10 | 1.725 |
| vegeta | proxy | 25 | 250 / 250 / 250 | 250 / 0 | 25.10 | 1.238 |
| vegeta | proxy | 50 | 500 / 500 / 500 | 500 / 0 | 50.10 | 1.667 |

全12点保持原命令和顺序：hey `-n300`、C1/8/32；Vegeta10/25/50req/s、每点10s，两路径均为GET `/health`。每路径10次warmup单列，点间idle2s，timeout5s，HTTP/1.1/keepalive/no redirects。hey/Vegeta被1CPU/2GiB客户端槽限制，和服务同机；没有重复试验或跨点混池。

配置意图总3500，工具安排3468，观察到3468个HTTP2xx，实际安排回执缺失0、HTTP错误0。32个请求属于hey0.1.4的worker整数除法余数：C8每路径4个未安排，C32每路径12个未安排。**这些未发出请求不算服务成功。**每点同时保留成功/安排、成功/配置意图完成率。依据[该版本官方源码](https://github.com/rakyll/hey/blob/v0.1.4/requester/requester.go#L241-L245)和Master的SC-NG15-HEY-01冻结规则；绝不用收到多少行来反推期望数。

P50/P95从该点成功cohort排序，取第ceil(p*n)项，错误与完整分母并列。hey CSV精度为0.1ms，且没有逐请求自定义ID；hey工具回执与代理日志只作时间区间/计数关联，不能声称逐条join。Vegeta保留binary、decoded、原生report和真实发送/完成窗口；有限first-to-last窗口使50req/s的观测完成率略高于50。Docker调用wall time另列。

[静态吞吐/P95曲线](curves.svg)来自标准matplotlib和原始summary，可由`service/scripts/nginx-entry/plot.py`复画。每点仅一轮，短hey样本受到调度、CPU配额及同机客户端干扰；例如C32代理P95低于直连，不能据此宣布因果改进。HTTP健康请求完成延迟不是模型TTFT，也不能推出Qwen吞吐或大用户容量。

## 失败轨迹与解释修订

| run | 实际执行SHA | 结果及当时影响 |
|---|---|---|
|01|d603c3b9da5e62c7f93df40207b1b4c58cb2416c|构建时Git VCS status128；进程级精确safe.directory修复。平台/任务/矩阵均未开始。|
|02|27f0e81（完整见该run identity）|嵌套bind目标不存在且父源目录只读；预建ignored目录。0任务/0矩阵。|
|03|cf689a752f24df7e85c4343a5f5fb76623310d61|PG/API/Pi启动，但Nginx默认fastcgi temp在只读根不可写；全部临时路径移入tmpfs，提前nginx -t。0任务/0矩阵。|
|04|fe98f8517d34e3dd384f2132f292036d3cfdd3b6|Go实际命令通过，自检误把无Test字段的包级skip当必需测试skip；收窄到测试事件并强制PG测试存在。0平台任务/0矩阵。|
|05|1a2ee6286ca2922f44819666d971cc927dfddc96|平台与原12点实际执行；旧parser把hey未安排余数误记missing/error，完整入口失败、lab未运行。旧raw/summary/failed状态不回写。|
|06|ae0764d140cc2d8b6a089e77eb90d6cc2214b1cb|NG1.1新身份完整执行CPU/平台/原12点/lab，Builder自检通过并清理。|

每次都保留原manifest、命令、退出码和cleanup，不能用run-06覆盖前五次失败。后续更正只新增解释。代表性设计与判断过程见[私有学习/博客/X稿](LEARNING-DRAFT.md)，尚未发布。

## 资源、清理与复现

server宿主工作全部位于获授权的本工单builder根，每个SSH先cd且设置CUDA_VISIBLE_DEVICES=0；容器无GPU设备。复用已有LinuxNode22.23.3、Go1.24.13、Pi锁依赖、Python/PG与GCC镜像，新增官方Nginx镜像及隔离aiohttp3.12.15/pytest8.4.2依赖。Go二进制在Linux有界编译容器独立构建，没有挂macOS可执行文件。

平台PG0.75CPU/1GiB、Pi1CPU/3GiB、API1CPU/1GiB、Nginx0.5CPU/256MiB；编译/测试/生成器每次只加1CPU/2GiB槽。第二API探针独立错峰。lab在平台stop后运行。并发总量在6CPU/10GiB/6容器内；没有改系统Nginx、daemon、驱动或外来comfyui。配置、inspect及连续资源采样见run-06。一个完整invocation最多15min，非后台服务。

最终[owned进程回执](owned-final.txt)为空；run-06 summary和各失败summary的remaining_owned_running均为空。PG/Pi诊断卷保留，不能声称删除了全部资源。[工作根字节数](disk-root.txt)和[owned镜像/卷统计](disk-owned.txt)单列，总新增留存量低于2GiB；未清理历史或外来资源。静态图渲染容器也已退出。

运行入口和必需环境见[指南](../../../service/scripts/nginx-entry/README.md)。最终同SHA hosted CI需要成功，最多4个完整run；Handoff提供真实run链接，不能用当前自检替代CI。R另用新工作树、自己的源构建和owned资源执行，Master只有收到正式accepted后才可集成。

贡献：Human给方向、问题和预算；Master发现/裁定单控制器边界和hey计数修订；Builder Agent实施、排错、记录；Regulator独立验收。没有将本候选写入事实账本、现实简历或公开内容。
