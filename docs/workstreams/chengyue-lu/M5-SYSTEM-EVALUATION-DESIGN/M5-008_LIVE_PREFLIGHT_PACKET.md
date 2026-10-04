# M5-008 live preflight 实现候选

2026-10-04。Evaluation owner：路诚钺；Provider/Host接口复核：黄毅；风险R2。
PR136隔离候选，未接受；M5-008 Task仍BLOCKED。本段没有真实Provider/Tool调用。

## 输入与重算

新[compiler与reader](../../../../src/research_workbench/evaluation/live_preflight.py)产生独立的
`evaluation_live_preflight@2.0.0`、Schema`0.2.0`、purpose=`live-pilot`。
[Schema](../../../../schemas/v0.2.0/evaluation-live-preflight.schema.json)在v0.2 catalog内自包含，
状态固定为`preflight-checked`，六个authority boundary全false。旧H2 producer/record和默认Core入口不改。

`FrozenLiveContext`由可信调用方独立提供Protocol、scope、H1 plan、case closure、Provider config/
applicability、Windows context、预算checkpoint与authorization refs，以及source commit、case freeze、
run ID和累计token ceiling。引用沿用共有FileReference normalization，固定path/hash；对象和引用副本不可变。
不得从待验preflight中取回自己的expected context或时间。

compiler重读这些工件，核对context与scope、外部ceiling和冻结时间，拒绝过期的scope窗口。
preflight可在执行窗口开始前准备；这不核实官方闲时或执行当时的可信时钟。
H1直接调用原非执行plan validator重算。A2必须消费原M6 producer产出的qualification；
A3消费已有qualification。共享资格、runtime availability、overlap、A4 lineage与pairwise
校验器直接复用，逐case核对Task、overlap、A3/A4引用与pre-run阶段，再重算M6 baseline公共payload。
case bindings必须恰好覆盖所有冻结case；unresolved overlap拒绝。
不论共享overlap是否held-out，所有输出case的primary_confirmatory_eligible和pilot_primary_eligible均false。

validator身份显式为`evaluation-live-preflight@2.0.0`，记录所调用模块的source hashes及版本命名空间
Schema digest。它描述本preflight校验器，完整Provider/Host实现图仍属于独立applicability核验。
所有输入和Schema在外部核验后及返回前复查；校验期间source身份变化拒绝。

## 外部核验边界

`LivePreflightVerifiers`要求四个可信Maintainer接口，没有默认回调：

| 接口 | 必须由调用方独立核实的事实 |
|---|---|
| admission | 已有完整A4 lineage的实际Evaluation、具名Human接受与promotion来源 |
| authorization | 已冻结context下的具名Pilot专项权限、数据/Tool/预算与有效期 |
| applicability | 已接受M6证据及当前source/config/install/Windows/Host的真实适用性 |
| budget_checkpoint | 实际唯一账本的冻结prefix、已知累计用量、未决预占与上限 |

前三项只接受布尔`True`；字符串、整数或文件内的`approved`/`qualified`声明不能代替核验。
外部接口接收独立副本；接口异常只产生固定诊断，原异常文本及exception context不外泄。
当前实现提供接入接口，尚未实现真实authority/applicability/journal verifier factory。
测试中的独立fixture authority仅覆盖其合成环境，不是生产默认许可。

预算接口须返回不可变`VerifiedBudgetCheckpoint`，其ref与外部context一致，usage完整、held=0，
已知总量等于scope历史，scope上限≤账本上限≤外部ceiling。DTO是可信reader的返回值，
不是从某个JSON `verified=true`字段生成的证明，也不是当前可用余额或新的调用预占。
运行前及每次Provider/Tool入口仍必须核实当前累计账本、权限、source/config与可信时间。
现有实际历史1744 tokens和10million上限保持；本段临时SQLite测试的合成用量不计作真实调用。

## 验证与后继

[离线测试](../../../../tests/test_live_preflight.py)及其[fixture](../../../../tests/live_preflight_fixtures.py)
覆盖完整共享链路重算、M6 A2 producer隔离、外部ref/run/source/time替换、缺失/假授权、
预算类型/实际临时账本/未决用量/上限、unresolved overlap、case/Task/pairwise替换、
输入与Schema漂移、purpose/version/authority拒收，以及新进程重算和输入字节保持。
本地24项preflight、24项live输入、22项codec及46项相关用例共116 PASS；
提交字节复验、安装包与hosted CI分别保留其实际source身份。初始失败保留在私有Attempt。
新进程测试只证明合成preflight重算，不是实际execution Receipt的cold replay。

下一节点是实际verifier factory与每次调用guard、M6 baseline/M11 Provider-backed Driver和
真实响应/usage/Receipt失败保留；随后有限blind package、全部Human review冻结、reveal及
measurement/analysis joins。真实A4准入、案例/oracle冻结、专项授权与全部run-set具名验收继续由
[原Gate](M5-008_LIVE_PILOT_GATE.md)约束；完整M5-008完成后在M5-004前停止。
