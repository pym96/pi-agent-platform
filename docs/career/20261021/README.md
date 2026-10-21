# DeepSeek研究与三方向候选简历｜2026-10-21

**候选草稿·禁止投递。** 私有审查包，Pi [#5](https://github.com/pym96/pi-agent-platform/issues/5) Criteria1.0阶段B。Builder产出不代表独立accepted；新增Pi事实尚未获Human披露许可。没有更改根现实版、事实账本或产品，没有启动server/GPU/付费请求。

| 候选方向 | 一页A4 PDF | 可编辑源文件 | 主要取舍 |
| --- | --- | --- | --- |
| 平台可靠性Infra | [PDF](01平台可靠性Infra/resume.pdf) | [TeX](01平台可靠性Infra/resume.tex) / [MD](01平台可靠性Infra/resume.md) | 持久状态、幂等、失败恢复、容器资源与容量口径 |
| 推理服务Infra | [PDF](02推理服务Infra/resume.pdf) | [TeX](02推理服务Infra/resume.tex) / [MD](02推理服务Infra/resume.md) | 流式服务与输入/完成速率；未写GPU推理成果 |
| Agent应用开发 | [PDF](03Agent应用开发/resume.pdf) | [TeX](03Agent应用开发/resume.tex) / [MD](03Agent应用开发/resume.md) | 已批准Runtime、协议、Trace、实验有效性 |

- [研究附件](research/README.md)：DeepSeek/分布式/容器机制、固定官方来源和有界学习建议。5件从Researcher冻结材料复制，只有README内部导航改写；[复制身份](research-copy-manifest.json)。
- [逐句事实/归属映射](fact-map.md)、[机器可读句子](claims.json)、[待Human披露清单](disclosure-review.md)。
- [原件身份](source-baseline.json)、[只读来源快照](source-snapshots/README.md)：非新真源，5件根原件hash构建前后核对。
- [构建日志与限制](build-log.md)、[两遍编译回执](build-receipts.json)、[验证结果](validation.json)、[验证脚本](validate_package.py)。使用既有Fandol字体，由XeLaTeX嵌入PDF，不安装字体或共享依赖。

本目录三个resume.tex可编辑；修改正文时同步同目录resume.md及claims.json/fact-map，重新两遍编译。命令示例：`python3 <resume-builder>/driver.py build --resume-dir <该方向目录> --tex resume.tex`连续执行两次，再在包目录运行`python3 validate_package.py`。日志检查无需运行任何业务或模型。

来源快照保留原上下文链接；审查导航使用本README/fact-map，快照不另建真源。未验证事项：本人对Pi/DeepSeek/K8s的独立掌握、GPU推理性能、多机/多副本可靠性、生产容量、有效上海实习JD。

[上级入口](../README.md) · [仓库真源导航](../../../SOURCE_OF_TRUTH.md)
