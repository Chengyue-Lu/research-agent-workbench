# ENTRY-C 可见通信与执行记录

2026-10-07。Agent Profile：bounded capability-freeze caller worker；required-Skills=[]。本文件仅记录当前 ENTRY-C；机器路径归一化为 `<worktree-root>` / `<primary-checkout>`，内容不含凭据、隐藏推理或其他窗口工作材料。所有任务约束保留；旧 Task253/275 不重复归档。

## 收到的任务与授权

Root：实现有界子Task ENTRY-C（控制选择/冻结生产接点），用户批准隔离分支。cwd `<worktree-root>`，branch `codex/research-entry-integration`，base `d3c4d23`。先读 AGENTS/README/primary own-row 与 `docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/{README,TASK_PACKET,RISK_LEDGER}`。不是唯一参与者，不撤销别人修改。

独占 `src/research_workbench/entry/binding.py`、`tests/test_entry_binding.py`、本目录 COMMUNICATIONS/HANDOFF；禁止旧 Supply/Resolver/Runtime、Schema/Registry、CLI/__init__ 共享文件修改。读域现有 Capability Supply/Requirement 函数、对应 validation、runtime_bundle/execution_view 显式 manifest/producer、相关 Schema 和限定 fixtures/tests。

补可复用 caller：显式 pinned Task/Method/Requirement/Supply reports 与 trusted evidence；复用 assess_supply/resolve_status，生成独立 Resolution/Snapshot；保留 gap/ambiguous/blocked；不自行建立 runtime-execution 资格。显式 closure/consumer/policies/binding 形成并校验 Bundle→View，允许两个 public functions。外部输入 path/hash/root/type 严格，新目录独占，完整 Schema/交叉引用检查，唯一 selection、View 不重选、无 fallback、fail closed。接口参数尽快发 Root。

测试可用合法 offline fixture，不复制固定 case 到 production；不将 structural replay 转成 Runtime 资格。证据信任由真实 caller 供应，不扩大方法或人类范围；无源完整资格仍 blocked。30分钟/6轮；自身 offline tests 允许，Python 由 Root 提供；0API/生产Tool/Key/真实账/原Attempt/安装/再委派/commit/push。不增加核心 Authority/Task identity/Kind；交付有界 producer 与限制，由 Root 集成。通信/Handoff 落盘，回 hash 后停止。

Root 后续：Python `<worktree-root>/.rwb/entry-venv/Scripts/python.exe`（3.11，editable .[test]）可用，禁 reinstall。Pin 优先复用 CloseoutPin/FileReference/PinnedExecutionInput；辅助 dataclass 可用，不新增 core Schema identity。Root 每次 RoleInvocation 经 binding_factory 按实际 Task 生 pins，不固定 case。Runtime freeze 可接 explicit closure manifest+policies，复用现有 View producer；资格外部提供，不能提升 structural，blocked 可读持久化。

## 发给 Root 的可见消息

1. 已读任务入口，复用 assess_supply/resolve_status 与 Bundle/View。拟两个函数：freeze_capability_selection(root,pinned Task/Method/Requirement/Supply,qualification,evaluated_at,trusted callbacks,unique output dir)→Resolution/可选 Snapshot；freeze_execution_inputs(root,exact closure manifest/profile/slice,pinned policies/Profile/binding,execution_at,unique output dir)→Bundle/View。请求 Python 与 pin 偏好；不建立 runtime 资格。
2. 发出 exact signatures：selection 的 Task/Method/Requirement/Supply 参数采用 PinnedExecutionInput；supporting_documents 采用既有 kind/path/sha256；evidence_check 外部输入。结果 status/resolution/snapshot/summary_path/assessments。Runtime 参数完整 manifest + 四 consumer pins，结果 bundle/view/summary_path。缺 trusted evidence 持久化 blocked，无 Snapshot；正规 Resolution 复用现有选择函数并独立重算；View 不重选。
3. 两函数与 result 已落盘，首测 11 项 7 通过。3 个 Runtime 测试被旧 M11 fixture 的 comparison 文案漂移阻断，因新 caller 进行完整 SupplyChain 重算。准备由新 selection producer 重建匹配的 Resolution/Snapshot 后显式重绑 manifest；production 不改旧 Runtime。权限测试改合法较窄 Requirement，因为既有 Supply Schema 禁 external_write=true。
4. 11/11 通过，可集成两个 public functions。缺 verifier 返回 blocked + summary，无 Resolution/Snapshot；普通 gap/ambiguous/permission-blocked 保留合法 Resolution。所有结果 pins 复用 PinnedExecutionInput。Runtime 接现有 manifest dict，失败保留 candidate Bundle + blocked summary 并抛 EntryBindingError，不返回成功。先 selection，再显式重绑 manifest documents/imports/entrypoint，测试 `_execution` 给出例子。
5. 最终 15/15 通过，signatures 未变。trusted verifier fail/unknown 保留 blocked SUMMARY 与实际 assessments，不伪造与 typed 原件一致的 Resolution；Runtime Skill 有 projection 无 trusted projection verifier 也 blocked。Method capability_requirements 并集必须等于 Task.required_capabilities，沿已有 Runtime 约束。其余正常 gap/ambiguous/权限 blocked 保留 Resolution。准备 Handoff/hash，随后停止。

## 执行事实

- 13:31 UTC 开始；13:33:39 UTC 已读共同入口及 API/Schema/限定 fixture；13:36:17 UTC producer 落盘并继续 offline tests；13:39:21 UTC 14项通过，随后补人类 Task 范围约束并 15项通过。全过程未调用 API/生产 Tool，未读取 Key/原 Attempt/生产账，未安装、再委派、commit、push。
- 命令：`<worktree-root>/.rwb/entry-venv/Scripts/python.exe -m unittest tests.test_entry_binding -v`。
- 首次：11项，2 failures + 2 errors。Runtime 三项在 `CAPABILITY-RESOLUTION-COMPARISON-DRIFT` 阻断；权限测试使用非法 external_write=true 在 Schema 阻断。保留并修正测试输入，不放宽 production 校验。
- 第二次：11项通过，6.380秒。Runtime 测试先执行新 selection producer；对新 refs 显式重绑 closure，再执行 freeze。
- 第三次：13项通过，5.242秒。独立保留 trusted unknown 与源文件 mutation 断言。
- 第四次：14项通过，3.295秒；trusted fail 留可读 blocked、不改原件。`git diff --check` 无输出。
- 最后：15项通过，2.934秒；新增 Task/Method capability demand 精确一致测试。
- 六个有界工作轮：入口/API；Schema/fixture；producer+首测；fixture重建；trust fail/unknown；Task范围与交付。未做宽泛测试矩阵。

## 持久化交付

最终路径、代码/测试 SHA、接口限制和下一步见 [HANDOFF](HANDOFF.md)。Root 负责 shared PROJECT_MEMORY own-row、集成、总体回归与 PR。

## ENTRY-JOINT-CONTROL 追加通信与验证

Root 新任务：仅新建 tests/test_entry_control_chain.py、本目录 HANDOFF_JOINT.md，追加本 COMMUNICATIONS；不是唯一参与者，保留他人修改。Profile=bounded integration tester；required-Skills=[]。输入 entry/{intake,binding,executor,driver,workflow,state,guide}.py、tests/execution_fixtures.py、test_entry_executor.py、已有 binding tests 和明确 fixture 源。目标完整离线正例：compile/persist 的实际 Protocol/Task/Method输出→trusted typed evidence selection→exact manifest 重绑→Bundle/View freeze→FrozenRoleExecutor 的实际 Session/Host/Receipt→workflow→checkpoint/Guide。所有下游必须用新 producer 实际返回 pins；不能仅独立 module 验证，不能声称 fixture live；允许既有 RuntimeBundleFixture/ExecutionViewFixture，不 import其他 TestCase。0child可，本例不重测动态0..N。10分钟/2轮；契约若不能闭合，保留具体桥接缺口，不改 core/validator/资格/Mock pass。禁止 Key/真实API/生产Tool/安装/commit/push及其他源码修改。Root 处理 CLI/总体回归。

发给 Root：首次通过完整 producer→Session/Host/Trace/Receipt→workflow/state/Guide request。实际编译/持久化 pins 进入 selection，再重绑7-doc/11-edge manifest；实际 offline Provider端口1次 generate，1main/0child，usage38/held0，Receipt独立验证通过；Task完成/Human接受=false。没有改旧core/validator或建立live来源资格；Guide仅构造只读请求未发送。本例证明离线模块接合，不证明 intake 模型/API质量或whole Task完成。

实际读取：上述指定入口/public interfaces、限定原 fixture/test；通过 executor test 的明确 fixture 导入，定位并读取 tests/test_entry_driver.py 中的 ScriptedRoleProvider/observe、scaffold._protocol；为控制 Draft 的 pin/Mode/Requirement 形状定向查看 tests/test_entry_intake.py 相关测试。没有读私有日志、原 Attempt、Key 或真实账。

执行：13:48:54 UTC 开始；13:50:35 UTC 首测结束。命令 `<worktree-root>/.rwb/entry-venv/Scripts/python.exe -m unittest tests.test_entry_control_chain -v`，1项通过，8.578秒。真实调用已有 compile/persist、assess/resolve、Bundle/View loaders/producer、SessionExecutionDriver、execute_frozen_view、generic Receipt build/independent validate、workflow、checkpoint、Guide request builder；没有 monkeypatch/mocking 校验器或固定成功状态。

测试输出在 TemporaryDirectory，执行结束清理；报告保留明确输入、输出类型、断言和命令，测试源可重跑。两轮：接口定位+测试实施；通过结果+Handoff。交付详情见 [HANDOFF_JOINT](HANDOFF_JOINT.md)。没有变动旧binding.py、任何现有fixture、core或Schema/Registry。
