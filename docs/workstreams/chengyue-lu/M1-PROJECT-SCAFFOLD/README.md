# M1-009 — 可复用项目 scaffold

- Task：M1-009；责任人：路诚钺（`Chengyue-Lu`）；初始基线：`b111dbbed9c250c0bcf3afe1c754819b30eae935`。
- 分支：`feature/m1-009-project-scaffold`；目标：develop；R2（package smoke 的 `.github` 路径触发）。
- 授权：用户要求合入 #73/#69 后推进 M1-009；M1-009 原为 READY，hard dependency M1-006 已 DONE。
- 主目录 develop 保持原 SHA，仅在独立 worktree 实现；不调整 M1-009 定义、owner、依赖或验收。

当前候选已 rebase 到包含 PR #71 的 `develop@60bdf8c28f6cf8c52c04e481e0309bbd6e8cba8b`；STATUS
同时保留 M5-006 已实现的状态和本次 scaffold 说明。初始冻结 Archive 保留原 baseline/bytes；
最终验证与审查以 PR #74 当前候选为准，旧基线成功 CI 不代替新候选验证。

## 交付

`rwb init` 默认生成完整 no-Skill 项目，支持 offline-demo 和 minimal 模板；`project check` 校验显式
项目 root、模板版本、资源 pin 与输入结构。Schema/Registry/Skill 继续消费安装包现有 catalog，
Profile 是项目自己的无 Provider 绑定声明。目录不可覆盖，旧最小模板/验证/checkpoint 保持可用。
模板固定 catalog 与文件哈希，可选示例适配当前解释器环境；真正执行须显式调用既有 Run reproduce。

[实施说明](../../../implementation/PROJECT_SCAFFOLD.md) 给出仓库外安装、初始化、证据定位与 Run 检查/
重建路径；[兼容政策](../../../compatibility/CLI_SCHEMA_POLICY.md) 明确 0.x 版本、弃用和显式迁移边界。
公开 README/Getting Started 只同步本次实际 CLI 输入，M14-004 最终验收仍独立。

## 验证与风险

- `tests/test_scaffold.py`：默认/可选模板、实际独立进程重建、迁移目录、poisoned cwd、资源与模板 drift、
  拒绝覆盖、失败清理和身份不一致。
- `portable_package_smoke.py`：沿用现有 direct wheel / sdist-to-wheel、双 Python、新环境与 cwd poisoning，
  增加同一 scaffold → project check → Run reproduce → report validation 路径。
- Coverage suite 仅新增 scaffold 测试；90/95/90 阈值与既有 critical/adversarial 义务保持。
- 本地与当前候选 hosted 证据见 PR 和 [Attempt archive](../../../../work/M1-009/A-20260912-001/INDEX.yaml)。
- R2 权威依据为 accepted M1-009 与用户推进授权；cross-owner 审查确认接口与验证改动，具名 owner 决定
  是否接受 Task 完成。没有新授权模型、Provider/live conformance、Claim acceptance 或 release topology。

允许读取：AGENTS、Task/开发导航、相关 CLI/Runtime resources/Run reconstruction/Schema 接口与测试、
模板来源示例、package/CI/coverage 检查以及本工作流。写入限定为本次 CLI/scaffold/模板、打包测试、
兼容与关联文档、M1-009 状态及本 Attempt。风险处置见 [Risk Ledger](RISK_LEDGER.md)。
