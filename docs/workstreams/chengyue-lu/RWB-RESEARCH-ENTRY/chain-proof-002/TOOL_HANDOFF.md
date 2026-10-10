# CHAIN-TOOL-PREP-011 Compact Handoff

2026-10-08；Profile=bounded implementation worker；required-Skills=[]；控制owner路诚钺，API reviewer黄毅。仅静态开发候选，不产生Supply、Source/live/Human/Skill接受或真实项目任务。

交付 [runtime/synthetic_tool.py](runtime/synthetic_tool.py)；接口 `create_synthetic_lookup(root, task, target_path="materials/intent.txt") -> ClientTool`。Task可为Mapping或具有input_refs的现有对象。name为`entry-api-bridge`、闭集JSON参数仅`path`且enum仅声明target、side_effect为read-only。`ToolDefinition.strict=False`，不因客户端闭集Schema/handler校验宣称供应商strict支持。创建时仅检查root和Task元数据，不读取目标内容。

每次handler调用重新核唯一exact Task ref与冻结声明一致，拒绝越root、portable alias和filesystem link，打开文件前后用实际fstat限制大小与变更，最多读取4096 bytes；实际bytes SHA匹配后严格UTF-8解码，返回紧凑`{path,sha256,text}`。未知path、额外字段、重复/缺失ref、pin drift、无法读取、oversize与invalid UTF-8均在返回成功前失败。没有文件写入、目录扫描或网络；不追随文内链接。

Root显式选择/hash handler，制作其actual Tool component和tool_refs映射，确保Task/Profile/selected Supply允许同一Tool name，按现有Driver配置每role正数Tool/batch上限和Session预算，消费actual结果进入fresh模型请求。max_tool_result_chars需覆盖JSON编码后的实际payload，不能把4096-byte读取上限视为序列化字符上限。子数量仍由main决定；本Tool仅当前合成桥接的显式可选映射，不成为通用必选组件。

只做AST/内存compile、格式、引用和hash检查，不执行产品imports、create函数、handler、tests、API、Tool、Key或账，不读实际项目/Attempt文件。Root转述已有no-Skill主子main消费接通与Guide LENGTH停点复测，未由本worker验证；Source/Human仍false。本helper没有放宽外传许可，实际returned text出站由Root依Task/Profile/Supply/View与授权负责。

限制：这是bounded text reader，不认证材料真实/来源科学质量，也不是OS sandbox；revision字段仅用于发现Task ref变更，文本内容不额外宣称document revision验证。filesystem并发变更依fstat/path复检与实际SHA fail closed，不宣称普适物理时钟或文件系统原子性证明。后续Root唯一测试者执行正反场景与actual Tool回传/Trace/Host/Receipt闭包，任何错误保持真实失败。

可见通信与实际读域见 [TOOL_COMMUNICATIONS](TOOL_COMMUNICATIONS.md)，任务来源 [TOOL_PREP_TASK_PACKET](TOOL_PREP_TASK_PACKET.md)。source hash另交Root并停止。
