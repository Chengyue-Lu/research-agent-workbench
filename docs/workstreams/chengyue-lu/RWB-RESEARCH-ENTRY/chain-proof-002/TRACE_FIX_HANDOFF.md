# CHAIN-DEV4-014 Compact Handoff

2026-10-08（Asia/Shanghai）；Agent Profile worker；required-Skills=[]。当前 CODEWT 局部候选，未提交/合入/具名接受。Root 唯一产品与 API/Tool 测试者；路诚钺维护 Trace policy/fixtures，黄毅负责运行时接点/live 接受。

输入为主准备窗口 `RWB M5-008 续接` 的 CHAIN-DEV4-014 Task Packet；[通信记录](TRACE_FIX_COMMUNICATIONS.md) 保存本片段可见输入、进展、检查与交接。Root 报告 Attempt11 已实际调用 handler 1 次，结果写入 FileNotFoundError，Trace 目录绝对路径长度 216、旧结果路径 276，tool-events 目录存在。本代理未读取该 Attempt、运行响应或账验证这些事实。

## 实现与 source pins

| 文件 | 最小改动 | SHA-256 |
| --- | --- | --- |
| [trace.py](../../../../../src/research_workbench/observability/trace.py) | `_record_tool` 文件名使用下一事件序号与 operation_id SHA-256 前 12 hex，脱离原 ID 长度/路径字符 | `31c60dcd8ed61d8d6437f5001c9072f8c4a234197db487ed1f919d51c465bed5` |
| [test_agent_trace.py](../../../../../tests/test_agent_trace.py) | 两项回归代码：极长/不安全 ID；不同 ID 清洗重名及重复 ID 的结果互不覆盖 | `11a930d9be9b955f626db5722c66ed0d9241fa1feb0f4632a91e6209756491c4` |

结果 basename 为 `0002-<12 hex>.json` 这类序号/短哈希形态，序号按既有事件序列增长；长度与 operation_id 长度无关。序号区分同一 ID 的重复调用，也避免仅靠短哈希碰撞覆盖。`_create_exclusive` 的 O_EXCL、真实文件 `_ref` 哈希、事件/INDEX 引用和 validator 均保持原实现。非敏感 ID 完整保留在 event；已有 credential/hidden reasoning 脱敏继续适用，不将原件重命名或更写。

只改变新 Tool 结果工件的命名实现；公共 operation_id 身份、Schema、权限、全局 `_safe_id`、运行时 ownership、引用/哈希语义不变。没有新核心语义或 ADR 需求。

## 具体回归代码与验证范围

- `test_long_unsafe_tool_operation_id_uses_short_result_filename`：用重复 1000 次、含路径穿越/分隔符/Windows 非法字符/中文的 ID，断言原 ID 保留、basename 32 字符内且为安全字符、文件在 tool-events 下、实际 JSON 结果与 hash 匹配、INDEX 与事件 refs 一致及 Trace validator 不阻断。
- `test_repeated_and_sanitization_colliding_tool_ids_keep_distinct_results`：`lookup/id`、`lookup\\id`、再次 `lookup/id` 的三次记录，断言三个不同文件、原 ID 顺序与各次实际结果保留、文件 hash/INDEX refs 匹配及 Trace validator 不阻断。没有执行生产 Tool handler。

2026-10-08 00:20:37+08:00 静态 AST 与内存 compile 通过；未执行 code object、项目 import 或测试。返回前再次核源码/测试 hash 与本输出相对 Markdown 文件目标。静态通过仅证明语法与文件引用，不代表新回归通过、Windows 实际长路径写入成功或 API/整链成功。

本片段未执行产品、测试、API、生产 Tool、Key/账读取、预占、安装、Git 或 primary/global memory 写入。保留其他工作者的编辑，只修改以上两产品/测试文件和本两份报告。

实际读取：本消息 Packet；本 checkout AGENTS/README/docs 导航与 Development；primary PROJECT_MEMORY 当前入口；trace `_record_tool/_create_exclusive`、相关初始化/seal/事件序号/引用与 Tool validator；test_trace* 文件名/公共测试构造、filename 发现后的 test_agent_trace 相关 Tool 用例。全局 memory 仅用于确认项目入口与协作边界，项目状态以现场来源为准。没有读取 API 原始日志、private 输入或不相关代理产物。

## Root 下一步与 continuity

1. 执行两项新回归及 Agent Trace/Tool provenance 相关 suite，关注原 ID、重复调用、独占创建、旧引用/哈希与 orphan/tamper 的 fail-closed 行为。
2. 在报告的实际 Windows Trace 目录复核新结果路径，保持 Source closure/hash 绑定，在新源码下重新冻结后才进入新 Attempt；不覆盖或改判 Attempt11 原失败。
3. 如验证暴露核心语义问题，继续按有界 Packet 处理；本片段不宣称链路已成功或代签 Source/live/Human 接受。

Primary PROJECT_MEMORY 由 Root 更新，本片段无写权；建议条目：

> 2026-10-08 · CHAIN-DEV4-014：Tool 结果原 operation_id 拼接文件名在 Attempt11 长路径下写入失败（Root 报告）；局部候选改为事件序号 + ID 短 SHA 文件名，event ID/脱敏、O_EXCL、实际 hash/refs/Schema/权限保持；新增超长/不安全、清洗重名与重复 ID 回归代码。仅 AST/内存 compile 和交接 hash/link 静态检查，未跑测试/API/Tool/Key/账/Git。来源 chain-proof-002/TRACE_FIX_HANDOFF.md 与 TRACE_FIX_COMMUNICATIONS.md；source pins 见交接。Next Root 复测 Trace suites及实际 Windows 路径、重冻 Source 后决定新 Attempt；原失败保留，候选未接受。
