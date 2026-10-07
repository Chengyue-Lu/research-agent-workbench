# CHAIN-API-PREP-004 Compact Handoff

2026-10-07；Profile bounded implementation worker；required-Skills=[]。具名路诚钺控制/预算、黄毅 API 接点审查。仅隔离 caller helper 候选；Root 是唯一测试与实际执行者。本组未执行模块、facade、Provider、transport、模型或 Tool，未取 Key、读取历史账/Attempt、预占、安装、Git mutation 或写 primary memory。

## 交付与公开接口

[helper](runtime/api_budget.py) SHA-256 `97c8a6459d66775a9d2148690a0342cfc49a1bc20c93b82bd12b8a2191317e54`，431 行。未改变 src/core/Schema/Registry 或其他代理文件。

- `BudgetConfig(namespace, prior_known_tokens, prior_held_tokens, deadline_monotonic, input_reservation_tokens, total_token_cap=10_000_000, max_calls=6, max_output_tokens=1024, max_body_bytes=32768)`：严格整数/有限时钟；累计上限不得超过人类 1000 万。输入预留是 caller 明确提供的上界，不估算实际 tokenizer。
- `ApiBudgetFacade(directory, config, *, authorize, clock=None)`：clock 为 None 时在函数体取 time.monotonic；仅实际构造时创建新独占目录；parent 须存在且由 caller 独占。相对当前 monotonic 的 deadline 必须在 120 秒以内。
- `facade.build_provider(config, *, root, credential, transport, model_environment=None, implementation_closure_ref=None)`：返回 `BudgetedProvider`。凭据/transport 必须显式注入；不调用 available/resolve。构造沿用真实 `build_profile_provider`，guard 的 response limit 透传实际 transport。
- wrapper 的 `capabilities()`、`binding_descriptor()` 透传底层真实 ConfiguredProvider；`.configured_provider` 可供 Root 独立 binding observer。此处不从 View 造 actual facts，不创造 Source qualification。
- `facade.snapshot()` 为内存观察；`facade.close()` 串行持久化 closed event 和独占 snapshot.json 并返回 snapshot。跨 intake/main/children 的 fresh Session 应共享同一 facade。跨 Attempt prior 的选择/完整性/授权由 Root 控制，不提供自动发现、续写或 Supervisor。

新增纯 `_wire_request(request)`：严格拒绝未知 metadata/非字符串值，仅去除 entry_role、task_id、baseline_sha256、input_snapshot_sha256、qualification 五个本地字段；返回 replace(request, metadata={})，不改其他字段或 extensions。Root 前置 exact wire 计算复用同一函数，不复制算法。authorize 仍接原 request，codec 与 Provider 只接 wire_request；安全本地 metadata 原件有独立文件和 actual ref/hash。

公开 material 为冻结 `RequestMaterial(url, wire_body, profile, provider, model, max_output_tokens, reservation_tokens, body_sha256)`；body/profile 字段不进入 repr。authorize(request, material) 必须严格返回 True。callback 接受 dataclass，非 dict；wire_body 是实际 bytes，profile 深冻结。

## 静态接点与行为

helper:233 起 precompute encode_profile_request/json_body、endpoint/model/output/body/calls/累计 reservation 校验；payload/URL/provider/model 经过既有 sanitizer，检查授权后编码漂移；exclusive request body + reserved event 的 fsync 完成后才进入 ConfiguredProvider.generate，随后现有 adapter 才 resolve credential。

helper:391 起 transport 二次校验实际 POST、URL、body、deadline、唯一 active guard 与一次发送；send-intent/http-entry 先 append+fsync，然后进入 caller transport。headers 只在 HttpRequest 转交过程中经过，不读取/序列化/归档。socket timeout 限为当时剩余 Attempt 时间；响应归档后再核 deadline。

响应 body 经 UTF-8/既有 sanitize_trace_value 检查；敏感或隐藏推理形状时仅记录 capture-gap 的类别，不保存正文或正文 hash。安全 body 按收到的原 bytes 独占保存并 hash；HTTP status/ref 保留。非 UTF-8/过界 body 留缺口停止；invalid JSON 的 UTF-8 body 按字符串 sanitizer 检查后原样保存，仍交当前 adapter 拒绝/分类，不生成成功响应。

helper:285 起结算：未进入 transport delegate 的释放；已进入且标准 input/output 完整已知的结算；已进入未知的保留 full hold 并停止。exception 冷核仅复用当前 codec 的纯 _profile/_usage，读取确已收到的标准字段；不将 cache/reasoning subsets 重复相加，不补零。失败本身停止，不 retry/fallback。已知 usage 超过 caller 预留会保存实际数并停止，明确报告 reservation-exceeded/cap_exceeded，不能追溯阻止已经发生的消耗。

“http-entry/sent” 是 transport delegate-entry 前的保守 attempted 事实，不证明远端已经接收；进入边界后异常亦保留 unknown hold。usage 原件仅临时用于冷核，之后释放内存引用。Archive I/O 失败设置 stopped/archive_failed，阻止后续调用；不把 partial files 当完整成功档案。

## 实际读域与固定来源

全文：本 Packet、总 TASK_PACKET、DEV4_INTAKE_HANDOFF、checkout AGENTS/README、configured.py/http.py。窄正文：base.perform_json_request、port ModelRequest/Usage/ModelResponse/ModelProvider、wire encode/usage/decode 接口、observability/trace.py 的 sanitizer。entry/intake_call.py/driver.py/executor.py/workflow.py 只作 public interface/consumer 索引窄读。没有读取凭据、真实账、原 Attempt、原 private transport 或其他代理 runtime 工件。hash 是整个源文件 bytes 的定位 pin，不表示全文解释性阅读。

| 来源 | SHA-256 |
| --- | --- |
| API_BUDGET_TASK_PACKET.md | d632484b5f187050a9266b6a541da305bcef18694553e4406d9a681481b54e3b |
| TASK_PACKET.md | 4b46cde3dbb25a5691d1c41d5f87aaab953bec2cf8bbfc18c9435ae92c2d9b95 |
| DEV4_INTAKE_HANDOFF.md | 3622933b5a7907691c12c4213c469971591ccb5952dbfc6a777dc4a52c330e84 |
| src/research_workbench/adapters/models/configured.py | 616d6b0d33c68fb1a8222ad22a9e719fbe748a99cb8148a2f78f65aabbccf043 |
| src/research_workbench/adapters/models/http.py | 8185c96c3f9a880d83099cc9da0bbc8b057fc3c2ab862483a8f93c398e91ddee |
| src/research_workbench/adapters/models/base.py | ab5500eada8ab64c12282cb496eb24772c4ebd99b7e0966312e87250c6ff3a75 |
| src/research_workbench/adapters/models/port.py | b12494881a5d3586f2d529c1af31c8fa94b1846c43a48a1d13b6ab3f3037239c |
| src/research_workbench/adapters/models/wire_codecs.py | b78f59ec04eb23e379dea60eb2b8b23a5749cb4c8041e59acb41c7db40916696 |
| src/research_workbench/observability/trace.py | e32a0e52759e97ab7f061ef5ae57976ec2c1aef5fe9133cce54c26c489d1be61 |
| src/research_workbench/entry/intake_call.py | 03717b2d7cb0bf6267e7082301697fa2eef3b41ab0c80f1319bb28bdeee9f913 |
| src/research_workbench/entry/driver.py | fd36b69a1f230098fecd22dcab7cdd7f0a2270fc1c724ad17df366d265fae46b |
| src/research_workbench/entry/executor.py | 33a356423bdf515d386083104ac9f2023ca255d22daf7b47c560497e18276ff8 |
| src/research_workbench/entry/workflow.py | 8649b896deedff5d23659dd5bb8b629589582ac3d8cbecccde8d9e7efa1f9685 |

## 验证与 Root 必测反例

静态 AST parse 与 compile(tree, ..., 'exec') PASS；未执行所得 code object、未 import helper，模块执行 0。393 行中间版本静态 PASS 后，仅追加 Tool 声明 ceiling、清理收到 usage 原件引用和 closed archive-failure guard；最终 398 行再次 AST/compile PASS。静态检查仅语法证据，不是产品测试或整链/资格接受。

Root 的最小离线/实际验证顺序：

1. 当前 profile/config +显式 scripted transport/credential：authorize 在 resolve 前，reserved fsync 在 send 前；capabilities/actual binding descriptor 对应真实 guarded ConfiguredProvider；request bytes 与 adapter 最终 body exact。
2. 非 strict True、body/output/call/总 token/deadline/模型越界、request mutation、第二 transport/重复 send：不允许 HTTP；拒绝的材料不产生成功档案。
3. intake 与 main/child fresh Session 共用 facade 后 known/held 不重置；已选择 prior held 必须始终占总 cap。并发/重入拒绝；不同 facade 不自动合并。
4. success 已知 usage、HTTP error 但标准 usage 已知、send failed/usage missing/malformed counters、model identity rejected：核真实次数、cold usage 或 full hold、failed 状态与停止，无 retry。
5. 敏感/hidden reasoning、非 UTF-8、超 response bound、request/response/event/snapshot I/O 失败：不保存 forbidden body/hash，不发布完成资格。
6. 超时后才返回、actual usage 超输入预留、未知 total：保留事实/known/held，停止；Root 报告不能把未知当 0 或声明硬取消。
7. callback 必须核 grant/source/history/time/material、Task/Profile/只读 Tool 权限交集及 output scope；helper 只限制 Tool 声明最多 2，不执行 Tool 或判断其只读实现。

## 限制与交接

本 helper 使用当前 configured._endpoint 与 wire_codecs._profile/_usage 三个私有纯函数，固定于上列 pins；未来 SDK 变化必须重新核。wrapper/guard 是额外 caller 代码，必须由 Root 真实 source closure/binding observer 明确纳入或拒绝，不能沿用旧资格；未执行该适配验证。本 helper 不提供 CLI/top-level export、Host/Receipt 或跨 Run 账，也不把新接口存在视为可 live。

独占 parent/无外部路径置换、输入-token reserve 上界、授权时窗与实际 monotonic 来源、跨 Attempt 累计 prior 完整性属于 Root 注入责任。fsync 保证文件写入提交，不提供整目录事务、跨进程 CAS 或同步 transport 的硬取消；发生部分失败保留目录供 Root 诊断。最终 close snapshot 才是串行冻结结果；运行中 snapshot 不能用于并发准入。

Root 后续：重读本文件/hash，执行关键正反测试，接真实 binding/source 资格与预算材料；按路诚钺/黄毅职责审核。primary memory 由 Root 写，本组无写权。

## Root 实际 binding 阻断反馈后的限定修复

Root 反馈：ConfiguredProvider capture_configured_provider_binding 会闭包检查 _BudgetTransport 所在整个模块的函数默认值；Facade.__init__(clock=time.monotonic) 超出当前 closed literal default language，实际构造 Provider 报 EvaluationValidationError: Provider callable default is outside the closed literal language。此运行结果由 Root 提供，本组没有执行或复测。

本组仅把 clock 默认值改为 None，函数体显式在 None 时取 time.monotonic；保持显式注入 clock 与所有核心 source binding 规则。新 400 行 helper SHA-256 137171d3b5e4ae90a536eca05d75d9f725fca687c4b56d6d1cae2c136b426538；AST_PARSE=PASS COMPILE_ONLY=PASS MODULE_EXECUTION=0，静态 clock default=Constant(value=None)。Root 自有 fixture 已改为显式模块是 Root 的反馈，本组未读取/修改该 fixture。其他 closed-default 缺口尚未运行验证，实际构造与 source closure 仍由 Root 测试；没有据此宣称 binding 已通过。
## Root 完整 intake metadata 阻断后的限定桥接修复

Root 反馈当前 helper 7/8 budget checks PASS；完整 intake 请求因必载 host-local metadata 被 wire_codecs._validate_request 拒绝，实际 API 0。此反馈是 Root 的执行证据，本组未复测。Root 要求五个字段显式保存而仅 wire 层剥离；不得放松 core codec 或吞未知供应商 metadata/extensions。

新增纯 _local_metadata/_wire_request（无默认参数）；只接受允许的五个字段和严格 str 值，空 metadata 亦可。Facade 先生成同一 wire_request，原 local metadata 纳入 sanitizer；authorize 收原 request，授权后检查原 metadata 与非 metadata 请求漂移；编码/精确 body 复核及 ConfiguredProvider.generate 用 wire_request。安全 local metadata 以 call-NNN-local-metadata.json 独占写+fsync 后记录 reserved event 的 ref/hash，snapshot 每调用亦保留该 ref。其他 messages/tools/data policy/output/extensions 保持原值，扩展仍由核心 codec 校验，helper 没有自行吞掉。

新 helper SHA-256 97c8a6459d66775a9d2148690a0342cfc49a1bc20c93b82bd12b8a2191317e54，431 行；AST_PARSE=PASS COMPILE_ONLY=PASS MODULE_EXECUTION=0。未执行 _wire_request、Provider、测试/API/Tool/Key/账/预占。Root 下一步复用 _wire_request 做 exact wire 计算，并测 original authorization/local metadata 原件与 wire metadata={}、unknown/non-str 拒绝、metadata 敏感/漂移阻断和 extensions 保持拒绝语义；实际构造/8项预算checks/完整intake仍由 Root 复验，不据静态通过声称桥接已运行。