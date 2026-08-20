# 仓库目录规划

状态：历史目录设计原则；实际目录以当前 checkout 为准。

## 1. 原始阶段说明

M0 当时只提交文档和可移植示例。实现目录随后已按 M1–M7 Task 建立；下列结构用于解释模块
边界，不是当前文件清单或未来扩目录的授权。

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
│   ├── adapters/                   # model API, optional runtime, and tool adapters
│   │   ├── models/                 # Provider Port / Model Pool / API Session
│   │   └── codex.py                # optional Codex mapping
│   └── cli.py
├── schemas/                        # 生成并版本化的 JSON Schemas
├── registry/                       # Agent/Skill/Mode/Provider/Model Pool manifests
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
    ├── README.md                   # 按目的选择最小阅读集
    ├── DEVELOPMENT.md             # 实名责任、协作与当前入口
    ├── ARCHITECTURE.md
    ├── PROJECT_CHARTER.md
    ├── TASKS.md
    ├── modules/
    ├── implementation/
    ├── workstreams/                 # 以实名责任人命名的当前分支计划
    ├── decisions/
    └── references/
```

## 3. 边界规则

- `kernel` 不依赖 `adapters`、模型 SDK 或具体工具。
- `capability` 只处理元数据和解析，不执行 Agent。
- `adapters` 依赖上层契约，反向依赖禁止。
- `validation` 的 deterministic 部分不得调用 LLM。
- `.agents/skills` 可调用 `src` 中稳定脚本，但不能复制核心状态。
- `registry/models` 只保存非秘密槽位模板；模型 ID 从本地环境显式绑定，不做自动路由。
- `.codex/agents` 只是可选平台配置，不是 canonical Agent Profile 的唯一来源。
- `examples` 只使用合成/公开数据，不提交研究者私有材料。
- 项目实例与框架仓库分开；框架仓库不积累真实项目 raw/runs。
- 真实项目在自己的 `work/<task>/<attempt>/` 保存 Attempt Archive；框架仓库只提交脱敏 fixture，不默认保存真实 Agent Trace。

## 4. 为什么不先创建所有目录

空模块会诱导团队为架构图补代码。每个实现目录只有在对应 Task 进入 `IN_PROGRESS` 时创建；模块若只需一个文件，不强制拆包。
