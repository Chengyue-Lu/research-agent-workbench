# M1-010 / M2-009 / M11-008 包内调用切片

2026-10-10；R2；required Skills=[]；定义基线develop `e49386140c18cdfb9e6065b7c59e2545f863e386`，实施起点PR140接入文档后的 `acba750d7e8f06d308296a363ba01af825e393b6`。人类明确要求补齐包内受信caller/factory，按已有授权验证三桥接。完整Task定义与状态以 [TASKS](../../../../TASKS.md) 为准，单个切片不把三项一起判DONE。

## 功能与输入

已有 `call_intake` 生产实际草稿及request/response/usage；新包内factory只消费explicit Task/Profile/Method/Requirement、外部Supply/typed evidence、独立observer/verifier、data/host policies与时间。caller核对真实IntakeCallResult及已发布report/refs，以同一预算/剩余wall time进入既有workflow/executor，main选择0..N并实际消费fresh child结果。没有workspace扫描、credentials/生产账默认、Supply资格制造、Host重新选择或自动Guide/State接受。

允许读取：仓库入口与本Packet、现行Architecture/相关模块；具体设计、现有entry直接模块/测试、原候选 `chain-proof-002/runtime/api_factory.py` 与 `api_budget.py` 的契约。API原件、历史累计账与Credential reference仅测试执行过程按授权使用；实现者不读取Key/账/完整原始API或外部私有评分答案。

## 互斥写域与交付

- Factory切片：`src/research_workbench/entry/factory.py`、`tests/test_entry_factory.py`、必要的`tests/entry_factory_support.py`。沿用现有候选class契约，去除code_root与workstream runtime import依赖，SchemaCatalog使用既有随包默认；返回实际FACTORY记录pins，不扫描档案。不修改旧API原件。
- Caller切片：`src/research_workbench/entry/caller.py`、`tests/test_entry_caller.py`。从实际published intake报告与exact pins核对status/usage/holds；拒绝Task/Method替换与未声明Requirement，保留失败或unknown并零workflow调用；共享total budget只计算intake一次，wall time使用同一deadline。可使用明确外部Requirement仅当实际Method声明其exact identity且显式输入pin核验通过，须记录其不同producer；不把外部对象写成intake输出。
- 集成/测试范围：相应workstream记录、原候选helper的显式包内兼容接点、direct entry tests、checkout外安装与独立冷回放。Schema/Registry/Resolver/Host/core identity、权限和资格规则不改；公共CLI/统一UI、非只读Tools、真实Skill加载为其他Task。
- 实施Profile=bounded factory/caller worker，required Skills=[]；实现预算各15分钟一轮及有界修复。互相保留编辑、共享接口先协调；实现者不执行任何测试/API/生产Tool/Key/生产账/Git操作。测试按既有单执行窗口规则，先确定性、再有资格的实际API。
- 交付紧凑handoff、实际读范围、变更hash与建议正反cases，持久化可见通信。日志/JSON作为可复核附件，可读报告逐桥列输入、实际输出、消费者与缺口。

## 验收与停止

正例从真正intake producer refs进入包内factory/executor、main无子和变量children、新main消费、file Receipt冷回放、显式checkpoint与独立Guide。反例包括替换/drift/歧义/未proceed Method、缺资格/fixture/Skill供给、observer错配、越权写/Tool、失败unknown费用及deadline/预算停。结构/Receipt成功不是Task或科学接受。

完整API验证沿用1000万累计token预算、授权时间窗与fresh官方闲时，无付费自动重试或fallback；actual/failed/unknown与未开始均保留。来源/配置/历史资格重新核对，不代签Source/Skill/Human接受。已授权受控工程材料足以先验证，无需接入真实科研。若缺真实资格、输入、权限或突破core边界，停止相应执行并留具体事实，继续互斥合法切片。

2026-10-10 补测边界：当前 Runtime Bundle 的 exact execution scope 仅消费 `action_ref`，planning Method 的 `planning_action_id` 无受支持的执行字段；本切片保留 planning 参数的显式早期 block，不改 Core/Schema 或制造 Action。现有 workflow→checkpoint 是工程结果移交，尚不证明正式/compact Handoff producer 和完整性消费者。两项缺口进入验证记录，已支持的 no-Skill Action 通路继续验证；三个 Task 不因本切片或 API 成功自动 DONE。
