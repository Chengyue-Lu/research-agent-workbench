# FOLLOWUP-003 检查

基线 `27cbf860e48e9639bd3af32a58c12bfd88d87526`。最终 source/head 及完整组件、安装、
治理结果由本轮冻结检查补入；历史 head2e0c 的 SUCCESS 不借用于新源。

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
