# 风险与剩余消费者

| 项目 | 本切片处理与证据 | 剩余边界 |
| --- | --- | --- |
| 来源记录隐式扩大读集 | 仅捕获显式 pins；未选派生项零读取，原件和选中派生关系必须由获准 sidecar 证明 | 多格式及大型材料由 M3-010 接入，普通文件的未声明来源保持可见 |
| 路径别名绕过来源区 | 同时检查声明路径、解析后位置与大小写；用真实 Windows 路径及 junction 检查 | 分区检查不授科学来源资格或 egress 权限 |
| 捕获之后或最后时钟回调漂移 | 最终 Provider 入口复验；调用计数只在进入原 Provider 时增加，材料失败代码可核 | 有权修改文件的外部并发写入属于实际文件漂移；不声称文件系统事务或 OS 隔离 |
| 捕获数量与实际调用混用 | 零调用 Host 事实及已捕获请求分别保留，失败不能变成成功 Receipt | 现行 generic closeout 在此失败分支可能 incomplete；M11/M6 后续需按真实事件分离计数 |
| 候选来源与接受混淆 | Source、Skill、科研和 Human 资格保持独立；使用离线注入 Provider 验证程序消费者 | 没有新增真实 API、生产 Attempt、科研验收或 net-value 评价 |
| M6 新旧版本及材料槽 | 纯投影独立验证，旧控制版本与角色请求保留原身份 | provenance 槽、角色请求、Task/Policy/View/Host/Session 迁移尚未接入，M6-013 不计 DONE |
| 持久归档路径与异常详情 | 保存安装正例的 FileNotFoundError、safe-paused、unknown hold；用同包同测试的短归档根作对照 | 原 wrapper 未持久化 errno/filename/stack，无法凭恢复证明具体系统根因；归档环境适用性与异常保真仍有缺口 |
| PR144 定义与实现的合并顺序 | 本地组合只作为开发候选，PR144 仍是 task-definition 的来源 | feature 不能直接重写或新增 Task 定义；PR144 接受并进入 develop 后须同步基线、重核治理与实际合并差异 |

具体测试及历史失败见 [验证记录](VERIFICATION.md)，执行边界见 [Task Packet](TASK_PACKET.md)。
