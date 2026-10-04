# 封存输入消费者的 fixture 准备成本

2026-10-04。此候选独立于 PR132 的 M5 JSON 表示和 PR135 的开发记录边界，基于 accepted develop `6fa105b720254fae82d2e889385c89292272b2d7`。改动只在测试准备，不改变产品执行、权限、时钟、预算或验证结果。

## 实施边界

[Skill closeout 测试](../../../../tests/test_skill_execution_closeout.py) 的11个档案消费者原本各自生成相同的 completed Host/Trace。每个 class/process 生命周期惰性执行一次原真实 Host 路径及既有确定性 fixture Driver，保存封存文件和普通状态。每个 case 仍有独立目录、独立文件及深拷贝状态，并重新加载当前 Bundle/View，真实 loader/hash/checker/receipt 校验继续执行。

33个原方法、69处 assertion-call AST 保留；11处只替换准备来源。其余22个 cold、真实执行、Driver/capture、binding/projection、blocked、tool、异常和时钟方法原样。缓存不保存 live Driver/Recorder/clock、加载器对象或“已通过”判定，class cleanup 清理种子。Driver 是原离线 fixture，所有实验均无真实 API 或凭据操作。

独立复制检查保留27个文件，交错修改首副本的文件、nested host 和 validation 不污染种子或第二副本；Bundle/View 重绑自身目录，无共享 mutable ID，第二副本通过当前产品 API 正向 replay，三个临时目录均清理。

## 配对观察

Python3.11.16，branch coverage 开启，真实调用计数观察器两侧相同。suite wall 包含首次种子生成、所有 case setup/body/teardown 及 class cleanup；导入、coverage 初始化/落盘另记。第一组用观察器v1，第二、三组用v2；只比较组内，不混算两个观察器版本。

|组|观察器|原准备/秒|封存输入准备/秒|组内减少|结果|
|---|---|---:|---:|---:|---|
|1|v1|28.244747|20.006266|29.168%|两侧各11 PASS|
|2|v2|29.979051|20.173474|32.708%|两侧各11 PASS|
|3|v2|29.415991|20.172214|31.424%|两侧各11 PASS|

每组 Host/fixture Driver.execute 准备调用11→1；receipt build 仍11→11，原攻击/拒绝与产品 line/arc 集合等值。每个正式 fresh shard 独立生成自己的种子；不把此单进程选集的比例推广到整个模块、远端四分片或全量 CI。

证据汇总最初假设所有 independently generated before Trace/validation hashes 与一个 after seed 逐字节相同，因 Recorder 的实时时间字段而失败。原失败和各阶段原值保留，六次测试均通过。正确核验是每个 after 副本严格等于自己真实生成的种子；不同 before 生成的动态 Trace 不重新签名或归一化为相同。

## 验证与集成

原始配对、隔离、失败和可见委派收录于[紧凑记录](../../../../work/TEST-PERF-002/A-20261004-002/README.md)，包含来源 hash 和 capture-gap。正式新 target 执行完整33方法及适用短回归/安装 smoke 后，才记当前可审核结果；本地11-method branch 集合不是全仓 coverage 门槛证明。

日常组件路线使用Python3.11和诊断 coverage；显式多版本/full checkpoint 义务沿用[开发规则](../../../DEVELOPMENT.md)，不由此测试准备变更额外触发或签发。质量定义、critical inventory、exclusions、CI selector/mapping/workflow 均不变。

PR135 对同一模块的历史 replay 对账和冻结 checker 删改仍独立审查；本候选保留其基线33方法，不预先带入删减。后续组合须保留已接受的边界，并按实际基线处理一次必要迁移。Provider source closure/AST 的生产成本改进仍由相关 owner 独立处理。
