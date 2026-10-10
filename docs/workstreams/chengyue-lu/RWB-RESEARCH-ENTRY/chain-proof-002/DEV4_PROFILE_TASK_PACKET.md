# CHAIN-DEV4-007：当前 Profile 输出上限桥接

Root离线适配检查发现当前develop Profile Schema/parser仍把implementation.limits.max_output_tokens硬限256；旧私有candidate已获1024授权但不能直接用于新SDK，8个检查均在Provider构造前拒绝，真实发送0。这是实际API整链阻断，不能降低到256并虚构完整intake。

Profile：bounded implementation worker；required-Skills=[]；ownership：src/research_workbench/adapters/models/profile_configuration.py、schemas/v0.1.0/provider-api-profile.schema.json、tests/test_provider_profile_configuration.py中的输出上限边界用例，以及本目录DEV4_PROFILE_HANDOFF/COMMUNICATIONS。具名黄毅API接口、路诚钺控制预算；仅隔离R2候选不代签接受。

读域：本Packet、总Packet、API_BUDGET_HANDOFF、docs/ARCHITECTURE、docs/DEVELOPMENT、相关module06（先filename发现）、上述三个owned文件相关limit/API Profile段。Root已有用户授予token用量限制下无限Attempt，当前单call1024、整个1000万累计上限；输出最大1024授权保持。

实现最小一致调整：Profile parser和对应Schema允许1..1024（原Profile默认/已发布bytes不变）；仍拒绝bool/float/nonpositive/nonfinite和1025，request admission继续按每个Profile自身声明max_output限制而非一概1024。更新原257拒绝边界为1025，并补1024可解析/Profile自身256请求257仍preflight拒绝的静态用例代码。没有新对象identity/Skill路由/Human/Runtime ownership改变，不改Registry/accepted ADR/config。

你不独自在代码库，保留所有他人编辑。禁止运行测试/API/Tool、读取Key/账、安装/Git/primary memory。只AST/compile或SchemaJSON syntax静态；Root跑全部相关测试。预算10分钟/1轮，完成即停；超出此上限桥接不自行扩展。保存可见通信，给sourcehash与未测试事实，勿称live通过。
