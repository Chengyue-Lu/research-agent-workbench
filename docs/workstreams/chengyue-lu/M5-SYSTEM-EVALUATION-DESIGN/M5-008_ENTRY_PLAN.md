# M5-008 接手与进入准备

更新：2026-10-04。Task / Evaluation owner：路诚钺；Execution 接口 owner：黄毅。
Task 风险：R2。当前状态：**BLOCKED**；本次包含离线设计与只读实现候选，不改变Task状态。
当前核对基线：`develop@c80ec014925f0cbbbaef5486bce8422a5b4f73fb`；原接手/准备观察分别绑定b033c05/6fa。
当前跟踪：[Issue #123](https://github.com/Chengyue-Lu/research-agent-workbench/issues/123)。
范围继续由 [TASKS](../../../TASKS.md) 与 [Live Pilot Gate](M5-008_LIVE_PILOT_GATE.md) 定义。
用户已建立推进到 M5-008 run-set 验收、M5-004 前停止的目标；当前
[决定候选](M5-008_DECISION_CANDIDATE.md)把 Human 案例/准入/专项授权与可离线工作分开。

## 前置与责任

| 前置 | 当前核对 | 下一份必要输入 |
|---|---|---|
| M5-007 DONE | [收口完成](M5-007_CLOSEOUT_RECEIPT.md)，PR122 / Issue55 completed；Task、Gate A/B 与现有 H1–H5 证据闭合 | 冻结时重核 accepted source/validator/Schema/config 的适用性，路诚钺 |
| M6-010 DONE | 已由 PR133 收口；[source66 / installed002 / native005 的 Flash Windows部件证据](../M6-GENERAL-PROVIDER-IMPLEMENTATION/M6-010_COMPLETION.md)已接受；累计1744 tokens、held0，原失败/限制保留 | 本 Pilot 的 exact source/config/model/profile/Windows Host/Tool 尚未冻结；逐项核对适用性，旧报告不能重绑新 Driver/graph，黄毅 |
| `A4-RUNTIME-ADMISSION-GATE` | 尚无本 pilot 可接受的完整 lineage；accepted source 的 projection index entries 为空 | exact candidate/Evaluation、Human admission、accepted Release、Projection、Supply/Resolver/Snapshot/Bundle/View/Host pins；路诚钺决定准入，黄毅复核接口 |
| `M5-LIVE-PILOT-AUTHORIZATION-GATE` | pilot 案例、账户、模型、Tool、预算、执行窗口与审查人尚未提供专项授权 | 独立 public/private dossier/Protocol、账户与执行人/窗口、token/turn/time/费用/retry 上限、数据/Tool/副作用范围、停止条件与 Human review 安排，路诚钺 |

A4 与 Pilot 专项授权仍缺失，Task 继续 BLOCKED；新的 Provider binding 适用性也须在调用前闭合。
本准备阶段保持零真实调用。凭据只使用 credential reference，不写密钥。
当前 M6-010 不依赖 M11-004，也不能单凭 conformance 成功替代四臂 Harness pilot；原 M6-004 的 OpenAI 验收保持独立。
M5-001/002 不是 pilot hard dependencies；pilot 使用单独 Human-approved dossier，后续 held-out 重新审计暴露和调参。

## 当前源码已经限定的工程边界

以下是 b033c05 的静态观察，输入内容 pins 在
[接手 Attempt](attempts/M5-008-ENTRY-001/README.md)；它们不是新的执行或匿名性证明。

| 表面 | 已观察的限制 | 进入实现前要明确什么 |
|---|---|---|
| H3 `_context` / `execute_harness` | `harness_execution.py` 强制 Protocol purpose=`synthetic-contract-proof`；Python ports 不是 live grant | 独立版本的 live pilot 入口如何消费全部外部 Gate 和 use-boundary 重验；不得将真实调用标为 synthetic |
| H4a/H4c 证据与分析 | 多个 producer/Schema 固定 synthetic purpose，不能把旧结果改名用于 live | live-purpose 的记录身份、来源闭包及 pilot-only analysis scope；旧 v1.0.0 语义/回放保持 |
| H4b review/projection | 当前 rubric 是 synthetic integer equality；公开投影只接受单字符整数 | Human 先冻结 pilot 输出格式和审查范围，再设计有限白名单 projection/rubric、freeze/reveal；不声称任意自由文本匿名性 |
| A4 index | `registry/skills/release-projections.json` entries=[] | 提供合法 Release→Projection→Supply lineage；不能用测试 Projection、candidate direct-load 或同名 substitution 代替 |

第一工程设计节点已形成[准备与设计候选](M5-008_PREPARATION_PACKET.md)：建议独立 live-purpose@2.0.0、
有限 claim/source/relation 输出与四臂接入。用户已选独立工程案例类型、希望先考虑一般化Skill；
[具体决定候选](M5-008_DECISION_CANDIDATE.md)和[Skill候选包](M5-008_GENERAL_SKILL_CANDIDATE.md)
提供scope cards、非发现目录源包、正式Need与独立准入前评价方案；exact案例/准入、版本/输出/模型/Tool
及预算仍待冻结与人类接受。
本清单不接受新 Schema 或默认授权。复用 M6 baseline、M11 Core/Skill 和唯一
Capability Resolver；不新增 arm-specific Host dispatcher、selector、fallback 或旁路 runner。

隔离分支已形成[有限正文codec实现候选](M5-008_OUTPUT_CONTRACT_PACKET.md)，先进行离线结构/泄漏/兼容校验。
另形成[显式v2 Protocol/scope只读实现](M5-008_LIVE_PROTOCOL_PACKET.md)：旧入口拒收新版，
已有H1仅编译计划，声明与exact refs校验不认证applicability/checkpoint/grant。
[独立v2 preflight](M5-008_LIVE_PREFLIGHT_PACKET.md)继而复用共享资格、overlap/A4/pairwise校验，
需可信外部context和四项核验接口；真实reader factory/每次调用guard仍待闭合。
AGENTS将治理施加于共享接受边界；这个P0.5节点不把外部Gate写成满足，也不激活Task或执行API。

## 推进节点

1. **当前准备**：列齐 dossier、source/config、conformance、admission、authorization 与审查输入；
   每个未提供字段保持待人类决定。准备完成不解除 BLOCKED。
2. **进入核对**：收齐 A4/Pilot 两个外部 Gate 与 M6 binding 适用性的 exact identity/version/path/hash、具名决定；
   按原 Task 状态机提出合法 READY/IN_PROGRESS 候选。任何 Gate 失效即停止。
3. **R2 集成与接受**：隔离实现候选可在进入前离线准备；合法进入/共享接受再闭合版本化live-purpose与四臂transport，
   保留全部失败/retry/cost；正反用例先验证零调用拒绝、身份/预算漂移、cold replay 和用途隔离。
   完整 R2 review 与 CI 仍按该候选自身条件执行。
4. **获批 live pilot**：冻结独立 public/private dossier、Protocol/run inventory 与 source/config；
   完成预注册 run set，至少一个完整 case×replicate 四臂 block；记录 fresh Attempt/session、
   actual Provider/Tool/Host facts、Trace/Receipt、失败/停止和未完成 slots。
5. **工程验收**：新进程 cold replay → blind Human review/freeze → reveal → metrics/analysis joins，
   路诚钺与黄毅接受 exact source/config/run set 后，才以 feature/R2 提议 M5-008 DONE 并关闭 Issue123。

一个完整 block 只是工程覆盖下限，既不代替完成预注册 run set，也不论证科学样本量。
pilot 数据不进入 primary confirmatory run set，不因 phase 标签而绕过 overlap/pairwise 资格重验。
需要零调用阻断、post-call failure/fresh retry、预算停止和篡改/actual binding drift 拒绝的证据；
自然失败缺失时，只有在专项授权边界内才允许受控本地故障注入，并单列为故障验证。

## 本次交接输出与停止点

已完成 M5-007/Issue55 和 M6-010 部件收口，独立 M5-008 tracker 继续 OPEN；当前形成有限 live-purpose/
review 候选、exact-pin 输入清单与 P0–P4 顺序。用户另授权设为推进目标，到M5-008全部run-set具名验收后
停止、进入M5-004之前。当前修改事实记录、导航、设计准备与`skill-lab/candidates/`中的纯说明候选；
新增pure codec与显式v2 live输入reader/Schema/测试候选；旧H1–H5/source/Schema、Registry、
Task行、默认Skill发现和所有历史Attempt保持。
尚未冻结exact真实案例/账户/模型、取得准入或pilot授权、实现live执行器、调用API/Tool或产生新live证据。
真实 case、Human/Claim、科研净收益、Skill promotion、Topic 5 与发行仍按原边界处理。

2026-10-02通用Provider定义修订已接受：[M6-009/010](../M6-GENERAL-PROVIDER-DEFINITION/PLAN.md)已DONE；
原M6-004 OpenAI范围保留。M6的已保留部件调用不等于本Pilot；本次准备没有新增调用或live PASS。

M12按用户指示委托现有「RWB开发 (1)」窗口，先处理Phase C/Topic5进入候选；不成为本Pilot新增依赖。
