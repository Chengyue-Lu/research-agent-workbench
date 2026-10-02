# Risk Ledger

具名责任：Provider/Session 黄毅；Capability/View/DataPolicy/Evaluation 路诚钺。候选风险 R2。

| 风险 | 后果 | 必须满足的边界与反例 | 残余 |
|---|---|---|---|
| vendor 与 wire protocol 混为一谈 | DeepSeek/网关事实误记为 OpenAI | provider/adapter/profile/config 独立 pins；错 provider/endpoint/profile 零请求拒绝；returned model不匹配停止 | 官方兼容声明仍需账户实测 |
| 泛化配置静默吞掉参数 | thinking/tool/strict语义漂移 | 闭集配置，未知/不支持硬能力零调用；native mode 显式发送；tool续传未实现则 CapabilityGap | 模型升级需重验 |
| binding 漏掉配置/共享 helper | 不同 endpoint 或实现取得相同验收身份 | 版本化 manifest 固定 actual config/loaded source closure，producer/cold replay独立重建；endpoint/helper-only漂移须零出站 | 不认证远端weights/account；旧回放维持原历史语义 |
| 强制 ToolChoice 延续到文本轮 | 两轮Session被迫再次调用Tool或失败 | explicit versioned specific→none policy，默认caller语义不变；handler失败/第二轮Tool/超限必须失败 | 新政策须纳入exact pins |
| wire Schema 与本地业务断言混同 | 不支持const或false被误写PASS | 新probe独立方言审查与本地精确断言；旧probe/report保持 | 单响应不证明远端全面strict enforcement |
| 凭据泄漏或过早读取 | Key 进入日志/Trace/失败消息 | 晚解析 interface、repr/异常脱敏；预检失败的credential resolver计数0；fake sentinel 不能进入任何输出；OS bridge只对子进程注入 | 已授权 child 必须可信，不承诺不可变字符串全内存清零 |
| 自动redirect携带认证头 | 自选HTTPS endpoint之外追加跨host/降级请求 | 既有M6-001 transport维护先拒绝redirect，userinfo在resolve前拒绝；错误cause/正文不进持久诊断 | 离线handler证明不能写成真实外泄；自选endpoint仍须可信 |
| 相同模板表示多厂商全部通过 | 错误 support/科研证据 | 官方、离线、live三等级；禁用默认值；每家factory/encoder/decoder独立fixtures；unsupported能力明确拒绝 | 非DeepSeek没有live接受 |
| 费用/思考/token未知 | 失控开销/重复付费 | 硬 invocation/输出/累计token/time，0retry；未知token保留预占并停止，全部失败留存；用户接受费用/币种/账单不可得，记录unknown不填零 | 取消与remote billing可能仅有detective事实；不声称账单已核对 |
| 晚间调度被当成执行许可 | 缺失Gate时发请求 | 时间与exact Task/config/授权全部满足才调用，零请求负例 | 本机应用需保持可运行 |
| DS结果覆盖旧OpenAI验收或解锁Pilot | 虚假DONE/权限扩大 | M6-004定义和BLOCKED保留；新M6-010只接受Flash exact binding；M5 Gates保持 | 后续正式source/config drift须重验 |
| 跨worktree写冲突 | 他人更新丢失 | 独占产品worktree；共享PROJECT_MEMORY写前重读；child只交付各自准备包 | 集成前latest-base复核 |

资料/离线反例候选：未知profile/credential source；missing/ambiguous model binding；wrong returned model；
不支持ToolChoice/Schema/mode；thinking+Tool未闭合；tool ID重复/越界arguments；未知stop/usage；
pre-call零请求、post-call failure/unknown charge与停止；secret sentinel输出扫描；历史配置/报告回放。
它们是后续M6-009/010验收要求，不是此文档已执行测试。
