# M6-008 Risk Ledger

日期：2026-09-12。Owner：黄毅。范围：未接受的 M6-008 baseline transport 候选。
本表记录影响当前验收解释的具体边界，不增加 Task 定义、Gate 或新的执行权威。

| 项目 | 当前处理 / 证据 | 剩余边界 |
| --- | --- | --- |
| Task 控制泄漏到 plain arm | **已修正**：独立公开 projection 绑定 exact Task，且由 Manifest context pin；instruction / outputs 不从完整 Task 自动复制；未知字段、替换 Task 与未冻结输入有专项反例 | 冻结者需确认公开自然语言的科研含义与各臂公平性；字段白名单不证明无偏 |
| token / character 单位混用 | **已修正**：Tool 结果字符上限从已 pin ProjectProtocol.context_policy.baseline_transport 明确读取，拒绝缺失/非正整数；与 max_input_tokens 分开 | fixture 的 16000 字符是 case 配置，不是通用默认或模型 token 换算 |
| 冻结 Task 约束仅被记录 | **已修正**：写目标同时受 write_scope、文件权限及显式 allowed_roots 约束，执行预算不得高于 Task 已声明同名 ceiling | 文件绑定的 callable 仍须由已授权调用方注册；当前 transport 不是 OS 沙箱 |
| 不同 DataPolicy 形状被当空许可 | **已修正**：data_policy_ref 明确按 ProjectProtocol Schema 读取 data_boundary，不把 ExecutionPolicy.data_egress 当同形对象 | 当前候选未增加其他 policy 格式或授权机制 |
| actual binding 的证据强度 | 观察注册 ProviderCapabilities、真实 adapter 源码、Python 可执行文件和本机 transport 描述，并与响应 provider/model 对齐；Receipt actual binding 从 typed Trace facts 独立重算 | model content hash 表示能力与选择描述，不认证模型权重或远程部署；自报描述不能升级为历史身份认证 |
| Tool fact 与资格链配对 | **已修正**：strict replay / successful closeout 按 exact Task、Tool name 与 implementation pin 对比；同一 A2 产物中以公开输入替代 Tool 并重哈希的反例被拒绝 | 验证文件关系，不构造历史执行认证；失败 producer 保存不依赖已漂移的原文件 |
| 结构化响应脱敏一致性 | **已修正**：Trace 与输出均先转普通结构再递归脱敏；真实嵌套字段反例通过 | 发生脱敏时结果保留为失败，不承诺恢复原始秘密或隐藏推理 |
| 同步调用的时间上限 | 调用前以 transport 时钟阻止超额新调用；调用后侦测超时并保留失败，专项保留晚到响应 | 无强制中断正在执行的同步调用；post-call detection 不是 hard preemption |
| 输入 token 使用 | 使用 Provider 返回的 usage 检测单次输入是否超过冻结上限 | 无通用 tokenizer，也不提供调用前精确 token 拦截；缺失 usage 不证明 token 上限已被测量验证 |
| Tool 执行范围 | 当前支持 exact-qualified、接口匹配、file-bound 的只读 ClientTool；使用前核对源码路径/哈希与 availability | 不支持写入型 Tool、自动 reselect/fallback，且源码 pin 不构成操作系统隔离 |
| 失败保存与回放完整性 | Provider 异常和调用后超时可形成可回放失败；源漂移阻止后续调用，保存失败及原 envelope snapshot | 源文件已漂移时 strict replay 仍失败；不能将 retained failure 标为完整 evidence closure |
| 合成证据外推 | 本地 scripted Provider 与真实本地函数验证 transport / Trace / Receipt 接缝；cold replay 不调用 Provider 或 Tool | 不证明 live API conformance、研究质量、科研净收益、真实案例接受或 M5 Harness 已完成 |

M5 正式执行继续依赖已批准 case、live Provider/session conformance、Harness 和既有 Skill
closeout / admission Gate。本候选不关闭这些条件，也不修改 A3/A4、M12/M13 或 Human authority。
只处理能破坏当前 M6 验收的具体问题；真实扩展需求留给后续具名 Task。

入口与验证范围见 [README.md](README.md)；实质修正过程见 [WORKLOG.md](WORKLOG.md)。
