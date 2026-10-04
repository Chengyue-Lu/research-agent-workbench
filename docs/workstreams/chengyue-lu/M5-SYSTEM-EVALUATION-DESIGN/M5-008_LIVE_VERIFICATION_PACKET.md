# M5-008 live evidence/use-boundary 核验候选

2026-10-04。Evaluation owner：路诚钺；Provider接口复核：黄毅；R2。
Draft PR136内的隔离实现，未接受；M5-008仍BLOCKED，没有真实调用。

[实现](../../../../src/research_workbench/evaluation/live_verification.py)接入现有M6/M11确定性核验器，
服务于[新版preflight](M5-008_LIVE_PREFLIGHT_PACKET.md)。这些对象不取Key、不发送请求、
不调用Tool、不创建预占，也不授予Pilot或Skill准入。

## 独立证据选择

`LiveEvidenceVerifiers`由可信Maintainer独立提供冻结context、完整admission endpoints、Need与
admission evidence closure、Pilot owner/executor、Provider owner/具名applicability Decision、
binding manifest、当前Provider对象、已存在的唯一M6 DB/anchor/identity，以及实际Human与运行环境核验接口。
没有默认许可，接口不能从工件中反序列化；文件状态和哈希一致性不能代替实际具名接受。

Pilot Decision沿用Kernel Decision，必须accepted、named actor、Human owner，scope含M5-008和run ID。
metadata的`m5_live_pilot_authorization`绑定Task、live-pilot purpose、executor与冻结context。
commitment排除Decision自身的authorization_ref，避免自包含hash循环；外部context仍固定该Decision的实际path/hash。
context引用的scope/plan覆盖窗口、Model/config、数据/Tool边界、输出与预算声明。
核验接口须检查真实授权与当前有效性，不能用Agent生成的Decision记录代替Human。

A4端重新运行现有`assess_skill_evaluation`，要求actual evidence closure可支持human-decision-recorded，
核对Lifecycle的new-binding资格及baseline/trial/promotion evidence来自该Evaluation真实arms。
独立Need ref须出现在Lifecycle中；具名Decision绑定Need、Evaluation和evidence closure，scope含candidate ID。
实际Human接口负责完整Need要求与promotion来源的接受，不把共有paired evaluator的结果扩展成科研结论。
Release/Projection/overlay的端点与candidate替换规则继续由共有preflight核验。

admission closure是本Task的辅助输入commitment，包含version=1.0.0、purpose=skill-admission-evidence、
exact evaluation_ref和最多4096个独立file_refs；不是新的默认Core kind或权限对象。
pin所有声明文件，并核对传递FileReference与已有Receipt的Attempt/Profile/Assignment/Context/
output/validation路径都被闭合。Human回调后重验文件及共有Evaluation；source package hash同样重新核对。
该closure覆盖准入前证据，不包含将要引用其hash的Human Decision，避免循环。

## M6、当前环境与历史用量

applicability先用已有cold reader重验bound completed conformance报告、source/config/usage bindings，
要求其actual accounting与所选retained journal一致；再用已有`observe_provider_binding`核对当前
Provider对象、完整已声明source图及配置，匹配Protocol的exact Adapter/Model。
这些观察不探测Key存在性或解析凭据。

必需的可信运行环境observer返回不可变`CurrentLiveObservation`，包含actual source commit、
Windows context和source artifact refs，与scope/context精确比对。此接口必须由真实运行环境导出，
不能从待验applicability工件恢复自己的expected值。具名Provider接受绑定context、manifest和观察摘要。
旧source66/Python3.11.16的实际M6接受不能静默绑定到新的source/Driver/Python。

`RetainedConformanceBudget`只打开独立选定的已有DB、anchor、namespace、journal identity和可选
已接受attempt grant。缺文件不重建，identity/anchor/history变更拒绝；未知、held、未完成Attempt拒绝。
checkpoint必须与真实重放的完整snapshot一致。接口仍继承M6的caller-attested send观察与本地anchor信任边界，
不增加全局账本或外部身份认证。
原successful conformance结束后拒绝新Attempt的政策保持；不得把它当作四臂Pilot账本，亦不得重置历史。

## 每次入口核验与剩余接入

`LiveUseGuard`在Provider/Tool入口核对可信当前时钟、冻结的北京时间晚间窗口及官方闲时依据，
只接受预注册pilot attempt ID，拒绝confirmatory/unknown slot及A1 Tool。
执行成功路径前独立重算原preflight，并以当前时间重算资格、权限、applicability、overlap与pairwise。
时间、slot和预算的快速拒绝放在完整重算前，所有检查均先于实际执行端口。
完整核验后再读取当前时间、官方窗口与同一request预占ordinal；过期、时钟回退或预占被更改时拒绝，
不会沿用慢核验开始时的时间/预算观察。默认preinvoke要求未使用reserved预占；显式send阶段
要求同一原handle的durable intent且尚无HTTP entry，慢核验后再次核对这个状态和ordinal。
Tool没有send阶段。该阶段区分让Driver能在写入intent后、实际HTTP entry前再核验，
不改变事件、不授权第二次发送。[transport候选](M5-008_LIVE_TRANSPORT_PACKET.md)已显式
连接Pilot book的原handle、阶段和有界encoded body；实际Driver仍须绑定当前真实guard与input proof。

可信Pilot ledger接口必须返回该slot当前的typed reservation：实际已知累计、当前request预占、
其他held、完整性、累计ceiling、包含本次预占的call计数与单Attempt/全run elapsed time。
未知、其他held、历史不足、上限/turn/time耗尽均拒绝；Provider入口要求非零、已计数的预占。
DTO本身不能证明预占。实际ledger必须拥有原子单用handle、durable send intent、usage settlement和失败保留，
这些行为已有[有界Pilot账本候选](M5-008_LIVE_BUDGET_PACKET.md)，实际入口仍须与后续Pilot Driver接合。
入口检查不是可保存后复用的permit，也不启动执行。

[离线用例](../../../../tests/test_live_verification.py)分别检查真实确定性M6 journal/report/source-binding API、
共有Skill Evaluation及新入口边界；Human、运行环境、官方窗口与Pilot reservation均明确为合成test authority。
M6报告/graph和Skill admission是独立组件用例；入口用例的applicability/admission端口仍使用已声明合成authority，
不宣称当前已完成实际四臂链路。原始失败与修复复验保存在私有Attempt内。

后继接合有界多slot账本与合法Model semantic Method/Requirement/Profile slice、M6/M11 generic Driver，
再闭合真实Receipt/cold replay、有限盲审、review freeze/
reveal/metrics，以及具名真实输入/Skill Trial/admission/Pilot授权与完整run-set验收。
临时21/1744等fixture用量不计作实际消耗；真实历史1744、1000万累计硬上限、Flash与18:00后官方闲时保持。
