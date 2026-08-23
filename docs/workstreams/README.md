# Workstream 记录约定

Workstream 保存一个有界开发单元的范围、证据、审查和关闭记录。它不是实时任务清单，也不能
替代 Git 分支、Attempt Archive、ADR、`TASKS.md` 或 `STATUS.md`。

## 新工作流目录

新工作流使用：

```text
docs/workstreams/<owner>/<task-id-or-slug>/
```

既有 `chengyue-lu-mode-skill/` 是历史目录，保持原路径，不为统一外观重写历史。
路诚钺维护的当前入口见 [`chengyue-lu/README.md`](chengyue-lu/README.md)，黄毅维护的当前入口见
[`huangyi/README.md`](huangyi/README.md)；进行中材料放在具名子目录，
不把多个独立优化作为散落文件混在 owner 根目录。

每个新目录的 `README.md` 至少声明：

- 具名 owner、必需 reviewer、对应 Task 或审计 ID；
- 基线 commit、目标 base branch、工作分支和状态；
- 目标、非目标、读写范围与公共契约影响；
- 输入来源、验证证据、未证明内容和停止条件；
- 合并后的 history 入口与尚未完成的下一动作。

## 与 Git 的关系

- 每个独立 workstream 使用一个从最新 `develop` 创建或更新的受控分支；
- 普通修订在同一分支和 workstream 内留痕，不为每次微调新建分支；
- 功能分支 squash merge 到 `develop`；一个完整 workstream 通过集成检查后，再由
  `develop` 向 `main` 发布；
- Workstream 文档不能使未合并分支的状态、证据或接口变成项目真值；
- 合并到 `main` 后，目录转为只读审计记录，并从 [`docs/history/`](../history/README.md)
  建立入口；实时状态仍只写入 [`TASKS.md`](../TASKS.md)。

## 证据纪律

- 外部页面、会议和个人草稿先固定来源、获取时间和哈希，再提炼 claim；
- 原始私密材料、机器绝对路径、密钥和完整聊天不得提交；
- 事实、推断、建议和人类决定必须分开；
- PR diff 只证明该分支行为，不能覆盖 `main` 的 ADR、TASKS 或实现状态；
- 工作流结束时明确 `ADOPT / ADAPT / DEFER / REJECT`，未批准建议不得进入 Stable surface。
