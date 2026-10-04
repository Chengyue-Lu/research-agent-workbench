# FULL-CI-REPAIR-001 风险表

责任人：路诚钺；Provider/source-closure审核：黄毅。R2。

| 风险 | 控制与证据 | 剩余边界 |
|---|---|---|
| 为兼容Python3.13扩大可执行代码信任 | 只识别canonical递归repr包装器、源码dataclass声明与独立标准库生成的内层代码；保留注入/伪造/错误槽拒绝 | 既有Python运行时、依赖实现和生成方法trust boundary仍如原契约声明；不证明依赖实现或真实Provider资格 |
| 参考构造先执行不可信字段truth或元数据getter | class-local params/dict/Field及name/repr/kw-only精确类型检查位于读取/生成前；四种对象注入须拒绝且零callback，原P1与中间失败保留 | 仅修复生成repr新增输入面及扫描到这类dataclass元数据的入口，不宣称普遍消除Python反射的既有信任 |
| 精确排除位置修复掩盖可执行生产逻辑 | 只登记coverage已排除的Protocol纯占位；actual源码与排除配置不变；旧工件原policy FAIL/精确候选PASS分别保存 | 新HEAD full结果仍由其自身运行确定，不用旧工件重放替代 |
| 再次移动源码导致位置漂移 | 真实源码静态分析回归与三个声明文件/政策的直接消费者映射；现有双向差集检查保留 | 新增未登记排除仍由完整checkpoint确认，不宣称短检查覆盖全仓 |
| 添加直接消费者映射意外缩小旧选集 | policy路径显式保留ci_tooling；四路径逐值对比旧选集为新选集子集，smoke及Python flags保持 | 新映射只增加一个短guard；不据此扩大到其他未知路径 |
| 把失败或取消的运行时长当提速 | 原基线、新候选、短组件及完整checkpoint分别绑定身份；没有跨HEAD性能净收益声明 | 最新full尚未完成时不能报告通过或净缩时 |
| 修复改变未涉及的Provider行为 | 单独隔离分支，只改closure兼容、policy登记和必要回归；适用cross-owner审核 | 真实账户、模型、live资格及发布不由本修复接受 |

回退通过新的revert PR恢复本修复，保留原失败记录及最新运行身份；不直接写protected分支，
不修改ruleset、取消质量定义或自行使用review例外。
