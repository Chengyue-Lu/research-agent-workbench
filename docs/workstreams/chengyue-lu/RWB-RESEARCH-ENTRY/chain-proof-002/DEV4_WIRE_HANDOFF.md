# CHAIN-DEV4-008 Compact Handoff

2026-10-07；bounded implementation worker；required-Skills=[]；PR140 checkout 的局部 R2 候选，未提交、未接受。黄毅负责 API 接口接受，路诚钺负责控制预算；Root 是唯一产品/API/Tool 测试者。

依据：[Task Packet](DEV4_WIRE_TASK_PACKET.md)，SHA-256 `0058c48bc5f675dfb516d60a69d597cc4e1b82895941d6aa3e09ebb899e45324`；[007 交接](DEV4_PROFILE_HANDOFF.md)；[可见通信](DEV4_WIRE_COMMUNICATIONS.md)。预算 5 分钟、1 轮；本轮仅修改 wire_codecs.py 和这两份交接文件。

## 已实现的接点

[wire_codecs.py](../../../../../src/research_workbench/adapters/models/wire_codecs.py) 的 `_Profile` 新增 `limits: Mapping[str, int | float | str]`；`_profile` 从调用方已验证的 `implementation.limits` 复制字典并包装为 `MappingProxyType`；`_validate_request` 的 `ProviderCapabilities` 传入该不可变 mapping。没有新默认限额，也没有修改 Profile/Registry/fixture bytes、请求映射、source binding 或费用语义。

Source SHA-256：`a8d4e090a678b3b7895914fce261f61c2c7e6959fc0913f740ef1c478d15c77d`。

[007 回归文件](../../../../../tests/test_provider_profile_configuration.py) 未改，SHA-256 保持 `59d1d8e42168258aebdff62607977134542254f95226f804688436e43c576983`；保留 `test_profile_wire_admission_256_rejects_request_257` 的准确失败断言。

## 明确未决的行为缺口

Root 的 Packet 报告新增 256 Profile/request 257 pure encoder 回归实际 FAIL；本代理未运行该测试。当前代码窄读确认 [base.preflight](../../../../../src/research_workbench/adapters/models/base.py) **不读取 `snapshot.limits`**，仅检查 `max_output_tokens` 为正数。因此本次保存和传递 limits 的接点修复本身不足以实现超限拒绝；不能把它描述为该回归已修复或全流程成功。

发现后立即通知 Root。Packet 指定的最小改动没有授权修改 base.py；本轮未扩大实现范围。Root 下一步须决定在其所有域补齐 preflight 限额检查，或另发 wire 本地 admission 切片；保留现有回归，核实 Profile 实际较小上限及 Tool 数量限额，再重冻 current source closure 并进行新 Attempt。静态检查不能替代真实 admission 测试。

## 检查与边界

15:47:39 UTC 后对 owned Python 源进行 AST 和内存 compile，通过；没有执行 code object 或 import 项目模块。返回前检查本交接相对 Markdown 文件目标、owned source hash 和未改测试 hash。第一次补丁因 snapshot 的格式与预期不符而原子失败，重读该段后按实际格式应用；没有覆盖他人内容。

实际阅读范围：本 Packet、007 handoff、wire `_Profile/_profile/_validate_request` 与 encode 公共接点、base.preflight 完整函数及 port.ProviderCapabilities limits 接口、007 新增失败回归。仅语法/引用/hash 检查，未运行产品或测试、API/Tool、Key/账读取、预占、安装、Git 操作或 primary memory 写入。Root 报告此前真实 Attempt 已关闭（intake 7388 tokens、随后 Supply 枚举拼写拒绝、累计 63002/held 0）；本代理没有读取运行响应或账验证这些数值。

Coordinator 建议 continuity 条目（由 Root 核实后写 primary PROJECT_MEMORY）：

> 2026-10-07 · CHAIN-DEV4-008：pure wire `_Profile` 已复制且不可变保留 Profile limits，并向 preflight snapshot 传递；source hash 见 DEV4_WIRE_HANDOFF，007 回归未动。仅 AST/内存 compile 与交接引用/hash 静态检查；本地候选未提交/接受。发现 base.preflight 未读取 snapshot.limits，超限拒绝仍未完成，已通知 Root。Next 补齐实际限额检查、复测 256→257 及相关 Profile/wire suite，再重冻 source；Root 唯一实际测试者，黄毅接口/路诚钺预算接受。
