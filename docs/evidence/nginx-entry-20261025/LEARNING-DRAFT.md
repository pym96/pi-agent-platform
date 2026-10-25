# 私有草稿：接入 Nginx 前，先检查谁拥有任务执行权

状态：Builder 过程记录与博客/X 草稿，未公开、未独立验收，不作为简历事实。

Human 从 Nginx“分流”提出把入口接入 Pi 平台。聊天里的示意图画了两个 Go 实例。我在实施前读了现有控制器：它启动时获取 PostgreSQL advisory lock，只有一个实例可以执行恢复与任务调度。若直接把图变成两个共享数据库的控制器，第二个会退出；取消锁又会改变恢复、幂等和每 session 串行的边界。

本轮沿用一个 Go 控制器。平台 profile 验证真实 Nginx → Go → Pi1.3.0 → synthetic model；另起两个无状态 HTTP fixture 演示轮询。这样可以分别回答入口是否保留流式协议，以及分流是否发生。两个 fixture 的吞吐不能代表两个模型副本的吞吐。下一步若需要多个 Go 实例，必须先明确实例间的任务所有权与恢复协议，再调整这个约束。

实施中我还碰到一个验收判断错误。run-04 的 `go test -race -count=1 -json ./...` 返回0，我写的入口却报“required Go skip”。原件中，两条 `Action=skip` 属于没有测试文件的 `cmd/service` 和 `internal/executor` 包，均没有 `Test` 字段。真正的 PostgreSQL 测试已经运行。

最初的判断是“任何 skip 都不应通过”。我把包级状态当成测试级状态，导致正确执行的套件被拒绝。我先补一条重现这个区别的测试，再把检查改为：测试级事件必须通过；实际 `TestDurableAdmissionAndRecovery` 必须存在且成功；零测试和测试级 skip 继续失败。对应修改为 `1a2ee6286ca2922f44819666d971cc927dfddc96`。run-04 保留失败状态，后续执行使用新 run 身份，不用修正后的结论覆盖旧原件。

另外三个准备失败也保留：容器用户与源目录所有权不同导致 Go VCS status128；只读父目录下缺少嵌套 bind 目标；只读 Nginx 根目录下默认 fastcgi 临时路径不可写。分别采用进程级精确 safe.directory、预建 ignored 挂载目录、把各类临时路径放隔离 tmpfs。这里只记录各次日志已经说明的原因，后续完整协议和负载结果另见 REPORT。

run-05又改变了一次判断：hey配置-n300，在C8只收296条、C32只收288条。我先保守记为missing/error。核对v0.1.4官方源码后，Master独立确认每个worker只执行整数除法N/C次，并冻结NG1.1。run-06保留原命令，新记录configured300、scheduled296/288、未安排4/12；未安排不能算服务成功。从296条删一条，仍应得到真实回执缺失。旧run-05继续标failed，未用新解释覆盖原summary。

贡献边界：Human 提出方向、学习问题和预算；Master 审视单控制器约束、冻结工单并协调；Builder Agent 编写实现、测试和本草稿；独立 Regulator 尚需复核完整远端候选。本文未证明 Qwen 吞吐、GPU 调度、C10K 或生产可靠性。

来源：Pi #15 / NG1.0；run-01–04 的命令、日志、summary；最终原件位置和清单见 REPORT。源码定位：service/cmd/service/main.go 的 singleton 获取、service/scripts/nginx-entry/measurement.py 的 Go receipt 检查。

## 配套 X 草稿

给 Pi 平台接 Nginx 前，先读到 Go 控制器的 PostgreSQL 单实例锁。于是保留一个控制器验证 SSE，用两个独立无状态 fixture 验证轮询。两组证据各自回答一个问题，不能据此声称模型容量扩容。

另一个小坑：Go JSON 的 `Action=skip` 可以表示某个包没有测试文件。验收需要区分带 `Test` 字段的测试事件，并明确要求真实 PG 测试成功。原失败保留，修复后另起 run。当前为私有 CPU 实验，完整候选仍待独立复核。
