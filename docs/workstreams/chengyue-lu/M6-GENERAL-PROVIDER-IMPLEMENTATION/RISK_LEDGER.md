# 风险与剩余范围

| 风险 | 处理与证据 | 当前边界 |
|---|---|---|
| 协议兼容抹平服务身份或能力 | 实际 profile → factory → 编解码离线检查；未知角色、strict、模式、能力在凭据前拒绝 | 十二份 profile、九家工厂 fake 正例，不代表当前远端接受 |
| 密钥被重定向或错误诊断暴露 | 复用 PR126 的拒绝重定向和晚解析传输；畸形 Tool JSON 与响应 Schema 未解析引用错误在 except 外抛出，cause/context 均清空 | 不承诺解释器内存或 frame-local 擦除 |
| endpoint/config/helper 漂移未进入绑定 | actual instance、源码 bytes、源码声明 callable/defaults/政策常量及独立 cold replay | manifest 限同一冻结 Python runtime；生成的 dataclass 方法和外部依赖未独立源码认证 |
| 冻结类仍允许嵌套修改 | 深冻结配置/profile/政策；实际 transport/credential 方法及 options 在使用前重验 | fake identity 保持 fake，不认证远端或 fixture 内容 |
| first Tool 成功被误当完整 Session 成功 | 新政策显式两轮、Tool1；失败/取消/超限/未知 usage 不过渡 | caller 仍独立断言最终业务值及跨 probe 预算 |
| capture callback 修改当前输入或 Tool 结果 | 私有完整输入指纹及 Tool 参数/结果指纹，在 capture 后和执行/入上下文前重验 | 失败不发下一轮；回调与任意 Tool handler 的纯度仍由调用方冻结 |
| 显式 Session 经旧 Trace 泄露 raw dataclass | 独立闭集隐私摘要 sink；显式政策拒绝 generic recorder，摘要无原始内容或内容派生哈希 | 旧 M3 recorder 问题保留为独立维护缺口，未修改 Trace Core |
| 定义或 CI 被误当实现接受 | PR125定义按用户直接接受合入；PR126按正式cross-owner批准合入；本候选仅推进M6-009 IN_PROGRESS | 合法基线上另审实现，不自动merge/置DONE/live |
| fresh Attempt 清除失败用量 | 进程内 ledger 与 SQLite journal 保留成功/失败 input+output；Windows crash/reopen 及双连接预占回归；未知保持预占并阻断 | journal reopen 不清零；driver 必须冻结唯一预算文件/namespace、输入上界和真实 send 观测；替换/回滚文件与另建 DB 未获认证；费用/币种/账单不可得不停止 |
| 记账失败带出原 Provider 异常 | 独立 P2 原反例保留；统一错误出口清空 cause/context，实际 traceback 回归通过 | 仅 content-free ledger 错误边界，不承诺 Python frame-local 擦除 |
| 主流模板覆盖被误当完整实现 | SiliconFlow/OpenRouter 保留 blocking；另行核实最小可运行政策 | 未闭合前不提议 M6-009 完成 |
| 历史模型模板被当当前服务 | 官方 models/deprecations 已明确 Google2.0 Flash 关闭；新工厂在凭据前拒绝 | 原字节保留回放；独立 Gemma profile 仅 Text/off 合成路径，账户与远端接受保持 unknown |
| Windows 换行导致 FileRef 与 Git 字节不一致 | 规范为已有 Git LF blob、重 pin 33 个正例；独立 working/Git 核查 | 原失败源/receipts 保留；此前双 Python 切片不是最终新 hash 的多平台安装证明 |
| 过程留痕缺口 | 独占本地 archive 保留 dispatch、工作日志、原失败及 source receipts | 平台未暴露或未导出的完整工具事件不伪造；capture gap 保留 |

真实 Provider/API 调用、真实 Key 值读取为 0；根已在独立环境完成当前 wheel 安装检查。M5 Pilot、A4 admission、Phase C、
Supply/Resolver/Skill 和科研判断的权威边界保持独立。
