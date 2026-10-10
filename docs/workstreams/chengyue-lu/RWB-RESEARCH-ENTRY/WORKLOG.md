# 有界工作记录

2026-10-07；用户已批准本分支实现、测试、推送、新PR和两个独立规划窗口。Root负责集成/Git，三个代码代理各自限定ownership；两个新窗口只规划。无付费模型、生产Tool、科研Attempt或累计账操作。本页是导航与结果摘要，交付细节与可见通信分别留在各组文件。

| 阶段 | 实际结果 / 必要性 | 证据 |
|---|---|---|
| Source/隔离 | remote develop固定 `d3c4d23206339ebc7f18b5621f3aa5453f96335e`；managed worktree/new `codex/research-entry-integration` | TASK_PACKET；保留primary其他修改，新worktree仅local memory-policy未stage |
| 角色与控制 | baseline实际进入独立ModelRequest；控制草稿在独立人类ceilings内compile/persist；Guide独立只读 | [control/HANDOFF](control/HANDOFF.md) |
| 冻结与执行 | 显式typed Supply检查、冻结selection，Bundle/View生产与重放；注入Provider→Session→Host/Trace/receipt | [binding/HANDOFF](binding/HANDOFF.md)、[runtime/HANDOFF](runtime/HANDOFF.md) |
| 主任务caller/状态 | main提出可变0..N，校验完整child wave后顺序执行并消费结果；预算跨fresh调用；固定报告→exclusive checkpoint | workflow/state/executor源及所属tests |
| 独立复核/修复 | 原R1limits构造、R2failed/unknown计数、R3末轮Task预算、R4state字段证据一致性；实际反例保留并修复 | [原报告](review/RUNTIME_REVIEW.md)、[修复](control/HANDOFF_FIX.md) |
| 模块整链 | intake producer真实输出pins→selection→Bundle/View→真正Provider端口→Host/receipt→workflow→state→Guide请求 | [完整整链](binding/HANDOFF_JOINT.md)；首测1 PASS，8.578s |
| M12/前端 | 两个新窗口各自交付已实现接点、待桥接部分、边界与后续候选任务 | [M12](m12/PLAN.md)、[前端](frontend/PLAN.md)；只有静态规划 |
| 最终验证/交付 | 最终命令结果见COMPLETION；新PR和同head CI在完成后记录 | [完成矩阵](COMPLETION.md) |

## 命令与实际结果

解释器：独立 `.rwb/entry-venv/Scripts/python.exe`，Windows CPython3.11.16；`pip install -e '.[test]'`只安装到本worktree测试环境。构建安装环境另为 `.rwb/entry-installed`，不改变系统Python。

- 首次调用旧解释器时缺setuptools；建立独立venv后正常安装。最初 `-I -m unittest tests.<name>` 失败，因为isolated mode不把cwd放进tests导入路径；改为 `discover -s tests -t .`。原命令失败未算产品通过。
- 原workstream角色fixture缺 `model_policy.class`、binding fixture与当前资格重算不匹配、Root CLI fixture缺MainState非空machine refs，均在具体记录中保留；修的是fixture，不放宽产品validator。
- Root首个joint套件因plain directory write_scope anchor不兼容3 ERROR；按既有scope组件边界语义修caller，并补合法anchor/相似前缀反例。
- 新入口首个整套：`python -I -m unittest discover -s tests -t . -p 'test_entry_*.py' -v`，63 PASS/85.197s。之后补完整control-chain例和原R2残余driver-exception unknown反例，再做最终套件；不把初次63PASS当最终源码资格。
- 原消费者回归以isolated discovery选择 `test_cli.py`、`test_cli_command_branches.py`、`test_execution_host.py`、`test_generic_execution_closeout.py`、`test_runtime_bundle.py`、`test_documentation.py`：53 PASS/66.655s。
- 构建：`python -I -m pip wheel --no-deps --no-build-isolation . --wheel-dir .rwb/entry-wheels` PASS；candidate wheel SHA256 `c3364556c7e83583582262731046f29fc26e97eb9597fbe75bd8e6bd9e5d4d2d`。它是本地alpha candidate构建，未发布release。
- 最终新增套件（同discovery命令）：65 PASS/86.855s，包含完整producer整链和driver-exception未知占位反例。原53项消费者回归未改源码，无新增原因不重复全仓测试。
- candidate wheel在独立干净venv实际安装；isolated模式断言import来自`entry-installed/Lib/site-packages`；installed版两个CLI实际成功/失败测试2 PASS/4.071s，`rwb entry --help`、`rwb resources check`、`pip check`均通过。资源报告的merge_eligible=false/projections0未改，不把它作为no-Skill阻断或接受。
- 原R1～R4独立复查已闭合，见 [FIX_VERIFICATION](review/FIX_VERIFICATION.md)；最终Executor4 PASS10.140s，workflow13/state3此前exact source hashes保持。

后续未运行项见COMPLETION，不复用历史paid/API或CI身份证明本次候选。R2具名接受、merge和release仍不是本记录能授予的决定。
