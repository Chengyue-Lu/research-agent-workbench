# M6-008 开发接手准备

日期：2026-09-15。准备者：路诚钺侧 Codex；Task / Execution owner 仍为黄毅。
授权：用户要求先收口 M11-007 / Gate B，再准备接手 M6-008。此记录不修改 Task 定义、owner 或验收。

## 接手基线

- 已有候选：[PR #75](https://github.com/Chengyue-Lu/research-agent-workbench/pull/75)，分支
  `codex/m6-008-baseline-execution`，head `8f68879e781cbc09ba60f3718f436a4a5de42ae2`。
- 候选原基线：`60bdf8c28f6cf8c52c04e481e0309bbd6e8cba8b`；接手检查的 develop：
  `7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba`，包含 PR81。
- develop 的 M6-008 仍 PARKED；PR75 提议 READY，尚无审核记录。其所有硬依赖已 DONE。
  此轮只准备接手；正式状态变化随 M6 实施候选审查，不放进 M11 收口提交。
- 已建立隔离本地分支 `feature/m6-008-takeover`，固定在 PR75 head，工作区 clean。
  原远端候选未改写；接手正式开始时再次核对 head，吸收期间新提交。
- 原候选 CI：[34692847340](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/34692847340)，
  base `60bdf8c` / head `8f68879` / target `bcd612584a49c7a5b42299df4dc1ec836c64e24a`。
  PR75 报告双 Python 各 1232 PASS、coverage 1196 PASS，含 21 项 M6 专项；本轮未重算这些历史产物，
  它们不能替代接手后新基线的 CI。

## 接续的具体节点

1. **集成当前基线**：在同一 PR75 分支 rebase 最新 develop，并以 expected old head 的 lease 推送。
   只读 merge-tree 预检发现 `docs/M_SERIES_IMPLEMENTATION_MAP.md`、`docs/STATUS.md` 两处冲突；
   合并时保留最新 M11/Gate B 和 M14 状态，再并入 M6 候选说明。实际 rebase 须重新判断冲突。
   `document_kinds.py`、coverage policy、Schema catalog 测试和 TASKS 可自动合并，但需逐项检查语义。
2. **独立验收已有实现**：先看 `baseline_envelope.py` 的公开白名单和 A2 qualification，
   再看 `baseline.py` 的逐 request/Tool use-boundary 校验、trusted clock 与 actual facts，
   最后看 `baseline_closeout.py` 的独立重载、事实时间顺序和三种生命周期。借用 M11 review 的检查点，
   不把发现于 M11 的缺陷预先断言为 M6 缺陷。
3. **复现并修复实际缺口**：使用现有 8 项 envelope / 13 项 execution fixtures。重点核对 wrong-kind
   零调用阻断、每次使用前 exact pins、后续矛盾读取、调用后 model drift、Tool fact 对真实实现的绑定、
   output/Validation closed set，以及异常/超时后的事实保留。出现真实缺口后补最窄独立反例。
4. **固定新证据**：运行受影响的 M5 qualification、M6、Core/Skill/schema 回归；保留 A1/A2 synthetic
   complete/failed/blocked 产物及禁止 Provider/Tool 调用的 fresh-process replay。按新 CI plan 执行
   behavioral、impact/repository coverage、package、repository 与 governance；不得复用旧 head 的绿灯。
5. **R2 接受**：在 PR75 更新 exact head/base/CI 与风险，请 Execution owner 和 M5 consumer 复核。
   接受并合入后，M6-008 才可 DONE；届时 M5-007 可按全部剩余条件提议 READY。

## 范围与接口

读集：M6-008 Task、ADR-0020、M5-006 shared contracts、PR75 的 workstream/21 个变更文件及其
直接 session/Trace/qualification 依赖。写集在实施开始时固定为 M6 baseline modules/schema、相关测试和
文档、必要的共享 document-kind/coverage 注册；M5 shared contract、M11 Runtime ownership 保持原定义。
用户对接手的授权允许准备这些必要输入，任何扩大产品或研究权限的变更须另行接受。

A1/A2 的公开 payload 只含冻结的 instruction/input/output，A2 仅增加 exact Tool interface；
A2 formal execution 仍要求 runtime-execution qualification、逐 use-boundary pins 与预算语义。
M6 不产生 A3 record，不选择 Supply，不读取 Skill/oracle，不新增付费/live 调用。
M5 primary `A4 − A2` 保留 transport difference；A4 admission 与真实 case/live Gates 独立。
