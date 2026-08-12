# 旧项目迁移方案

## 1. 迁移目标

从旧 `Infra` 与 `glm` 原型中提炼有价值的科研诚信和上下文思想，但不迁移其控制面复杂度、固定模块 DAG 或自建运行时假设。

迁移是“选择性重写与验证”，不是复制目录。

## 2. 资产分类

### 保留并简化

- Memory 不等于 Truth；
- Machine PASS 不等于 Scientific PASS；
- Evidence、Gate、Decision 与不可自审原则；
- 稳定 ID、内容哈希、输入版本和 write scope；
- Task required outputs、失败分类和 Resume 思想；
- Pull memory、正式工件优先、负结果保留；
- 人工关键决策边界。

### 改写

| 旧概念 | 新位置 |
|---|---|
| Domain Profile | 可组合 Research Mode Pack |
| Team/Role/Session | Agent Profile + 原生 runtime thread |
| ResumePacket | Main State + Handoff + deterministic resume check |
| External stage control | Project Protocol + Task boundary |
| Failure taxonomy | 边界触发风险登记 |
| Human PI Gate | 通用 Human Decision Gate |
| 全局 Schema | 最小内核 + Mode/Skill 专用契约 |

### 不迁移到首版

- External Supervisor；
- Hook Canary 控制平面；
- Continuity SQLite；
- 固定 26 Module DAG；
- 复杂 governance epoch 与密钥审批体系；
- 为控制机制本身建立的循环自检；
- 无真实消费者的全量事件日志。

## 3. 迁移步骤

1. 冻结旧目录为只读参考，不直接改写。
2. 生成旧资产清单和 SHA-256 快照（M1 可选任务）。
3. 每个候选概念填写迁移卡：来源、真实消费者、解决的事故、目标模块、成本、删除条件。
4. 只把通过迁移卡的概念重写到新契约。
5. 为重写后的行为创建小型 fixture 和 contract test。
6. 在首批两个案例中验证。
7. 未被实际触发的兼容代码不进入新仓库。
8. 旧项目保留 tombstone 文档，说明其为 control-plane prototype。

## 4. 迁移准入问题

每项旧机制必须回答：

1. 它解决了哪个真实错误，而非想象风险？
2. 原生 Agent/Skill/权限/线程是否已经提供？
3. 能否先作为局部脚本、Skill 或 Mode 规则？
4. 谁读取其输出并作出什么决定？
5. 预计增加多少 token、人工和维护成本？
6. 删除它会造成的最坏损失是什么？

任一问题无法回答则默认不迁移。

## 5. 路径与数据风险

旧项目来自不同目录，路径可能错误。迁移时：

- 不信任硬编码绝对路径；
- 不运行旧脚本作为迁移前提；
- 不复制 `__pycache__`、临时数据库、运行日志和压缩包；
- 所有旧引用先解析、分类，再转为 repository-relative ref；
- 不把旧 Gate 的 PASS 当新系统的已验证状态；
- 不删除原目录。

## 6. 验收条件

- 新仓库可独立理解和实现，不依赖旧路径存在；
- 每个迁移机制都能追溯到真实价值与测试；
- 旧 Supervisor/SQLite/DAG 没有成为新系统前置；
- 新内核明显小于旧全局 Schema；
- 旧材料保留为参考但不成为运行时依赖。
