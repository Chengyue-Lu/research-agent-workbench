# M0-008 本地验证与剩余项

2026-10-10；定义/实现 base 为 develop `e49386140c18cdfb9e6065b7c59e2545f863e386`；当前为未合并 feature 完成候选。Task DONE 对应本分支验收，不等同 develop 已支持；实际远端同步证据独立见 [记录](REMOTE_SYNC_RECORD.md)。

## 改了什么

| 接点 | 实际结果 |
|---|---|
| PR body → 治理 parser | 固定 owner 不再必填或按账户名单拒绝；旧 owner 元数据继续可读，未添加新必填 actor/reviewer |
| policy → risk/workstream validator | 固定人员映射撤销；直接 Task 目录与原 namespace 目录均可用，README/R2 Risk Ledger、路径边界、Task 资格和风险检查保留 |
| 模板/CODEOWNERS → 提交与审核表面 | 模板去固定责任人；CODEOWNERS 不再按账户指派路径。检查所需风险和证据保持；两服务器review层已另行同步并核对hard层不变 |
| 文档 → 人类消费 | PR141 已合并事实校准；既有计划说明当前不用重复指定工程细节、正式准入/语义变化/具体合并的决定时点 |

## 实际检查

Python 3.11.16；执行 `python -m unittest tests.test_pr_governance tests.test_governance_helper_branches tests.test_documentation`：**105 tests PASS**。覆盖合法 ownerless body、旧 metadata、不同 namespace、直接 Task 工作目录；反例包含缺 Risk Ledger/必要元数据、路径逃逸、Task/DONE/依赖、风险、发布拓扑及现有 authority 约束。测试中的缺 GitHub event 和坏 JSON 的 FAIL 文案为被断言的拒绝反例，最终 suite 为 OK，原输出保留。

限定文档检查：修改/新增 Markdown 的本地链接目标存在，72 个原 DONE 行与 base 完全一致。此前全仓链接审计发现3个已知历史缺失，未引入新缺失；该历史清单未被本次结果覆盖。`git diff --check` PASS。没有新产品/API/生产 Tool 调用、凭据读取或累计账变化。

## 剩余与下一动作

按2026-10-10明确授权，两review层已各PUT一次并GET重新读取，取消人员审批并清空具名bypass；两hard层没有PUT且after规范字段与before完全一致。详见 [线上记录](REMOTE_SYNC_RECORD.md)。本地正反检查、原head hosted CI与线上事实闭合，M0-008提出完成；具体PR142合并仍待人类指令，新head检查按新CI结果接受。

另一条可直接实施的桥接切片是 PR140 包内 no-Skill/readonly 受信 caller/factory。现有材料足以先做离线实现；不需要人类重填角色数量或控制 JSON，实际 API 仍在既有 18:00–09:00 窗口及累计预算内重核执行资格。M1-010/M2-009/M11-008、实际 Skill 资格、真实项目和 M5/M12 等仍各自验收。
