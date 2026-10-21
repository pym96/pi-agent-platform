# 兼容与启动判断修正（进行中）

目标是取得同一真实模型的负载曲线；限制是不升级宿主驱动、不占他人GPU、最多8CPU/32GiB、Builder09:20Z前停。Human选择方向和资源，Builder执行，Master编排，独立Regulator尚未复核；以下不是Human独立实现或生产成果。

1. 官方vLLM0.8.5.post1确有cu121 wheel，但完整METADATA要求torch2.6.0/torchvision0.21.0，与已有torch2.5.1cu121不同。未强行no-deps安装或伪装Qwen3为Qwen2。服务器直连下载SSL EOF，本地大文件两次有界下载仍未完成；停止，保留官方release与range抽取METADATA，选择允许的serialized Transformers fallback。此选择只测单活动生成/FIFO队列，不能代表continuous batching。
2. 隔离pip overlay自动拉入NumPy2.2.6，导入generation间接导入已有sklearn时触发numpy.dtype ABI错误。将本轮下载的NumPy目录移动到本轮unused-deps，恢复镜像NumPy1.26.4；不修改镜像/共享环境。随后Transformers4.51.3原生Qwen3ForCausalLM导入成功。未因pip显示成功就认为运行时可用。
3. f733e8006c96f0153da5f015052fcd89253358d0首次GPU启动在tokenizer解析时报“缺少model_type”，没有加载权重或正式请求。最初以为配置解析问题；实际cache目录和文件权限为700、owner1001:1001，而root容器cap-dropALL后不能越权读取，os.path.isfile返回False使HF得到空config。CPU默认root能力预检没有覆盖实际启动权限，这是Builder预检遗漏。保留startup-attempt1.log/inspect，停止自有容器，不改共享cache权限。窄修复以--user1001:1001运行，并让deadline线程daemon化以免主线程异常后残留。相同read-only/cap-drop/UID CPU检查成功读取qwen3和官方tokenizer；GPU重启与正式矩阵仍待Master门禁。

改进：把身份、mount、capabilities与实际服务保持一致作为启动预检的一部分；分别验证包元数据、实际import、文件访问和真实生成。已知目前只是配置读取修正，尚不能据此断言权重加载、生成或负载矩阵成功。原始大件位于本轮专属raw目录，最终manifest将索引；先记录当时证据，不事后包装成功故事。
