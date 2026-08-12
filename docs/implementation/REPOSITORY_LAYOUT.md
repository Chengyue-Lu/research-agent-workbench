# 仓库目录规划

## 1. 当前阶段

M0 只提交文档和可移植示例。实现目录在 M1 按任务创建，避免空架构先行。

## 2. 目标结构

```text
research-agent-workbench/
├── README.md
├── AGENTS.md
├── pyproject.toml                  # M1
├── src/research_workbench/         # M1
│   ├── kernel/                     # 核心对象与引用
│   ├── protocol/                   # Project Protocol / Mode Pack
│   ├── capability/                 # Profiles / Skills / Resolver
│   ├── tasks/                      # Task / Attempt / Handoff
│   ├── context/                    # Main State / checkpoint
│   ├── artifacts/                  # store / hash / promotion
│   ├── validation/                 # deterministic checks / risks
│   ├── adapters/                   # runtime and tool adapters
│   │   └── codex/
│   └── cli.py
├── schemas/                        # 生成并版本化的 JSON Schemas
├── registry/                       # Agent/Skill/Mode manifests
├── .agents/skills/                 # M2 Codex/Open Agent Skills
├── .codex/agents/                  # M2 Codex custom agents
├── examples/                       # 无敏感数据的可运行例子
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── fixtures/
│   └── evals/
└── docs/
    ├── ARCHITECTURE.md
    ├── PROJECT_CHARTER.md
    ├── TASKS.md
    ├── modules/
    ├── implementation/
    ├── decisions/
    └── references/
```

## 3. 边界规则

- `kernel` 不依赖 `adapters`、模型 SDK 或具体工具。
- `capability` 只处理元数据和解析，不执行 Agent。
- `adapters` 依赖上层契约，反向依赖禁止。
- `validation` 的 deterministic 部分不得调用 LLM。
- `.agents/skills` 可调用 `src` 中稳定脚本，但不能复制核心状态。
- `.codex/agents` 只是平台配置，不是 canonical Agent Profile 的唯一来源。
- `examples` 只使用合成/公开数据，不提交研究者私有材料。
- 项目实例与框架仓库分开；框架仓库不积累真实项目 raw/runs。

## 4. 为什么不先创建所有目录

空模块会诱导团队为架构图补代码。每个实现目录只有在对应 Task 进入 `IN_PROGRESS` 时创建；模块若只需一个文件，不强制拆包。
