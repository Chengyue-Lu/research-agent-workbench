# M5-008 bounded Pilot journal candidate

2026-10-04。Evaluation owner：路诚钺；Provider接口复核：黄毅；R2。
隔离PR136候选，未接受；M5-008 BLOCKED，零真实调用。

[PilotUsageJournal](../../../../src/research_workbench/evaluation/live_budget.py)为单个冻结run保存预算事实，
不取Key、不调用Provider/Tool、不授予执行权限。既有M6账本和成功结束后的停止政策保持；
新文件不是全局额度服务或连续性数据库。当前只支持各臂一个预登记Attempt、失败即停的run，
不支持原run内的retry/recovery/reconciliation。

## 输入及历史

可信调用方独立选定SQLite/retained anchor/UUID identity、FrozenLiveContext、时钟及prior reader。
按已有H1重算冻结plan，仅纳入pilot slots并保留其顺序；confirmatory、未知ID、乱序和多retry slot拒绝。
budget来自exact scope，不超过context与用户1000万累计上限；最多3 calls/Attempt，
这个辅助记录的有界容量为1000 Attempts/3000 calls，不修改公共Schema。

prior reader必须返回typed VerifiedBudgetCheckpoint，实际完整known usage等于scope.prior_tokens，
无held且绑定同一checkpoint。现有RetainedConformanceBudget可直接提供已核实的M6历史；
不能用文件的approved/complete字段替代这个可信接口。新Attempt和Provider/Tool观察每次重验
prior及输入bytes。后续新run的prefix必须包含所有已执行的Trial/Pilot成功与失败，不能重选旧1744
checkpoint重置累计；本切片尚未实现跨run prefix接受或恢复。

## 单用发送与结算

每次reserve以SQLite BEGIN IMMEDIATE串行检查累计known+预占、request/call/elapsed上限。
只有创建进程持有原handle；复制、反射修改、其他实例/进程与reopen均不能使用该handle。
durable intent必须先提交，随后仅允许一次caller-observed HTTP entry；重复发送与intent后的release拒绝。
未发出拒绝可释放预占，但同样停止本run。Driver仍需在真实边界验证source/config/权限/时间、
实际input upper-bound proof与请求内容；这些账本观察不是HTTP认证或可复用permit。

所有成功和失败响应的input+output均结算。响应已收后的业务或capture失败保留实际usage，
prior/source检查随后失效也不妨碍仍持有handle的调用保存响应事实与failure。
HTTP entry是调用后保存的caller observation：已有durable intent且原handle有效时，
不因prior/source失效或返回超时抹掉该事实；迟到entry先记录并停止run，随后仍可保存实际usage。
这个记录入口不授权新I/O；真正发送前仍须检查current source/权限/窗口/原handle阶段。
晚返回或超出预占的已知usage先保留，再停止；不把超额截断成预占值。
缺任一token字段保留已知部分及整个不确定预占，usage_complete=false，不填零或自动retry。
计费币种/价格不进入此硬token账本。每个成功Attempt结束后才可进入下个冻结slot；
任何失败停止run，后面的slots保留not-started。completed仅是本账本的结算状态，不表示Task完成。

observe为[LiveUseGuard](M5-008_LIVE_VERIFICATION_PACKET.md)提供typed当前预占/累计/call/elapsed DTO。
默认Provider观察要求未使用的原handle；显式observe_before_entry只接受同一进程持有的原handle，
其durable intent已记且HTTP entry尚未发生。它不发送、释放或回退intent；entered/settled/foreign/reopen均拒绝。
use_verifier将preinvoke与send阶段分别绑定上述状态，不能用reserved预占代替durable intent，
也不能把intent重用为新Provider调用。Tool观察要求无pending hold。当前source/实际官方窗口/Human
以及transport入口与此接口的耦合仍待Driver接入，不把DTO当成执行授权。

## 文件闭包与复核

独立retained anchor在DB commit前追加并fsync完整事件chain；DB/anchor不一致即停，
不会自动截断、回滚、恢复或释放pending。SQLite schema/identity、WAL及FULL配置也每次核对。
open不重建缺文件，create不覆盖；关机/reopen保留holds，不恢复进程handle。
单个DB rollback/anchor truncation可被检出；可信本地用户的一致DB+anchor替换或另选账本
在认证范围外，必须由Maintainer独立保持唯一选择，不引入全局registry。

[离线用例](../../../../tests/test_live_budget.py)使用临时文件和明确合成authority，覆盖完整slot算术、
actual M6 retained reader接续、重复handle、并发/子进程、失败/partial/late usage、bounds和
closed diagnostics。它们不证明真实四臂transport、实际API、Human准入或科学正确性。
初始实现错误及Windows测试连接清理错误保留私有Attempt，后续结果按实际source身份记录。

下一步仍是合法Model semantic Method/Requirement/Profile slice、M6 baseline与M11 generic Driver、
actual response/Tool/Receipt及独立cold replay、有限盲审/freeze/reveal/metrics；
具体Human freeze、Skill Trial/Evaluation/admission、Pilot grant和完整run-set具名验收仍必须闭合。
