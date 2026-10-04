# FULL-CI-REPAIR-001 / A-20261004-001

责任人：Chengyue-Lu；风险R2；实际接受基线c80ec014。
本归档绑定候选源码hash和修复过程中可观察的结果；提交身份由Git历史与PR补充。

用户要求取消旧全量、针对最新develop测试并修复。旧6fa全量已取消，
最新c80已有全量接续执行，没有重复dispatch。原始API/官方plan及局部检查在
`raw-observations.zip`，内容索引为`RAW_INDEX.json`；各原生回执保留原head/hash/时间。
旧ede coverage工件的精确policy重放是新的evaluation，不是候选全仓证明。

原P1字段truth调用、元数据getter中间失败、legacy wrong-slot反例和组件映射P2
均与后续修复分开保留。最终独立复核属于源码/短probe，不替代实际hosted执行。
既有90/95/90和changed100/100、actual exclusions和完整checkpoint定义保持。

这是紧凑记录，`CAPTURE.json`如实保留capture-gap；不声称完整Agent Trace。
没有秘密或隐藏推理。原始工具/命令记录封存在ZIP中，允许保留其机器本地执行路径，
导航与产品文档使用仓库相对路径。后续新HEAD/run在新归档保存，不重签本次回执。
