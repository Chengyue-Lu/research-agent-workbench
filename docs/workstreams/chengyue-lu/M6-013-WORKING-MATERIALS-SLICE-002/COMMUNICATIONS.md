# M6-013 Slice 002 Communications / Work Log

2026-10-11；仅可见通信与可观察工程事实，不保存 secrets 或隐藏推理。sender 为主窗口 `01a1064a-eaef-7da0-aebd-962910ff42b8`。正式 Packet 正文及源字节 hash 见 [Input](INPUT_MESSAGE.md)；Compact 入口为 [Handoff](HANDOFF.md)。

## Root 启动可见正文

下列唯一 omission 为机器绝对 Packet 路径，以获准源文件名标识替代；完整有界文件正文已存 Input。

> 用户已明确要求继续与你推进后续实现。前置已完成：PR144已正常squash合并2009bd6a；PR145已同步7341f968，local与hosted governance均PASS，PR145产品冻结。请读取本轮有界Task Packet：[省略机器绝对路径，授权源文件 DEV4_TASK_PACKET.txt]，然后开始M6-013 Slice002 typed材料provenance/结果槽新版本纯投影。以7341f968为精确起点；独立分支与你已有worktree复用，不改旧0.2.0、共享角色/Runtime/CI，不运行测试/API/Key/账本。Root在codex/working-input-material-slots接实际请求consumer并统一执行。先给明确函数/字段接口；15分钟第一可消费切片后冻结并给精确提交/hash。不要另建重复PR，Root集成后发布后继候选。

## 本窗口第一接口回传

> Slice002 接口确定：新模块 entry.working_material_inputs；WORKING_INPUT_VERSION='0.3.0'；project_working_material_input(task, *, role, responsibilities, materials, stop_conditions, results=(), necessary_decisions=(), counterevidence=()) -> dict。materials 直接接 read_material_inputs 已捕获快照，material_provenance 按 ordinary-input/raw-source/source-admission/source-derivative 四个分支严格白名单（acquisition.origin/parser/ref 各层拒绝extras）；raw/admission/derivative refs 必须属于当前Task.input_refs并同时存在本次材料captures，互相base一致/own ref匹配。results 单独数组，输入每项 {kind:'formal-handoff'|'result-artifact', source_ref:<exact Task input ref>, text:<已捕获UTF8>}；与materials不重复，重核同字节hash，输出 verification_scope='captured-utf8-bytes-and-task-pin'/scientific_qualification='not-established'/contract_validation='not-established'/task_completion=false。caller应将获准结果refs显式加入fresh Task.input_refs并只放results，不作为materials；程序仍负责正式Handoff/权限/数据资格和Provider前复验。source Task仅0.1.0，五项boundaries=false；旧0.2源码/Schema/测试冻结。将按此签名交付新Schema/独立test代码，15分钟段从北京时间01:28:24开始，无测试/API执行。

工具返回成功。

## Root 实际消费接点补充原文

> Root消费接口补充：本次先接独立只读Guide的显式opt-in工作请求，不声称main/intake/child或整个无额度Runtime已通。新模块working_guide.py以已校验的旧Task/Profile内部控制保留其原grant，发送候选0.3.0工作输入，不发送完整Task/Policy/context。材料来自read_material_inputs完整快照；results是显式独立源ref+UTF8同字节快照，源ref必须在本次Task精确读集中，可能只是结果文件，不能仅凭slot名称称正式Handoff已接受。建议函数project_working_material_input(task, *, role, responsibilities, materials, results=(), stop_conditions, necessary_decisions=(), counterevidence=())；results记录可用原path/sha256/revision/text，不带不明context。请尽快给你最终签名/新Schema版本；不为迎合Root删掉provenance或默许extras。Root负责把新实际request→Provider→response的调用和零请求反例接入与统一测试，旧role/guide函数保持原语义。

## 本窗口最终接口回传

> 最终签名已写入新模块：project_working_material_input(task, *, role, responsibilities, materials, stop_conditions, results=(), necessary_decisions=(), counterevidence=()) -> dict；候选Schema/version固定0.3.0。results仍严格采用 {kind:'formal-handoff'|'result-artifact', source_ref:{path,sha256,revision?}, text}，建议Guide用kind='result-artifact'；外层path/sha256/text形状须显式映射成source_ref，不隐式接受两种形状。输出追加 contract_validation='not-established'/scientific_qualification='not-established'/task_completion=false，formal-handoff仅caller分类名不等于正式契约接受。materials必须完整消费read_material_inputs带provenance的captures；raw/sidecar/selected-derived关系及nested extras严格验证，results与材料refs不重复、Task精准读集+UTF8 hash重核。独立opt-in Guide消费范围与旧grant保持一致，Root无需更改旧role/guide语义；pure模块/Schema/test交付正在完成。

工具返回成功；Root 消费范围是独立 opt-in Guide，纯投影不冒称整个 Runtime/角色链通过。

## 可观察工程事实

01:28:24+08:00 开始 15 分钟工作段。复用 managed worktree，在 exact 7341f968a561e9be4c28bf2899a8d81ccb24c346 创建 codex/m6-013-working-materials；唯一继承未提交环境 diff 是 memory generate=false/use=true，保留且不 stage。新模块/v0.3.0 文件名未占用；metadata 查询不存在的新版本目录返回非零，未将该发现算验证失败或通过。

材料生产者的直接来源字段来自 entry/materials；为路径/嵌套字段边界，扩读 source-admission Schema 及 admission marker/sidecar helper，理由见 Task Packet。三次范围读取误用非数字 First 参数失败，后改为数字范围读取；没有因此运行项目或测试。没有打开旧 API/Key/账或研究文件。旧 Slice 001 档案和分支保持。

01:32:27+08:00，标准库静态 AST/内存 compile（不执行 code object）通过，14 test methods 计数；新 Schema JSON syntax 通过，未执行 jsonschema/产品/tests。旧 working_inputs.py、旧 test_entry_working_inputs.py、v0.2.0 Schema 与 fixed source 的 git blob 逐字节一致。新 Schema 从冻结旧 Schema 的非变化部分创建独立 defs/slots，不覆盖旧版。最终相对文件目标/hash/内部 refs 与 Git staged diff 在实际提交前检查；提交/ref 与完成回传以 Git/消息身份为准。

01:35:59+08:00 首轮最终静态归档见 [Static Checks](STATIC_CHECKS.json)：三份新产品 pins 与 Handoff 一致，64 个内部 Schema refs 可定位，19 个当时的相对 Markdown 文件目标可定位，旧三份文件仍与基线字节一致。新增本归档链接后再次核 Markdown 目标数量，更新 JSON 中最后范围；未运行测试。产品提交前仅 stage 本切片 10 个新文件，config 环境设置不 stage；最终 commit/push/remote 身份由实际 Git 结果和回传保留，不推定 merged/accepted。

提交前 Git 暂存提示新 JSON 的 CRLF 会规范化为 LF，故先统一新 Schema/静态归档的实际 LF 字节并更新最终 Schema pin；未改变旧文件或 Python 模块/测试。原暂存前 Schema SHA d9ba3a47b42776f7d123b8e341f9cc9bc9fbf87c3505f70b9d70feaf4a4ed51c 保留于此；最终 SHA abd3f3cd8346933cc4c225a2927c0fb0805b913e7029f7b1a382a9e43705f100。这不是产品测试失败或 Schema 语义变更。
