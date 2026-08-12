# 暂停点与下一步规划

状态：按用户要求暂停继续构建

暂停提交：见 `agent/m1-provider-neutral-foundation` 分支的最新已推送提交

日期：2026-08-13

## 1. 当前可恢复入口

恢复工作时先读取：

1. `README.md` 的当前状态与边界；
2. `docs/TASKS.md` 的各里程碑证据；
3. `CHANGELOG.md` 的最新条目；
4. 本文件的执行顺序；
5. 目标任务对应的 ADR、Task Packet、Skill Assignment 和 fixtures。

不要从旧聊天记录重建项目状态，也不要在恢复时加载全部候选 Skill、ZIP 内容或原始科研材料。

## 2. 恢复后的优先顺序

### P0：真实 Windows Provider conformance

- 在真实 Windows 用户上下文分别选择一个 OpenAI、Anthropic、Gemini 模型；
- 不在 Codex 沙箱读取、回显或导出令牌；
- 使用既有有界 runner，每家最多三个合成请求；
- 保存脱敏 conformance report，失败也保留；
- 验收：每家得到当前账户/模型的 `passed` 或可定位 `failed`，不把认证成功当作 API shape 通过。

### P1：两个真实原生子 Agent 垂直切片

- 运行 `evidence-scout + literature-evidence-extraction`；
- 运行 `simulation-auditor + simulation-vv`；
- 固化 Attempt、Skill Assignment、Handoff、Transfer Manifest/Audit、Context Snapshot 和 Execution Receipt；
- 至少人工抽查一次压缩前源条目与 Handoff，记录 preserved/distorted/unverifiable；
- 验收：删除子 Agent 会话后，主 Agent 仍能只凭工件恢复任务状态。

### P2：候选 Skill 的四类真实配对评估

- 对 `claim-preserving-rewrite` 运行 trigger、non-trigger、boundary、adversarial；
- baseline/with-Skill 使用相同 provider、model、脱敏配置、基础上下文和 checker；
- 独立盲评后再揭示条件；
- 验收：只形成 `eligible-for-human-decision` 或 `not-eligible`，不自动写 accepted Registry。

### P3：选择真实科研案例并建立对照

需要研究者先提供或批准：问题边界、可用来源/数据、隐私边界、Claim ceiling，以及“什么结果值得继续”。随后建立单 Agent、轻量委派、多 Agent 三组对照，记录质量、返工、上下文、时间、token/成本和人工决策负担。

### P4：仅由真实消费者触发后续实现

- 有预算的 client-tool loop runner；
- source admission、promotion 与 Run reproducibility；
- 观察统计、实验、理论推导等模式的专用 Skill；
- streaming、multimodal 或 server tools。

没有真实消费者时保持 PARKED，不为架构图补空模块。

## 3. 恢复前需要的输入

- 真实 Windows 中可用的 provider/model 名称；
- 一个证据综合案例和一个理论/仿真案例，或明确只先做其中一个；
- 数据是否允许外发以及允许的 provider；
- 真实评估可接受的调用/金额/时间预算；
- 盲评者与最终 Skill 准入决策者。

## 4. 不应在恢复时做的事

- 不重新实现平台已有的子 Agent 调度器；
- 不自动安装 ZIP 或候选 Registry 中的 Skill；
- 不把所有研究模式合并为一条固定科研流水线；
- 不用更多 reviewer Agent 挽救缺少工件或定义不清的任务；
- 不因 fixture、Schema 或离线测试通过而宣称科研价值已经验证。
