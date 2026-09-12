# M6-008 Worklog

日期：2026-09-12。Accountable / implementation owner：黄毅。
这份记录是跨 Agent 实现交接的导航摘要，不替代本地保留的可见协作消息和执行记录；
不为开发过程另造科研 Agent Trace。范围与状态见 [README.md](README.md)。

## 1. 共享输入与范围确认

按 M6-008 和 ADR-0020 复核 M5 qualification / Protocol / Manifest、现有 API session 与
M11 Trace / Receipt 接口。M5 shared contract 经 PR #71 合入，接受提交为
`60bdf8c28f6cf8c52c04e481e0309bbd6e8cba8b`。本次由黄毅优先推进 A1/A2 transport；
M5 contract ownership、A3 Resolver / Harness 分工和 A4 准入链保持原定义。
候选建议只激活 M6-008 至 READY，不将源码存在或本地 PASS 当作 Task 接受。

并行写入按 envelope / fixture、runtime、closeout 分开；本目录补充候选的接口说明和风险。
正式可见协作记录留在本地归档，最终 PR 承载可审查的变更与验证摘要，不提交机器路径、账户或原始会议内容。

## 2. Envelope 与 A2 producer

复用现有 EvaluationInputs 和 M5 `validate_qualification`，新增独立 envelope，而不要求 plain arm
具备虚构的 Method / Snapshot / Skill Assignment。A2 record 仅由 M6 producer 生成，调用共享 validator；
Task-specific Tool surface 在完整 qualification 验证后确定。

实现讨论发现完整 Task 的目标与 required_outputs 含 `method-resolution` 等控制义务，直接投影会污染
plain arm。改为由 Manifest context 明确冻结独立 public projection，并要求其 exact Task pin、输入引用
及实际 UTF-8 内容闭合。Schema 继续对白名单之外的字段拒绝，不建立自然语言自动审查机制。

Envelope 专项分阶段通过 8 项，包含共享验证、A1/A2 差异、Task 替换/未知字段、未冻结输入、
重编译不一致、非 UTF-8 字节与无效 Tool JSON Schema。测试 fixture 复用现有 M5 公开契约构造，
未生成私有 oracle 或额外 A4 对照。

## 3. Runtime / closeout 接缝与修正

runtime 使用真实注册 Provider 和文件绑定的本地函数，typed facts 绑定 Provider/Tool 的前后调用事件
及使用时文件闭包。closeout 从 Trace / facts / 最后响应派生结果，并以独立文件回放验证 Receipt；
预期的 Provider/Model metadata 不直接充当 actual execution 证据。

限定接缝审查与实际失败案例发现并修正以下问题：

- 把 `max_input_tokens` 数值用作 Tool 结果字符上限；改为已 pin ProjectProtocol context 中独立的
  `baseline_transport.max_tool_result_chars`。fixture 明确选择 16000，原 data_policy_ref 保持不变。
- Attempt 仅核对 write_scope；补充 Task 文件权限 / allowed_roots 和同名 Task budget ceiling。
- DataPolicy fallback 混同 ProjectProtocol.data_boundary 与 ExecutionPolicy.data_egress；当前实现明确
  只消费 Schema-valid ProjectProtocol，不从不识别的对象导出空限制。
- 结构化 ModelResponse 的嵌套凭据字段在 Trace 与输出工件中走了不同的脱敏路径；现在先将
  dataclass 转为普通结构，再复用现有递归脱敏逻辑。Trace 与工件均保存脱敏结果，发生脱敏时
  transport Validation 保留失败；没有改写全局 Trace 契约。
- 独立回放只检查 Tool fact 前后一致，未与资格链的具体实现配对；实际反例以已读公开输入
  替代两条 Tool ref 并重算外层哈希，旧实现错误接受。strict replay / successful closeout 现按
  exact Task、Tool name 与 implementation pin 比对；失败 producer 仍可保留漂移前已观察的事实。

失败测试保留真实失败结果：Tool 调用前源码漂移时函数不执行；Tool 返回后 envelope 漂移时第二次
Provider 不启动；Provider 异常和调用后超时保留失败；改写并重哈希 Receipt 的 actual binding 仍被
独立 Trace facts 拒绝。源漂移时保存失败不等于 strict replay 通过。

## 4. 当前证据与交接

本轮集成专项为 21 项 PASS（8 envelope + 13 execution），运行 79.411 秒。执行测试实际调用 A2 本地函数，
并在 fresh process 中验证 cold replay 不重新调用 transport / Provider / Tool；验证范围是合成离线工程行为。
本记录不声明 hosted CI、全仓 full、全局 coverage、安装或模型测试已经通过。

最终 Tool 引用修复前，三个新增模块的局部 coverage 为 line / branch 100%（480 条可执行语句、86 个分支）。为满足既有
impact 规则，仅将现有 A1 成功案例改为使用 API 默认 UTC 时钟并窄复验该方法（8.124 秒）；
没有新增测试方法，源文件未变，coverage 在同一源码上追加合并。
文档链接、Schema catalog 和 coverage inventory 三项窄检查 PASS（0.722 秒）。
Tool 引用修复以同一 A2 成功产物验证：旧源码反例 FAIL（10.308 秒，未拒绝变造）；
修复后同一方法 PASS（10.770 秒）。未新增测试方法或重新生成第二套执行材料。
覆盖率文件保留为修复前历史证据，最终源码覆盖由 hosted CI 验证。
最终候选的 hosted 检查和 review 结果由 PR 记录。
没有对应变化或失败时不重复整套测试。尚需 R2 跨 owner 审查及届时必需检查，之后才作 M6-008 接受决定。
M5 真实运行条件以及 M12/M13 的 Phase C Human review / 真实反馈入口继续独立推进。

具体限制和后续触发条件见 [RISK_LEDGER.md](RISK_LEDGER.md)。
