# M5-008 reserved Provider transport candidate

2026-10-04。Evaluation owner：路诚钺；Provider接口复核：黄毅；R2。
隔离PR136候选；M5-008 BLOCKED，零新增真实API/Key/Tool调用。

## 复用及输入

[ReservedProviderTransport](../../../../src/research_workbench/adapters/models/reserved_transport.py)
复用已有M6的单用发送、durable intent、deadline clipping、callback后绑定检查和调用后留痕逻辑。
[原conformance facade](../../../../src/research_workbench/adapters/models/conformance_transport.py)
继续使用ConformanceUsageJournal与固定三阶段body policy；业务断言和成功终态未改。
新[Pilot facade](../../../../src/research_workbench/evaluation/live_transport.py)
显式接受PilotUsageJournal，不能把Pilot handle传入旧conformance facade。
Provider编解码及Session仍来自已有M6；没有新vendor client、retry/fallback或Runtime selector。

[PreparedProviderRequest](../../../../src/research_workbench/adapters/models/request_admission.py)
通过既有profile resolver及wire encoder冻结当前ModelRequest的完整非秘密字段、profile/config、
目标URL、实际encoded body、输出上界与正文容量上限。nested字段、model、config/source引用、
body或目标变化即拒绝；忽略于wire的metadata变化同样不能悄悄替换原请求。
正文仅存私有内存，诊断不输出正文或headers。

input_upper_verifier是可信Driver独立提供的端口，必须返回绑定exact material root的typed
VerifiedInputUpperBound；准备和发送前重验，回调后重新计算输入，不能用另一请求的结果。
正文byte上限只约束容量，不换算成billable tokens。
本切片未实现真实官方token rule/tokenizer上界证明；合成测试的32不是实际计费证据。
file字段、typed DTO或checksum本身不授予Task/Pilot权限。

## 每次调用

可信Driver先完成语义输入/权限及input upper proof，再以所选book预占并arm同一原handle。
Pilot facade以preinvoke核对reserved，持久化intent后以send核对同一未entry intent；
拒绝copied/foreign handle、bounds不同或替换的admission，不新增预占或释放旧intent。
共享机械层只委派一次send，timeout裁剪为当前remaining deadline。
慢input verifier先于current-use guard，随后只进行本地material核对，再检查deadline；
迟到、binding漂移或guard拒绝时停止，intent已写则保留hold。

可选[PreparedHttpTransport](../../../../src/research_workbench/adapters/models/http.py)端口
由[既有HTTP helper](../../../../src/research_workbench/adapters/models/base.py)在序列化后、credential.resolve之前调用。
该端口收到空headers与实际非秘密body/URL/timeout，Pilot拒绝跳过该步骤的直接send；
之后的有凭据send仍重验完整绑定/handle阶段/body并持久化intent。
原未声明此可选端口的Provider transport路径保持；conformance facade未声明该端口。
凭据仍在原helper内按一次resolve注入，不进入body admission或报告。

委派返回或抛错后记录caller-observed HTTP entry。私有response在entry capture之前保留；
正常entry、迟到或prior/source后来失效仍由book保存已发生事实。
Driver还须结算decoded usage或从受限raw response提取已知数字，并保存失败/缺口。
entry写入失败时内存response可保留数字观察，但持久账本hold不能因此释放。
这些观察不证明socket传输或remote billing；进程crash后的完整事实恢复仍须独立证据。

## 验证及后继

[合成测试](../../../../tests/test_live_transport.py)通过实际ConfiguredProvider/resolver/codec/
precredential helper/temporary Pilot book验证发送阶段及fake credential顺序，并检查正文/URL/
metadata/admission替换、foreign handle、bound漂移、slow proof、intent后拒绝、迟到/prior漂移
和entry capture失败。其Human/source applicability/输入token authority均为合成范围；
没有完成实际四臂Driver、Windows live资格或真实Skill/Pilot grant。
原M6 transport/conformance正反测试必须复验，不能把旧source66的接受绑定到新实现。

下一段是完整累计history reader、合法Model semantic Method/Requirement/Profile、M6 baseline
和单个M11 Provider-backed FrozenExecutionDriver、实际Tool/usage/Receipt/失败与cold replay，
继而有限blind package/review freeze/reveal/measurement/analysis。
具体Human freeze、独立Skill Trial/Evaluation/admission和Pilot专项授权仍待具名决定；
原1744历史和1000万累计input+output上限/Flash/北京18后且官方闲时保持。
完整获批run-set具名验收后停止于M5-004前。
