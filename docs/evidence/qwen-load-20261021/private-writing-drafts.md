# 私有写作草稿｜未发布

选题：模型配置报错背后的容器文件权限。Human提出推理负载实验目标并提供资源；Builder执行排查与修改，Master限定范围并批准窄修复。本文不把Agent执行归为Human独立实现。稿件使用engineering-judgment梳理因果，并按stop-slop修订表达。

## 博客正文候选

### 容器里的root为什么读不到模型配置

这次Qwen推理实验由Agent执行。实验先在CPU容器里检查依赖，再以只读文件系统、`--cap-drop ALL`和限定GPU启动服务。CPU检查能够读取Qwen3配置，服务启动却提示配置缺少`model_type`。原文件里写着`qwen3`。

Builder先在相同只读挂载和capabilities配置下复现，发现Hugging Face返回了空配置。接着检查模型目录和文件权限：所有者为普通用户，权限为700；服务容器使用root。

Linux把部分root权限拆成capabilities。Docker默认保留的`DAC_OVERRIDE`允许进程绕过文件读写和执行权限检查；`--cap-drop ALL`移除了这项能力。此时，UID0也受这份700权限约束。目录无法遍历，库中的文件检查返回False，后续解析才出现“缺少model_type”的报错。[Docker文档](https://docs.docker.com/engine/containers/run/)、[Linux capabilities说明](https://man7.org/linux/man-pages/man7/capabilities.7.html)

Builder将容器UID/GID改成模型文件的所有者，保留只读挂载和capabilities限制。相同权限环境下的CPU检查通过，随后服务加载了Qwen3权重，并完成真实生成。第一份请求记录包含242个输入token、128个输出token及完整流式终态。它证明这次配置能够加载和生成，负载容量另由正式矩阵测量。

预检遗漏在执行身份上：CPU检查使用了默认root能力，正式服务采用更严格的权限。以后复用同一镜像时，应把UID、挂载和capabilities一起带入检查命令。遇到配置字段缺失，也可以沿着“进程能否访问目录和文件”往下查，保留原文件内容和容器身份作为证据。

## X单帖候选

一次由Agent执行的Qwen实验：CPU预检能读取配置，容器启动却报缺少model_type。模型目录是普通用户所有、权限700；正式容器用了root和cap-drop ALL，移除了绕过文件权限的DAC_OVERRIDE。改成文件所有者的UID/GID，保留只读挂载后加载成功。预检需要匹配正式进程的身份、挂载和capabilities。https://docs.docker.com/engine/containers/run/

## 私有来源定位（不属于公开正文）

- [问题与取舍记录](compatibility-case.md)，启动执行源f733e8006c96f0153da5f015052fcd89253358d0，修复正式执行源601918edd4198e32e6940fbab3e2d5a2ba6095b5。
- `raw/startup-attempt1.log`、`raw/startup-attempt1-inspect.json`、[相同UID CPU检查](uid-config-check.log)、`raw/warmup/requests.jsonl`与模型日志；最终原件manifest提供bytes/SHA256。
- 本稿未发布，无博客链接、X账号或发布授权；独立性能Verdict尚待完成。模型来源为上游Qwen，实验与排查由Builder执行；Human掌握与披露仍需本人确认。
