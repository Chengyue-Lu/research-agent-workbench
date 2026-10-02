# M5-007 H1–H5 整体验收复核候选

日期：2026-10-02。Task / Evaluation owner：路诚钺；Execution 接口复核：黄毅。风险：R2。
审查基线：`develop@2618ef4fa7a1b16722e097af9a91b00b40ec700a`。本文件提出整体验收所需的
证据映射，**不自行接受 M5-007**；`docs/TASKS.md` 仍为 IN_PROGRESS，Issue #55 仍 OPEN。
[进入记录](attempts/M5-007-ACCEPTANCE-REVIEW-001/TASK.md)固定本次读取、写入与停止边界。

## 依赖与当前源码

M5-006、M6-008、M11-004/006/007 在当前 Task 清单中均为 DONE；
[Gate A](BASELINE_TRANSPORT_GATE.md) 和 [Gate B](../M11-SKILL-CLOSEOUT-GATE/GATE.md)
均为 SATISFIED。H1–H5 的六个实现切片
分别由 [PR86](https://github.com/Chengyue-Lu/research-agent-workbench/pull/86)、
[PR89](https://github.com/Chengyue-Lu/research-agent-workbench/pull/89)、
[PR90](https://github.com/Chengyue-Lu/research-agent-workbench/pull/90)、
[PR96](https://github.com/Chengyue-Lu/research-agent-workbench/pull/96)、
[PR104](https://github.com/Chengyue-Lu/research-agent-workbench/pull/104)、
[PR106](https://github.com/Chengyue-Lu/research-agent-workbench/pull/106) 合入；
[PR107](https://github.com/Chengyue-Lu/research-agent-workbench/pull/107) 只合入整体验收准备文档。
这些 merge SHA 与当前 GitHub 记录逐项一致，见[输入清单](attempts/M5-007-ACCEPTANCE-REVIEW-001/INPUTS.json)。

[独立 source/pin 核对](attempts/M5-007-ACCEPTANCE-REVIEW-001/evidence/source-audit.json)确认：
PR106 获审 head `68e612b353233bb8faf739d5012876739793cd84` 到本次基线间，
`src/research_workbench/`、`schemas/`、受信 H5 replay helper/fixture/test 没有 Git 差异，
M5-007 Task 验收行逐字相同；PR107 历史入口的五个哈希在各自声明的快照或保留 ZIP 上全部匹配。
本次审查入口另有五个基线文件内容 SHA-256，亦全部匹配。
H5 454 文件 proof ZIP 原字节 SHA-256 为
`176c47b3ebbc8e71d3cdb27f835d82a8e5af2ac876638d7ca7d0c7601a063b2d`。
历史输入 pins 属于 PR106 合入前快照，不冒充当前文档哈希。

## 对照 M5-007 验收行

| 验收簇 | 复核依据 | 当前边界 |
|---|---|---|
| 冻结计划与四臂 treatment | H1/H2 `harness_plan`、`harness_preflight` 和 H3 `harness_execution`；计划、case/replicate/arm/slice/Attempt 与 fresh retry 正反测试 | plan 非执行；A1/A2 不注入 Mode/Method、dummy Snapshot 或 Skill Assignment |
| A4 准入、overlap 与资格 | M5-006 的 overlay/overlap/comparability validators；H2 对外部 admission authority、freeze 时序、private-oracle closure、A2/A3 qualification 和 A3/A4 pairwise 独立重算 | 缺失/unknown/absent、hash drift、Supply substitution 均 fail closed；`skill-bearing-package` 不升级为 Skill-only，synthetic 不获 primary 资格 |
| 执行 transport 与生命周期 | H3 消费 M6 baseline、M11 Core/Skill；H4a 独立比较 actual binding/typed Trace fact/replay-valid Receipt；Gate B 接受 Skill-bearing closeout | completed、post-call-failed、preflight-blocked 与未启动项分开；planned View 不能充 actual facts；Harness 不取得 Supply selection |
| 评价记录与盲审 | H4a actual evidence，H4b public/private 匿名包、具名 freeze、受控 reveal；外部 Human/clock/authority 是显式输入 | 有限 synthetic rubric 只检验契约；不宣称真实 Human 审查或任意自由文本匿名性 |
| 指标与分析输入 | H4c 独立重建 run/Attempt/slice/method/observation/metric 关联、完整失败/retry 与 pairwise，13 指标四状态及 null 规则 | synthetic 全部 13 项 unavailable/null，`primary_confirmatory_eligible=false`；没有正式净收益或科研有效性结论 |
| 持久化与对抗性 proof | H5 [原始 Attempt](attempts/M5-007-H5-001/README.md) 的四臂 8 cells / 10 pairs、1 post-call failure / fresh retry、454 文件及冷回放；当前源码重新运行的 proof/负例另记本次验证 | 原 proof 不被改写；伪造数值/资格、删失败 Attempt、hash/source/Schema 漂移、越权回放均须拒绝 |

上表是 Task 验收的结构与执行契约复核，不把 synthetic proof 写成真实 case、
Provider/Tool/Human/admission 的验收。H1–H5 各 PR 的接受只证明其切片；整项具名 R2 决定尚未取得。

## 当前验证与审查缺口

当前基线的 [component push CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36955201813)
已经 SUCCESS；[source CI](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/36955201792)
仍在运行。本次已从原 454 文件 ZIP 解压至空目录，在当前受信源码下使用原 inventory ref
[独立冷回放](attempts/M5-007-ACCEPTANCE-REVIEW-001/evidence/archived-replay.json) PASS：
四臂 8 cells / 10 pairs、8 completed / 1 post-call-failed / 7 not-started，
13 指标均 unavailable/null，primary eligibility 为 false。
Python 3.11.16 H1–H5 集中测试 111/111 PASS，耗时 1924.555 秒；原始输出与命令由
[本次验证记录](attempts/M5-007-ACCEPTANCE-REVIEW-001/verification.json)及
[测试日志](attempts/M5-007-ACCEPTANCE-REVIEW-001/evidence/focused-h1-h5.log)锁定。
文档/公开接口测试另有 23/23 PASS。
即使上述检查通过，也只能作为行为和身份依据，不能替代具名接受。

PR107 的旧跨负责人批准在发布基线 rebase 后被 DISMISSED；它由路诚钺按直接指示合入，
当前 head 没有新的 cross-owner approval，也没有第 5.4 节 reviewer 不可用决定。
本次整体验收审核应把 PR107 文档及冲突解决一并纳入，而不能把旧批准复用为当前批准。
H5 的 Agent Trace capture-gap warning 继续保留。

## 请求的决定与下游边界

请黄毅复核 Execution 接口、actual facts/Receipt、Gate B 消费与当前 source/proof 身份；
请路诚钺核对 Task 全部验收、评价解释、失败/缺测量及后继 Gate。对未闭合条款保留具体反例，
回到所属切片修复。只有形成绑定当前候选与验证的具名 R2 接受后，后继 PR 才提出
`M5-007 IN_PROGRESS → DONE`，并按 Issue #55 的 Gate A、Gate B 与内部验收检查关闭条件。

M5-008 仍受 M6-004 live conformance、`A4-RUNTIME-ADMISSION-GATE` 与专项 pilot 授权阻断；
M5-001/002、M5-004/005 的真实 case、正式评价、Human 决策和 Skill lifecycle Gate 均不改变。
