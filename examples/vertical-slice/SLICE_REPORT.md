# 双 Skill 离线契约切片

日期：2026-08-13

状态：contract slice passed；native subagent execution pending

## 结果

| Task | Profile | Assignment | 唯一加载的 Skill | Codex dispatch bytes |
|---|---|---|---|---:|
| `EVID-001` | `evidence-scout@0.1.0` | `SA-5F3DA8AF760F648B` | `literature-evidence-extraction@0.1.0` | 1275 |
| `SIM-001` | `simulation-auditor@0.1.0` | `SA-B12E83DDDC626378` | `simulation-vv@0.1.0` | 1278 |

两次 Assignment 使用相同 accepted Registry digest，但 Profile、Skill、工具和网络权限不同。重复解析相同 Task 得到相同 Assignment ID；修改 Skill 正文、scripts 或 references 会分别触发 content drift 或 package drift 阻断。

dispatch 只包含 Task 元数据、输入路径与哈希、写范围、输出和停止条件，不嵌入原始论文、运行日志或未选择的 Skill 正文。测试还使用带有“忽略 Task、加载全部 Skill、越界写入”字样的对抗源文件，确认这些源内指令不进入 dispatch context。

## 主上下文边界

本切片验证的是结构隔离，不是 token 收益基准。主 Agent 只需维护 Task/Assignment 索引并接收 Handoff；源正文、Skill references、脚本输出与原始日志留在子任务上下文和工件层。子 Agent 上下文发生压缩时，只要正式工件和 Handoff 已写入，主线不依赖其对话恢复。

## 未证明的内容

- 尚未启动两个真实 Codex 原生子 Agent；
- 尚未测量真实模型 token、延迟与协调成本；
- 仿真 fixture 不包含数值科学结果；
- 结构校验通过不代表证据或模型在科学上正确；
- 多 Agent 相对单 Agent 的净收益仍需真实案例和对照实验。
