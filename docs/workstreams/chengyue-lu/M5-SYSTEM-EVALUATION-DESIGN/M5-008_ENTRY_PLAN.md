# M5-008 接手与进入准备

日期：2026-10-02。Task / Evaluation owner：路诚钺；Execution 接口 owner：黄毅。
Task 风险：R2。当前状态：**BLOCKED**；本次是只读核对及文档准备，不改变 Task 状态。
接受基线：`develop@b033c0535baded6dafcbea18f638fda58858ee92`。
当前跟踪：[Issue #123](https://github.com/Chengyue-Lu/research-agent-workbench/issues/123)。
范围继续由 [TASKS](../../../TASKS.md) 与 [Live Pilot Gate](M5-008_LIVE_PILOT_GATE.md) 定义。

## 前置与责任

| 前置 | 当前核对 | 下一份必要输入 |
|---|---|---|
| M5-007 DONE | [收口完成](M5-007_CLOSEOUT_RECEIPT.md)，PR122 / Issue55 completed；Task、Gate A/B 与现有 H1–H5 证据闭合 | 冻结时重核 accepted source/validator/Schema/config 的适用性，路诚钺 |
| M6-004 DONE | Task 仍 BLOCKED；当前版本 Windows text/structured/tool/bounded evidence conformance 尚待授权重放 | 适用于选定 exact Provider/Adapter/model slot/Windows Host/Tool 的具名 live 证据，黄毅 |
| `A4-RUNTIME-ADMISSION-GATE` | 尚无本 pilot 可接受的完整 lineage；accepted source 的 projection index entries 为空 | exact candidate/Evaluation、Human admission、accepted Release、Projection、Supply/Resolver/Snapshot/Bundle/View/Host pins；路诚钺决定准入，黄毅复核接口 |
| `M5-LIVE-PILOT-AUTHORIZATION-GATE` | pilot 案例、账户、模型、Tool、预算、执行窗口与审查人尚未提供专项授权 | 独立 public/private dossier/Protocol、账户与执行人/窗口、token/turn/time/费用/retry 上限、数据/Tool/副作用范围、停止条件与 Human review 安排，路诚钺 |

后三项缺一即继续 BLOCKED，保持零真实调用。凭据只使用 credential reference，不写密钥。
M6-004 不依赖 M11-004，也不能单凭 conformance 成功替代四臂 Harness pilot。
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

第一工程设计节点是上述 live-purpose/有限审查闭包的 R2 候选。具体版本、pilot 输出格式、模型、Tool
及数值预算尚未决定；本清单不接受新 Schema 或默认授权。复用 M6 baseline、M11 Core/Skill 和唯一
Capability Resolver；不新增 arm-specific Host dispatcher、selector、fallback 或旁路 runner。

## 推进节点

1. **当前准备**：列齐 dossier、source/config、conformance、admission、authorization 与审查输入；
   每个未提供字段保持待人类决定。准备完成不解除 BLOCKED。
2. **进入核对**：收齐三个 Gate 的 exact identity/version/path/hash、具名决定和配置适用性；
   按原 Task 状态机提出合法 READY/IN_PROGRESS 候选。任何 Gate 失效即停止。
3. **R2 实现候选**：明确版本化 live-purpose 和有限输出审查契约，接入已有四臂 transport，
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

已完成 M5-007/Issue55 收口，建立独立 M5-008 tracker，记录四项前置、源码缺口和进入顺序。
只修改事实记录、导航及准备清单；源码、Schema、Registry、Task 行与所有历史 Attempt 保持。
尚未选择真实案例/账户/模型、取得准入或 pilot 授权、实现 live 入口、调用 API/Tool 或产生新 live 证据。
真实 case、Human/Claim、科研净收益、Skill promotion、Topic 5 与发行仍按原边界处理。
