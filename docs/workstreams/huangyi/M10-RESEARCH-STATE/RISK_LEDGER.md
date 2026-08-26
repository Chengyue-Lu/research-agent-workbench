# M10 风险台账

状态：Stage PR 提交前更新（R2 workstream 必备）。

| # | 风险 | 触发条件 | 缓解 | 判定 |
|---|---|---|---|---|
| R-1 | 越权冻结最终 Schema（candidate 冒充 accepted architecture） | 把 Unknown/Contradiction/Frontier 表示写成预冻结语义 | 契约 §1 显式标注 bounded candidate；Contradiction 用既有 Evidence–Claim 关系；Frontier 不建对象；最终接受权在路诚钺 R2 review | 守住 |
| R-2 | 改写既有 research-object/claim/decision Schema identity | candidate 与 accepted Schema 混淆 | 四个新文档类型全部显式新建；decision_object_ref 复用而非平行重建 | 守住 |
| R-3 | Gate 被误当 Runtime authority（fresh actor 变 planner） | 选择集分类被写成通用科研决策 | 分类只对 runner 声明的固定 choices + repeats_failure_ref 生效；reviewable 只浮出不执行；契约 §3 明示非新 authority | 守住 |
| R-4 | fresh actor 读取面泄漏（读了 chat/oracle/expected） | actor 扫描 case 目录 | 只经 exact ref 约定路径打开；read_surface 全记录；oracle forbidden_reads 断言（测试锁定） | 守住 |
| R-5 | ref pin 不校验导致 exact closure 破洞 | actor 只按 id+revision 取文档 | resolve_ref 内 pin↔content_hash 比对，漂移 fail-closed（测试锁定；实现中实测发现并修复） | 已修复 |
| R-6 | revisit 语义退化为自动触发器 | condition 满足时自动重跑/推荐 | reviewable≠recommended 双状态；测试锁定 revisit_met=true 时 rerun 不被推荐 | 守住 |
| R-7 | Method Trace 复制正文/与 Execution Trace 混层 | 事件内嵌对象 body | ref-only schema（additionalProperties false）；六族闭集必备 ref；不扩张 observability/trace.py | 守住 |
| R-8 | 与路诚钺侧 codex/phase-c 分支重叠实现 | 双轨并行 | workstream README §4 记录分工确认；PR 以本分支为审查基础，合并策略由 Task owner 裁定 | 开放，PR 审查时关闭 |
| R-9 | Topic 5 提前解冻误读 | gate PASS 被引用为 thaw 依据 | 契约 §4 与 TASKS M10-003 验收一致：PASS≠closeout≠thaw；Topic 5 解冻仍需独立 R2 review | 守住 |
| R-10 | 与 PR #39/#43 的 docs 相邻行冲突 | 三 PR 并行改 README/STATUS | 变更均为纯增量行，后合并方 trivial rebase（已声明） | 已知，可控 |
