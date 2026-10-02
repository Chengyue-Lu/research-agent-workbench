# 隔离候选 Task Packet

身份：M6-009 candidate / CANDIDATE-001。Profile：Provider factory integrator；Required Skills：[]。
Provider/Session owner：黄毅；协调准备：路诚钺。用户授权通用 API Key 层、完整主流资料、
先以 DeepSeek Flash 测试并继续推进目标；本候选不代填 owner 接受。

起点：定义候选 badbf2489235d6539ca875208ffe9cd23e735680，加 PR126 两个维护提交的 cherry-pick，
本分支起始 db46c8fa6e0767bf5a44968fa1fb5efd4cba37e7。产品集成基线仍为 develop。

读集：AGENTS、README、DEVELOPMENT、Task M6-009/010、定义 PLAN/PREPARATION、
ADR0003/0007 与 Provider Adapter plan，M6 Port/base/http/配置/协议/Session，
baseline producer/envelope/replay 的直接消费接口，以及相关 Schema/tests/fixtures、
CI component plan 和 tests/ci_components.json 的直接输入映射，以及已核验官方资料。

写域：新 configured/profile_configuration/wire_codecs/provider_binding/session_policy/conformance_ledger/conformance_journal，
显式 optional Session 分支、baseline 的 manifest 直接消费者、对应新 Schema/profile/禁用模板/
测试、组件 CI 的直接测试/fixture 输入映射、通用 repository validator 的新文档 kind/v2 分派、base响应引用错误归一和本 workstream。协议、配置、绑定、Session 委派写域互斥；协调者串行整合。
不修改旧三 facade/Port、M5/M11/Resolver/Skill 实现或 Task 完成状态。

预算：各实现切片 30～45 分钟，补充复核限 20 分钟；各委派均 0 Provider/API、真实凭据读取、安装。
根整合另做有界 repository/schema/资源检查，并可在本 worktree 忽略目录的独立环境安装当前 wheel；
不改变全局环境或其他 owner 的环境，不下载 Provider SDK，不读取 Key。
18:07 heartbeat 补充切片：纯进程内 token 预占与结算限 20 分钟，独立复核限 10 分钟。
调用者负责输入上界、实际 send 标记和独立用量回执；此 helper 不证明跨进程持久余额、
真实发送、计费上界或 live 接受。累计用户上限为输入加输出 10,000,000，失败同计。
本轮用户直接接受PR125定义，并确认费用/币种/账单不可得不阻断；PR126获正式批准后合入。
持久journal切片限25分钟，旧响应引用错误修复限10分钟；均零Provider/API、Key和安装。
继承定义以已接受develop为准，M6-009仅推进IN_PROGRESS，不改验收/依赖或置DONE。
停止条件：Core identity、Runtime ownership、Human authority 或未声明消费者需要变化时只提出问题。
输出：可重现的离线候选、原失败与最终源哈希、独立有界复核、检查和 Compact Handoff。
正式 feature PR 需合法 base 和原风险/审核门禁；不把依赖 PR 的未接受定义混入 develop 产品 PR。
