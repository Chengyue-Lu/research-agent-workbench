# FOLLOWUP-008 检查

产品 source 保持 `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`。本切片提交公开资料与便携审查摘要；selected runtime、预算组合源码、原始官方实体和合成日志仅留本地。PR128仍Draft，M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE；完整实现与exact-run具名接受均未代填。

| 检查 | 结果 | 绑定与范围 |
|---|---|---|
| selected-root预算组合 | 9/9 PASS，0.146s | 仅合成临时root；准入前零selected I/O，固定排他marker、历史basis pin、保留failed known7tokens/unknown reservation，无reset或open→create fallback |
| 预算独立复核 | 范围内无阻断 | 只读，复核自身0测试；另一root/一致rollback/native race不由marker证明 |
| runtime初版两场kernel | 2/2 PASS，186.529s | 初版源码b06cee切片：3次fake urllib调用、纯Tool7、cold1.1与exclusive输出；摘要失败保留known7tokens/失败报告/partial；不是最终源码完整测试 |
| runtime最终便宜检查 | 8/8 PASS，0.288s | 最终0fc15774；每次clock后复验pins，最后remaining漂移保留durable intent/356合成预占，HTTP entry和fake sends为0 |
| runtime最终成功kernel | 1/1 PASS，129.708s | 最终0fc15774，只重跑已有成功场景，fake opener/合成凭据/固定时间；不是120秒性能证明 |
| Qwen公开收集 | 两个document GET200，断言PASS | exact qwen3.8-max六区域价格、普通角色表与Tool例子范围、usage有限关系；费用币种不由其他型号文字补全 |
| BytePlus公开收集 | 三个目标，6项材料检查PASS | 原A5是200/null-document/零MD；按实际href取得beta1232行及Chat2518行，generic keyword/subset与selected model支持分开 |
| BytePlus linked model-list | public GET200 shell，支持表未取得 | 仅实际href一次，无JS/登录/账户；不把HTTP200当支持证明 |
| docs/public | 24/24 PASS，0.917s（final；初轮0.938s另留） | 内部链接与公共surface检查 |
| CI组件/结果/metadata契约 | 23/23 PASS，2.298s | 原有offline fixtures，真实API0；取消producer仍被result拒绝 |
| 本地R2治理 | PASS | 当前body与develop基线、显式paths；不是human review |

初轮budget fixture调用了不存在的方法，第二轮重复关闭已failed Attempt，错误日志均保留；只修fixture，最终9PASS。runtime初轮mappingproxy序列化fixture错误同样保留。独立复核发现最后send guard后裸WindowClock读取没有再核local helper pins，最终修复已独立复核关闭；最终源码检查与旧两场kernel精确分开，旧摘要失败negative未在final重复。

预算组合先由existing external admission guard接受，才读取选定basis或显式initialize/open。固定claim以O_EXCL创建并fsync；初始化/partial失败不删除，open必须匹配原claim/namespace/limits/DB/anchor，无隐式重建。该claim只约束已选root，不是全局连续性数据库或active-process锁；实际唯一累计历史、可信文件系统、另一root及一致rollback由caller承担。这里没有实际namespace、真实DB/anchor或零历史声明。

runtime是可调用的既有kernel组合：selected config/profile/model/manifest、已打开的同一journal对象与anchor/snapshot、冻结日期窗、body policy、summary sink和cold exclusive report。候选inspection入口仍拒绝；外部trusted guard才是原有执行准入，JSON/hash/测试不能替代具名接受。默认只构造environment/DEEPSEEK_API_KEY引用；真正available/resolve属于获准驱动内的晚解析。caller在outer finally关闭journal，composer只关闭自己的sink。最终父环境清理、vault child桥接和实际启动argv仍待冻结，没有在本切片调用bridge或探测凭据。

R6补强六个既有P字段，D31/P129/U5保持：qwen3.8-max两模式/百万token/input档0<Token≤1M，Singapore/International标准$2/$6，另外五区$1.65/$4.951；所选行没有夜价标签，精确cache价格仍未取得。普通角色表与Tool例子范围不同；output计费包含思考与答案不补成usage子集契约。BytePlus beta有7种type、local #引用、array/object keyword表，oneOf/allOf精确语义不严格保证，additionalProperties=false是建议；例子另一型号不为selected seed2lite/off背书。公开support表未取得，不表示服务不支持。不改变任何profile能力或Responses/中国Ark承诺。

原始官方字节与独立收据hash列在[矩阵](../../../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_MATRIX.md)；旧R4/R5、原shell与web失败保持。价格是日期化公开事实，actual账户优惠/账单另核。BytePlus支持页是SPA shell，停止于公开目标，不执行其脚本或进入console。

旧head1bd2eea hosted848项/1573.007s/2FAIL保持。head903bac6的component37062327222因实际30分钟上限CANCELLED，GitHub annotation明确30m0s；CIresult FAILED并拒绝未完成producer，原日志保留。两项修复成功路径在该日志已ok，不能冒称完整suite PASS。仅将component execute job的有界上限30→45分钟；selector、测试集合、权限、result fail-closed和legacy release CI保持，真实Flash120秒不变。产品、Schema、Registry、policy和build配置保持，既有source64/installed41/smoke8/repository202/0/0/wheel177资源119模块证据见[FOLLOWUP-006](../FOLLOWUP-006/CHECKS.md)，本切片未复跑full/global coverage。

真实API、Key值/presence、账户、实际环境/bridge、真实budget claim均0。仅精确Flash，每request北京18+且当前官方idle；累计所有成功/失败input+output≤10,000,000，非目标。计划每Attempt≤3calls/1pureTool/256output/120秒；失败STOP/归档/离线修复/refreeze后才fresh Attempt，无retry/fallback。unknown金额不阻断；unknown tokens保留预占STOP。M5/A4/Pilot/科学/发布权威独立。完整平台导出不可得，可见消息、原失败和限定收据保存，capture-gap保持；无隐藏思考。

本地冻结源码身份：预算组合 `2f4a7f8136c6ab028816517b9fbaa7f92e386feee3f5643f1e1bc60016ddc2e6`；最终runtime `0fc1577472189f1222aad9bfb39cb34f1888df9c294e062338615095118019a2`；最终runtime test `fca26dcb227a8dd2e621f3737fe5bc9e0ad5b3d58721d1f93fc27cfdada3d93b`。预算只读review receipt `47cb11aadc8f68fbbda7aaeac3268d3a490dc4b3e01f538dfe8f19ad59a5a95c`；runtime只读review receipt `646930810099404a1a2d54448e3a467700e1a1b5b9ad46b4c300a21355dc65bb`。这些不是human接受或全平台Trace。

CI timeout只读review receipt `51a1d41dc22f3f0d3fed1aae3bbc4880abb8b2adfd37ebf81573f2567c37fa2c`；确认原30m无额外强制契约，仅execute一行变化。每job上限多15分钟，是否足够仍须新head实际CI观察；不把部分日志或上传artifact覆盖producer CANCELLED。
