# CHAIN-API-PREP-004 可见通信与静态准备

2026-10-07；Profile bounded implementation worker；required-Skills=[]。本组只准备代码，不执行预算 facade、ledger、reservation、Provider、Transport 或 Tool。

## Root → 本组（机器路径归一，其余原文）

> 执行 CHAIN-API-PREP-004，Packet 已落盘：docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/API_BUDGET_TASK_PACKET.md。按其完整读域、Profile、Skills=[]、ownership、预算与停条件做准备。你不独自在代码库，保留其他改动。只负责 runtime/api_budget.py 和两个对应 handoff/communications 文件，禁止测试/API/Tool/Key/历史账/预占/Git mutation。当前 SDK 与旧 private reserved transport 不兼容，需要纯静态可审 helper；Root 是唯一测试执行者。先存可见派单原文及你的回传，最终给接口与静态检查证据。

原消息的绝对 Packet 路径归一为 repository-relative；可见传递可在 Root 对话定位。

## 本组回传/进度

> 我先读预算准备 Packet，确认 helper 的接口和禁用操作；只做静态准备，测试与实际调用留给 Root。

## 后续可见回传与静态事件

本组 → Root（公开接口预告原文）：

> CHAIN-API-PREP-004 接口拟定：BudgetConfig(namespace, prior_known_tokens, prior_held_tokens, total_token_cap=10_000_000, max_calls=6, max_output_tokens=1024, max_body_bytes=32768, deadline_monotonic, input_reservation_tokens)；ApiBudgetFacade(directory, config, *, authorize(request, material), clock) 只在 Root 实际构造时建立独占目录；facade.build_provider(config, *, root, credential, transport, model_environment=None, implementation_closure_ref=None) 返回 ModelProvider wrapper，.configured_provider 可供实际 binding observer，capabilities()/binding_descriptor() 透传底层当前 ConfiguredProvider；facade.snapshot()/close() 返回累计 known/held/remaining 与每调用 sent/usage 状态。单 facade 可共享 intake/main/children，禁止并行/重入；每 generate 在 credential 前 encode+authorize+durable reserve，send 再核 URL/body/deadline。当前 codec 私有纯函数 _profile/_usage 用于 Provider 失败后的实际收到标准 usage 冷核，不复制计数语义；此 helper 不执行 Host/Receipt/qualification。

本组 → 可见进度：

> 预算包装会共享同一 Attempt 的累计数，先授权和持久化预留，再允许取凭据与发送。实际响应缺少完整 usage 时保留预留；敏感字段或隐藏推理触发归档缺口并停止。

> helper 已落盘，AST 解析和仅编译检查通过，尚未执行模块或测试。Root 验证时需特别检查未知 usage 保留、发送前漂移阻断和取凭据的顺序；同步 HTTP 的硬取消仍取决于注入的 transport。

本组 → Root（交付前接口/限制回传原文）：

> CHAIN-API-PREP-004 helper 与 handoff 已落盘；最终 public material 是冻结 RequestMaterial dataclass（非 dict），authorize(request, material) 严格 True。BudgetedProvider.configured_provider 供 observer 使用；capabilities/binding_descriptor 透传实际 guarded ConfiguredProvider。单 facade 共享 intake/main/children；close 持久化最终 snapshot。398 行版本 AST_PARSE/COMPILE_ONLY PASS，module/import execution=0、tests/API/Tool/Key/账/预占=0。需你实际验证 source closure 纳入 caller wrapper/guard 与 independent inner transport identity，不能沿用旧 Source qualification。仅 socket timeout 受剩余时间约束，未声称硬取消；input reserve 上界和 prior 完整性由授权 callback/Root 核。

实际阅读范围/固定 hash 见 API_BUDGET_HANDOFF.md。代码目录元数据发现 runtime 尚不存在，随后仅为本组新文件创建目录；一次 trace 文件名定位使用旧 src/research_workbench/trace 路径未命中，随后 rg --files 定位现有 observability/trace.py 并只读 sanitizer。不递归读取其他代理工件。一次批量接口输出被截断，采用允许域内窄读补接口；未把截断当全文证据。

中间 393 行 helper SHA-256 2b49d5d3a3ba0c3e4c8377dda3a76fe787adab699dde5e39a61e9eca0d3ff58c，AST/compile-only PASS。后加 Tool 声明最多 2、usage 原件临时引用清理、closed archive-failure guard；最终 398 行 helper SHA-256 8ff6058516aebf406a9faed216895cd77f211e006ccad65030aae4f25fb62d6b，AST_PARSE=PASS COMPILE_ONLY=PASS MODULE_EXECUTION=0。纯 stdlib 脚本解析/编译源码及 hash bytes，未 import helper 或执行 compile code object，未创建实际事件/账/预占目录。

最终交接只写 helper、API_BUDGET_HANDOFF.md、本通信文件。产品测试、API/Tool、Key、历史账/Attempt、实际 budget reserve、安装、Git mutation、primary/global memory、再委派均为 0。候选未实际接口验证、未资格/科学/共享接受。落盘交接后停止，Root 接测试/真实材料审查。

## Root 实际阻断反馈与单点修复（2026-10-07）

Root → 本组（原文）：

> Root实际检查发现一个真实接点阻断：ConfiguredProvider capture_configured_provider_binding 会闭包检查 _BudgetTransport 所在整个 api_budget 模块的函数默认值；Facade.__init__(clock=time.monotonic) 不属于当前 closed literal default language，构造Provider报 EvaluationValidationError: Provider callable default is outside the closed literal language。请仅在原ownership修成 clock=None，函数体显式取 time.monotonic，再静态AST/compile并保存新的handoff source hash/Root反馈通信。不要放松core source binding，不运行任何测试/API/Tool/Key/账。Root自有测试fixture已改为显式模块；未知是否还有别的closed默认缺口，当前先修此具体项。预算5分钟1轮，完成停；你不独自在代码库，保留其他编辑。

本组 → 可见进度：

> 我只修正 clock 默认值，保留核心 binding 校验；随后做静态解析与编译检查，更新交接 hash 和 Root 反馈记录。

本组 → Root（原文）：

> 已仅修 api_budget.py 的 Facade.__init__：clock 默认 None，函数体 if clock is None: clock = time.monotonic。未改核心 source binding。新 helper SHA-256 137171d3b5e4ae90a536eca05d75d9f725fca687c4b56d6d1cae2c136b426538，400 行；AST_PARSE/COMPILE_ONLY PASS，AST clock default=Constant(value=None)，module execution/tests/API/Tool/Key/账均 0。正在保存你的具体阻断反馈与交接新 pin，随后停止；其他 closed-default 接点仍未运行验证。

实际范围：重读本组 helper 的构造片段、Handoff 接口段与通信尾部，保留现有其他编辑；只变更 clock 默认值/函数体 fallback，Handoff 当前接口/hash/定位及此可见通信。静态 AST parse、compile code object（不执行）与 hash 通过；无 helper import、Provider construction、产品/模型/Tool测试、Key/账/预占、Git mutation、memory 或再委派。原398行版本证据保留为历史；本次交付是400行新 pin。Root运行错误和fixture变更只作其反馈，不作本组独立验证。落盘后停止。
## Root intake metadata 接点反馈与限定修复（2026-10-07）

Root → 本组（原文）：

> Root检查当前helper：7/8预算checks PASS；实际完整intake请求失败于 wire_codecs._validate_request，因为entry必载的host-local metadata（entry_role/task_id/baseline_sha256/input_snapshot_sha256/qualification）被Profile codec拒绝。需要真正接桥：helper显式保留并归档这些5个RWB本地字段，仅在交给当前profile pure encoder与ConfiguredProvider.generate时用replace(request, metadata={})；authorize仍拿original request（含role/hash）。任意未知metadata/非string值必须拒绝，不能随意吞供应商metadata/extensions，其他消息/tools/data policy/output不变。exact body comparison也使用同一wire_request。新增纯函数闭合literal defaults，保存安全local-metadata原件。只改原ownership helper+两交接；核心codec不放松，测试/API/Tool/Key/账仍禁止。预算5分钟1轮，sourcehash后停。Root自己会调整前置exact wire计算到同一入口，实际API0。

本组 → 可见进度：

> 我会保留并归档这五个本地 metadata 字段，只为 encoder 和 Provider 生成清空 metadata 的请求副本。授权回调继续接收原请求；未知字段或非字符串值直接拒绝，核心 codec 保持不变。

Root → 本组（原文）：

> Root前置精确wire计算会复用你新增的纯函数，请将名字固定为 _wire_request(request)，只移除已声明5个host-local metadata；返回replace后的 ModelRequest，unknown metadata拒绝。Root会从当前api_budget import它并同源固定hash，不另抄转换算法。

本组 → Root（原文）：

> 已按你固定名字提供纯 _wire_request(request)：仅接受5个 RWB host-local metadata 字段且所有值严格 str，unknown/非str 拒绝；返回 replace(request, metadata={})，其余字段与 extensions 原样保留。Facade authorize 仍拿原请求；encoder、authorize 后 exact comparison 与 ConfiguredProvider.generate 均使用 wire_request。安全 local metadata 独占保存 call-NNN-local-metadata.json，reserved event/snapshot 带实际 ref/hash，并检查授权后 metadata 漂移。新 helper SHA-256 97c8a6459d66775a9d2148690a0342cfc49a1bc20c93b82bd12b8a2191317e54，431行；AST/compile-only PASS，模块/测试/API执行0。保存通信和交接后停止。

本轮实际读域仅本组 helper 的 _Call/_prepare/generate 与 Handoff 公开接口段。只改允许 metadata 窄转换/安全原件ref、同一 wire_request consumer 和这两交接；保留核心及其他代理编辑。静态 ast.parse/compile/tree定位/hash，未 import helper 或执行 code object/任何新函数。产品测试、API/Tool/Key/账/预占、安装、Git mutation、memory、再委派=0。7/8 PASS与失败原因为 Root 反馈，尚未作独立运行验证。保存后停止。