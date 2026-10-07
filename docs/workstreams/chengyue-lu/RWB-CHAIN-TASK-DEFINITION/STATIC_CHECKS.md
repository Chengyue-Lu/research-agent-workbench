# 全文档静态检查

Base: `d3c4d23206339ebc7f18b5621f3aa5453f96335e`。全仓 Markdown 文件 697，active 文档 67。
本地文件/目录链接：baseline 1512，当前 1797；baseline 缺失 3，当前缺失 3，新引入 0。
Active 文档 heading fragment 检查 30 项，待核 0。此 slug 检查不代替语义阅读。
此检查解析 Markdown links/images；不访问外部网页，不将 path/heading 存在当作语义或科学验证。
原 DONE Task 行内容变化：0。
新增真实化 Task 24：{'READY': 6, 'PARKED': 18}；原桥接 Task 3。重复 ID 0，未知新依赖 0，新 DAG 环 0。

| 新 Task | 分支状态 | hard deps 全 DONE |
|---|---|---|
| M1-010 | READY | True |
| M2-009 | READY | True |
| M11-008 | READY | True |
| M0-008 | READY | True |
| M1-011 | PARKED | False |
| M1-012 | PARKED | False |
| M1-013 | PARKED | False |
| M2-010 | PARKED | False |
| M2-011 | PARKED | False |
| M2-012 | PARKED | False |
| M2-013 | PARKED | False |
| M3-010 | PARKED | False |
| M3-011 | PARKED | False |
| M3-012 | PARKED | False |
| M4-006 | READY | True |
| M4-007 | PARKED | False |
| M6-011 | READY | True |
| M6-012 | PARKED | False |
| M8-006 | READY | True |
| M9-007 | READY | True |
| M11-009 | PARKED | False |
| M11-010 | PARKED | False |
| M1-014 | READY | True |
| M1-015 | PARKED | False |
| M2-014 | PARKED | False |
| M3-013 | PARKED | False |
| M11-011 | PARKED | False |

## 本地链接缺失

- `work/TEST-PERF-002/A-20260920-002/checks/docs-input-audit.md` → `docs-probes/run_probes.py`（baseline 已有）
- `work/TEST-PERF-002/A-20260920-002/checks/docs-input-audit.md` → `docs-probes/summary.json`（baseline 已有）
- `work/TEST-PERF-002/A-20260920-004/RESULTS.md` → `../../../../docs/workstreams/chengyue-lu/TEST-PERF-002/CONSUMER_SHADOW_READINESS.md`（baseline 已有）

## Active 锚点待核


## 本轮适用验证

2026-10-08；Root 在独立 Python3.11.16 文档环境执行。上表 PARKED 的 `False` 表示后继依赖尚未完成，不是 READY 资格失败。

- `python -m unittest tests.test_documentation -v`：3 PASS，公开文档/发行输入闭包与第一接触面职责检查通过。
- 模块05 Task YAML 示例：现行 Task Schema 零错误。
- 72 原 DONE 行内容不变；27 候选定义 ID 唯一，全部 READY deps 为 DONE；24真实化与原3桥接依赖无缺失/无环。
- 治理器现有 Task parser 支持原8列和新增5列独立表头，均以末第二列解析 dependency；未改历史行以迁就表形。
- 首次环境缺 Markdown 依赖；准备后第一次测试仍缺声明的 linkify，补齐后重跑通过。原错误留存，不修改产品或测试。
- 独立窄审：Core/Skill互等疑点已澄清并补读确认，见 [窄审](REALIZATION_NARROW_REVIEW.md)。人员配置/远端规则同步仍待 M0-008。
- 本次公开闭包首次失败：Architecture新增详细候选链接跨到未发行 ADR/workstream/STATUS；改为公开概念边界、详情留开发面后3tests重跑PASS，未改变测试/发行政策。
- [本次窄审](SHORT_LANE_NARROW_REVIEW.md)：摘要漏写 none 同时须 refs 有效/无活动输入失效已修复并限定复读关闭，未新发现 P级问题；不作实现/提示词质量判断。
- Git diff whitespace、PR治理与最终 hosted CI 以当前 PR141 head 和在线检查为准；本轮未运行产品/API/Tool 或科学评价，不把文档通过记作 Task DONE。
