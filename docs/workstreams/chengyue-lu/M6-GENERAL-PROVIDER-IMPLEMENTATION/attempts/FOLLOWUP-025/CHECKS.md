# FOLLOWUP-025 检查

固定输入review dbe1836/base3579e67：产品未发现blocking defect，required component45分钟超时与metadata计划竞态阻断。旧超时和缺result工件已归档；当前dbe的运行终态另核。

Root新增真实四模块/八用例的分片验证：完整collect、源码/类/方法去重、imported alias不重复执行、同模块fixture只初始化一次、分片records完整覆盖库存。故意漏片、重复/外来case、旧版本/错误head或plan/index/count、重算digest的库存漂移、失败/subtest失败均拒绝。小型计划/串行checkpoint和额外版本smoke的原职责保留。

CI_FOCUSED_001的36项有1error：小型docs+smoke被误分片；改为依据主测试模块数，CI_FOCUSED_002的36/36 PASS5.196秒。CI_CONSUMERS_001有一个attempt漂移反例的两项assertion失败：API的可变run对象导致pin被同改；冻结run字典和PR tuple后CI_CONSUMERS_002运行62项，61PASS+1 Windows skip，16.643秒。最初的编排字符串语法错误未执行patch、无文件副作用；原失败保留。

metadata测试使用虚拟clock与fake GitHub API：迟到计划等待后绑定但不宣称执行success，7秒预算按5+2耗尽，completed/missing、expired/ambiguous立即拒绝，head/attempt变化与非法等待预算拒绝。真实GitHub读取仅用于PR/CI核验，不是Provider调用。

开发2提供的7d19提交只含两个旧Provider测试文件；Root核对diff及Git对象后cherry-pick6f382。其18例本地PASS、coverage单pair197.071647→182.098508秒为peer证据，不当最终组合head或全量提速。Root真实组合源码绑定/冷回放、最终文档/治理/仓库和新head hosted结果在本档后续记录；未执行内容不补为PASS。
