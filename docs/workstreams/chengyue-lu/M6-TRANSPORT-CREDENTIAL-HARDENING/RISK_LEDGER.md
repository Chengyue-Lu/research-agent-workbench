# Risk Ledger

责任：实现/PR 路诚钺；Provider 维护黄毅 cross-owner review。有效风险 R2。

| 风险 | 修复/对抗性谓词 | 剩余边界 |
|---|---|---|
| redirect 携带认证头追加 egress | 同 host/跨 host/HTTP 降级，301/302/303/307/308均无第二请求；终止安全status | 合法初始自选HTTPS endpoint仍由用户信任 |
| URL 存储秘密或解析失配 | userinfo/缺hostname/非法port 在resolve/send前拒绝；配置和raw transport一致 | 语法校验不认证DNS/远端服务 |
| 原异常/Schema正文进入记录 | str/repr/formatted traceback 与 cause/context 无合成sentinel；未知message/code不公开 | traceback locals/进程内存及可信自定义transport不由本补丁全面清零 |
| 安全包装抹去有用分类 | 正常认证/限流/transient/contract category,status,retryable回归；公开码闭集 | 未知厂商原始文本保留为未公开，不冒造细分原因 |
| 维护被写成新live资格 | M6-001定义/DONE不变；原三家离线回归；0真实Key/网络/API | 新Profile/Flash/M5/Pilot需要独立资格 |
| 测试 source 缺生成资源 | 使用既有build_backend.generate生成ignored closure后复跑；保留首次失败 | source检查不替代远端installed wheel CI |

证据与实际检查见[CHECKS](attempts/MAINTENANCE-001/CHECKS.md)。
