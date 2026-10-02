# FOLLOWUP-003 检查

基线 `27cbf860e48e9639bd3af32a58c12bfd88d87526`。产品源 `f7969bb2a3434ef603cce5743884307af5025473`。测试修复源`5a0b19d73f63477b66613ffade73045b75a74ed7`仅增加Schema完整清单的一个expected kind；
代码、其余测试/fixtures、Schema、Registry、CI和policy与产品源相同。最终再仅三份证据MD。


| 最终实际检查 | 结果与范围 |
|---|---|
| Python3.11.16 component原轮 | 产品源62模块，831项：826PASS、1FAIL、4skip、0ERROR；1185.049s |
| Schema清单修复复验 | 测试修复源仅补新kind，整个test_schemas6/6PASS；其余产品/测试/Schema字节相同，原FAIL保留；未重跑831或采full/coverage |
| Repository examples/registry | 202/0/0 |
| Fresh noneditable wheel | 8/8 smokes、pipcheck PASS；14profile/11厂商、两份disabled配置11+3条，CLI blocked/live false |
| Wheel Git字节闭合 | 177资源、119tracked模块全部等于产品源Git blobs；SHA256 `da0b9773610be8afc4dfdb781fa36c193c07a096fb9456fa02278f20c15778a6` |
| Actual完整DAG/本地R2治理 | policy_at(1.7.0) PASS，原8policy对象及字节不变；治理PASS，无ERROR/WARNING |
| 独立R2审计 | 最终3/3针对性PASS、81module pins稳定，无审查范围内剩余blocker；不是human或full-context接受 |

独立receipt SHA256 `81b2fe452309eff7911a29c76452eb17047061725b814d0f177a74bd5a214025`。
source006首轮组件因import修复主动中止，原partial log/exit1保留，无最终成功计数；最终f796另起plan/run。
独立73/82/33旧轮与owner17/44及root各阶段原FAIL/ERROR保留；两个P2及import回归逐一复验。
本地archive保留raw日志/source/index/build/安装/独立receipts，可见消息与平台完整capture gap。
当前head的远端CI另核，不将本地PASS当remote结论或cross-owner批准。

owner 定向检查：显式 body/transport/kernel44/44、source observer17/17，均为合成离线。
root旧绑定11/11、runtime resources20/20。初次 graph 联测与独立审计复现 MappingProxy
交给仅接dict的reader导致实际构造拒绝；消费者已显式转plain，reader闭集不变。
独立零调用另复现 new-bound实例使用旧manifest遗漏source graph依赖；stage/observe已拒绝降级。

root修复构造后的10项轮为9PASS/1ERROR：source drift已被拒绝，但异常仍为内部
SourceClosureError；统一为静态、无原异常链的 EvaluationValidationError，未放宽负例。
源码/生成runtime pin并发改变的原轮、owner原FAIL/ERROR及更正协议路径均保留。
这些阶段结果不冒称最终冻结源或远端CI通过。

新 manifest1.1/policy-v3、baseline1.2只证明声明的 Provider/source 图消费；当前 driver
和报告尚未自动消费完整运行上下文。trusted compiler/native/dependency/generated behavior
边界保留；remote strict/live qualified仍false，CLI无真实执行入口。

官方字段表11×15：D31/P129/U5，125来源ref全部定义；D是公开事实，P保留具体模型/账户/
失败用量限制，5个U是所选型号并行Tool控制。不是165项账户或live验收。

真实API/Key/presence/bridge、实际预算claim均0；平台完整工具事件导出不可得，capture gap
如实保留。M6-009 IN_PROGRESS、M6-010 BLOCKED，见[交接](HANDOFF.md)。
