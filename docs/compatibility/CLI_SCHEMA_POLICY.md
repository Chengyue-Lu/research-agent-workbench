# CLI / Schema 的 0.x 兼容政策

适用范围：本仓库的 `rwb` CLI、已发布的版本化 Schema 与项目模板。包版本、Schema 版本、Registry
identity/version、模板版本和项目 revision 分别表示不同对象，不能互相替代。内部 alpha 不表示已有
PyPI 发行物，也不授权发布。

## 版本与弃用

- 在同一 `0.x` minor 内，patch 更新保留受支持命令、参数、显式选择的模板语义和已声明的 JSON 字段
  含义；修复不得悄悄改变 Human Gate 或重写旧 Schema/Registry identity。
- 新增命令或可选参数可作为兼容扩展。改变默认行为、删除命令/参数/字段或改变其解释时，需要明确
  的 minor 迁移说明、before/after 示例和回归证据。
- 已公开的 CLI 拼写或模板弃用，至少提前一个 minor 在帮助/兼容文档和变更记录中标明替代项及计划
  移除版本；到声明版本前保留显式旧入口。当前没有计划移除 `--template minimal` 或旧验证命令。
- 安全修复可直接拒绝先前错误接受的输入，但须解释被拒绝的条件、修复路径和验证证据，不能借此
  增加权限或自动迁移用户材料。

## Schema 和工件迁移

- 消费方根据文档内显式版本选择 Schema；未知版本报错，不按最新版本猜测含义。
- 已接受的版本化契约与 Registry identity 按现有 append-only 规则保留；语义变化使用新 identity/version。
- 迁移须由用户显式启动，保留原文件、原/新版本与 hash、转换器身份和结果验证；不得覆盖原工件，
  不得在加载或 `project check` 中自动升级。迁移工具仅在对应版本已经实现并验证时才能宣传可用。

## 当前项目入口

`rwb init PATH` 默认建立完整 `no-skill` 模板；`--template offline-demo` 提供离线工程示例，
`--template minimal` 保留早期最小入口。所有模板都拒绝覆盖已有材料，checkpoint/validate 原命令继续工作。
从早期最小项目过渡时，先保留原目录，在新目录初始化所需模板，再显式引入并验证自己的工件；
不能对原目录重复 init 或把参考 fixture 当作自己的研究证据。

新项目元数据格式和模板版本目前均为 `0.1.0`。元数据固定 Runtime manifest hash；升级安装包后，
若资源 pin 不同，`project check` 明确拒绝。继续使用匹配的可信安装，或按目标版本的已实现迁移流程
显式验证新资源与旧工件；仅改写 pin 不构成兼容性证明。本次不提供自动项目升级器。

详见 [项目 scaffold](../implementation/PROJECT_SCAFFOLD.md) 和 [Runtime resources](../implementation/RUNTIME_RESOURCES.md)。
