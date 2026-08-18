# Agent Trace 手工 fixture

`valid/` 是 M3-008 的最小 H1 Trace Archive。它有意只保存可观察消息、读取、工具结果、写入、
状态与引用，不保存隐藏推理。`TRACE.yaml` 是验证入口；主 Agent 默认只需读取 Envelope、Index 和
Handoff 引用，不需要加载 `events.jsonl` 或消息正文。

运行：

```powershell
$env:PYTHONPATH='src'
python -m research_workbench trace validate examples/agent-trace/valid/TRACE.yaml --root .
```

负例由 `tests/test_agent_trace.py` 对同一手工档案做隔离复制后施加单一变异，避免维护多套容易漂移
的完整 Trace 副本。
