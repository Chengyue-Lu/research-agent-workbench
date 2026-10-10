# CHAIN-TOOL-PREP-011 可见通信

2026-10-08；bounded implementation worker；required-Skills=[]；6分钟/1轮。仅独占runtime/synthetic_tool.py、TOOL_HANDOFF.md、TOOL_COMMUNICATIONS.md，保留他人文件。

Root授权原文：

> 执行新有界 Task CHAIN-TOOL-PREP-011，Packet 位于当前 PR140 checkout docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/TOOL_PREP_TASK_PACKET.md。Profile/required-Skills=[]/读域/ownership/预算6分钟/1轮/静态检查与停止条件均按Packet。你不独自在仓库，保留他人内容；Root唯一测试/API/Tool/Key/账执行者。只准备runtime/synthetic_tool.py和TOOL_HANDOFF/COMMUNICATIONS，不执行产品imports或函数，不改src/Schema/Registry/Git/memory，不读实际项目/Attempt/Key。本轮真实noSkill主子main消费已实际接通，Guide首次LENGTH停点正在复测，Source/Human仍false。Tool是当前合成桥接场景的显式可选readonly映射；不是全系统必选工具或真实项目任务。落盘hash后停止。

worker commentary：我先核对 Tool 准备 Packet 和现有 `ClientTool` 接口，只创建合成场景的可选只读映射，并做静态检查；测试和实际调用由 Root 执行。

worker → Root：CHAIN-TOOL-PREP-011 接口已核：create_synthetic_lookup(root, task, target_path='materials/intent.txt')->ClientTool，name='entry-api-bridge'、strict JSON只允许path enum=[target_path]、side_effect='read-only'。将每次核实际Task唯一exact ref/sha、root containment、链接拒绝、打开文件大小前后≤4096、UTF-8；返回{path,sha256,text}。不读取任何实际项目/Attempt文件，不创建Supply或资格；Root接handler hash/component映射和实际Session limits。现在写独占文件并只AST/compile检查。

Root → worker：ToolDefinition.strict 需显式 False：当前 DeepSeek Responses candidate Profile 的 beta_strict_enabled=false，不能因 JSON arguments schema 严格闭集而声明供应商 strict mode。保留 schema additionalProperties=false 与 handler 自身 exact参数检查。只改你的 owned helper/doc，Root随后会验证。API Profile capabilities/Tool wire实际适用性由Root核，不准你读取production材料或测试。

按上述直接约束改为ToolDefinition.strict=False，Schema闭集与handler exact参数检查保留；前一条“strict JSON”仅为参数闭集表述，已在交接改用“闭集JSON”以明确不宣称remote strict。未扩读Profile或API材料。并补读后file identity/metadata比较，拒绝读取过程中发生替换。

实际读域：TOOL_PREP_TASK_PACKET、API_FACTORY_TASK_PACKET全文；port.py ToolDefinition声明；session.py ApiSessionLimits与ClientTool声明；driver.py readonly Tool映射、identity/权限/Session limits的精确rg命中；tests/test_entry_bridge_flow.py 126–144的readonly handler合同（只参考，不import或复制fixture资格）。metadata发现runtime目录名称与上述接口行号。没有读取实际项目材料、API Attempt、Key、账、日志、Registry或其他代理域。

实现只写上述三文件。使用现有ClientTool与ToolDefinition声明，不改src/Schema/Registry，未制造Supply/qualification。静态检查以标准库ast.parse及compile只创建内存code object，不执行code object，不import产品或调用函数；Markdown相对目标/UTF-8/尾空白/hash仅检查本次输出，结果交付前记录。未运行产品测试、API、Tool、安装、Git或memory操作。

## 最终静态检查与 Compact

仅对独占 helper 做 stdlib AST parse 和内存 compile，结果 PASS（114 行，无行尾空白）；没有执行代码对象、产品 import、handler、测试或 Tool。两份独占 Markdown 的 3 个相对链接均存在，问题数 0；未写入机器绝对路径。ToolDefinition.strict 已显式设为 False，闭集 JSON Schema 与 handler exact 参数检查保留。Root 负责实际 Tool/Profile/wire/Session 验证，静态结果不构成运行或资格证据。交付范围为这三份文件；最终 SHA256 由交付消息列出，避免自引用 hash。交付后停止。