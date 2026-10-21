# Builder构建日志｜2026-10-21

固定角色Working Agent，Pi #5阶段B/Criteria1.0；业务基线f1d172dda9e578cd1ff773363b14f03ff0a1d18d。仅构建候选文档，不是独立Verdict。

## 构建与检查

- 既有resume-builder driver对每份resume.tex连续构建两遍；6次退出均0，命令/输出见build-receipts.json。使用本机既有XeLaTeX/Fandol，无安装。
- pdfinfo：3份均1页A4，595.28×841.89pt；TeX日志无Overfull。pdffonts显示全部字体嵌入且子集化；CJK字体ToUnicode列为no，当前pdftotext仍能完整提取并核对中文句子，未声称所有PDF阅读器搜索行为一致。
- pdftotext -layout核对claims.json中的每句事实与Markdown；日期TeX的双连字符渲染为en dash，仅此及空白做比较归一化。按PDF实际行核每个bullet单行、无bullet内黑体。9/8/8条贡献共25条。
- 使用pdftoppm渲染至临时PNG并逐页视觉检查：三稿中文可读、单栏蓝灰、无照片、无遮挡；页眉警示与页脚披露状态清楚。PNG只是临时预览，不进入候选。
- 5件根原件前后hash相同，见source-integrity-receipt.json；研究5件复制身份见research-copy-manifest.json，除README相对导航外逐字节相同。
- 候选包与上级导航相对链接检查；原始只读snapshot保留原链接语境，不以该副本当根导航。

运行`python3 validate_package.py`产生validation.json，属于Builder产物检查，独立Regulator须从干净远端SHA重新编译、抽核原始来源并视觉检查。

## 取舍与剩余限制

Human原意为Infra/开发分版；研究表明当前GPU推理能力缺证，因此第二稿定位推理服务实习候选，只展开可迁移的流式控制面和负载口径，不将HTTP请求当token吞吐。平台稿保留容器硬配额与状态恢复，开发稿优先已批准F-AGENT原子事实。新增Pi句子明确Agent协作与待批准披露。

早期检查脚本错误地要求所有字体同时有ToUnicode映射，观察到Fandol字体嵌入但该列为no；已改为检查嵌入/子集，并另外逐句验证实际提取，不新增合约门禁。日期比较最初因双连字符与en dash失败；仅规范化该排版差异，不删数字或隐藏失败句子。

未启动server/容器/GPU/模型/集群，无付费调用；未恢复旧BVI/奖项/角色，无root账本或现实版改动。没有现实简历晋升、披露许可、生产容量、多机/多副本或本人掌握声明。本人学习建议保留为拟议动作，没有新运行授权。

[候选包入口](README.md)
