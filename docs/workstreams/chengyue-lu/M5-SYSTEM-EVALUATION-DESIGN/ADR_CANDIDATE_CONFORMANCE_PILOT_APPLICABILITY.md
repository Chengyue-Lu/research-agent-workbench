# ADR candidate：M5 不同 facade 的显式适用关系

状态：Proposed；2026-10-04；仅 Draft PR136 的隔离 R2 候选，不改变当前 Task Gate。

责任：路诚钺决定 M5 证据、trace 和 Human 边界；黄毅决定 Provider/API 资格适用事实与接口。接受须绑定 exact head 和关系证据，不能从目标授权、通用继续、CI 或 Agent 生成的 accepted 字段推出。

## 已观察问题

M6 按 `GuardedConformanceTransport` 绑定，Pilot 使用拥有原 Pilot journal handle、typed request admission 和入口阶段的 `GuardedPilotTransport`。共享 send mechanics 不产生相同 manifest，严格同 binding 路径会拒绝两个真实不同 facade。

## 提议

保留默认同 binding 路径。增加显式冻结的辅助关系，保存原 M6 report/manifest 与当前 Pilot manifest，冷重算完整 source/facade 差异。仅允许相同 adapter/profile/config/model/credential/compiler/runtime/transport limits 的窄路径。当前 Provider/Protocol 继续以 Pilot 原 manifest 观察；原 M6 accounting 继续与原账本核对。

独立具名 Human verifier 接收完整 report、关系和当前观察。决定精确绑定两侧 manifests、关系 FileRef、comparison 摘要、限定与当前 context，并负责是否接受适用性；冷比较只证明结构一致。调用者须显式选择，relation ref 纳入 frozen context。细节见 [关系候选](M5-008_PROVIDER_APPLICABILITY_CANDIDATE.md)。辅助证据不进入 Core Registry，不创建 runtime owner、全局服务、自动资格迁移或 grant。

## 代价与接受条件

须维护两侧证据、完整差异及实际 Human 接受；输入变化须重新冻结/复核。源码关系不独自证明 instance delegate/callback 或 hosted API fidelity，可信 Driver 和原资格限定保持。模型/Profile/runtime 变化超出此路径。

接受前须对 exact source 完成正反例、默认路径回归、独立安装及文档/治理检查；黄毅给出 Provider interface/事实审查，路诚钺给出语义/trace 审查。结构检查不等于实际 Human applicability、Skill admission 或 Pilot grant。未接受前不能进入共享默认路径或标记 M5-008 DONE。
