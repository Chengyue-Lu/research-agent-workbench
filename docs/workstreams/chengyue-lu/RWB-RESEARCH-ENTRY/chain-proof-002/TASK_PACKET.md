# AUDIT-RWB-CHAIN-002：全链路桥接测试与Task校准

2026-10-07人类指令：

> 你依旧负责测试全链路的实现，确认每个桥接都可以实现即可，暂时仍然不需要接入真实任务，测试通全链路，而且目前我们的测试内容与方向已经影响且部分脱离了目前的task，可以先做task定义以及文档更新，然后做好下一步计划后直接开始测试，并同步准备各类用于测试的不同类系统提示词，skill，等。

Root是唯一整链测试执行者；开发/资产准备可独立协作。本轮先定义任务/更新文档，再形成明确bridge/运行plan，随后立即执行已授权隔离验证。目的为真实生产接口接合可达与实际产物下游消费；采用有界人工测试材料，不接真实科研任务，不作四臂评价、Skill净价值/科学质量、准入或Release决定。M5-008保留原评价身份，不以本轮模块测试替代其验收。

## 当前来源与权限

- 代码候选PR140 `d630f8e174846f4932d05a7a0d69076930b53ee1`；develop `d3c4d23206339ebc7f18b5621f3aa5453f96335e`；原65入口/53回归及hosted CI证据保持其范围。
- docs-only task-definition在独立新分支准备；代码候选与诊断留在PR140 worktree。不变更已DONE Task定义、核心Schema/Registry/权威/Runtime ownership，不自动merge或解冻M12/Topic5。
- canonical Tasks、STATUS、ROADMAP、施工导航明确对应当前目标；未合并定义标作候选，共享接受不从草稿推导。当前人类指令授权隔离准备、诊断和桥接测试。
- 读域：项目共同入口、上述对应权威文件、entry及其直接生产消费者/Schema/测试；历史运行仅按索引读取当前授权/配置/账的导航和完整性事实，不读私有评分/oracle或无关原件。凭据只经已有授权reference晚解析，不输出/归档Key或认证头。
- 真实API只由Root执行；必须先重新核当前source/config/grant/history/实际时钟与既有累计上限，不能重置或假设尚余次数。多独立同供应商会话算一个整体Attempt；unknown/failed保留，无自动付费重试/fallback。
- no-Skill/direct-tool/Skill-bearing分别列bridge与资格条件。候选提示词/Skill先为测试隔离资产；候选文件或模拟accepted/fixture不产生真实Runtime admission。未支持路径不能称整链已通过。

## 并行准备（不是测试窗口）

每次委派明确Agent Profile、required-Skills、input refs、ownership、输出、预算、停止，保存可见传递和固定输出hash。不独自在代码库，保留他人修改。准备代理不执行产品/研究API测试、生产Tool、Key/账读取、安装、commit/push、primary memory写入。

- Task-definition scout：只读canonical TASKS/ROADMAP/施工导航与原COMPLETION，给Root最小exact Task切片、owner/deps/验收、与M5/M12分界；只写本目录TASK_DEFINITION_PROPOSAL.md/通信。
- Prompt/Skill准备worker：使用skill-creator；只写本目录assets下候选SKILL.md/角色prompt与资产索引/通信。角色baseline与方法Skill职责分别表达，变量化子agent数量/事件/预算；给0..N/读域/输出格式/交接/Guide/通用写作测试材料，不接真实研究。
- 开发（4）：收到Root有界packet后定位当前缺失bridge，提出或实现可复用接点；只开发，不取Key、不跑真实测试、不建/预占生产账。

## 预期测试包

先建立逐bridge可读矩阵：人类输入→intake请求/模型输出→Protocol/Task/Method/Requirement→供给比较/唯一冻结→Bundle/View→main实际选择0..N→child独立请求/输出→main消费→Handoff/Trace/receipt→checkpoint/人类待办→独立只读Guide；另列材料接入、Source/Evidence/Claim/Method Trace、可选Skill/Tool、Human Gate/Need等启用条件，不假设每任务必须开启所有分支。

每例保存实际输入refs、实际请求角色/所载prompt-Skill hash、实际响应/Tool事件/usage及failed/unknown、producer输出、下游消费、可读结果/缺口；冷复验不调用模型。可变项由配置/主agent实际决策给出，测试场景值不写成平台固定规则。

停止：达到本Task明列bridge资格与验收；或某个切片缺实际输入/权限/资格/预算/实现并无法在当前Task解决时，保存原件和精确阻断。不得因单模块PASS、无异常退出或可读summary就报告全链已通。
