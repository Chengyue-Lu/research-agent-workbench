# 维护范围与接受边界

既有 [M6-001](../../../TASKS.md) 三家薄 Adapter 已 DONE，本维护不改 Task 定义或状态。
[ADR-0007](../../../decisions/0007-THIN-PROVIDER-ADAPTERS.md) 要求 Key 不进入记录、标准库
HTTPS transport、晚解析、隐藏敏感 repr 和受控 live 诊断；本改动恢复这些已有边界。

## 具体问题与行为

现有 urllib 默认 redirect handler 在 HTTPS POST 的 301/302/303 后可追加 GET，并携带
Authorization/X-Api-Key/X-Goog-Api-Key。纯内存 handler 在两版 CPython 已复现跨 HTTPS host
和 HTTP 降级；没有真实外泄。transport 专属 opener 拒绝全部自动 redirect，保留安全状态与
终止分类。明确配置的合法自选 HTTPS origin/path 继续有效；不引入域名、IP/DNS trust policy。

配置与 raw transport 拒绝 URL userinfo、缺 hostname/非法 port；adapter 在 credential.resolve
前完成非秘密 URL admission 和 payload 编码。HttpRequest repr 同时隐藏 URL/header/body。
原 transport reason、HTTP response body、provider message/code、Schema/Tool 参数不能进入
公开错误链；保留 category/status/retryable 和既有 decoder 明确理解的公开 error-code 闭集。
异常在 handler 结束后抛出，不挂载原生 cause/context；不承诺内存清零或外部 traceback locals
采集器自动脱敏。原始 HTTP 响应作为内部解码输入仍存在，不能宣称它在内存从未出现。

## 互斥范围

只写 `adapters/models/http.py`、`base.py`、`configuration.py`、必要 OpenAI tool-JSON 直接
consumer 和针对这些边界的 tests。Port、Provider identity/capabilities、Session、Resolver、
View/Slot、Runtime authority、Core schema、Task/Gate 不变。无 retry/fallback、网络、真实凭据
读取、model/API account 验收。新通用接入按独立定义处理，不用维护 PR 实现 M6-009/010。

正式委派 Profile/Required Skills/输入/范围/预算/停止及可见回执保存在本地 Attempt Archive；
公共检查摘要只引用 hash 和非秘密结果。named review 与必需 CI 是 R2 合入条件，本候选不合入。
