# CHAIN-API-PREP-005：真实入口逐角色冻结 factory

Profile：bounded implementation worker；required-Skills=[]。预算15分钟/2轮。Root唯一模型/Tool/Key/账/测试执行者；路诚钺负责控制面，黄毅负责API具名审查。你不独自在代码库，保留他人编辑。

Ownership：runtime/api_factory.py、API_FACTORY_HANDOFF.md、API_FACTORY_COMMUNICATIONS.md。只准备 caller helper，不修改 src/tests/Schema/Registry，不运行产品/模型/Tool测试、Key/账读取、安装或Git mutation，不再委派。

读域：本Packet、TASK_PACKET、DEV4_INTAKE_HANDOFF；entry binding/driver/executor/workflow/intake公开接口；examples/method-resolution-tasks/TASK-MR-ES-FROZEN-001.yaml、examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml、registry/capabilities/requirements/research-contract-check.yaml、examples/capability-resolution/supply-reports/no-skill-contract-check.yaml；schemas/v0.1.0/{capability-conformance-evidence,execution-binding,runtime-bundle-manifest,agent-profile,execution-policy}.schema.json（不存在者先metadata定位）；tests/execution_fixtures.py仅参考合同字段，不import、不复制fixture资格/假digest/假时间/伪conformance；当前models configured/provider_binding公开接口。

目标：通用逐Invocation factory，从Root提供的实际Task/Profile/Method/Requirement、真实typed conformance pin、实际独立ObservedExecutionBinding、actual timestamp、ConfiguredProvider创建完整比较冻结→Bundle→View→FrozenRoleBinding。不能自己制造pass/accepted/Source qualification；Root的conformance verifier必须显式回调，typed local证据范围仅本地procedure，不宣称供应商live接受。所有digest来自实际文件/独立observations，不从View倒抄。

同一总Attempt内初始与回收main严格使用call_intake真实产物Task/Method/Requirement pins；child Method基于真实parent Method绑定实际child Task；角色间完整预算由已有Workflow控制。本地Policy允许显式public synthetic context外传、不扩大Task/Profile权限；Guide保持独立只读。factory可接受readonly Tool映射/Session limits，当前先零Tool。

输出最小接口：构造factory(root, code_root, provider, observed_binding, input pins/policies/supply/conformance/verifier, timestamp callback)；__call__(invocation)返回FrozenRoleBinding，真实source/归档scope输出供Root使用。可另有纯prepare_documents函数，但不得运行它。只做AST/内存compile/Markdown/hash静态检查。

Root当前grant：在1000万累计token内不限Attempt，单Attempt当前最高6calls/output1024call/body32768/120sec，子Agent0..N由main决定。不是新Task/Method/Skill/Source/Human正式接受。遇到资格/核心Schema范围外缺口停止片段并清楚说明，不借fixture造可执行性。
