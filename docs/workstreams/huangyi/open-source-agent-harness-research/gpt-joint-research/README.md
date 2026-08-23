# GPT 与黄毅联合调研子工作流

> 文档性质：工作流导航；不是 TASKS、ADR、Stable Architecture 或双方正式决议
> 状态：Working Paper 审查中
> Owner：黄毅（`let778750-cpu`；昵称 `huangyi855`）
> Reviewer：路诚钺（`Chengyue-Lu`）

## 范围

本子工作流用于独立承载 GPT 与黄毅围绕开源 Agent Harness 的联合调研整理，重点覆盖：

- Agent Team 通信拓扑与受控同级证据交换；
- 上下文隔离、Memory admission、恢复和审计风险；
- AnySearch 的搜索能力边界与 RWB 证据分层；
- Ruflo 的通信、Federation、Memory、Trace 和性能主张审计；
- 候选机制的可证伪假设、对照实验与消融指标。

规范调研文档为：

- [GPT 与黄毅联合调研会话整理](../GPT_HUANGYI_JOINT_RESEARCH_SESSION_SYNTHESIS.md)

## 非目标

- 不修改 `docs/TASKS.md` 或任何任务状态；
- 不修改 ADR、Schema、Registry 或 Runtime；
- 不解除 Architecture Hold；
- 不把 GPT 建议、候选创新或上游项目宣传升级为项目真值；
- 不继承或修改 PR #28 的 GLM 联合调研文件与提交历史。

## 治理边界

本子工作流从 `develop` 洁净建立。后续如需采用任何 Runtime、Team、Memory、Federation 或 Search 接口，必须在 M8-003 后另立 Task、ADR、实现分支和验收测试。
