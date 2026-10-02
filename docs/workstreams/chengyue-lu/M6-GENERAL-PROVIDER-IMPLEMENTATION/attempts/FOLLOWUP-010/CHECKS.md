# FOLLOWUP-010 检查

产品 source 仍为 `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`。本切片把 clean parent launcher、隔离安装源码入口和公开资料的准备证据写入同一 Draft PR128；本地候选没有加入产品运行入口。M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE，完整 implementation/exact-run 接受仍 null。

| 检查 | 结果 | 范围 |
|---|---|---|
| clean parent launcher | 13/13 PASS，0.066s | 最终0685783a；全部fake process factory，固定exe/bootstrap/CWD、仅显式普通环境、guard后复验、封闭错误，无真实launch |
| 隔离 child | 20/20 PASS，2.431s | 最终b6005200；旧0e6f661a的19/19 PASS2.141s及强引用复核保持；loader两处compile明确dont_inherit，新增无future源码注解/codeflags回归 |
| genuine installed 组合 | 1/1 PASS，148.266s | 最终b600+冻结009caller/runtime/008budget/007window/sink+006安装包及原packet；3次fake HTTP、默认真实credential类读取合成dict3次、纯Tool1次、known合成用量21、cold report1.1及排他新输出。固定合成时间，不是实际120秒性能证明 |
| Google R8公开资料 | 三个无认证GET200，19条断言PASS | G6 native/G14 Interactions/G16 FunctionCallingConfig分别处理；所选Gemma4 F08仍U，D31/P129/U5不变 |
| Flash输入预留依据 | 两份公开文档GET200，条件化计算核对 | 每call input上界1,048,576加output256，每Attempt3,146,496；三批九slot预留9,439,488，低于用户累计10,000,000，不是消耗目标 |
| 既有head远端组件 | 855/855 PASS，1824.575s，0 skip | 同一run37070484155，triggerhead5d225f68；实际merge checkout8ea13cf8，parents27cbf860/5d225f68；Component3.11 job111048553444、CIresult111057574207 SUCCESS；installed smoke8步15.510s |

launcher source SHA `0685783aca819d6888eedd64226daa8c216fcb1cfe9e79816e0b14264bb3c1c4`。它消费冻结009普通环境 helper，准入前不加载或读取 selected inputs；spawn 前再次核对 guard/pins，固定 stdin/stdout/stderr DEVNULL、shell false、timeout120。默认实际 subprocess 实现存在，所有测试注入fake factory，未执行候选/original bridge、vault/presence 或真实父进程。

child 显式要求 Python `-I`、实际 exe pin、固定安装根、完整120份安装 `.py` pins，源码按验证字节加载，拒绝任何预加载 RWB namespace、归档代码、cwd/PYTHONPATH/bytecode 回退。只给 selection factory 只读 typed builders；捕获并复验实际 caller entry、code/defaults/kwdefaults 的身份，原对象强引用防止 id 生命周期复用，调用捕获的 genuine entry。119 tracked模块与生成 `_runtime_pin.py` 的区别保持，不借120静态计数替代既有wheel/Git字节等价证据。stdlib/native/第三方缓存与初始化仍属于显式实际上下文信任边界。

原 mutable caller-module factory 可以更换 entry 的问题已闭合；路径列表别名、同结构code替换、强引用阶段和fixture断言失败分别留档。强引用独立复核 receipt SHA `de6cbe5c3d722bc372b57b7171a47ac7f7eea1363f9f167a454c69eaaae3448b`，只认证当时0e6f661a，不自动覆盖后继修复。

最终child source SHA `b60052007fda8b5984db4cd2f3da693d659c61138020506489ef7041e1c09ef0`，owner receipt SHA `b1d21bdc24176f701d7ad0dc9c37b453a8ff63e39949b35f53cacdd0bcc9ed5e`。安装源码与固定caller源码两处compile使用`dont_inherit=True, optimize=sys.flags.optimize`，避免外围future annotations使无future源码的co_flags/注解漂移；已有source closure的独立code digest要求保持，原packet与产品没有重新生成或削弱。新回归检查实际int注解及无future编译语义，与旧19项边界检查一同通过。

最终compiler差异独立静态复核范围内PASS，receipt SHA `63d61647475bfa9581c16d5e9753a94ae7304ee80295447ffb065e6ef180b87d`；精确差异仅两个compile参数，旧强引用和fixture收据保持。复核自身0动态测试，不借owner结果或root组合冒称独立复跑。

组合失败诊断只记录异常类型、位置及四个非秘密 import-state 布尔值，没有 values/locals/请求内容。初次 `six` 导入注册 finder 的源链已经静态定位；保持之后的 finder 漂移拒绝。已有006 packet 用实际 EnvironmentCredential 的 source roots；合成测试替换 `os.environ` 属性为合成dict，原对象只保存引用，不枚举、读取或探测真实环境，genuine credential 类仍按冻结图校验。临时预算/history/output限本轮隔离目录，删除前核实绝对路径。原002失败report观察未在临时清理前保存、003观察JSON后来由诊断覆盖的capture-gap如实保留；原失败与两次具体闭集观察log均在，不补造用量或成功。

003/004及具体诊断观测均为provider-construction-refused、0 fake HTTP/0合成credential/known用量0；002只有失败stack，未补造其计数。最终005真实消费原006 EnvironmentCredential根与120份安装source pins，所有shape/text/schema断言通过、summary/report实际落在独立临时根，同一journal由冻结caller finally关闭，临时文件清理成功。fixture独立静态 receipt SHA `59a7b69a4e7de197bab64bfe2047de68b802dd2162e15db0c77e0c63f6983a73`，只核直接合成环境/class/pins，不冒称kernel、native注入或compiler差异复核。

输入预留仅是公开资料派生的候选：pricing列精确deepseek-flash/DeepSeek-V4.1-Flash、context1M；list-models文档示例给出1048576，定义包含input+output。这是文档示例，不是认证账户 `/models` 返回；按全部容量作为input再额外预留output，需实际运行前重新确认exact model/context适用性，server遵守上限仍是Provider信任。三批上界9,439,488，余量560,512；失败包括在累计中，unknown保持预占STOP，unused只有known usage才结算，不建立真实history或zero-use声明。

- pricing实体 SHA `210f102275ccf1a6542f08a3bc9e4b4c7c83278cb74b35217bffa112df6363b2`，取得2026-10-02T22:18:21.216471Z；[官方价格](https://api-docs.deepseek.com/quick_start/pricing/)。
- models文档实体 SHA `41551c3c498a93b6e6459eaeee89829940ca8acf999b24436a38a2231c7e091b`，取得22:18:21.444794Z；[公开参数文档](https://api-docs.deepseek.com/api/list-models/)。web读取该文档timeout保持，另一个独立无认证文档GET200。
- R8三份Google实体与收据见[矩阵](../../../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_MATRIX.md)；没有profile能力升级、账户/模型调用或JS。

CI成功属于原head5d225及实际PR merge checkout8ea13cf；三个原生ZIP SHA均与server digest一致，receipt SHA `861d1640530e8128c406807f1474a331805d2a541efe407cd88e27a1eddad273`。原生结果是所选65模块/7组件，coverage not-collected/diagnostic-only、merge_eligible false；不是full/global coverage或审核。原公共日志包含一个预期negative-exit的smoke失败文本，实际smoke工件八步SUCCESS，原文保留。旧失败/取消/成功证据各自归其head，未rerun旧handle。新的文档head须单独核验。

真实API、Key值/presence、真实Provider环境、vault/bridge、实际budget claim均0。每request只精确Flash、北京18+且当前official idle，用户累计成功/失败input+output≤10,000,000；计划每Attempt≤3call/1pureTool/256output/120秒，失败STOP/归档/离线修复/refreeze后fresh Attempt，无自动retry/fallback。unknown费用非阻断，unknown tokens held-STOP。实际 native bootstrap、普通值、第三方初始化、Windows context、唯一累计history/fresh输出和具名接受尚未闭合；M5/A4/Pilot/科学/发布权威独立。可见Task/messages/stages/失败保留，完整平台导出不可得的capture-gap不冒称完整Trace。
