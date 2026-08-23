# 综合分析与主线建议

## 1. 当前项目的真实位置

RWB 的优势不是再实现一个通用 coding agent，而是把 Task、Method、Evidence、Claim、
Human Gate、Trace 和文件恢复放在平台之上。`main/develop@b1d5a5a` 的 API traced path 已有
扎实基础，但项目仍是 internal alpha：没有普通用户 E2E，也没有可执行 Agent Team。

当前最具体的结构性断点是：规范已接受 no-Skill/direct-tool，正式执行与归档仍耦合 legacy
Skill Assignment。该缺口不能用 dummy Skill 绕过，也不能借增加 Team 调度掩盖。它应在
M8-003 后的 Method→Capability→Execution consumer seam 中诚实解决。

## 2. 五个核心 Harness 的辩证价值

| 项目 | 值得学习 | 必须克制 |
|---|---|---|
| DeepSeek Harness | capability definition/provider/consumer、可选 subagent、durable mailbox 与 typed failure | developer-preview/实验机制不能成为 RWB 稳定依赖；session log 不能取代 Research State |
| Codex | App Server 双向协议、生成 Schema、显式 experimental Gate、原生多 Agent/权限/工具生态 | Host 状态和通知不是 RWB 权威；公开 failure signal 不证明发生率；本机启动仍产生隔离状态与网络尝试 |
| OpenCode | server/client、HTTP/OpenAPI/SSE、session lifecycle、parent deny 继承 | logical permission 不是 OS sandbox；UI/client stream 未必是完整 child Trace |
| Pi | 小型 SDK/RPC、清晰 session tree、durable harness specification | 无内置 team/permission/sandbox；spec 中未实现行为不能写成成熟能力 |
| Cline | durable core、queue、compaction、只读 subagent 与 squad example | generic orchestration 不得决定科研 Method、Evidence 或 scientific acceptance |

补充项目适合提供局部反例与机制，不足以扩张近期主线。Open Science 因身份错配完全排除
在正式结论之外。

## 3. 目标架构的精确措辞

推荐措辞是：

> RWB 保持可移植的研究控制与证据内核，以隔离 API session 作为最小参考执行；当真实
> consumer 出现时，通过可替换 Host Adapter 复用外部 Runtime 的进程、会话、工具、权限
> 和团队能力。

其中“可替换 Host Adapter”与“portable Team contract”仍是候选假设。它们不意味着现在
新增 `ExecutionHostPort`、`TeamExecutionPort` 或 Capability Snapshot v2，更不意味着恢复
全局 Supervisor。任何生产接口都须等待 M8-003、独立 Task/ADR 和同等 conformance。

## 4. Codex 实证带来的修正

Desktop 实际 Runtime 与 PATH 中 npm CLI 不是同一版本。本轮按 binary hash 固定 Desktop
缓存运行时，成功生成稳定/实验 Schema，并验证 initialize/initialized、初始化前拒绝、
重复初始化拒绝、未知方法拒绝和 experimental capability Gate。

同时，启动过程会在隔离 Codex Home 中创建 SQLite、installation ID 与 bundled skills；网络
采样看到指向失败代理 `127.0.0.1:9` 的连接尝试。它证明“只发送握手消息”不等于“进程
没有任何副作用”。因此未来 adapter 必须同时记录协议动作、runtime 自身副作用和 capture-gap。

## 5. 对 PR #20 的可操作差异

PR #20 保持独立，不成为 M8 前置。待本 workstream 合并后：

1. 固定 Codex/DeepSeek 来源，移除 moving branch 作为唯一证据；
2. 将 model-visible/logged、request snapshot、capability seam、permission、Trace completeness、
   recovery 从宽泛 `SATISFIED` 改为 scope-qualified `PARTIAL`；
3. 将“拒绝 global Supervisor”与“是否适配 portable delegation contract”拆开；
4. 为 request reconstruction 增加 redaction round-trip、完整 Trace validation 和 path-escape
   negative fixture；
5. 只称 provider-neutral sanitized reconstruction，不宣称 wire-byte replay。

Issue #17 只有在 PR #20 合并并留下最终 adoption summary 后才能关闭。

## 6. 顺序与决策

1. 不改变 M8-002 → M8-003 → Method→Capability→Execution 主线；
2. 本调研作为非阻断证据并行进入 develop；
3. M8-003 后优先闭合 no-Skill/tool-only/Skill 三路径；
4. 再用 Codex、Pi、OpenCode只读 conformance 验证 Host 假设；
5. 只有真实消费者与 ADR 才允许生产 Host/Team 实现。

因此，本工作流的交付不是“选定某个 Harness”，而是把可借鉴机制、不可越过的研究边界、
当前真实缺口与未来实验条件分开，避免外部 Runtime 反向成为项目真值。
