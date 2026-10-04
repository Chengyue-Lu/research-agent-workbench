# M5-008 live Protocol 输入实现候选

2026-10-04。Evaluation owner：路诚钺；风险R2。基于`develop@c80ec014925f0cbbbaef5486bce8422a5b4f73fb`。
PR136仍是隔离分支候选；原Task **BLOCKED**。本段实现只读输入与非执行H1计划，不产生live资格。

## 实现范围

[LiveEvaluationInputs](../../../../src/research_workbench/evaluation/live_inputs.py)显式选择
`system_evaluation_protocol@2.0.0`、Schema`0.2.0`、purpose=`live-pilot`，以及独立的
`evaluation_live_scope@2.0.0`。默认`EvaluationInputs`/Core catalog仍使用`0.1.0`，拒绝这个新Protocol；
旧H2–H5、measurement和synthetic purpose不能通过新reader转成live。
版本处理理由见[未接受的设计决定候选](M5-008_LIVE_PROTOCOL_DECISION.md)。

新[Protocol Schema](../../../../schemas/v0.2.0/system-evaluation-protocol.schema.json)复用固定的旧版
属性定义，仅增加live purpose、版本与scope ref，并要求非null admission closure。
相关common/binding定义以内嵌`$defs`冻结，可由独立v0.2 catalog读取，无跨版本内部registry拼接、
远程Schema下载或默认Core分派改变。旧v0.1和v0.2 release Schema均保持原字节。
共享Protocol的Manifest/Mode/Action/Method、A2/A3 implementation与binding检查继续复用原校验器。

新[scope Schema](../../../../schemas/v0.2.0/evaluation-live-scope.schema.json)的状态固定为
`frozen-inputs-not-authorized`，六个authority boundary均为false；执行phase白名单只有`pilot`。
它保存source commit和工件、Provider config/applicability、Windows context、预算checkpoint、
typed input closure、Tool配置与官方窗口的exact refs，以及冻结的有限输出IDs和预算/时间候选。
scope不引用自己的Protocol或未来authorization；后续外部grant从可信上下文绑定两者，避免哈希循环。
这些字段属于Evaluation/Maintainer，不进入公共model payload或Runtime Bundle。

## 实际校验与限制

reader要求调用方显式提供外部累计token ceiling，无全局默认额度。检查提议上限不超过该ceiling、
声明的历史用量与所有Provider调用预占总和不超限、Attempt/call上下界、整个pilot slots的预算覆盖、
共享每Attempt时间、freeze先后、同一北京晚间18:00后的有界窗口及整体运行时间容纳。
该窗口只检查形式；官方闲时条件和执行当时可信时钟必须由后续实际guard核对。

所有列明refs都重读并核SHA；路径越界、漂移、重复source路径拒绝。
scope中的input closure沿用已有`evaluation_case_closure`的`confirmatory`比较集合类型，
**不代表本次run用途**；新scope的执行phase仍只有pilot，后继analysis须保持primary eligibility=false。
唯一case数量必须符合Protocol；有限输出spec逐case恰好覆盖冻结集合，使用已有codec的C/S闭集、
16,384 UTF-8 bytes和容器深度5。JSON非有限值、额外authority字段和不匹配的版本/purpose拒绝。

已有H1 producer复用为`evaluation_harness_plan@1.0.0`、`compiled-not-executed`：
冻结算法、公共正向白名单、私有bytes隔离与reserved identities不变。新reader额外要求H1的
case closure和scope **exact path/hash/revision一致**；相同字节的另一ref不能替换。
H1仍描述pilot与confirmatory slots；它本身不调度，后继live入口只能执行scope允许的pilot slots。
不能因非执行plan存在就批准或启动其中任何slot。

通过输入校验只证明结构、声明之间的一致性和exact bytes。测试特意保留`qualified=false`的
applicability和fixture checkpoint作为可读取输入；reader不判断它们的真实资格或额度。
实际M6接受证据及新source/config/Windows/Host适用性、当前唯一累计账本、官方模型/窗口、
Task/Tool/egress权限、A4完整lineage与具名grant，必须由后继独立可信核验闭合。
现有1744 tokens历史不因新scope重置；当前没有新增实际调用。

## 兼容与验证

[24项离线用例](../../../../tests/test_live_evaluation_inputs.py)覆盖跨版本拒收、完整H1复用与closure
替换、外部预算/时间/phase限制、refs/schema漂移、冻结IDs、独立v0.2 catalog和新进程只读加载。
冷读输入不是cold execution replay；本地用例、安装包检查与hosted CI分别记录实际source身份。
两次新增用例的初始失败已保留：旧binding版本字段只要求非空，负例改为非法hash；H1 refs位于
`request`字段，接入检查修正后两个H1用例通过。没有删失败或用旧305项CI冒称当前head验证。

## 后继实现与原验收

下一实现节点是新版本独立preflight、实际授权/applicability/admission verifier接入、
M6 baseline与M11 Provider-backed Driver，以及实际call/Tool/Receipt/usage的失败保留和replay。
之后准备有限blind package、全部Human review冻结、受控reveal、metric/analysis joins。
这些可在隔离分支准备离线候选；共享R2接受、Task合法进入与真实执行仍遵守
[原Gate](M5-008_LIVE_PILOT_GATE.md)。完整获批run set与具名验收完成后才提议M5-008 DONE，并在M5-004前停止。
