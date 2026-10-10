# CHAIN-API-PREP-004：当前 API caller 的预算与原件接点

2026-10-07 最新人类原文：`直接用，授予token用量限制下的无限次attempt。`
此答复针对 Root 的“当前单个 Attempt 最高6次模型调用、20次 Attempt 与1000万累计token”的具体提议。
次数改为不限，累计仍为10,000,000；当前工程模型调用上限6、output1024/call、body32768 bytes、Attempt120秒、readonly Tools最多2及既有时窗保持。
不是 Source/Skill/Human 接受，不操作旧 paused Goal。

Profile：bounded implementation worker；required-Skills=[]。具名路诚钺控制/预算，黄毅审核 API 接点。Root 为唯一测试/API/Tool/Key/账/预占执行者。

读域：本文件、TASK_PACKET.md、DEV4_INTAKE_HANDOFF.md、entry/intake_call.py/driver.py/executor.py/workflow.py 公开接口；当前 adapters/models/configured.py、http.py、base.py、port.py、wire_codecs.py；现有 trace.sanitize_trace_value。只能读取代码，不读取任何凭据或实际账/历史运行文件。

Ownership：本目录 runtime/api_budget.py、API_BUDGET_HANDOFF.md、API_BUDGET_COMMUNICATIONS.md。只准备隔离测试 caller helper，不改 core、Schema、Registry 或 src。你不独自在代码库，保留其他编辑。禁止运行产品/模型/Tool测试、取Key、建实际账、预占、安装、Git mutation、写 primary memory或再委派。

补接点原因：当前 develop 的 ConfiguredProvider 不包含旧 private Candidate request_admission/reserved_transport 组合，旧helper不能直接套用。需要显式可检查的当前 ModelProvider/HttpTransport wrapper，Root给已验证 grant/source/history/time/material 授权回调与已选 prior 数字。

最小功能：

1. caller-owned 独占目录的 append+fsync 预算事件与最终 snapshot。单个 Attempt，传入 namespace/prior known/prior held/total cap/max calls/output cap/deadline/input reserve。无跨窗口自动选择或新全局 Supervisor。未发送释放、已发送 known settle、失败/usage unknown保留fullhold，不自动 retry/fallback。
2. 包装当前 ConfiguredProvider 与显式 HttpTransport。先 pure encode_profile_request/json_body 固定wire body、URL/profile/model/输出，校验body/output/calls/总tokens和deadline；外部 `authorize(request, material)` 必须严格True；再预留，再允许credential resolve/实际send。transport.send 再核body与URL/time，并durable记录send intent/HTTP entry；不归档认证头或Key。
3. 完整保留获准 request body、响应body（现有sanitize后发现敏感/隐藏推理形状时标注缺口并停止，禁止将其录入或资格化）、HTTP status/已发事实/usage与failed/unknown。归档失败时停止；不把未知当0。Provider异常可从确已收到的标准usage字段冷核已知数，不能猜账。
4. 透传真实 configured capabilities及独立binding_descriptor，只作为当前caller端口，不造Host/Receipt/Source qualification。Root每个实际Task仍走真实compile/resolver/freeze/Host等原接口；helper不能自己选供给或跳过profile/Task/Tool权限。

输出紧凑公开接口（配置/建立Facade/生成Provider wrapper/关闭与snapshot）、静态handoff及Root关键正反验证建议。预算20分钟/2轮；遇范围外契约缺口停止该片段并具体列出。Root准备全部实际材料及测试，不借fixture造资格。
