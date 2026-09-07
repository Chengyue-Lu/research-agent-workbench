本轮整改方向已由用户确认，继续在 PR #66 / TEST-PERF-002 实现。

目标调整为：**对本次变更的受影响闭包做完整验证，闭包外的测试允许不运行。** `R2 -> repository-wide full behavioral` 是前一阶段的保守限制，本轮将解除该绑定；风险继续决定治理、cross-owner review、authority basis 和相关 adversarial evidence。

重审在 `2808189` 上以 10 个真实 Git fixture 复现了范围过宽：R0 test-only 仍 full；Provider 局部修改加无关测试会升级 full/repository；局部 critical inventory 增补或 planner 普通注释也会扩大到全仓。

具体整改：

1. 将行为测试范围改为受信规则推导的源码/契约/测试依赖闭包，支持 R2 + focused；新建或修改的测试及必要消费者不得遗漏。
2. 扩展局部选择能力，覆盖实际源码与测试依赖，区分“已证明广泛影响”和“尚未解析的依赖”。未知影响仍 fail-closed，并输出具体升级理由。
3. 细化 consumer fingerprint 的失效范围；无关测试修改不应使既有局部闭包整体失效，候选 policy/fingerprint 仍不能自行授权缩小机器下界。
4. 区分局部 critical/suite/acceptance 增补与真正全局 coverage authority 变化。局部增补证明相关文件及验收，不自动附带全仓行为。
5. 保留 exact Git diff、base-side authority、dependency closure、Agent 只能扩大范围、metadata isolation、obsolete HEAD cancellation、固定 `test (3.11)` / `test (3.13)` aggregate gates，以及独立 impact/repository 义务集合和双 checker。
6. 保留 affected critical whole-file 95/90、changed executable statements/outgoing branches 100/100、integration/release repository global 90%、原有 exclusions 和必要真实集成/对抗行为；不以删除测试、降低阈值或 mock 替代必要证明来缩时。
7. 同时增加“不能遗漏相关测试”和“不能无理由扩大到全仓”的回归。保留 #65 的 exact Git fixture，但把其期望改为相关测试及消费者集合，coverage none、无关 smokes false。
8. 输出 selected/excluded tests 的依据；用一次 full oracle 对照验收新的选择器，并分别报告 scoped CI 关键路径与累计 runner time。此一次性 oracle 不成为后续每个 PR 的 full 要求。

#66 已修复的两个 coverage 语义 P1 保持成立。本轮是进一步修正测试范围模型；已有绿灯和技术 review 不代表新方向已经实现。完成后提供新 exact-head 证据并继续 cross-owner review，本轮不自行合并。
