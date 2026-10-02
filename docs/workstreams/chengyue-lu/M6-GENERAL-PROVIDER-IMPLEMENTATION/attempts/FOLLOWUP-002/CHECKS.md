# FOLLOWUP-002 检查

产品源 `a3971381a45310e885a621a254c627f623e5f9de`，基线 `27cbf860e48e9639bd3af32a58c12bfd88d87526`。
后续最终提交仅修改本检查、交接及风险表的历史模板说明；代码、测试、Schema、Registry、CI和public policy与产品源保持相同。

| 实际检查 | 结果与范围 |
|---|---|
| Python 3.11.16 exact-source component | 46个声明模块，596项：592 PASS、4平台skip、0fail/error；322.12s；coverage未采集 |
| Repository validation | examples和registry，202/0/0 |
| 新非editable wheel环境 | 8/8 installed smokes，pipcheck PASS；14 profiles及两份disabled配置11+3条；offline CLI仍blocked/live false |
| Wheel字节闭合 | 176资源、117个tracked Python模块逐一等于产品源Git blobs；wheel SHA256 `e49fa8d7b70fec5fb514d3f1a9fcc371681bec3a8336491e86ae543fd2995cab` |
| Public构建输入历史 | 实际完整commit DAG `policy_at(1.7.0)` PASS；旧七policy对象不变，1.7仅三个exact文件；没有export/发布 |
| Local R2 governance | 产品源与当前完整PR metadata核对PASS，0error/0warning；不是cross-owner批准或远端CI终态 |
| Owner合成检查 | vendor联合102PASS+1Windows skip；budget anchor联合103/103 PASS |
| 新有界独立复核 | 100 direct PASS/0skip；11实际factory、32 Text/网关边界、8 retained-anchor真实临时文件案例；未复现产品blocker |

首轮component 596项中591PASS、1FAIL、4skip（322.075s）：scaffold的`-I`子进程加载旧安装包，
其资源pin与新source不同。原日志保留；只将本地检查解释器安装为当前wheel后复跑，没有为此修改产品或放宽pin检查。
其他owner/probe原错误、未提交1.6扩展草案及历史PR127 source CI37022594303 FAIL保留。
旧PR128 head957的hosted SUCCESS只覆盖旧head；新head CI另观测。本轮不声明full/global coverage或live PASS。

独立复核receipt SHA256 `22a27020164b00512b5df42ad89d2bf0f623ac7dbedb736831da71c0bbbe4929`；
54输入hash稳定，16个Provider资源字节重核。其Git归属引用由root提供，未冒称独立Git审计。
两个失败探针的合成临时目录清理被自动审批拒绝，原因只有`blocked by policy`；残留元数据与原错误保留，未绕过。
本地archive保留可见dispatch/messages、原失败、source/index/build/安装/审查receipts；完整平台事件导出不可得，Trace capture gap明确。

官方字段表为11家×15字段，17已冻结事实、75部分待核、73未冻结；不是165项实现或账户验收。
公开官方资料GET独立于Provider调用，不保存密钥或隐藏思考。真实API/Key/presence/bridge均0。
M6-009 IN_PROGRESS、M6-010 BLOCKED；见[下一步交接](HANDOFF.md)。
