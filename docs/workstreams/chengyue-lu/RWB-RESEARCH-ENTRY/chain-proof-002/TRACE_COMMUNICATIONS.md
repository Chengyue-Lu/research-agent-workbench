# CHAIN-TRACE-013 可见通信

2026-10-08；Agent Profile targeted_reviewer；required-Skills=[]。只写TRACE_REVIEW.md/本通信；Root修产品，本组保留其他编辑。

## Root派单（仅机器worktree目录归一，其他原文）

> Task Packet CHAIN-TRACE-013。Agent Profile targeted_reviewer，required Skills=[]。背景：Root 的 Attempt11 实际 readonly Tool handler invoked1，但 tool-result 写入 Trace 抛 FileNotFoundError，Session trace-capture-gap 后停止；真实 Tool 返回 {path:'materials/intent.txt',sha256,text}。输入仅 CODEWT（当前PR140 code worktree）内 src/research_workbench/observability/trace.py 的 Tool/result引用处理、entry/driver.py、adapters/models/session.py、execution/baseline.py、对应 tests/test_trace*.py 文件名发现及相关函数，和 chain-proof-002/runtime/synthetic_tool.py。先文件名/相关定位，不读 raw实际账、Key、项目或别的目录。职责：静态确认失败原因、给出最小适配方案和必要测试断言；不写产品代码、不跑测试/API/Tool，不操作 Git。写范围仅 chain-proof-002/TRACE_REVIEW.md 与 TRACE_COMMUNICATIONS.md，持久化本packet/输出。预算8分钟，原因与建议清楚即停止。你不是唯一工作者，Root正在修复入口，勿覆盖别人编辑。必须明确 structural pass不等于科学正确。

原CODEWT绝对目录在Root可见派单保存；本文按仓库文档portable规则归一，不复制机器路径。

本组 → 可见进度：

> 我先定位 Tool result 的引用识别与路径解析，再沿 Driver、Session 和 baseline 窄读传递链，确认失败原因并给出最小适配方案。只写审查记录，不执行 Tool、测试或 API。

## Root新增事实（原文）

> Root新增事实：实际 trace目录绝对长度216，Tool结果当前文件 call_00_pnfRy1fddAcqHQmoAcyl7881-succeeded.json 合成绝对长度276，tool-events目录存在而无结果文件。_create_exclusive已mkdir，_record_tool不解析result.path。高度指向Windows路径长度。请仅静态确认bounded filename是否应以序号+operation hash生成，operation_id仍原样在event；Root会给dev4产品修复，不需你写代码。

本组 → Root（原文）：

> 静态代码确认：trace._record_tool 632–637 将 result 作为JSON保存，不解析 result.path；_create_exclusive 81–88 已mkdir父目录，_safe_id 701–703 只替换字符、不限制operation_id长度。你新增216/276字符且父目录存在、无结果文件的事实高度符合Windows路径长度阻断。建议 basename 仅序号+operation_id hash（如 0001-12hex.json），不要再把 -succeeded 放文件名；当前216字符trace前缀下此方案约251字符，status及完整operation_id留event。Seq/hash方案维持event/index result_ref+bytes hash即可，validator只要求tool-events前缀/存在/hash/索引相等，不要求旧命名。更长archive前缀仍需独立边界拒绝/短路径，不能声称文件名变短保证所有Windows路径。

本组 → 可见进度：

> 代码中没有把 Tool 返回的 path 当作外部引用读取。结合 Root 提供的 276 字符结果路径，失败高度指向 Windows 路径长度；建议用短序号和 operation hash 命名文件，完整 operation ID 与状态仍留在事件中。

实际读域与source pins见[TRACE_REVIEW.md](TRACE_REVIEW.md)。Root实际handler/capture失败、目录/长度事实仅作其反馈，本组未查看实际路径/账/Attempt或运行重现。部分批量只读输出截断，关键consumer/validator窄读补齐；没有扩大到其他test目录或产品运行。仅静态定位、文档引用/length算术与hash；source写入、测试/API/Tool/Key/账、Git、记忆、再委派=0。Root/dev4接产品修复及必要回归，本组原因/建议清楚即停止。structural pass不等于科学正确。

## CHAIN-TRACE-016 派单与限定复查（2026-10-08）

Root → 本组（原文）：

> Task Packet CHAIN-TRACE-016，沿TRACE013 Profile/Skill/readset/writebudget限制。dev4已写 trace.py _record_tool 为 event_sequence+1四位 + operation_id SHA前12hex.json；test_agent_trace新增long unsafe/repeated collidingIDs两用例。只静态复查这两个改动与原validator/Compatibility：不改变完整operation_id、status、event_ref/hash/index，历史filename仍可验证；确认无新增权限/原件覆盖。输出追加TRACE_REVIEW/TRACE_COMMUNICATIONS，8分钟内完成止；不执行tests/API/Git。Root正在真实离线Trace+bridge regression。

本组 → 可见进度：

> 我会静态复查短文件名实现和两条新增用例，重点核对事件身份、独占写入、ref/hash/index 一致性及旧文件名兼容；只追加审查记录，不运行测试。

本组 → Root（原文）：

> CHAIN-TRACE-016 静态复查无新增实质P：_record_tool 634–641只改basename为下一event序号+operation ID hash前12；event operation_id/status、sanitizer、body bytes、O_EXCL、result_ref/hash与index未改。两新用例243–298覆盖长unsafe ID、归一化碰撞/重复ID的独立文件与原身份、JSON/hash/index及validator。原validator只要求tool-events前缀、containment/存在/hash/index，不要求新命名，历史名仍可读。两测试未直接构造216字符archive prefix；Windows深前缀/实际Tool roundtrip仍待Root实测，不能从静态用例存在宣称PASS。正在追加原报告与通信/hash，随后停止。

只读新trace相关函数/旧validator、Root明确提供的test_agent_trace两新用例及相关compat/hash反例，和本组原报告尾部。实际source pins/范围在报告TRACE016段。Root离线回归正在进行仅是反馈，没有执行结果，本组不宣称PASS。仅追加本组两文档与静态引用存在性/hash，无source写入、tests/API/Tool/Key/账/Attempt读取、Git/记忆/再委派；原因/建议已清楚，落盘后停止。structural pass不等于科学正确。
