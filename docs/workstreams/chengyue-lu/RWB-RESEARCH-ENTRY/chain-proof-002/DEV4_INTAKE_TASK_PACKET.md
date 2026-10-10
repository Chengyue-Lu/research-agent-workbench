# CHAIN-DEV4-003：有界 intake 调用与明确结果

AUDIT-RWB-CHAIN-002；人类已授权在 Task 校准后测试实际桥接。Agent Profile：bounded implementation worker；required-Skills=[]；具名路诚钺控制、黄毅审核 API 接点，正式接受保持待审。

输入：本目录 TASK_PACKET.md、DEV4_HANDOFF.md；entry/intake.py、roles.py、guide.py、workflow.py 的公开接口；adapters/models 的 ModelProvider、IsolatedApiSessionRunner、ApiSessionLimits、Usage、ModelRequest 及序列化接口。只按接口必要性读取，不查凭据或运行账。

Ownership：新增 src/research_workbench/entry/intake_call.py；本目录 DEV4_INTAKE_HANDOFF.md / DEV4_INTAKE_COMMUNICATIONS.md。不要改现有 intake/compiler、Schema、Registry、任何测试或其他文件。你不独自在代码库，保留其他修改。Root 负责所有测试、整体调用组合及真实 API。禁止安装、产品测试、API/Tool/Key/账/预占、Git mutation、primary memory 写入。

目标：补上现有模型端口 → compile_control_draft → persist_control_draft 的调用接点。调用参数显式给 project root、独立 intake Task/Profile、human Protocol/Task ceilings、provider/model、fresh output directory、预算与可选受控 context。用 build_role_request 的 intake baseline 和 exact input refs；单轮、无 Tool、无 fallback/retry。自然语言需要可作为已固定 Task 输入，不要求模型猜权限。

要求：

1. preflight 验证网络/data policy、Role/Task/Profile/权限、output write scope、预算；output directory 独占，禁止覆盖。原件不捕获 secrets/认证头。配置/权限拒绝须有明确返回/记录，不得伪造 Host、Receipt、Skill admission 或 Runtime qualification。
2. 保留实际 request/response、Session status/stop、usage（含 failed/unknown）、实际 Model calls。模型输出非 complete、缺 usage、或 compiler 拒绝都不得发布成功 draft。已发送事实和未知 usage 不能丢掉。输出是可读结果报告加受控原件，而不是把未产生 draft 当成功。
3. 成功仅表示受 ceiling 约束的 draft 编译发布，返回其真实 pins。未开始、失败、拒绝、成功分别明确；后续 caller 将 intake usage 计入同一 Run，不重置预算。
4. source qualification / Method 选择 / Human 接受由既有外部契约负责，不复制 Fixture accepted 字段、不扩大 20-attempt 授权。

输出：最小可复用接口、Compact handoff、静态检查及 Root 应测正反情形；预算20分钟/2轮。缺核心契约或需改其他模块则停止对应切片，报告具体缺口。不派测试代理。本片段不能宣称全链完成。
