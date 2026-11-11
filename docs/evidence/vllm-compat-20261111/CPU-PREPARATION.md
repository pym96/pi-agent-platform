# Nov11 CPU 准备记录（候选，非最终验收）

Builder 在源码 `90b27c7ab148019ee9c55e76efbd9d207776a853` 下完成了 152 个官方 wheel 的隔离安装。第二个有界 CPU 入口的 `pip check`、12 个顶层模块导入、安装文件摘要和 ldd 记录均返回 0。CPU阶段未暴露GPU。随后首个精确授权GPU入口在CUDA初始化Error804失败，容器生命周期13.581239770秒、实际生成调用0，见[失败原件](gpu-smoke01-summary.json)；原 C-G0-01–04@1.0 没有降为 CPU 验收。

## 原件与身份

- [完整闭包](closure152.json) 与 [哈希锁](requirements152.lock)：152 文件、3,509,693,145 字节；包含官方 Ray cgraph 必需的 CuPy CUDA12 标记子树及显式运行时支持包 setuptools75.8.0，核心 Torch/vLLM cu118 不变。
- [源码执行映射](source-execution-map.v2.json)：区分旧518c、首次6de与实际90b。早期 [恢复映射](source-restore-map.json) 只描述6de检查点，不能用其旧哈希代替90b。
- [CPU阶段结果](cpu-stage-summary.json)、[逐命令起止/退出](cpu-stage-commands.jsonl)、[实际导入](cpu-imports.json)、[原始导入日志](cpu-import-audit.log)、[ldd原件](cpu-ldd.json)。完整47,523个常规安装文件、4个符号链接的manifest SHA为`8399994fa82aac42c3cd82a0f3e697bb46f70e16d4ba62969a13ce3a76fc8820`，定位见 [外部原件索引](external-evidence-index.json)。
- [Source CI1/2](CI-SOURCE.json)：实际CI2运行43003385021，source90b，15组212项、skip0；源码测试不证明CUDA兼容。早期 [九项CPU结果](cpu-summary.json) 与 [十项source90b结果](cpu-source90b-summary.json) 分别保留。

## 两次安装阶段

首次151闭包的哈希禁网安装和pipcheck通过，Triton3.2在加载后端时无条件导入setuptools，实际报缺模块。官方Triton METADATA没有声明它。Builder停止该入口，冻结完整环境和调用链；Master前瞻SC-RUNTIME-N11-04只准添加官方setuptools75.8.0，Regulator复核新的152闭包与精确入口后才执行。

补充入口先核对原151安装文件集合、摘要和符号链接，再只安装setuptools。其外层实际区间为11:03:06.953–11:03:40.168Z，exit0。完整闭包复核、支持包安装、pipcheck、导入与安装manifest、ldd均保留逐项原件。核心版本和原模型没有变化。

CPU容器使用缓存08619镜像、`--pull=never`、禁网、只读根、NVIDIA_VISIBLE_DEVICES=void、CUDA_VISIBLE_DEVICES=0、无DeviceRequests，唯一可写bind为自有目录。补充入口上限600秒，宿主机工作截止提前60秒供清理；独立native仍绑定绝对截止。每项命令保留成功、失败与超时结果，清理未知必须非零。实际宿主机文件/partial摘要先于删除四个已停止自有容器；11:07:23.462Z新回执确认剩余0。早期约10:10的cpu-closeout回执属于此前准备容器，不冒充安装容器的清理。

## CPU证明的边界

Torch、vision、audio、setuptools、Triton、xformers、transformers、tokenizers、NumPy、vLLM、Ray、CuPy的版本与导入路径匹配。Torch构建CUDA版本11.8，记录的初始化标志为false。

刻意不投射NVIDIA能力的CPU容器中，vLLM记录UnspecifiedPlatform，捕获了`vllm._C`缺`libcuda.so.1`的ImportError；13个ldd记录中3个二进制只缺同一driver库。SC04b保留这些原件，允许同void的独立CPU审计；任何后续CUDA加载/生成仍需精确GPU GO。这里没有观察到undefined symbol，也没有完成GPU扩展加载证明。

上游日志另称Triton被替成placeholder。Regulator读取官方源码后指出，该日志位于`if not HAS_TRITON`分支之外；本次先导入真实Triton，因此日志文字不足以证明实际模块被替换。R第二次实际审计确认vLLM导入后仍为真实builtins.module、Triton3.2.0、env内triton/__init__.py；不能把一句日志提升成运行模式结论。

独立Regulator第一次安装后审计完成了47,523文件与4链接比对，但导入阶段未形成最终结果。外层239.244秒、exit137、OOMKilled=false；日志出现OpenBLAS thread63/64创建失败，其pids上限128与Builder512不同，具体阻塞点及因果仍未确认。实际停止/删除在原截止前，11:19:14是后来的只读空槽确认。它是失败/partial记录，不是兼容性通过。后续使用新nonce和前瞻GO执行第二次审计，没有重放旧入口。

第二次独立CPU审计只修探针pids512、OpenBLAS1、OMP4和阶段日志，使用相同152闭包/runtime/source。外层11:27:38.499–11:28:50.894Z返回0：完整47,523常规文件及4链接匹配，12导入、pipcheck、ldd完成；11:28:52.429Z明确剩余自有容器0并释放。仅3处libcuda缺失仍属void边界。R只读观察确认缓存基底没有gcc/clang/cc/g++/c++及Python.h；没有执行编译器，未观测GPU编译失败，任何新增编译工具仍须另行裁决。

## 成本与过程限制

[成本记录](preparation-cost.json)保留新增官方body保守上界9,214,102,292字节，低于12GiB；精确server失败/丢弃wire、首次bulkSCP时段仍未知。早期汇总漏计resume2的49,955,185字节，Regulator指出后生成版本化修正，原件保留。vLLM本轮实际用了3次显式传输，前瞻上限5，另两次未用。旧Nov10失败成本和Pi13成本分别保留，不能重置。

[开发过程限制](tdd-process-limitation.json)保留6de先实现后测试、后来才读到项目TDD要求的偏差。Ray根元数据修复有开发red/green日志，但其绝对起止未持久化；Regulator不声称独立证明了开发时序。独立旧/新源码行为证据与开发顺序分别陈述，不补造时间。

Human决定方向、角色、资源预算和披露；Builder实施与执行，Regulator在独立进程复核及补负向。本文未登记为项目/简历事实，未公开发布。[案例](CASES.md)和[私有博客/X草稿](PRIVATE-DRAFTS.md)仅作内部学习材料。

## 随后单独授权的 B GPU 结果

原CPU准备于12:11:11截止，之后没有新增依赖或工具链。修正源d803在原运行时8399上通过实际535映射门，完成一次31输入/16输出token的原模型生成；[原始结果](gpu-smoke02-summary.json)保留native/watch/配置/警告与清理。首轮804、无初始化诊断和本次成功的设备生命周期合计33.486328255秒，实际生成调用1。独立R生成与最终G0仍待完成，CPU阶段文件不倒写成当时已验证CUDA。
