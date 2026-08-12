# 实施任务清单

状态：`DONE / IN_PROGRESS / READY / BLOCKED / PARKED`

## M0：架构与仓库

| ID | 状态 | 任务 | 验收 |
|---|---|---|---|
| M0-001 | DONE | 冻结产品定位与非目标 | Project Charter 完成 |
| M0-002 | DONE | 确立总体架构与模块边界 | 总架构 + 10 模块文件 |
| M0-003 | DONE | 将不同 Agent—Skill 绑定纳入架构 | Resolver、Assignment、预警与验收明确 |
| M0-004 | DONE | 建立实施、迁移与测试计划 | 三份实施文档完成 |
| M0-005 | DONE | 创建并推送独立 GitHub 仓库 | `main` 可访问，首次提交完成 |

## M1：契约与 CLI

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M1-001 | READY | 初始化 Python 包、pyproject 和基础 CI | M0 | 空包测试在 Windows/CI 通过 |
| M1-002 | READY | 实现核心对象模型与 JSON Schema | M1-001 | 7 类对象正反 fixture 通过 |
| M1-003 | READY | 实现 Protocol、Mode、Profile、Skill Manifest | M1-002 | 组合冲突和权限上限可验证 |
| M1-004 | READY | 实现 Task、Attempt、Handoff、Main State | M1-002 | 示例交接与 incomplete 交接可验证 |
| M1-005 | READY | 实现引用、revision、SHA-256 和 stale 检查 | M1-002 | 修改输入会使依赖结果失效 |
| M1-006 | READY | 实现最小 CLI | M1-003..005 | init/validate/trace/checkpoint 可用 |
| M1-007 | READY | 建立确定性风险检查 | M1-004..006 | 关键故障注入按预期阻断 |

## M2：Agent 与 Skills

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M2-001 | READY | 实现 Skill Registry 与 Resolver | M1 | 最小覆盖、冲突、版本锁可重放 |
| M2-002 | READY | 定义四个 Agent Profiles | M2-001 | 权限、工具、输出边界完整 |
| M2-003 | READY | 创建 literature-evidence-extraction Skill | M2-001 | 正/反/注入 eval 通过 |
| M2-004 | READY | 创建 simulation-vv Skill | M2-001 | 收敛、版本、Claim ceiling eval 通过 |
| M2-005 | READY | 创建 handoff-integrity 检查 | M1 | 优先确定性脚本，语义部分可选 |
| M2-006 | READY | 实现 Codex Runtime Adapter | M2-002..005 | 生成/验证原生 Agent 与 Skill 绑定 |
| M2-007 | READY | 执行首个双 Skill 垂直切片 | M2-006 | 两个子 Agent Skills 不同，主 Agent只收 Handoff |

## M3：上下文与风险

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M3-001 | READY | Main State checkpoint/resume | M1 | 新会话可恢复下一步 |
| M3-002 | READY | context pressure 代理指标 | M3-001 | WARN 能触发 checkpoint/rollover |
| M3-003 | READY | Handoff loss/stale/summary 抽查 | M2 | 故障注入被识别 |
| M3-004 | READY | review loop/fanout/write race 检查 | M2 | 预算和停止规则生效 |
| M3-005 | READY | 敏感 trace 策略 | M2 | fixture 中密钥/敏感字段不泄漏 |

## M4：工件与复现

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M4-001 | READY | source admission 与 provenance | M1 | inbox 不可直接引用 |
| M4-002 | READY | work → object/run promotion | M1 | 只有校验通过可提升 |
| M4-003 | READY | Claim trace 与 counterevidence | M1 | 支持/反证/限制一次定位 |
| M4-004 | READY | Run manifest 与复现检查 | M2 | 仿真案例可重建 |
| M4-005 | PARKED | DVC 技术 spike | 真实大文件需求 | 无需求则不启动 |

## M5：真实案例与删减

| ID | 状态 | 任务 | 依赖 | 验收 |
|---|---|---|---|---|
| M5-001 | BLOCKED | 选定证据综合真实案例 | 人类提供/批准边界 | 问题、来源、数据边界明确 |
| M5-002 | BLOCKED | 选定理论+仿真实际案例 | 人类提供/批准边界 | 模型、参数、Claim ceiling 明确 |
| M5-003 | READY | 建立单 Agent/轻量/多 Agent 对照 | M2..M4 | 指标与评估表固定 |
| M5-004 | READY | 运行案例并分析净收益 | M5-001..003 | 质量、上下文、成本数据完整 |
| M5-005 | READY | 里程碑删减评审 | M5-004 | 至少做出一项保留/删除/停止决定 |

## 当前下一任务

仓库首次推送后，从 `M1-001` 开始。`M5-001` 和 `M5-002` 保持阻塞，直到人类选择真实案例；不以虚构课题替代真实验证。
