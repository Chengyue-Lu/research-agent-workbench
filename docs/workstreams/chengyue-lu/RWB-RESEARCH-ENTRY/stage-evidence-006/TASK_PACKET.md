# 执行阶段证据与 Guide 消费修复

2026-10-10；PR140候选；M2-009 / M11-008；R2。人类授权先合并PR142，然后继续实施。PR142已squash进入develop `67a7c5f6a0c3495f1ad583864d87b25f5bf892e2`；本分支已同步该来源，PR140尚未合并。

此前实际API桥接已完成，但MainState保留多个阶段的限制，Guide曾把早期“尚未返回/待发布”误当当前缺失。本切片修复实际阶段证据的发布与获准消费，不做通用风险关闭、自动恢复或完整M2-013解释验收；M2-013/M3-012仍按原依赖保持PARKED。完整Task状态不因本切片自动DONE。

## 输入、输出与允许范围

读取现行AGENTS/README/Development/Architecture、M2-009/M11-008 exact Task、REALIZATION_PLAN，以及entry workflow/state/handoff/guide/roles及直接context模型、现有MainState Schema和对应tests。原API失败只按planning-handoff-004可读记录及既有Root验证索引读取；workers不读私有付费原件。

保持MainState Core对象、Schema与human接受边界。优先用应用层版本化阶段证据工件和既有machine_state_refs/index接点，准确指向实际workflow/child Handoff/Receipt及阶段序号；保留全部限制、冲突、Human待办和未知，不按关键词删除风险、不猜测风险已关闭。读到ref、结构检查成功、产物已记录、语义或科学接受须区分。

Guide只读取明确获准的MainState和额外refs。新增阶段证据必须有独立source/hash闭合；不能凭其自述制造执行成功。不自动追读机器refs或主聊天，不写项目，不通知main。缺证据就明确未知，实际已发生的publication不再要求额外模型发布授权；不制造新Receipt种类。

交付可读模块输入/输出/直接消费者、确定性正反证据、安装消费与必要真实API原件/费用。API仍由本窗口单独执行，既有无限Attempt、累计10M、18:00–09:00及每请求fresh官方闲时授权继续适用；临时6calls/1024output/32768body/120秒/2readonlyTools仅为当前测试配置。保持所有旧Attempt原件不变，不自动付费retry/fallback。

## 有界协作

- Explorer Profile=bounded checkpoint evidence explorer；Skills=[]；只读上述state/workflow/handoff/guide/roles、MainState模型/Schema及直接tests；只写私有stage-evidence-006探索与通信，最多12分钟/8000token，给出数据来源/阶段识别、最小接口与不能推导的事实。禁止代码修改、测试/API/Tool/Key/ledger/Git。
- 实施Packet在探索后限定互斥写域，最多20分钟/12000token；workers不是独占代码库，不撤他人更改，正式输出与可见传递先落盘。Root负责测试、实际API、production Tool、凭据引用和账本。
- 只允许已授权scope的普通修复；如必须修改Core身份/Schema或自动风险关闭，报告具体缺口并停该设计，不顺手改Task定义/依赖、Registry、Topic5或source/Human接受。
