# M5-003 Evaluation Manifest / Baseline Harness Workstream

- 实现责任人：黄毅（GitHub `let778750-cpu`）
- Task owner / 必需审查人：路诚钺（GitHub `Chengyue-Lu`）
- Task：`M5-003`
- 基线：`develop@6b16129`
- 分支：`agent/m5-evaluation-baseline`
- 风险：R1（共享 Evaluation contract）

## 范围

本 PR 只完成规范化后的 M5-003：最小 Evaluation Manifest、四臂 Phase D treatment vocabulary、
M5-003 v0.1 指标/evidence-class freeze，以及 deterministic non-executing baseline plan。
M5-001/002/004/005 不推进，状态不变。

## Review 整改

1. 已删除 legacy `single-agent / lightweight / multi-agent → Phase D` 的 `arm_map`；coordination
   topology 不再与 Skill/Mode treatment 耦合。
2. Task set、exact Model、Host、budget 与 context 改为唯一顶层共享条件，arm 不能覆写。
3. 每个 arm 显式冻结 `treatment_control`：plain 两臂 suppress Mode/Method control，mode 两臂
   pin exact Mode refs 与 Method Resolution；`plain-agent-tool` 只接受 Tool Supply Snapshot，
   `mode-no-skill` 拒绝任何 Skill Supply。
4. candidate Skill 强制 exact binding 与 pinned Skill Evaluation，且 closure 校验二者 identity
   一致；Capability Snapshot、Method Resolution 与 frozen Task 也做交叉闭合。
5. 每个 canonical treatment 必须且只能出现一次；重复/缺失均拒绝。
6. `rwb eval plan` 在编译前复用 `eval check` 的 exact FileReference/treatment closure，再为所有
   arm 绑定同一 frozen-condition digest；missing/hash-drifted inputs 不能生成 plan。

## 验证证据

- `tests/test_evaluation_manifest.py`：44 passed；
- `rwb eval check examples/evals/manifests/EVAL-MANIFEST-M5-003-001.yaml --root .`：
  no blocking deterministic risks；13 metrics verified；
- `rwb eval plan ...`：四臂 canonical 顺序、同一 frozen digest、`compiled-not-executed`；
- `rwb validate examples registry --root .`：validated=155, errors=0, warnings=0；
- 全量回归：476 passed，3 skipped。

## 非目标与后续

本层不选择真实案例、不运行模型、不记录 trial/result、不作删减决定，也不把 fixture Model 或
Snapshot 当作 live availability。M5-004 仍等待 M4 链、案例 Gate 与具名执行授权。
