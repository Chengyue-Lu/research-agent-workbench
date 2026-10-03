# FOLLOWUP-007 检查

产品 source 仍为 `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`；本切片更新便携文档与离线测试时钟，
运行入口候选、原始官方实体及合成测试留在本地。未改变产品、Schema、Registry、CI或policy。
PR128仍Draft；M6-009 IN_PROGRESS、M6-010 BLOCKED、候选NOT_EXECUTABLE。

| 检查 | 结果 | 证据范围 |
|---|---|---|
| 日期窗候选 | 15/15 PASS，0.001s | aware UTC、当日北京18点至午夜、UTC/monotonic非递减、重复send与失败拒绝；全部fake-time |
| installed transport + 日期窗 | 5/5 PASS，0.134s | 真正已安装transport搭配fake delegate：intent后跨窗/时钟倒退保留50合成token预占、零entry；guard工作期间跨窗和18点前拒绝 |
| 摘要sink | 12/12 PASS，0.047s | 七类闭集事件、source/output漂移、容量、secret canary、partial/失败后永久停止、exclusive输出 |
| installed summary消费者 | 4/4 PASS，0.094s | 仅抽取已安装Session的既有emit函数，合成payload消费七类事件、实际stop enums和capture-gap pairs；没有运行Session；初轮0.096s日志另保留 |
| 官方资料补充 | 两项HTTP200，12个归档索引hash匹配 | Qwen required限制、MiniMax Responses requestBody角色枚举；web原超时另留，不改写为成功 |
| 旧exact-head hosted组件 | 848项、1573.007s，2 FAIL | head1bd2eea / run37057738296，两项bound-driver成功路径返回deadline-exhausted；原日志保留 |
| 修复后source binding模块 | 7/7 PASS，349.285s | 完整bound-driver模块，fake-clock契约路径；不是live性能测量 |
| 修复后installed binding模块 | 7/7 PASS，349.596s | 复用与source字节核对一致的非editable安装产品；无需重建产品 |
| 本地caller负例 | 12 PASS＋1 native symlink SKIP，0.503s | 13项，0fail/error；JSON重复/非有限/闭集、路径/观察到的reparse、大小/总大小/hash漂移、execute先拒绝 |
| 实际候选inspection | 11个选文件pins通过 | Python3.11.16 `-I`，接受null、env PENDING、NOT_EXECUTABLE；只验证选文件bytes |
| fresh PowerShell inspection | inspect exit0；execute exit70 | `-NoProfile -NonInteractive`，实际同packet与Python/caller pins；无bridge分支 |
| docs/public | 24/24 PASS，0.912s | 内部Markdown链接及既有公共surface检查；初轮0.957s另留 |

两项失败的测试验证source/config/body与cold report，原fixture隐式用CI主机墙钟。完整图
检查消耗120秒时会使成功路径随主机负载失败。现在通过已有clock参数显式注入固定合成
monotonic值；仍保留deadline/max_seconds=120，生产实现和推进时间的deadline/timeout
拒绝测试没有改动。这是离线契约测试的时钟确定性修复，不是放宽真实运行时限。
该通过也不证明实际三调用及图检查可在120秒内完成；真实Windows部件运行的耗时仍待验收。

WindowClock每次clock读取都检查冻结的`[start,end)`，使最后remaining检查也覆盖caller
guard/source检查消耗的墙钟时间。官方idle证明、当前模型身份和具名运行选择仍来自外部
caller；不宣称native时钟可信度、socket物理发送或响应完成时间已被证明。
日期窗拒绝可能以固定WindowClockError走既有保守失败路径，不据此填零token。

本地入口/launcher仅实现inspection，接受字段必须为null，状态必须NOT_EXECUTABLE，普通
环境处理PENDING；`--execute`在读packet前拒绝。11个选定ref使用共同本地根内的相对路径，
拒绝观察到的symlink/reparse及逃逸；不导入或执行归档Provider源码，不创建报告/预算文件。
候选packet SHA256 `0211f1cdf16c214b022bbca3ec1cd7d09dba1ab717a2ccc8f1fef25edcb2506b`。
caller SHA256 `9463f121731a0680ee4d48a72efb8e27f46ac5e09d068f043c4f6fcb8d6072ed`；
launcher SHA256 `de6f31c82b04bd8994794475b2d72065296bc53fcf3afe82ff3fa4319b95d15a`。
这些hash及实际inspection argv是准备身份，不是具名接受；native/filesystem及最终运行信任
边界保留。原生symlink权限skip与未执行的native-junction补验保留，不冒充全平台链接证明。

本地summary sink仅接收现有`conformance_summary_version=1.0.0` / `record(kind,payload)`；
source pin与唯一打开的exclusive文件约束捕获。输入为固定身份、enum、有限数字和闭集字段，
拒绝原始请求、响应、Tool参数/结果、header及内容hash。第三Schema探针独立由report/journal
记录，不能冒充第三轮Session摘要。partial/fsync失败文件保留但不是成功持久化证明。

官方字段表仍为11×15=165登记项，D31/P129/U5；160项有保留事实不是完整资料收集率。
Qwen非思考required不能保证Tool，思考required不支持，托管Kimi示例不得给Qwen背书。
MiniMax message输入角色枚举补齐，但角色优先级/降级、exact模型往返仍未证明。
所有账户/部署/失败计数未知保持，公开可补字段另列；资料补充不改变Provider能力声明。

已接受计划与矩阵旧“live总最多3次”一致性已修正为每Attempt最多3次，失败归档/离线修复/
refreeze后最多再建两个fresh Attempts。全部成功/失败input+output累计≤10,000,000；次数
属于执行计划，不是用户指定9次调用或消耗目标。无自动retry/fallback。

真实API、Key/presence、bridge、真实预算文件/namespace claim均0。金额未知不阻断；
token未知保留预占并STOP。精确Flash，每request北京18+且官方idle，执行前再次核对。
原FOLLOWUP-006 source64/installed41/smoke8/repository202/0/0和wheel177资源/119模块证据
不冒称本切片重新执行。完整组件/full/global coverage不因文档准备扩大复跑。
平台完整导出不可得，所选可见输入/输出及失败保留，capture gap保持；无密钥或隐藏思考。
