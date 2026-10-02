# 实施前零调用预检

2026-10-02；源基线 `1c9cef27983e93362be33830f989e124ad3ccc41`。
这是 PR125 的定义修正依据。Provider owner 保持黄毅，公共语义由路诚钺复核；没有新增 live PASS
或具名接受。两个既有协作窗口只写各自本地准备包；真实 Key、网络/API 调用均为 0。

## 已确认的缺口与修正谓词

| 对象 | 证据与边界 | M6-009/010 要求 |
|---|---|---|
| endpoint binding | 协调者实际构造同 class/model/caps、仅 endpoint 不同的两个 OpenAI Responses Provider；现行 observe_baseline_binding 完全相等，fake credential.resolve/send 都为 0。不是远端部署认证或 live 复现。 | actual 非秘密 config 与 source/helper 闭包进入新版本 manifest；endpoint-only/helper-only 漂移出站前拒绝。 |
| source closure / cold replay | 当前 adapter hash 只读 generate 所在单文件；baseline replay 要求 use_refs 等于独立 compiler 派生集合。单加 manifest 到 fact 不能完成回放。Session 整个源文件已经进入 host hash，不能声称所有 helper 均遗漏。 | 新版本 envelope 显式绑定 manifest，compiler/producer/replay 独立重建引用闭包；新 profile 不能退回 legacy binding；旧合同保留。 |
| Session ToolChoice | current=replace(bounded_request, messages=...) 每轮保留初始 specific；第二轮 text 不符合该 choice，第二次 Tool 又不符合一次 Tool 预算。静态源码结论。 | explicit versioned conformance specific→none transition，仅成功验证并执行 Tool result 后启用；默认行为不变，不改变 baseline 默认调用。 |
| probe 方言 | 旧 Schema/Tool probe 使用 const；所选 DeepSeek strict 子集的该 keyword 支持未闭合。 | 新版本 wire 方言独立审核，本地业务断言仍精确要求 ok=true / value=probe；结构有效与业务通过分开。保留旧 probe。 |
| transport 凭据边界 | 两版本 CPython 的真实 redirect handler 用纯内存 parent 复现 301/302/303 追加 GET 时携带三类认证头，跨 HTTPS host 和 HTTP 降级均成立；没有 socket 或真实外泄。userinfo 与原生 exception cause 也有合成反例。 | 既有 M6-001 的局部维护另行修复并审查；真实凭据前拒绝自动 redirect，先验证非秘密 URL，再 resolve，并收敛公开错误诊断。 |

实际 endpoint 反例与 transport receipts 保留在本地 Attempt Archive；机器路径、合成原始
diagnostics、官方 snapshot 不进入公共仓库。此表只总结进入定义决策的可观察事实，不能代替
实施期的产品回归或 exact source attestation。

协调者随后用独立探针再次观察该 endpoint 碰撞，并核对实际加载的 OpenAI/base/http/Port/
Session/baseline 六个源文件 bytes 全部等于上述基线 Git blobs。结果仍为 binding 相等、
fake resolve/send 均 0；原探针及首份回执保持不变。这补充来源固定证据，不扩大远端结论。

## 最小直接消费者范围

M6 adapters/config/session/conformance 与直接 CLI/Schema/registry 原范围保留。显式增加 M6 自有
`execution/baseline.py`、`baseline_envelope.py`、`baseline_closeout.py` 及其直接测试和新版本
Schema/fixtures，用于 actual Provider closure 与独立 cold replay。manifest/config/source FileRefs
按实际 bytes 校验，component closure root 按独立版本化 canonical 规则计算；不能把两个 hash
概念混同、盲信 Provider 自报 hash，或把 closure 塞进 capabilities。

保持 ModelProvider 两方法、Core five-component binding shape、provider-visible request 字段、
explicit Slot/View、四臂与唯一 Resolver。新绑定只核对已经选择的 Provider/Protocol，不替换
Supply。若实施必须改变 Core identity 或 Runtime ownership，停并另行 ADR。

新配置闭集、真实 vendor/profile、深冻结解析配置、auth/mode/endpoint、显式 codec/policy registry
以及新报告与旧版本回放在离线实现时分别验证。gateway/upstream 不可观察的信息保持 unknown；
某厂商无法完成所声明的离线路径时保留缺口并回到定义审查，不把 disabled 空模板称可运行。

## 用户预算与有界运行计划

用户最新更正原文：多打了一个零，输入输出总预算10million。
据此记录全局累计 input+output 上限 10,000,000，全部失败同计。该数值不是 Agent goal 的
推理 token budget，也不授权其他厂商、模型、数据、Tool 或 Pilot。

[PLAN](PLAN.md)的小批计划是每 Attempt 最多 3 次调用、一次纯函数 Tool、256 输出 tokens/次、
120 秒、无自动 retry/fallback；先失败归档、离线修复、重新冻结再 fresh Attempt，最多预留两次
修复复验。执行计划的这些数值由实施者保守选择，未冒称用户逐项批准。具体输入/token 预防界限、
timeout/remaining deadline、官方价格与未知费用处理在 exact-run packet 冻结。

Flash、北京时间 18:00 后和官方闲时窗约束继续有效。18:05 follow-up 是一次前置检查，定义/
实施/运行 packet 未闭合即零请求；时间、保存 Key 和预算输入不能替代任务接受或产品实现。
