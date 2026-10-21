# DeepSeek AI Infra研究与三方向候选简历｜Criteria 1.0

状态：ready-for-agent，阶段B Builder；Researcher已冻结5件研究附件并交接。WorkOrder https://github.com/pym96/pi-agent-platform/issues/5 ，唯一候选分支`workorder/5-candidate`。本轮Human重申研究DeepSeek AI Infra、分布式系统、容器化并形成Infra/开发多份简历。Master沿用Human已授权的原生subagent协作。账户为当前订阅，不启用额外API付费。没有新loop、训练或GPU运行授权。

## Input

- 根AGENTS/SOURCE_OF_TRUTH、空反馈队列、职业路线中2026-10-21双方向提纲和唯一fit map。
- `20-现状与事实/事实账本.md`、`50-简历/现实版.md`、`50-简历/builder/README.md`、已有事实安全版TeX/字体。旧`50-简历/说明.md`存在与最新登记不一致的历史叙述，不能覆盖事实账本或恢复旧C级事实。
- 独立Pi项目accepted基线 `f1d172dda9e578cd1ff773363b14f03ff0a1d18d`，#1/#3 Verdict、业务README和压测报告。Pan #146仍needs-triage，禁止顺带修复或使用其rejected结果作成果。
- 官方DeepSeek open-infra-index/DeepInfer/3FS/DeepEP/DeepGEMM/FlashMLA，以及Docker/Kubernetes/Go/PostgreSQL文档；先核版本与实际范围，再做推断。

## Output 与角色阶段

A. 新Researcher Agent：在`40-规划与路线/04-研究与原理/DeepSeek-AI-Infra-分布式与容器-20261021/`产出README、研究报告、来源清单（URL/抓取日期/commit或版本/适用硬件/支持的具体结论）、学习实验建议。更新04目录README，以及既有职业路线中的唯一fit map（不另建第二张市场fit map）。研究报告把来源事实、项目Evidence、推断和待验证假设分开。交接材料与文件清单，不签accepted。

B. 新Working Agent：Researcher交接后再激活。在独立Pi仓库新clone、`workorder/<issue>-candidate`上仅新增`docs/career/20261021/`候选包，及更新`docs/career/README.md`、根SOURCE_OF_TRUTH中的候选导航。不能修改业务实现、既有Evidence或根现实版/事实账本。

阶段B现已激活：新clone位置`60-项目/pi-agent-platform-career5-candidate/`，完整基线f1d172dda9e578cd1ff773363b14f03ff0a1d18d；研究附件5件取自阶段A目录。允许原始资料只读snapshot/来源摘要置于包内并明确非新真源，确保复制后相对链接可用。原事实/母版身份清单在`/private/tmp/pi5-source-baseline.json`，须随候选保留用于独立比对。后续本地交付副本拟放`50-简历/builder/resumes/2026-10-21-Infra与开发候选/`，仅由Master在独立accepted后逐字节复制并登记，不由Builder修改根简历目录。

候选包包括三份中文一页A4 PDF、可编辑TeX/Markdown：01平台可靠性Infra、02推理服务Infra、03Agent应用开发；另附事实—句子—来源—贡献归属映射、待Human批准披露清单和构建日志。各版明显标识“候选草稿·禁止投递”，未实现的学习目标不出现在既有经历/熟练技能内。当前已批准F事实可改写，新增Pi材料只能陈述可定位的项目能力/Agent协作执行及限制，不声称Human独立实现或已掌握。BVI/奖项等继续按当前事实门禁，不恢复旧简历C级条目。

研究最终稿与来源清单作为private candidate pack的研究附件一起提交，保证Regulator可检出同一SHA；原root报告是研究交接材料，不冒充新的事实真源。Builder在候选内使用内部相对来源；保持私有，不上传公共Pages/公开站点/投递或外发。原件/字体只复制必要内容，不读凭证。提交完整远端SHA、draft PR和Handoff后冻结。

C. 新Regulator Agent：全新干净clone Handoff远端SHA，逐句核事实和贡献归属、抽核官方原始来源、编译两遍并核PDF与文本、独立视觉检查。探针在独立scratch，不混入候选。签署候选包accepted/rejected；本合同accepted仅指研究/候选稿满足约束，绝不等于简历披露获批或可投递。Master在accepted后按原SHA快进集成，核PR MERGED再删远端候选；保留研究/简历PDF的本地交付副本和导航。

## Constraints 与预算

只读调研、文档/候选简历制作和本地PDF构建；禁止安装共享环境、启动server容器/模型/GPU/集群、付费调用、改产品、发布/投递、晋升项目/现实简历事实。原生subagent各固定角色，不接管旧session或换角色。

研究阶段有界为20分钟左右，足以查明决定定位的关键来源即停止；Builder约20分钟，Regulator约15分钟，时间为本轮编排预算，遇阻断给ScopeChallenge而非扩展项目。不是后台定时任务，不沿用已结束的loop。若无合适硬件，只给来源支持的可行性判断与候选实验，不做假复现。研究深度优先服务三份稿的可信定位。

## 验收标准 Criteria 1.0（均由独立Regulator复核）

### C-RC-01｜来源与机制
- Given：指定DeepSeek组件及Docker/Kubernetes/Go/PG机制。
- Observe：报告和来源清单中的原始官方段落/路径、版本、具体主张。
- Pass iff：每项技术主张可回到官方源或明确项目Evidence；说明引擎/服务边界、GPU代际与网络约束、容器namespace/cgroup/volume、K8s调度与恢复、任务持久化/幂等/所有权/未知执行；过时索引不能冒充当前版本要求，访问失败明确未知。
- Fail when：用二手传言作既定事实、编造DeepSeek能力/硬件支持、把容器当完整安全沙盒、把连接/HTTP吞吐当模型吞吐或多机可靠性。

### C-RC-02｜关联与可行动性
- Given：现有Pi #1/#3和Human近期Go/ROS/线程交替打印学习背景。
- Observe：机制映射、唯一fit map及有界学习建议。
- Pass iff：能从对象/状态/约束解释并发vs速率、goroutinevs进程/节点、服务控制面vsGPU调度、PG事件vs模型KV cache；区分已验收实现/本人掌握/拟议工作，给最小学习动作、可观察结果与停止条件。JD定位如使用社招或非上海示例，必须标注，不能伪造实习招聘结论。
- Fail when：只列工具清单、把建议写成已做、生成与现有项目无关的大量功能需求或新的运行授权。

### C-RC-03｜三份稿与事实边界
- Given：同一事实账本、最新事实安全版、Pi accepted边界。
- Observe：三份稿的文本、事实映射和角色/指标/技能措辞。
- Pass iff：三版有不同职位定位与项目展开重点；教育/日期/身份一致；每个成果/数字有来源且未扩大；Human/Agent/上游贡献区分；保留synthetic、120s/一次观测、1000重连/21写失败等与规模主张相关的限制。没有实现/掌握的DeepSeek/K8s/多卡项目不写为经历。所有PDF有禁止投递标记，当前现实版和账本不变。
- Fail when：无映射数字/奖项/作者角色、夸大个人实现、把研究当工程经验、未经批准晋升新事实、可投递标记或不同版本基本信息冲突。

### C-RC-04｜构建与交接身份
- Given：私有Pi候选SHA、既有字体模板和三份稿。
- Observe：干净clone、diff、双次编译、PDF metadata/text/font/视觉及Handoff。
- Pass iff：仅允许路径修改；三PDF均一页A4、中文可读、字体嵌入、无overfull/遮挡且文本与MD一致；Regulator独立检查，不仅相信Builder；最终PDF/源文件/研究附件都绑定同一完整远端SHA。缺未披露项或有误返回rejected。
- Fail when：缺任一稿/源文件/警示/独立复核、候选身份漂移、探针进入候选、main/事实账本越界或将过程自述当Verdict。

## 对offer证据链的贡献

将已有Agent开发和server实验转为不同岗位可评审的候选表达，指出分布式/容器/GPU推理的真实缺口，并交付Human可学习和核对的材料。以最小额外投入区分“项目已有Evidence”“本人能讲解/修改”“可披露进入简历”，减少只堆术语或把学习计划写成成果。最终公开披露或投递须Human对具体稿/新事实另作决定，本轮不请求空白授权。
