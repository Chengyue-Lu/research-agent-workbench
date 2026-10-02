# FOLLOWUP-009 检查

产品 source 仍为 `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`。本切片更新公开资料和便携审查摘要；selected caller/runtime、环境候选、原始官方实体与合成日志保存在本地，未加入产品执行入口。M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE，PR128仍Draft。

| 检查 | 结果 | 精确范围 |
|---|---|---|
| 独立输出根 runtime | 10/10 PASS，0.373s | 最终320e32f6；Provider refs仍在原input root，summary/report在独立output_root；拒绝相对/缺失root及逃逸目标，准入、pins和journal边界保持 |
| 独立根成功组合 | 1/1 PASS，126.778s | 同一最终runtime，三个fake urllib调用、一次纯Tool7、cold report1.1和排他输出；固定合成时间，不是实际120秒性能证明 |
| typed selected caller | 11/11 PASS，2.521s | 最终bfd747dc；实际合成临时budget，recording fake driver，0 kernel；显式initialize/open、sum(inputs)+768前置限制、opened capacity复核、同一journal finally关闭，无fallback/reset |
| caller/runtime独立复核 | 范围内静态PASS | 复核自身0动态测试；瞬态总预算遗漏已修，最终hash稳定；manifest在claim前只核路径/字节，完整binding仍在runtime，不把任意候选当执行输入 |
| Qwen R7公开资料 | 两个无认证GET200，提取断言PASS | 既有Q2 Responses与Q9实际Context Cache href；12条所选model/region cache行、5个Responses usage样例；console-only read价格保持unknown |
| 普通环境/bridge候选修复 | 13/13 PASS，0.002s；PS parse/C# compile PASS | 9个合成callback canary场景，固定错误清除message/attrs/context/cause；两层规范化斜杠，TEMP/TMP一致；候选/原bridge均未执行 |
| 环境修复独立复核 | 两项缺口闭合，无scope剩余行动项 | 静态/哈希、0动态测试；旧review/stage身份保持，实际启动边界仍未接受 |
| 文档与公共surface | 24/24 PASS，0.930s | 当前R7与本轮便携摘要；内部链接及既有公共边界检查 |
| 既有head远端组件 | 855/855 PASS，1695.863s，0 skip | 同一run37066458707、Component3.11 job111035413307；触发head1b68fb3，实际PR merge checkout e9e178a9（parents base27cb/head1b68），CI result111044688939 SUCCESS，smoke15.1761s |

实际原有config/profile/manifest reference root与声明报告目录不同。最终runtime新增显式`output_root`，只用于输出约束；没有复制或重写冻结Provider引用。cold reader/writer的root仍解析原绑定，排他新建/partial保留不变。目录或hash本身不授予Task写权限，实际write scope仍由既有外部trusted guard接受。

typed caller在任何selected I/O/helper加载前要求既有guard的精确True，封闭绑定自身及budget/runtime/window/sink四个helper的实际路径与hash，拒绝执行归档Provider代码。固定config/profile、两个fresh输出和日期窗先检查，随后明确initialize或open，不自动改变模式。open要求已选retained snapshot hash；namespace、anchor、剩余容量及失败修复边界在credential/run前核对。同一journal由outer finally关闭，runtime只关闭sink；默认构造environment/DEEPSEEK_API_KEY引用，不调用available/resolve。唯一真实历史与history-basis语义仍需外部接受，本地marker不证明全局连续性或防一致rollback。

已有预算 helper `2f4a7f8136c6ab028816517b9fbaa7f92e386feee3f5643f1e1bc60016ddc2e6` 保持；runtime最终SHA `320e32f6ae7a95d3b512f9a6d26409b101d868243ab08c424430550e0172c5c8`，caller最终SHA `bfd747dc3d96f23803ffe72e40c747af7267732c9298553f5a08cdc13db3eb4a`。独立复核收据SHA `a8cf4b4c272ee79c62a2529d1b89362ed8e14d92c6ba707305708090c1d2ceb4`；旧008源码和失败日志保持，不借旧结果宣称最终负场景已重跑。

环境候选只接受显式SYSTEMROOT/TEMP/TMP、固定隔离Python argv、既有trusted guard与固定DS凭据target；桥的候选源码清除继承环境，guard在vault前和spawn前，晚注入仅DEEPSEEK_API_KEY。原bridge保持且未执行。初次静态复核发现callback错误透传/context残留和TEMP/TMP跨层写法差异，初版源码/10PASS及复核收据保持。最终错误使用固定消息/新异常、清除cause/context；两层斜杠规范一致，13合成/静态检查通过。实际普通值、clean父进程bootstrap、native guard、Python import pins与Windows context尚未绑定；纯准备/AST/C#编译不称真实native launch。

环境最终Python SHA `07253f8a7ef93bfea0070d6d0babe13de3db2712a36cef38839e9dbd7cec6e81`、bridge候选SHA `15e23144aca62138663401c9eedef479ea572c4642c4a8a61b0ae2145c1ca335`、owner修复收据SHA `5caae15ffaf24b272924842d6546755a7259adb48e3e55d55f104c5e8792d582`。初次独立review收据 `8afc823182c48ca94f9b51ee8b81844f3140c9be498cb3edd214dd3c6b2d42c3` 保持，不覆写为通过。

最终独立环境review收据SHA `58d9ba02d9bbdb17bc7b35b766952d4227f9f206949cb37f3c5759bc959052c0`；只确认两个修复，不声称traceback frames或任意child具有通用秘密脱敏保证。旧review的瞬态size观察疑点经精确hash已排除，没有恢复或修改原件。typed caller owner最终收据SHA `c2ba95b01ec9c59cb49eaf023c1545a680c507a5cd161026eaff7e9b6833e76f`，不借review-time尚未生成的Handoff推断接受。

R7按surface补充Qwen Responses端点、thinking/context、cache usage/控制和所选read价格例外，字段数量仍D31/P129/U5。Chat缓存子集不能套用Anthropic兼容或Responses；marker支持角色不等于完整Responses白名单，built-in Tool样例不证明client ToolChoice/strict。所选read精确价由公开正文指向console，保留unknown且不访问账户；没有新增所选夜价证据。原R6标准价与原收据保持，公开实体身份见[矩阵](../../../M6-GENERAL-PROVIDER-DEFINITION/OFFICIAL_MATRIX.md)。

远端成功仅归实际既有head/merge checkout。原1bd的848项/2FAIL和903的30m取消/result失败保持；未rerun该取消handle、未放宽真实Flash120秒。855项结果是所选65模块/7组件，不是full/global coverage；result工件明确coverage diagnostic-only/merge_eligible false，不能替代审核。最终文档新head的本地检查和远端状态另行记录。

CI原始日志SHA `525e37ba8a652ab9729b8ae43927ad50fbf4cf3aea86000baf6dfcea98573b00`，native ci-result与component result/plan/smoke和artifact元数据留本地。triggerhead与test merge checkout分开核对；新head不自动继承旧head状态。

真实API、Key值/presence、实际provider环境/bridge、账户、真实budget claim均0。每request仍只精确Flash、北京18+且当前官方idle；累计全部成功/失败input+output≤10,000,000，非消耗目标。计划每Attempt≤3calls/1pureTool/256output/120秒；失败STOP/归档/离线修复/refreeze后fresh Attempt，无自动retry/fallback。unknown费用非阻断；unknown tokens held-STOP。实际implementation/run/history/context接受仍null，M5/A4/Pilot/科学/发布权威独立。可见消息与失败保留，完整平台导出不可得的capture-gap如实记录。
