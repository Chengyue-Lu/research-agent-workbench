# M5-008 live Protocol 版本处理决定候选

2026-10-04。状态：**proposed，未接受**。责任人：路诚钺；Provider/Host接口复核：黄毅。风险R2。
这是workstream内的实现设计候选，不是accepted ADR、Pilot授权或Task完成判断。

## 问题与选择

现有Protocol@1.0.0只接受synthetic-contract-proof/confirmatory-protocol，H3与H4
执行/审查记录固定synthetic。把真实调用改purpose或放宽原Schema会重解释历史记录。
有限JSON正文也不能放进旧单字符整数盲审格式。

候选选择：保持旧文件与默认分派，新增Schema0.2.0的Protocol@2.0.0、purpose=live-pilot，
由显式LiveEvaluationInputs消费；新增Evaluation-owned scope@2.0.0。
在新Protocol内固定复用旧属性及其必要Schema fragments，v0.2 catalog独立加载。
沿用已有非执行H1排列和Core引用校验；后继H2–H5/measurement/review族另行明确新用途、版本、
实际source/catalog身份与pilot-only资格，不透过新reader接受旧synthetic downstream记录。

## 身份与authority

Core的Task/Method/Requirement/Resolution/Snapshot/Bundle/View对象身份、唯一Resolver选择、
Thin Host所有权和Human准入边界不改。采用新的Evaluation record版本与显式adapter，不增加
默认Core-kind选择或独立运行时。accepted ADR0020双传输与estimand继续是原语义依据。
后继若改变Core对象身份、routing、Human boundary或runtime ownership，须先提交相应正式ADR。

reader的Schema identity按版本目录命名，防止同名Protocol覆盖旧fingerprint。
未来parent record必须明确新validator/source/schema refs；旧H4完整catalog identity与历史zip
保持其冻结上下文，新schemas不能被当成旧身份的一部分而静默重绑。

scope是输入commitment，六个authority flags全false。Schema中的状态、hash一致性和Agent回调
不能授予Pilot、Skill admission、数据出站或Tool权限。具名authorization从外部引用已完成输入，
不让Protocol/scope反向引用未来grant形成hash循环。

## 接受要求与当前证据

具体实现、正反用例及剩余限制见[实现包](M5-008_LIVE_PROTOCOL_PACKET.md)。
原输入切片24项离线用例已通过；后续新增[独立v2 preflight](M5-008_LIVE_PREFLIGHT_PACKET.md)，
直接复用共享校验并声明可信外部接口，未改默认Core身份或权限。尚没有live execution、
实际qualified applicability verifier接入、accepted Skill或Human评分。
完整R2审查与必要CI只接受本候选范围，不代替真实输入、准入、专项授权、独立回放与run-set验收。
M5-008仍BLOCKED；所有Pilot数据保持primary_confirmatory_eligible=false。
