# 工作 Guide：实测结果与剩余范围

2026-10-11；Windows CPython 3.11.16，Root 单一工程测试执行者。来源为 PR145 `7341f968`、开发切片 source `45f4101e` / docs receipt `f0ffb564`，加本 PR 的 Guide consumer 与 CI 登记；各自提交和字节身份保留。本轮新增实际 API、生产 Tool、Key 读取与生产 Attempt 均为 0。

## 模块、实际输出与检查

| 验证对象 | 实际结果 |
| --- | --- |
| 新材料/结果纯投影 | 14 项通过。实际 reader 捕获原件/sidecar/派生后投影；严格 nested provenance、exact Task pins、UTF-8 原文与结果分槽成立；错配、未授权、额外字段和伪资格主张拒绝 |
| 新 Guide 请求消费者 | 16 项通过。请求只含 baseline 与 `work`，实际注入 Provider 接收一次；来源关系、费用原文和结果文本保留，正式契约/科学资格仍未建立；不会扩大显式读集 |
| 旧接口回归 | 旧 0.2.0 投影 9 项及旧角色请求 14 项通过；新 Guide 内部仍验证原 Task/Profile 与独立 output grant，不改旧默认入口或控制语义 |
| 独立安装包 | 同一组 53 项全部通过，无失败、错误或跳过；实际产品模块从 fresh venv 的 installed site 导入。Guide 使用安装后的 pinned 0.3.0 Schema，另核源/安装模块和两版 Schema 的 byte equality |
| CI 路由 | 最终 42 项运行，41 PASS、1 Windows 上的 POSIX symlink 专用检查 SKIP，0 失败。新增模块进入 entry 组件，角色 fixture 改动选择实际 Guide 消费者 |
| 文档与 Task 保留 | 文档结构 3 PASS；130 个定义与接受的 PR144 完全一致，73 个既有 DONE 行保留。内部 Markdown 目标与锚点另按最终文档核验 |

源码组为 53 PASS、0 failures/errors/skips/drift；安装组是同一 53 个 case 的另一消费形态，不作为另 53 个独立用例。纯投影测试读取声明的 checkout Schema；实际安装 Guide 与资源身份检查消费 wheel 中的 Schema。离线 Provider 注入的响应是测试输入，证明程序请求/响应边界，不是付费 API 或科研内容评价。

CI 第一轮保留了旧 entry 预期集合未含新增两个模块的 10 个 subtest failures；修正集合并覆盖新 source/fixture 路径后复验通过。没有改产品行为来规避失败，也未把平台 SKIP 记作 PASS。静态审查提出的空选择 fallback、最终复验期间取消两处问题，在实际消费者测试前修复。

| 固定内容 | SHA-256 |
| --- | --- |
| Guide consumer | `09e4c6361caa5b81ac034502e3c0a2d2988b445cec28bd914c035065e919b1f4` |
| 材料/结果投影 | `f2f2d5304aa0ddeef59d022a78ff36cae365c90db9a4df1e1fde3246a23cffbe` |
| 新 0.3.0 Schema | `abd3f3cd8346933cc4c225a2927c0fb0805b913e7029f7b1a382a9e43705f100` |
| 本轮 wheel | `18c3ef5901454126beb9c6eab0157a02b6fc7515f9f18b95b3f23c0e72a7f95b` |
| 本轮 Runtime resources manifest | `866d3b9ca45caa019f5d69419b60fbe837f58c377373c4550db5664ff4acf2f8` |

原 0.2.0 模块、Schema、测试分别保持 `cfc4ede8…`、`5f08be38…`、`f26498de…`，未原位扩宽。默认 Catalog 仍 0.1.0；新候选 Schema 通过原资源生成器进入包，增加新资源会形成新 manifest 身份，不能冒称上一轮 wheel/manifest。依赖未升级，完整原日志/结果与模块资源身份记录留在任务工程归档 `material-continuation-012`，可见通信与开发原件见 [Slice002 Handoff](../../M6-013-WORKING-MATERIALS-SLICE-002/HANDOFF.md)。

## 基线与后续

PR144 正常 squash 合入 develop `2009bd6a`。PR145 fixed head `7341f968` 的 governance、四个 component shard、plan 和 CI result 均 SUCCESS。初次 governance 的 component-plan metadata binding failure 及其失败日志保留，后来计划就绪后重跑失败 job 通过；未证明具体 race 根因。这里的 PR145 线上事实不能代替本后继 PR 的 checks。

尚未迁移 main/child/intake/默认 Guide、Task/Policy/View/Host/Session；现行经济控制仍在程序内。正式 Handoff 接受、记账完整性与执行完成分离、新无经济配额路径、实际 API 新版本行为和完整 M11 产品 Gate 均须另有证据。原 M1-010/M2-009/M11-008/M6-013 保持 IN_PROGRESS。

下一步按 [实施计划](../../RWB-CHAIN-TASK-DEFINITION/REALIZATION_PLAN.md)推进其余角色请求与新控制版本；研究对象编译另补显式场景、授权读取闭包、Evidence/Claim 草稿、来源定位及真实 Method Trace lineage。当前只读解释无需这些科研产物，也不声称科研净价值已测。
