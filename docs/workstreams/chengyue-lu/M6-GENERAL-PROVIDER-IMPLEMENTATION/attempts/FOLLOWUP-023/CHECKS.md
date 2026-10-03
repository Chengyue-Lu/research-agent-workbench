# FOLLOWUP-023 检查

原installed859 wheel/install/pipcheck/installed smoke通过；packet第一次PREPARE_001因helper不在
v3 graph失败。第二variant已中断，partial和exit1保留，未把package pin冒称graph通过。
只读parser诊断表明qualified import显式记录helper edge；真正source-bound与guard漂移复验待完成。
这些旧安装和partial不具备执行资格，必须以修复新head重建。

首轮qualified-import回归52项中51通过、1fixture断言失败（307.200秒）：helper graph member/edge已通过，
漂移测试误复用了已completed预算，首先被Attempt admission正确拒绝，未到预期guard阶段。
修正为已grant但未开始第四组的零调用construction失败fixture，集中复验进行中；不改预算完成后
禁止retry的产品语义，不把初轮结果冒称全通过。原GRAPH_DEPENDENCY_001.log保留。

只读实际历史核查PASS，25个anchor checkpoints均一致，原claim/basis/identity/DBhash不变。
独立receipt `7484e7b7ab2a095e1bab0769617067b5b1b4c809d91e4c33ac452a562704f11c`；
应用recipe要求Root在同新packet根复制原始用户ref及canonical prefix/decision，显式独占追加grant，
独立核对原事件prefix与新event26，然后另选实际第四组。未执行grant或journal.open真实历史。

独立官方核对2026-10-03：精确Flash/context1M、POST `/responses`、`reasoning.effort=none`、
Tool specific/none与text.format，以及周末全天闲时。根记录初稿误写`/v1/responses`已保存，
按选定profile与官方operation修正，未发请求。时间候选UTC13:25–15:00仍需实际前fresh检查。

真实API/Key/真实预算写入为0。后继安装、完整Windows合成与实际结果分别记载，不外推unit/marker结果。
平台未导出的完整事件为capture gap。全部本地明细在 `.rwb/m6-general-prototype/followup-023/`。
