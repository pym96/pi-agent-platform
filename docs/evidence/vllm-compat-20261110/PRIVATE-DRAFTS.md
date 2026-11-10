# 私稿：复制命令成功，下载文件却没有保留下来

状态：博客与 X 草稿，未发布。Human 决定方向和预算；Builder Agent 执行准备与保全；Regulator Agent 另行复核。没有把 Agent 的工作写成本人独立实现。

这次任务要在固定截止前准备隔离的 vLLM 环境。首个官方 wheel 下载很慢，Builder 最后观测到180,092,928字节，并计划先暂停专属容器，再把 `/tmp` 复制出来，最后删除容器。

`docker cp` 返回0，Builder 随后删除容器。核对目录大小时，才发现目标目录只有约3.4MB，下载 partial 没有留下。命令回执只能证明复制调用结束，不能证明目标文件符合预期。

Builder 当时漏查了 tmpfs 的导出语义。[Docker 官方文档的 Corner cases](https://docs.docker.com/reference/cli/docker/container/cp/)说明，`docker cp` 不能直接复制 tmpfs 等特殊挂载中的内容，并给出了在容器内执行 tar 导出的办法。这能解释此次观察；本轮没有再起容器验证替代办法。

下一次可以让 partial 写入专属 bind mount，或在容器运行时从挂载命名空间导出。无论选哪条路径，都应在删除前核对目标文件的路径、大小和 hash。这里的关键取舍是停止不可恢复的删除动作，直到关键产物验证完成。

本轮只剩最后一次字节观察和停止日志，原服务端 partial 的最终大小与 hash 未知。本机另一次90秒下载超时，27,113,311字节的 partial 已保留。这些结果证明准备未完成，不能据此判断 vLLM 与硬件兼容或不兼容。

来源：本目录 ledger.json、raw/server-preserve.jsonl、raw/server-closeout.json、raw/local-full-download.log；工单 #21；源码518c82b287f47c70bb224158d27b2f9a5f77b8f7。内部定位不进入对外稿。

X 单帖草稿：

一次下载收尾里，Builder Agent 看见 docker cp 返回0，就删除了容器。后来核对目录大小，才发现 tmpfs 里的180MB partial 没导出来。Docker 文档明确列了这类挂载的限制。下次要在删除前核对目标文件大小与 hash，或先写进专属 bind mount。本轮准备未完成，无法判断 vLLM 兼容性。未发布，也没有公开博客链接。
