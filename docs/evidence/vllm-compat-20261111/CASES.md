# 本单判断与修正记录（内部）

1. Nov10下载以tmpfs为唯一实时副本，Builder把docker cp exit0当保全成功，删除容器后丢失partial。Nov11直接写自有hostbind，删除前从host核size/hash/receipt；四个CPU容器移除后原件仍存在。本轮事实不改写旧损失，最终旧server字节仍未知。
2. Builder把未回收工具session句柄和静态filesize当作下载活性，未fresh核OS PID。读取native结果才发现curl早已exit18；保留实际区间和partial。后续以命令终态及起止为准，不把“未取回结果”写成“仍在运行”。
3. 官方Ray有1份根dist-info及14份vendor嵌套元数据。全suffix计数的validator误拒合法包；Builder最小修为只选根metadata，Regulator用真实Ray和缺根/多根/错NameVersion/漏CuPy负向独立验证。官方字节未重打包，来源、hash和activeextra校验保留。
4. declared closure与pipcheck均通过后，Triton真实import仍缺未声明的setuptools。先停并冻结环境，再经前瞻SC和独立152入口复核补官方支持包。观察到Python导入缺模块，不能据此宣称driver ABI不兼容；后续新错误仍需另停/SC。
5. CPUvoid缺libcuda与vLLM捕获的_C加载错误必须保留；只有后续GPU环境的实际加载与生成能补这一证明。日志“placeholder”位于上游条件分支外，Builder曾概括过头，Regulator源码定位后修正，保留原日志和更正轨迹。
6. Earlyreceipt字段不一致造成resume2字节漏加，Regulator指出后保留旧汇总并追加49,955,185字节修正。未知wire和首次SCP时间维持null，不填0；实际失败不从分母消失。
7. 原6de没有遵循test-first，Rayfix开发时刻未记录完整，独立行为测试不能制造过去的开发顺序。Human没有被归为这些Agent实现/判断的执行者。

每项原件与SHA见[CPU记录](CPU-PREPARATION.md)、[执行映射](source-execution-map.v2.json)、[外部索引](external-evidence-index.json)。这些记录不新增实验、验收门槛、公开声明或简历事实。

8. CPU独立导入和文件比对通过后，第一次GPU入口实际在torch._C._cuda_init报Error804，LLM构造失败、generate尚未调用。正常检测到CUDA平台不等于能初始化设备。独立watch停止/删除成功，13.581239770秒启动成本保留；实际libcuda选路尚未测量，不能仅因base含cuda-compat-12-4就宣布根因，也不先装编译器或改驱动。

9. 随后一次不调用CUDA API的CDLL/maps探针测到容器实际选中550.54.15，其摘要与compat包一致；真实535.309.01也已投射且摘要与宿主机一致，通用libcuda.so.1却指向550。这个观测把“依赖包CUDA版本”与“动态链接器实际选库”分开。加载器选择差异已证实，修正能否解除804仍待另行授权实测，不能提前声称因果修复成功。

10. 首次selector修复0e41被R实际预检打回：批量替换误造tuple字典键，原15测试没有经过有效模型身份路径；map解析还漏掉带(deleted)的额外550库。Builder先补真实预检及deleted负向得到red，再最小修复到d803/16green、R独立及CI3通过。旧SHA/原red保留，不能把第一版写成已通过。
11. 已知缓存基底没有C编译器/Python.h，Builder先保留风险，没有盲装工具链。固定eager路径在原有环境实际完成生成；这只证明该次路径没有被缺编译器阻断，不扩展为任意Triton/JIT都不需要编译器。

12. 独立R的原生生成和精确清理都在截止前完成，archive的只读取回却晚7.378839秒启动。两种时间分别记录，不能把晚取回伪装成准时，也不能把它改写成GPU超时；最终Criterion由R按冻结合同裁定。
13. Builder准备私有博客正文时核到仓库为PUBLIC，在首次候选发布前把正文保存为候选外私有原件，候选仅留digest/status指针。Master确认没有公开授权；保留实际visibility和决定轨迹，不删除或改写已推历史。
