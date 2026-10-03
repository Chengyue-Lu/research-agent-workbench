# 风险与剩余范围

| 风险 | 处理与证据 | 当前边界 |
|---|---|---|
| 协议兼容抹平服务身份或能力 | 实际 profile → factory → 编解码离线检查；未知角色、strict、模式、能力在凭据前拒绝 | 十四份 profile、十一家工厂 fake 正例；新 SF/OR 仅 standard Text，不代表当前远端接受 |
| 密钥被重定向或错误诊断暴露 | 复用 PR126 的拒绝重定向和晚解析传输；畸形 Tool JSON 与响应 Schema 未解析引用错误在 except 外抛出，cause/context 均清空 | 不承诺解释器内存或 frame-local 擦除 |
| endpoint/config/helper 漂移未进入绑定 | opt-in manifest1.1/policy-v3 派生 helper/package-init 图，检查支持语法的 callable/defaults/alias/global/class policy；ConfiguredProvider、baseline1.2 和独立 cold replay 显式消费 | compiler/native/dependency 及生成 dataclass/Enum/typing 行为是声明信任边界；现有 driver/报告仍非完整运行上下文，旧版本保持原七模块语义 |
| 冻结类仍允许嵌套修改 | 深冻结配置/profile/政策；实际 transport/credential 方法及 options 在使用前重验 | fake identity 保持 fake，不认证远端或 fixture 内容 |
| 摘要故障漏记已收到的用量 | 显式路径先保存已freeze/validate响应；FOLLOWUP-001将request、Tool attempt/result/context及普通终态捕获故障统一为SAFE_PAUSED，gap/stop写入各至多一次，终态失败不重复写入 | 不认证远端账单；unknown tokens不补零，不再执行后续Tool/模型；默认Session不变 |
| first Tool 成功被误当完整 Session 成功 | 新政策显式两轮、Tool1；失败/取消/超限/未知 usage 不过渡 | caller 仍独立断言最终业务值及跨 probe 预算 |
| capture callback 修改当前输入或 Tool 结果 | 私有完整输入指纹及 Tool 参数/结果指纹，在 capture 后和执行/入上下文前重验 | 失败不发下一轮；回调与任意 Tool handler 的纯度仍由调用方冻结 |
| 显式 Session 经旧 Trace 泄露 raw dataclass | 独立闭集隐私摘要 sink；显式政策拒绝 generic recorder，摘要无原始内容或内容派生哈希 | 旧 M3 recorder 问题保留为独立维护缺口，未修改 Trace Core |
| 定义或 CI 被误当实现接受 | PR125定义按用户直接接受合入；PR126按正式cross-owner批准合入；本候选仅推进M6-009 IN_PROGRESS | 合法基线上另审实现，不自动merge/置DONE/live |
| fresh Attempt 清除失败用量 | 显式 anchor 先 durable checkpoint 再 DB commit；prefix rollback、torn tail、单边回退、同 anchor 换 DB 与不确定提交均停，未知保持预占；默认 journal 原语义不变 | caller 仍固定唯一 DB/anchor/namespace；同用户同时重写两份或另选 anchor 不获全局防篡改认证；输入依据与真实 send 另验；unknown 金额不停止 |
| 记账失败带出原 Provider 异常 | 独立 P2 原反例保留；统一错误出口清空 cause/context，实际 traceback 回归通过 | 仅 content-free ledger 错误边界，不承诺 Python frame-local 擦除 |
| 主流模板覆盖被误当完整实现 | 旧 SF 非思考与 OR GPT-5.2 模板保留 blocking；新增独立 standard Text profile 的实际 factory 合成正例 | 新文本路径不解锁旧模板，账户与远端能力未验；未闭合前不提议 M6-009 完成 |
| 安装包缺少新profile或读取不同字节 | 显式打包14profile与两份禁用配置；新配置仅三家Text模板，typed kinds/FileRef/hash由已校验字节解析 | 原11adapter配置字节与disabled保留，不推导厂商live能力 |
| 公共源码缺少已声明安装输入 | 原 draft policy1.6.0 的13输入保持原对象，append1.7.0仅增两个Text profile与一份disabled配置；旧七个policy对象不变 | 不树形开放provider目录，不执行export或发布，不改变Skill projection、release gate与main/tag；作为R2候选审查 |
| 驱动误把shape当往返或严格远端Schema | 一次纯Tool实际执行、第二轮实际call ID/result进入历史后验证精确文本，第三轮enum Schema与本地exact业务断言分开 | 新内核只有合成离线证据，remote strict与live qualified均false |
| 冻结合成计划与实际编码 body 漂移 | 显式 immutable body policy，credential 前核 ModelRequest，intent 前核实际 closed JSON bytes；local phase 与真实 call ID/history/result 绑定 | None 保持原路径；远端 Responses strict 方言、service 并行/取消和实际费用不由本地断言推导 |
| 发送意图冒称实际网络发送 | 预占与持久intent先于委托transport调用；记录委托方法入口，失败未知保留预占；检查delegate方法/响应界限与剩余deadline | 不认证socket、远端账单、官方时间窗或调用者guard的权威；完整运行闭包另验 |
| 可序列化结果冒称具名接受 | 独立版本化闭集report Schema，报告只记录计数/数值/固定code/非秘密identity refs，fresh排他输出；CLI只离线计划 | guard/input上界caller-attested，source refs为局部，M6-009未DONE、M6-010仍BLOCKED |
| 历史模型模板被当当前服务 | 官方 models/deprecations 已明确 Google2.0 Flash 关闭；新工厂在凭据前拒绝 | 原字节保留回放；独立 Gemma profile 仅 Text/off 合成路径，账户与远端接受保持 unknown |
| Windows 换行导致 FileRef 与 Git 字节不一致 | 规范为已有 Git LF blob、重 pin 33 个正例；独立 working/Git 核查 | 原失败源/receipts 保留；此前双 Python 切片不是最终新 hash 的多平台安装证明 |
| 新图消费者拒绝路径不完整 | 独立复现MappingProxy构造拒绝、旧manifest降级遗漏引用及静态异常出口漏import，最终修复和针对性复验3/3PASS；组件原轮及清单修复分别留档 | 仅当前声明的离线作用域，driver/report和完整运行context另整合 |
| 过程留痕缺口 | 独占本地 archive 保留 dispatch、工作日志、原失败及 source receipts | 平台未暴露或未导出的完整工具事件不伪造；capture gap 保留 |

真实 Provider/API 调用、真实 Key 值读取为 0；各冻结源的安装检查见对应 Attempt CHECKS。M5 Pilot、A4 admission、Phase C、
Supply/Resolver/Skill 和科研判断的权威边界保持独立。

## FOLLOWUP-004 驱动和报告

- 显式 source-bound driver 只允许实际 UrllibTransport 与固定 body policy，启动前匹配 v3 manifest，
  caller guard 返回后复验 graph/config。普通 None 路径保留原行为；CLI 仍仅离线计划。
- 报告 1.1 保留已入场的 frozen refs，即使当前 helper 漂移或源码文件不可读取也能保留失败与用量。
  cold reader 对 config/graph/profile/model/source、policy output 和明确 Attempt 的预占引用作一致性检查。
  Unknown final accounting 保留已观察事实，不能由丢失的 cumulative snapshot 声称通过账本复核。
- 实际 delegate 身份只在运行边界观察；归档不能独立证明 socket、外部 callback 全局变量、
  native/dependency 行为、账户用量或 Windows context。caller-attested / windows-unaccepted 限定保持。
- 旧 head982c43e hosted CI37048711145 的安装路径测试 ERROR 原样保存；修复将测试指向实际
  loaded package root，原错误位置负例保持。新 head 的 CI 独立观察，不借旧绿色或抹去此失败。

## FOLLOWUP-011 本地启动准备

- parent-only超时不能证明子树退出。本地候选改为外层独占非继承Job、creation-time JOB_LIST，
  没有Start后Assign回退；原bridge仅作inner，原生Windows层级/继承/owner死亡与终止延迟仍待验证。
- 磁盘pins不足以发现已加载类方法漂移；连接层捕获强引用身份并在callback后复核实际entry。
  backend guard后按同一deadline重算wait，向下取整且过期STOP。两个独立原反例和后继修复证据分开。
- [FOLLOWUP-011检查](attempts/FOLLOWUP-011/CHECKS.md)记录39/14合成测试与独立2项复验；
  无native/Key/API/history动作，不把fake ABI或CI成功当具名接受。实际三bootstrap和完整run/context仍待闭合。

## FOLLOWUP-012 原生合成证据与数据边界

- [FOLLOWUP-012检查](attempts/FOLLOWUP-012/CHECKS.md)首次执行无凭据Windows Job测试：正常退出、超时、恢复前/后外层退出四场景通过，实际child/leaf成员和触发后停止核对。仅当前合成context；PowerShell/bridge/完整launcher/bootstrap及M6具名接受保持独立。
- 初版probe成员证明、observer握手、原子marker、触发截止和清理错误出口经独立review修复，三个旧source阶段和早检失败保留。触发≤5秒/观察同trigger+2秒排除12秒自然fuse假通过；不以最终结果抹去review晚归档17秒。
- DeepSeek Responses `store` 不支持且响应固定false；自动cache、运营日志、训练用途与账户控制不能合并为零保留。R9公共事实补强字段F07/F15但状态不升级，实际数据接受仍null。
- cf8实际855项CI及三个ZIPdigest独立归档，不借c78结果。真实native操作本轮非0，Provider/Key/vault/bridge/实际history/预算claim0；文档后继head独立核验，M6-010仍BLOCKED。
