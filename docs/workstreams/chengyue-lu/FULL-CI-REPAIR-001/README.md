# 最新 develop 全量故障修复

Audit ID: `AUDIT-FULL-CI-REPAIR-001`；责任人：路诚钺（`Chengyue-Lu`）；
Provider/source-closure 维护及跨 owner 审核：黄毅（`let778750-cpu`）。风险：R2。
入口：[Issue #87](https://github.com/Chengyue-Lu/research-agent-workbench/issues/87)。

用户在2026-10-04要求停止旧全量，针对最新 `develop` 测试并推进修复。
旧 `6fa105b` 的全量37171230339已取消；实际接受基线 `c80ec014` 的现有全量
[37176315620](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37176315620)
接续启动，避免额外触发同一基线。此运行仍按双 Python、full behavior 和 repository coverage执行；
本候选的结果与该基线运行分别绑定。

## 已定位故障

1. Python3.13的 dataclass `__repr__` 使用 `reprlib.recursive_repr` 包装器，原 class layout
   checker 只识别 dataclasses/Enum/typing生成方法，误报 `ProviderAdapterConfig.__repr__`。
   两个旧全量的3.13原生结果均包含该错误。修复按标准库实际生成结构识别递归repr，
   使用当前标准库独立生成的同字段repr作代码比较，保持外层包装器身份、模块globals、
   closure与内层代码的检查。构造标准库参考前，先检查类本地元数据和字段的精确类型，
   再检查字段名及repr/kw-only布尔值；自定义truth getter、字符串或元数据子类必须零调用拒绝。
   归档源码、Provider构造、字段factory不执行。
2. 旧全量37168512882的3.11测试体2055项通过，但coverage精确排除对账失败：
   `session.py` 的既有Protocol排除位置已从90–93移动到97–100，
   `session_policy.py` 的35–38已被coverage实际排除却没有登记。
   更新policy到2.3.7只对齐这两个现有Protocol占位位置。实际源码、coverage配置和实际排除集合不变。
   同一旧工件在原policy下产生12个差集错误，在精确位置候选下通过；这是新checker evaluation，
   没有把旧工件重新标记为候选HEAD的全仓证明。

## 提早发现位置漂移

新增局部回归使用coverage公开的 `analysis2` 静态解析真实源码，核对已登记排除位置，
不执行Provider或Host。原policy在此回归失败，修正后双Python通过。
三个声明文件与 `tests/coverage_policy.yaml` 登记为该短检查的直接消费者，
日常组件CI因此能在相关源码位置移动时发现漂移，无须等全量完成。
全仓对实际排除集合的双向对账仍保留；该短检查不替代新文件的全仓排除审计。

## 验证与接受边界

用户后续提供的P1揭示函数自身捕获的builtins仍可与模块globals不同：
`FunctionType`克隆可保留wrapper的code、globals、closure和`__wrapped__`，
构造时捕获替换的`id`，再恢复模块builtins。原候选在两Python版本均接受该clone，
后续repr会执行替换引用。跟进修复同时核外层wrapper和生成inner的
`__builtins__`为canonical builtin namespace对象，拒绝复制dict、dict子类和自定义mapping，
不查询这些对象。正常生成与真实递归repr、既有源码/code/closure/metadata控制继续保留。
原反例、新源码局部检查与独立复核使用新归档[A-20261004-002](../../../../work/AUDIT-FULL-CI-REPAIR-001/A-20261004-002/README.md)；
原A001及e939 hosted结果保留原身份，不能替代跟进提交的执行证明。

修复保留正常生成repr和明确源码声明的自定义repr；未知注入、伪造包装器、替换内层、
错误属性槽均需拒绝。独立复核发现的字段truth调用与组件policy路径选集缩小问题，
以及修复过程暴露的元数据子类getter调用，均保留原始反例与后续修复身份。
现有源码closure、静态policy与组件选择的正常/负例继续执行。
验证证据和exact候选身份在PR正文更新；局部PASS不代表候选全仓覆盖通过。
原基线全量、失败日志、候选局部回归和候选组件CI各保留自己的身份。

完整验收的global90%、critical95/90、changed100/100定义、实际exclusion配置、
critical inventory和正负验收映射保持；没有删除行为测试或调低门槛。
日常组件路线仍按已接受的开发规范执行，coverage诊断与完整checkpoint证明分开。
本候选不修改M Task状态、Provider/session使用权限或发布资格。

合并仍需要适用的cross-owner审核及必需checks；本轮没有授权合并本修复PR。
剩余风险与回退见[风险表](RISK_LEDGER.md)。本次记录使用紧凑归档，保留capture-gap，
不声明完整Agent Trace。归档入口：[A-20261004-001](../../../../work/AUDIT-FULL-CI-REPAIR-001/A-20261004-001/README.md)。
