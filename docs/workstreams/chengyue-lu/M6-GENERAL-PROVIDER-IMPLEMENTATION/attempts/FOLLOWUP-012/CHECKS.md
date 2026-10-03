# FOLLOWUP-012 检查

本切片在真实 Windows 上执行一次无凭据的合成进程树测试，并补充 DeepSeek Responses 数据控制的官方资料。产品 source `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`保持；本地启动候选没有接入产品入口。M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE；完整实现、实际运行、bootstrap、history/output和数据接受仍为null。

## 无凭据原生验证

Probe source SHA `9d6ec60ae8ee53997e70f8ce5c0598b023259ae59f4c161fc6faff433aa2d75c`；factory `bef79c801bea1c7dd37283a96a07551c4568ceb394e7c8b3213c7c1ef71f6c4c`、backend `c0c4e4a83d2b8a89afc1e106d71e99790676f7dc0ca34a4dbcbc1dccfe11579d`均为FOLLOWUP-011的冻结源。作者17项AST/compile检查PASS，独立review静态核对最终源；两个角色未执行原生操作。根窗口以固定安装Python 3.11.16/64位、`-I -B`、closed SYSTEMROOT/TEMP/TMP环境、NUL三stdio和hidden窗口执行一次；不读取父环境，不加载RWB/Provider或凭据bridge。

| 真实合成场景 | 结果 | 整个场景耗时 |
|---|---|---|
| 正常child退出，外层关闭Job终止仍存活leaf | PASS | 0.203s |
| 0.2s有界等待超时，关闭Job终止child | PASS | 0.313s |
| child已创建但尚未恢复时，终止外层owner | PASS | 0.094s |
| child已恢复且leaf已创建时，终止外层owner | PASS | 0.187s |

内层batch0.812s，根controller调用0.875s、exit0；Windows版本10.0/build26200。四owner、四child、两leaf共10个合成进程，另一个controller共11个，低于12上限。所有native Job/进程/观察操作均只针对本次创建的已知对象；不枚举系统PID，不终止任意进程。观察器按原始进程句柄或fresh marker的PID＋creation time核对身份，持有query/sync句柄；Job句柄不复制、不继承。`IsProcessInJob`对实际child及两个leaf核对精确owned Job；creation-time JOB_LIST没有Start后Assign回退。

触发前对象仍运行，触发不得晚于场景开始5秒；关闭/外层退出后按同一个trigger+2秒核对停止，因此12秒自然fuse不能冒充Job清理成功。owner15秒、case20秒、batch90秒约束包含setup/cleanup；不增加等待宽限。一次观察只证明当前Python/Windows/context下这些场景，不认证硬实时截止、全部Windows层级、实际PowerShell/credential bridge、完整连接层或三进程bootstrap。实际M6具名接受仍null。

原生OBSERVATION SHA `49b2e09aaebab0e3c407d71038e915544649ac34903fc49b0f1453fd08884195`；作者receipt `25eeccbc4fa666d64994c828cbd3bb5411e41c0ca0da339ef690337fc3bcf7b0`。独立源码review receipt `fb9230499e1d9b98affb9fcffa65af17c56fbf76cfd5158b26befb33a8754c51`，source review在deadline内完成，首次终态归档晚17秒如实保留。原2b7/eb735/7b610三个阶段、路径/成员/握手/原子marker/触发截止/清理错误问题及首次静态检查两处false positive均留档；不以最终通过替换旧失败。

## 同一已完成CI

[run37080501344](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37080501344)为本次独立归档的真实cf8提交CI，非借用c78结果。实际merge checkout `6cb5e932a110c7d41c0dd258b4fbb2bc01a12bcb`，父提交base `27cbf860e48e9639bd3af32a58c12bfd88d87526`、head `cf8d6180399c517ca2a37545c341e290c365a1d8`。plan111079735482、Component111079766182、CI result111085199327均SUCCESS。

- 855/855 PASS、0failure/error/skip，native测试1442.063s；installed smoke8步SUCCESS/12.886s。
- Component耗时1473s；run API开始至更新1500s，不将其当账单或受控提速比较。
- plan65模块、result72 selection entries、实际records68模块分别保留，计划项无遗漏。
- 三个artifact ZIP SHA与GitHub digest一致，36份public raw log原样归档。
- coverage未采集、百分比null、diagnostic-only、merge_eligible=false；不是full/global coverage或人工接受。

CI receipt SHA `a2ca4068bb8e218a669a97ef842ac3f6f9856059bd9ba5897323041c42535c0b`。原cf8治理37080503182 SUCCESS与初始37080501339 CANCELLED保留原身份；本次后继文档提交独立检查，不借cf8绿色，不手动rerun。

## DeepSeek数据控制资料

三官方正文的日期化事实见[矩阵R9](../../../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_MATRIX.md)和[字段表](../../../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_FIELD_COVERAGE.md)。Responses无服务端conversation状态；store不支持、响应固定false；previous_response_id/conversation及prompt_cache_key/retention不支持，缓存自动管理。API Terms与一般Privacy和开发者下游责任分开；未知ZDR、日志/cache具体期限、API训练用途与账户开关保持未知。没有增设store开关或变更model/profile；D31/P129/U5保持。

公开资料receipt `2e6d80a3edab5d9a84fd5228a537a706a5deb4b36267cfde7ef214d914adc8ee`。Guide两次web reader400 Timeout以及随后同URL匿名static GET200的身份均保留；其他reader实体没有原始HTTP状态/日期，不虚构。正式公开资料不授予账户或运行接受。

本轮真实模型/API、Key/presence、Provider环境、vault/bridge、真实history/预算claim均0；真实native操作已有上述限定证据，不能继续写为0。仅固定合成输入，实际Flash仍须每request北京18:00后且fresh官方闲时；所有成功失败input+output累计≤10,000,000，unknown tokens held-STOP、unknown钱非阻断，无自动retry/fallback。M5/Pilot/A4/Phase C/科学/发布保持独立，PR仍Draft，无ready/merge。可见消息/阶段/失败与本地原生工件留档，完整平台导出capture gap保持。
