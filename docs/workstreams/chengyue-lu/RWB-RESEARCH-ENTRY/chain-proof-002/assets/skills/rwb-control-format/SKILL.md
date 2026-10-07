---
name: rwb-control-format
description: "Shape already bounded human configuration into the supplied RWB control JSON format without adding decisions, authority or permissions. Use only when a Task explicitly selects this optional formatter. Test candidate; not admitted."
---

# RWB control format

**test-candidate / 未准入**。这是可选的格式成形方法；intake 角色职责、Human Gate 与权限检查仍由必载 baseline/Task/caller 承担。本文件不是 Skill Manifest、Release、Lock 或 Runtime admission 证据。

只转换当前已给定的人类配置与 exact refs。按 caller 实际提供的 Protocol/Task/可选 Method/Requirement Schema 输出一个 control JSON；详细 envelope 见 [reference](references/control-output.md)。不从习惯或示例补入目标、Profile、预算、权限、并发、深度或领域。

未知事项保留为 unknowns。不要删除原有门禁、stop conditions、输出要求或 data boundary 来使 Schema 更容易通过。选定值不能超出 caller 人类 ceilings；没有合法 ceiling 时不能产生可批准或可执行的配置。

Method 需要真实获准 Mode/Action 依据，Requirement 描述需求而不绑定供应。不得伪造 refs/hash/Skill 锁/批准；Task hash 留给 compiler。Scope、Schema 或 compiler 检查成功只说明相应结构边界，不证明研究正确性或资格。

关闭本候选后 intake baseline 仍能执行控制成形职责。候选加载失败不能被描述为已启用；若 Task 走 required Skill 路径，真实加载/锁/资格必须由 caller 检查，未满足则阻断。
