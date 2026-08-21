# API 执行离线示例（K-API-2）

本目录保存 `rwb execute` 的离线脚本化示例。它演示一个已冻结 Task Packet + Skill
Assignment 如何被编译成一个有界隔离 API 会话，执行后以原子方式落盘为可重放的
Attempt 文件闭环。设计契约见
[docs/implementation/K_API_2_FILE_LOOP.md](../../docs/implementation/K_API_2_FILE_LOOP.md)。

## 文件

- `scripted-session-evidence.json.txt`：两轮脚本化 Provider 响应。第一轮调用
  `read_file`（读取 `examples/fixtures/paper-001.txt`）与 `write_artifact`
  （写入一个合法 Evidence 对象 YAML），第二轮返回 `completed` 的最终 JSON。
  该文件是执行证据输入，不是仓库文档种类；`.txt` 后缀使
  `rwb validate examples` 不会把它当作正式对象（与
  `examples/mode-skill-routing/` 的机器夹具惯例一致）。

## 用法（全离线，无网络、无凭据）

脚本化路径豁免槽位的 `model_env`，但槽位本身必须存在且启用；脚本化 Provider
只声明 text/tools/structured_output，因此槽位不得钉 `reasoning_effort`（仓库模板
的 `primary` 槽钉了 `reasoning_effort: high`，请改用 `worker` 槽）。仓库模板
`registry/models/pool.example.yaml` 的所有槽位默认禁用，因此先复制一份本地
配置并启用 `worker` 槽（`.rwb/` 与 `work/` 均被 Git 忽略）：

```powershell
New-Item -ItemType Directory -Force .rwb
Copy-Item registry/models/pool.example.yaml .rwb/pool.local.yaml
# 编辑 .rwb/pool.local.yaml，把 slot worker 的 enabled 改为 true

# 用 historical-replay 语义生成冻结的 Skill Assignment（0.1.0 为 legacy）
rwb task resolve examples/task-evidence.yaml `
  --profile registry/agents/evidence-scout.yaml `
  --registry registry/skills/accepted.json `
  --historical-replay `
  --output .rwb/assignment-evidence.yaml

# 编译 + 执行 + closeout：completed 时退出码为 0
rwb execute task `
  --task examples/task-evidence.yaml `
  --assignment .rwb/assignment-evidence.yaml `
  --slot worker `
  --pool .rwb/pool.local.yaml `
  --attempt-id AT-API-001 `
  --scripted-session examples/api-execution/scripted-session-evidence.json.txt

# 仅凭文件重放全部确定性检查（幂等）：无 BLOCK 时退出码为 0
rwb execute verify --attempt work/EVID-001/AT-API-001
```

`--scripted-session FILE` 与 `--allow-live` 互斥且必选其一；两者都不给时
CLI 以退出码 2 拒绝。live 路径（`--allow-live`）只从环境变量读取模型名与
凭据，其真实 Windows 验收属于 M6-004，不在本示例范围。
