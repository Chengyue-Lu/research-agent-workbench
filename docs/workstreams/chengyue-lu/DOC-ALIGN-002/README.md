# Accepted-state documentation maintenance

- Audit ID：`DOC-ALIGN-002`；责任人：路诚钺（`Chengyue-Lu`）。
- 风险：R2；`docs/decisions/README.md` 触发 accepted policy 的路径最低等级。
- 基线：`develop@11c3b57dfbf8af0dc2587fc421d097e2544941c3`；目标分支：`develop`。
- 工作分支：`docs/accepted-state-alignment-20260911`；PR class：`feature`。
- 状态：维护修订已准备，等待 exact-head CI 与 `let778750-cpu` cross-owner review。

## 输入与范围

按用户于 2026-09-11 提供的 D0～D5 文档维护表执行 D1～D4。Task 主表来自上述 frozen base 的
[TASKS](../../../TASKS.md)，当前实现覆盖、派生施工位置、模块导航与 Gate 状态据此校正：

| 已核实输入 | 合入 develop 的事实 | 本次维护 |
|---|---|---|
| [PR #62](https://github.com/Chengyue-Lu/research-agent-workbench/pull/62) | `2026-09-10T23:50:24Z`；`11c3b57dfbf8af0dc2587fc421d097e2544941c3` | M4-004 accepted bounded reconstruction；M4-001～004 主表均 DONE |
| [PR #61](https://github.com/Chengyue-Lu/research-agent-workbench/pull/61) | `2026-09-07T03:43:21Z`；`b8a38a1d0cea4e8422ade8481aec4c277250d6cb` | M4-003 accepted Claim evidence localization |
| [PR #60](https://github.com/Chengyue-Lu/research-agent-workbench/pull/60) | `2026-09-10T01:47:26Z`；`f78fae6bfd57085a244ca63918d7669c501f2812` | M14-001～003 DONE；继续保留 release Gate |
| [PR #56](https://github.com/Chengyue-Lu/research-agent-workbench/pull/56) | `2026-09-04T17:13:19Z`；`6a032e12c30a88a501258eec8c0b5d6c6082d81d` | ADR-0020 index Accepted、Gate A SATISFIED |

当前 Phase D 入口为 M5-006；M6-008 等待其 shared contract，M5-007 还受 Skill closeout replay Gate
约束。M11-005/006 已实现的 projection/mapping 与空 production index 分开表述。

D0 的 M14-004 activation 和 D5 public documentation surface 属于独立 M14 lane。维护分支中的
M14-004 继续按 canonical TASKS 为 PARKED，M14-005 为 BLOCKED；本次不改变 TASKS、root README、
Getting Started、release surface 或 Runtime/Schema/Registry。基线 TASKS 后方 owner 摘要仍含旧 M4
candidate 文案；本次以 canonical Task 行为依据，该共享文件留给正在推进的状态维护。

## 证据与停止条件

- 读写限于本 PR 的 11 个既有文档、本 workstream、owner 索引与有界
  [Attempt archive](../../../../work/DOC-ALIGN-002/A-20260911-001/INDEX.yaml)。
- ADR-0020 正文、Gate 第 2 节之后的 frozen mapping 和 M4 workstream 历史正文逐字节保留。
- 文档测试检查内部链接与 surface ownership；范围检查确认代码、契约、TASKS 和 public surface 无差异。
- 验证命令与结果固定在 Attempt archive；最终 commit 的 CI 和治理结果以 PR checks 为准。
- 既有合入记录只证明 bounded implementation 的接受，不证明真实 M5 结果、科学正确性或 release authority。
- 以新 PR 和独立 review request 为本轮交付终点；具名 owner 审查与 merge decision 仍待完成。

处置：**ADAPT** 用户指南的 D1～D4，按 accepted base 校正文档；D0/D5 继续由 M14 lane 承担。
剩余风险见 [Risk Ledger](RISK_LEDGER.md)。
