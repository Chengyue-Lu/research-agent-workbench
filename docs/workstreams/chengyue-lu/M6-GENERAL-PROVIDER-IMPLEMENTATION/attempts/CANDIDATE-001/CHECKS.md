# 候选检查范围

以下均为离线候选验证，真实 Provider/API 和 Key 值读取为 0。委派切片没有安装；
根最终检查在本 worktree 的独立环境安装当前 wheel 与冻结版本的测试依赖，原有环境未修改。

- 配置/profile：原切片 Python3.11 和 3.14 各 29 tests，其中 28 PASS、1 Windows 符号链接权限 skip；
  十一家 Schema/config 正例、77 独立反例，九家实际文本编解码通过、两家明确拒绝。
- 协议：29/29 PASS；四协议、实际 profile、精确非思考控制、角色/Tool/Schema/usage/stops/安全错误反例。
- 工厂：最新源 15/15 PASS，官方已关闭 Google 模型在凭据前拒绝。
  八家 fake 正例及三条阻断覆盖深冻结配置、漂移、Schema 本地验证、指定非 strict Tool、
  畸形响应和请求 Schema 的安全诊断。DeepSeek Responses 未臆造官方未定义的 strict 成员。
- 工厂独立审查：11 个先前工厂检查与 5 个对抗检查通过；发现的错误上下文和实际 defaults 漂移已修复复验。
- Session：修复后 owner 离线检查 80/80 PASS，含 37 新政策、19 原 Session、22 原三家 Adapter 和 2 kernel。
  当前请求与 Tool 参数/结果在 capture 后重新校验；默认循环 AST 与起点相同。
  显式政策仅接收独立的闭集隐私摘要 sink，拒绝 generic AgentTraceRecorder，防止已发现的 raw dataclass Trace 缺口。
  Tool context 的 local-history 事实与 Provider.generate submission attempts 分开计数；
  独立修复复验 7/7 有界 PASS，所复核源码字节与 owner 冻结一致。
- 绑定：11/11 直接测试通过，含新 envelope 1.1 的 fake 执行、独立新进程 cold replay、篡改和使用前漂移；
  原 baseline 最终联合 56/56 PASS，source freeze receipt 已保存。

分切片 receipt 位于本候选 worktree 的忽略目录 `.rwb/m6-general-prototype/` 的
profiles、wire-codecs、factory、factory-review、binding、session 和 session-review。
## 冻结源整合检查

源提交 `02695d854d7bfd27a67feb375d4908dcc9cabced`，组件差异起点 `db46c8f`：

- actual component：477 tests，**475 PASS、2 Windows skip、0 failure/error**，unknown paths 0，308.454 秒；
- repository：**198 documents / 0 errors / 0 warnings**；直接新旧 Schema/配置分派、仓库与 CI 检查 **44/44 PASS**；
- 当前 3.11 wheel 的独立安装 smoke **8/8 PASS**，10.343 秒；公共新接口导入、12 个改动源码与 Git blob 全等；
  默认 v0.1 catalog 110 Schema，全部版本共 111，pip check 无破损依赖；
- 11 profile / 33 正例 FileRef 与 working/Git HEAD 字节同 hash，独立有界复核 PASS；
- 前一纯 public surface 检查 **13/13 PASS**；最终文档检查在证据摘要提交后补验。

第一联合源 `a3fe48a` 的 471 tests 中 3 failures、2 skip，及 repository 的 66 errors 保留。
实际原因是旧 adapter 字段校验、新 profile 类型分派及新 Schema inventory 未整合；已在当前源修复。
另保存 CRLF profile pins 与 Git LF blob 不一致的原始候选，33 个正例引用已改为可移植字节。
组件测试中的 `installed-component-smoke-v1: failure` 是故意失败的单元测试 stdout，不能当安装候选结果；
当前 wheel smoke 有独立的 8 步成功 receipt。

以真实 develop `1c9cef2` 作 feature 发布预检仍有 **5 个 Task-definition 错误**：
未接受的 PR125 定义随候选源存在，不能合法混入产品 PR。该拒绝保留，未创建 implementation PR、
未 merge，也未把本地组件 PASS 当具名接受。源/test 与最终摘要提交的字节等价需另核。
当前仅验证一条 3.11 wheel 路径；profile 资源尚未纳入安装 catalog，未执行完整 direct/sdist、多 Python portable 验收。
完整 full/coverage 或 remote live 证据不在本轮声称范围。

初始 Runtime 资源缺失、profile/codec 政策不一致、测试 fixture 错误及独立审查原失败日志保留。
不能用后续 PASS 覆盖前一源版本的失败，也不能把较早源哈希上的检查移用到新源。

## 18:07 heartbeat：进程内用量记账切片

新增 `conformance_ledger.py`，文件 SHA256 为
`e0caed691bc8a007cfecb22e7586105e5dc990305baa5fea779ab6b97350d3e2`；
对应测试 SHA256 为 `7a4dfe2fa11265cffa37d1496a36c17b07818fc421a4fcf41eddc07fbf061bd4`。

- owner focused **29/29 PASS**；独立复核 **8/8 workflows + 29/29 tests PASS**，源码前后稳定；
- root 记账、CI 登记及文档/public surface 联合 **67/67 PASS**，无 skip/error/failure，三个直接输入哈希稳定；
- 原始独立 P2 为异常隐式上下文带出 Provider 错误，已清除 cause/context 并补真实 traceback 回归；
- root 首次验证器缺少 repo import path，产生两个 `tests` 导入错误；仅修验证器，原日志保留，未改产品源；
- 新测试已登记 adapters 组件；当前新切片未重新构建 wheel、运行 full/coverage 或真实 conformance。

预占、Provider invocation、调用者报告的 send attempt、响应及结算事实分开记录。
失败用量仍累计；未知用量保留预占并阻断，不能通过 fresh Attempt 清零。
缺少 reported cost 时保留有效 token 数，金额仍 unknown，费用核对及暂停条件由实际 driver 负责。
本 helper 无现有入口消费者，仅约束同一进程内、调用者声明的输入上界及 send/verified receipt；
不证明计费上界、真实 HTTP 发送、跨进程持久余额、账单结算或 Task/live 接受。
本切片 archive 为 `.rwb/m6-general-prototype/usage-ledger/`、`usage-ledger-review/` 和 `flash-heartbeat-checks/`。

## 接受基线后的最终源检查

PR126 正式 cross-owner APPROVED 后正常 squash 合入 `f5afc4b`；PR125 按用户直接文档接受并同步费用决定后正常 squash 合入 `64c93c0`。原六个实现提交 patch 等价 rebase，不沿用旧定义拒绝的资格判断，也不把本实现当已接受。

本轮源提交 `b1c5679d55d5938adf5f3c050002dd138b4f815d`，actual component 起点 `64c93c05ab1267a796eecbee94e1920c44b72e97`：

- component **553 tests = 551 PASS + 2 Windows skip，0 failure/error**，306.678秒，unknown paths0；
- repository **199 documents / 0 errors / 0 warnings**；
- 3.11 非 editable 当前 wheel 安装 smoke **8/8 PASS**，10.406秒；15个改动产品源码的 wheel、installed bytes 与 Git blob 全等，pip check PASS；default110/all versions111 Schema；
- R2 feature exact-base/source 治理 **0 errors / 0 warnings**，仅合法 M6-009 READY→IN_PROGRESS 提示；
- 持久 journal owner **57/57**（journal28＋原 ledger29）及独立 **8/8 workflows PASS**，含真实 Windows crash/reopen、双进程竞争、锁/namespace/limits/unknown token/费用对象不读/隐私错误边界；
- Gemma Text slice **42/42**（新增13＋原codec29）及响应引用安全 **6/6 PASS**；根另复核旧factory15和repository直接6通过；
- 十二份 profile 覆盖十一家身份，九家离线 fake 正例；Gemma 仅 Text，原退休Google、SiliconFlow/OpenRouter 的拒绝继续保留。

当前归档为 `.rwb/m6-general-prototype/accepted-base-integration/`；各切片冻结 source/hash、dispatch、Handoff与独立复核见 `journal/`、`journal-review/`、`gemma-profile/`、`reference-error-repair/`。Gemma 首轮断言不符和 journal review runner 的初始子进程/import/escaping 失败均保留。根 component 首次传短 SHA 被预检拒绝，改完整 SHA；首次调用无 main 的 cli module 是空 no-op，实际 package main 复验199/0/0。它们没有修改产品来规避检查，不能记初轮 PASS。

用户最新决定覆盖此前费用暂停建议：费用/币种/账单不可得为 unknown，不阻断；未知 token 仍保留预占并停止。SQLite journal 不认证实际发送、input计费上界、另一DB或文件替换/回滚；实际 driver、唯一预算路径、完整运行 source closure、报告/CLI及 profile 安装 catalog 仍未完成。本轮无 full/global coverage、多Python/sdist最终资格或真实 Provider/API/Key/presence 证据；M6-009仅IN_PROGRESS，M6-010仍BLOCKED。
