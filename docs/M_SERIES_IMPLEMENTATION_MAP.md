# M-series Implementation / Construction Map

状态：canonical implementation navigation；由 [`TASKS.md`](TASKS.md) 派生，不拥有独立的 Task
状态、依赖或验收 authority。

这张图只回答“普通开发沿哪些 M-group 与原子 M Task 施工”。Phase、Topic、authority 与 architecture
Gate 的原因解释见 [`DEVELOPER_ARCHITECTURE_MAP.md`](DEVELOPER_ARCHITECTURE_MAP.md) 和
[`ROADMAP.md`](ROADMAP.md)。

```text
M-group = implementation family / development route
Mxx-yyy = atomic executable Task
```

## 1. M-group 主施工图

```mermaid
flowchart TB
    Foundation["M0 / M1 / M2 / M3<br/>Foundation"] --> M7["M7<br/>Mode–Skill selection baseline"]
    Foundation --> M6["M6<br/>Provider / API execution seams"]
    M7 --> M8["M8<br/>Method Core"]
    M8 --> M9["M9<br/>Evolution Foundation"]

    M9 --> M4["M4<br/>Artifact & Provenance"]
    M9 --> M10["M10<br/>Research State & Verification"]
    M9 --> M11["M11<br/>Execution Reintegration"]
    M6 --> M11

    M4 --> M5["M5<br/>Evaluation"]
    M10 --> M5
    M11 --> M5

    M5 -. "activation evidence only" .-> M13["M13 — RESERVED<br/>Strategy & Governed Evolution"]
    M10 -. "closeout may activate" .-> M12["M12 — RESERVED<br/>Continuity & Recovery"]
    M11 -. "maturity input" .-> M14["M14 — RESERVED<br/>Product / Release Closure"]
    M5 -. "maturity input" .-> M14
    M12 -. "only if later activated" .-> M14
```

箭头是 family-level 施工导航，不是机械的 hard dependency。任何具体 Task 的 exact dependency、状态、
owner、scope 与 acceptance 都以 `TASKS.md` 的 Task 行为准。M12～M14 是 reservation，不在执行队列；
虚线只表示未来 activation evidence 的可能来源，不授权实现。

## 2. M-group 索引

| M-group | Family | Definition status |
|---|---|---|
| M0 | Architecture & repository foundation | task-defined |
| M1 | Contracts & CLI | task-defined |
| M2 | Agent & Skill foundations | task-defined |
| M3 | Context, Trace & risk | task-defined；部分 residual work PARKED |
| M4 | Artifact, provenance & reproducibility | task-defined |
| M5 | Evaluation & pruning | task-defined |
| M6 | Provider/API execution seams | task-defined；具名责任人维护 |
| M7 | Mode–Skill selection & coordination evidence | task-defined |
| M8 | Method Core formalization | task-defined and complete |
| M9 | Evolution Foundation | task-defined and complete |
| M10 | Research State & verification | task-defined |
| M11 | Execution reintegration | task-defined |
| M12 | Execution Continuity & Recovery | **RESERVED** |
| M13 | Strategy & Governed Evolution | **RESERVED** |
| M14 | Product / Release Closure | **RESERVED** |

`task-defined` 只表示该 family 已有原子 Task，不表示全部 Task 已完成。实时状态仍见 `TASKS.md`。

## 3. 当前原子施工链

以下只展开已经 task-defined、与近期施工有关的链；没有为 reservation 伪造原子 Task。

```mermaid
flowchart LR
    subgraph M4["M4 Artifact & Provenance"]
        M4001["M4-001"] --> M4002["M4-002"]
        M4001 --> M4003["M4-003"]
        M4002 --> M4003
        M4002 --> M4004["M4-004"]
    end

    subgraph M10["M10 Research State & Verification"]
        M1001["M10-001"] --> M1002["M10-002"]
        M1002 --> M3009["M3-009 Method Trace"]
        M1001 --> M1003["M10-003"]
        M1002 --> M1003
        M3009 --> M1003["M10-003"]
    end

    subgraph M11Core["M11 Execution Core"]
        M1101["M11-001"] --> M1102["M11-002"]
        M1102 --> M1103["M11-003"]
        M1103 --> M1104["M11-004"]
    end

    subgraph M11Skill["M11 Optional Skill Supply"]
        M1105["M11-005"] --> M1106["M11-006"]
        M1102 --> M1106
    end

    subgraph M5["M5 Evaluation"]
        M5003["M5-003"] --> M5004["M5-004"] --> M5005["M5-005"]
    end

    M4001 --> M5004
    M4002 --> M5004
    M4003 --> M5004
    M4004 --> M5004
    M5001["M5-001 Human case Gate"] --> M5004
    M5002["M5-002 Human case Gate"] --> M5004
```

上图保留 `M3-009 Method Trace` 的历史 identity，即使它位于 M10 的 canonical implementation chain；
不得为了图形连续性 cosmetic renumber。M11 Core 的每个 producer/consumer layer 保持独立 Task 验收，
可按通用 module-level PR 规则在同一 workstream 中依 DAG 集成；optional Skill supply 不阻塞 Core。
图中省略的 hard dependencies（包括 Human/external Gate）仍须
从 `TASKS.md` 读取，不能由图推断。

## 4. Reservation activation

将 M12、M13 或 M14 从 reservation 转为正式 M-group，必须依次满足：

1. 对应 architecture area 的 activation Gate 已被接受；
2. 有证据证明现有 M-group 不能自然承载该 coherent implementation family；
3. 完成独立、docs-only 的 `task-definition`；
4. 当时再定义具体 Task ID、具名 owner、risk、hard dependencies、acceptance 与 negative boundaries。

在此之前，reservation 没有 Task state、branch/PR、CI 或 implementation authority，也不得解冻 Topic 5、
Strategy、Release，或扩大 Runtime、Capability、Method、Claim、Gate、Human Decision authority。

## 5. 日常使用

- 查项目施工位置：先看本图的 M-group，再到 `TASKS.md` 查 exact Task。
- 建 branch/PR/CI：只能引用已声明的 `Mxx-yyy`，不能引用 Phase、Topic 或 RESERVED group 代替 Task。
- 解释为何允许启动：回到 Architecture Map 查 Phase/Topic/authority/Gate。
- 发现近期工作没有 Task：停止实现，走独立 `task-definition`，不能从 reservation 或示意箭头自行扩 scope。
