# CHAIN-TRACE-013：Tool result持久化窄审

2026-10-08；Agent Profile targeted_reviewer；required-Skills=[]。静态审查，非产品修复或测试执行。具名Root协调修复；仅写本报告与[通信](TRACE_COMMUNICATIONS.md)。

## 结论与证据边界

**[P1] Tool result 文件名直接扩展 operation_id，当前深目录下造成实际归档阻断。** Root报告Attempt11 readonly handler invoked1、tool-result归档 FileNotFoundError、Session trace-capture-gap停止。新增Root事实：trace目录绝对长度216，结果 basename call_00_pnfRy1fddAcqHQmoAcyl7881-succeeded.json，总路径276；tool-events目录存在但无结果文件。结合下面源码，故障高度指向Windows路径长度，而非返回值中的materials/intent.txt缺失。本组没有打开实际Attempt/文件目录，也没有复现Windows调用或检查OS长路径配置；系统限制是有证据的原因推断，不伪称环境机制已直接验证。

定位：

- trace.py:631–637 取cleaned.result、JSON序列化、以 tool-events/{_safe_id(operation_id)}-{status}.json 作为结果路径，exclusive写完再计算ref/hash。
- trace.py:701–703 的 _safe_id仅替换字符，无长度上限；sanitize/replace不会把较长operation_id变短。
- trace.py:81–88 已创建父目录；Root报告父目录存在吻合。根本缩短结果basename是最小适配点，不是再mkdir。
- trace.py:108–180 的plain/sanitize递归只清理内容，不把result.path/sha256作为要读取的外部文件ref；_record_tool没有解析或读取result.path。Tool返回的 {path,sha256,text} 本身不是此处FileNotFoundError的证据。

## 传递链与失败含义

synthetic_tool.py:59–119 的lookup只在handler执行时按Task exact ref、边界、大小/文件漂移/hash/UTF-8复核，并返回path/sha256/text；这是输入读取后的结构，不应改写成Trace文件路径。

Session session.py:379–410 计数并record attempted，执行handler，原样把output送event sink；result符合字符上限时进入Trace transient保存。411–425捕获result写入异常后record capture-gap并SAFE_PAUSED/trace-capture-gap返回；437–450仅在capture通过后组装tool结果消息并继续下一Model请求。因此handler已发生而Trace未捕获时，不能报告Tool结果已完整交给下一模型或成功完成整链。

driver.py:295–313只将Tool client name映射为冻结Supply component identity，保持result不变并调用recorder；baseline.py:223–250同样将payload plain后送recorder。两条消费路径都不能靠改 result.path 解决长结果文件名。调用次数应保留真实已发生事实，gap保留，不把失败当未发或成功。

## 最小产品适配建议（供Root/dev4）

1. 仅改 _record_tool 生成结果basename：短序号+operation_id的稳定hash，如 0001-0123456789ab.json；完整operation_id与canonical status仍原样作为event语义字段保存（继续现有sanitizer）。**不在basename重复-succeeded。** 当前Root提供的216字符前缀下，tool-events/加22字符basename总长约251，低于旧276。hash只是文件命名标识，真实result_ref.sha256仍须对已保存body bytes计算。
2. 序号使用即将记录的event sequence或其他现有单recorder单调号；相同operation_id再次捕获也产生不同exclusive路径。basename不含来自operation/status的任意路径片段；保持O_EXCL、fsync、现有JSON正文、sanitizer、event/index双引用与原operation身份。不要修改核心Schema或引入新资格对象。
3. validator trace.py:1511–1603只检查event与INDEX引用多重集合一致、tool-events/前缀、目录内存在/hash与无orphan；_checked_ref1348–1398检查containment/实际文件/hash。未要求旧operation-status命名，可直接消费新短名，历史ref可保持原样replay。
4. 更长archive prefix仍可能超过平台限额，不能声称短basename保证所有Windows路径。Root应另给prefix余量/短archive位置或明确预派发阻断；不以启用系统注册表、\?\路径或重新写用户result为本次必要修复。trace写失败继续fail closed，保留真实调用与已有原件，不能追补资格。

## 必要测试断言（本组未执行）

- 单元录制安全 {path:'materials/intent.txt',sha256,text}，Trace目录下没有materials/intent.txt：仍把完整JSON作为transient写入tool-events，事件operation_id/status不变；证明不会把返回path当外部ref读取。
- 使用很长call_id及Windows实际长prefix回归：新basename长度有界，路径在tool-events内；216字符prefix本例从276降到约251；json正文/hash/event/index相符。跨平台静态命名断言+Windows实际写入各自注明覆盖。
- 相同operation_id不同事件、normalize后相同的不同id、异常字符status/id：不互相覆盖、不escape；序号提供唯一性，event原身份保留。文件存在/IO失败保持exclusive失败，不吞异常继续下一Model。
- Session+Driver离线链：handler invoked1、result archive成功、下一Provider真正收到原Tool output；Tool component identity在Trace保持冻结ref，receipt独立冷复验。捕获写失败反例须handler1/model后续0、SAFE_PAUSED/capture-gap、真实计数保留。
- 原件字节修改、删ref、INDEX缺/多ref、orphan/escape仍structural BLOCK；Credential/hidden reasoning仍sanitize并留redaction/gap，不能因为改短名绕过安全处理。旧命名Trace仍能冷读。
- Root再做获准实际readonly Tool roundtrip，确认返回原件→Trace→下一请求→下游消费；新名字的存在或structural PASS不等于实际Tool链已跑通，更不等于科学正确。

## 实际读域/source pins

文件名/符号发现后，窄读trace record_tool_call342–367、record486–502、_record_tool619–640、写入/ref/sanitize69–184、_append_event642–707、_checked_ref1348–1398、Tool provenance1511–1603；driver.record273–318；Session Tool loop342–461；baseline sink223–253；synthetic_tool.py全文。tests/test_trace*.py仅发现test_trace_properties.py与test_trace_risk_codes.py；properties recorder/三项性质相关1–100窄读，risk_codes仅相关函数/词汇索引。本允许test文件没有命中长Tool结果文件名回归，未搜索其他测试以补矩阵。两次输出截断，关键sink/Session/ref/provenance后窄读补齐；不将截断部分当全文证据。

| Repo-relative source | SHA-256 |
| --- | --- |
| src/research_workbench/observability/trace.py | e32a0e52759e97ab7f061ef5ae57976ec2c1aef5fe9133cce54c26c489d1be61 |
| src/research_workbench/entry/driver.py | 9f1beba886947509bbd2ce77a1acc8b9191d1d37461eb6a500cc225b542130aa |
| src/research_workbench/adapters/models/session.py | 0f705d19759be7a43ccd8b8312ae62c9a50b36e666cf0536a0d00d1d91a58ba9 |
| src/research_workbench/execution/baseline.py | e9184fb6d536120853f256e2f45dd05d65f1184b5d64a4b6ac58b119063c1406 |
| tests/test_trace_properties.py | 4f15090210ec00ba24f40a18c0452bc29cb24865a1549df96a0ee44dcacb3ed6 |
| tests/test_trace_risk_codes.py | a32032de1a16952b3025fbf77d0429b0e20ca023daea5b6b4c5a8002e610a077 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/chain-proof-002/runtime/synthetic_tool.py | c10fc9eee696873e8e2aebf146d81f7239cf73b77127803abe97ac1c7fa18a66 |

Source pins固定本轮读取版本，不代表已修复版本。无source写入、测试/API/Tool/Key/账/原Attempt读取、Git或记忆操作。Root正在修复；原因/建议已清楚，本组落盘后停止。**Structural validity不等于科学正确，也不产生Source/Human接受。**

## CHAIN-TRACE-016 限定静态复查（2026-10-08）

Agent Profile targeted_reviewer；required-Skills=[]；沿TRACE013边界，只追加两份审查工件。结论：原P1的“operation_id直接扩展结果basename”机制已在源码静态修正；本次未发现新增实质P级风险。是否解决当前Windows实际深目录写入与API Tool roundtrip仍待Root运行证据，不把源码修改或测试存在称为PASS/全链完成。

- **完整身份/状态保留。** trace.py:619–633仍先执行既有sanitizer，operation_id仍原样取cleaned payload并放event（625），status仍放原canonical event字段（627）；本次只在634–636计算operation ID的SHA前12hex与下一event序号作为basename，没有把event身份改成hash。
- **结果原件与权限未变。** 632–641的result JSON正文/newline、result_origin transient、result_ref对真实bytes的hash与_tool_refs/index传递保持原接口。81–88仍O_EXCL+fsync；已有目标文件在os.open失败，不进入清理新文件的except，无覆盖已有原件。basename由序号/hex/固定后缀构成，不能携带operation/status路径片段，固定在既有tool-events目录；没有新增读文件、网络/写权限或资格。序号区分重复ID，即使hash前缀碰撞亦不靠覆盖原文件。
- **新增用例接点。** test_agent_trace.py:243–269用很长unsafe/unicode ID，断言event原ID、tool-events parent、短name、result JSON/body hash、INDEX引用和validator；271–298用lookup/id、lookup\\id、重复lookup/id，断言三个distinct results、原operation IDs和独立正文/hash/index。用例只做Trace结构/序列化验证，不证明工具输入科学正确或实际API已消费。
- **旧filename兼容。** 原validator1513–1605仍核transient event/index refs集合、tool-events前缀、contained文件/真实hash、无orphan；不从operation_id重新导出新filename，不强制sequence-hash命名。历史operation-status结果文件仍按其原ref/hash验证；本次没有引入命名迁移或legacy特殊资格。既有715–731 hash-tamper反例仍通过引用实际结果文件检查，不依赖旧basename；642–664 stable-source仍被拒，未因改名放松transient语义。

两新增测试没有直接构造Root的216字符archive prefix；路径示例251字符取前次Root提供的prefix算术，不是本组OS写入验证。:04d是最小宽度，序号超过四位会自然增宽，不能宣称所有运行basename永远22字符；既有有界Attempt及更长archive prefix的余量/阻断建议仍适用。本次不增加并发支持或整目录事务；写入/index部分失败仍应保持gap并停止，未作资格补录。

本次实际窄读：trace.py619–644、81–90、1513–1605及相关symbol索引；test_agent_trace.py234–302、642–664、715–733及相关函数索引；旧本组报告/通信尾部用于追加。test_agent_trace.py是本次Root显式扩展的相关测试读域；没有搜索/读其他目录、账/Attempt或API原件。未重新阅读driver/Session/baseline或声称其新版本已测。

| Repo-relative source | 本次SHA-256 |
| --- | --- |
| src/research_workbench/observability/trace.py | 31c60dcd8ed61d8d6437f5001c9072f8c4a234197db487ed1f919d51c465bed5 |
| tests/test_agent_trace.py | 11a930d9be9b955f626db5722c66ed0d9241fa1feb0f4632a91e6209756491c4 |

旧表trace pin保留TRACE013修复前版本含义。Root正在离线Trace+bridge regression是派单反馈，没有结果可据此写PASS。本组仅静态引用/hash，无产品代码写入、测试/API/Tool/Key/账、Git/记忆/再委派，落盘后停止。**Structural pass不等于科学正确或Source/Human接受。**
