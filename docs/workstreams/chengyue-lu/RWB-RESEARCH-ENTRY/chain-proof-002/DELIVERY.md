# 本轮交付与验证范围

2026-10-08 · Draft PR140 后续候选；未合并、未接受。文档定义与全导航校准独立在 Draft PR141。

首读 [API_RESULTS](API_RESULTS.md)：模块实际输入、输出、消费者与每次停点；[ROOT_REPORT](ROOT_REPORT.md) 解释修复和边界；[COVERAGE](COVERAGE.md) 列出确定性验证范围。本清单固定文件和日志口径，不要求评审人逐份读 JSON。

## 完成的本轮切片

| 切片 | 本轮交付与完成度 |
|---|---|
| ENTRY-01 角色请求 | 实现内置 baseline、实际 Task 和核验快照；外部 prompts/三个 Skill 为未加载 test-candidate，非空 required Skill 仍阻断 |
| ENTRY-02 intake | 受控实际 API producer 的草稿 refs/pins 被下游消费；未评价自由需求的规划质量 |
| ENTRY-03 执行与 Tool | Profile ceiling、Task 默认 revision、Session 有界 Tool 循环、失败阻断、Host/Trace/Receipt 和 Windows 短结果文件名接通 |
| ENTRY-04 主子协作 | main 自主0..N；离线0/1/3、真实0/1及fresh main实际消费；child 当前顺序执行 |
| ENTRY-05 状态消费者 | hash-pinned workflow→独占人工 checkpoint；不是 CAS/事务/自动恢复或科学接受 |
| ENTRY-06 Guide | 独立实际 API、COMPLETE 与项目字节不变分别核验；不自动回传 main |
| ENTRY-07 交付验证 | 最新整套、安装包、实际账冷核对和可读报告完成；CI 与提交状态由 PR/Git 记录维护 |
| PLAN-M12 / PLAN-FRONTEND | 两窗口规划交付，未实现或解冻 M12/Topic5，不据此计为模块运行通过 |

## 实际 API 结论

Attempt15 `chain-390138a6-3dd8-4fa5-9615-d8986b6b5345` 同次6次 HTTP、32.641秒、新增known24,862：intake→main两轮与readonly Tool→main自选child1→child complete→fresh main complete→checkpoint→Guide COMPLETE，项目字节集合不变。三执行 Slice 有各自实际 Receipt；intake 与 Guide 不冒充同类 Slice Receipt。workflow 含 intake 为5calls、known21,922/held0，task_completion=false、human_acceptance=false。

全部新增15个closed Attempts共41个 HTTP entries；累计known246,860/actual held0，包含原55,614，10,000,000累计上限不重置。Root新进程核对15账的原件集合/hash/source/project/settlements及旧17账2082引用；17份新实际 Receipt 和各自 Bundle PASS；A12～15四份 Tool 原始结果bytes/hash与下一实际请求 Tool 消息相等、Trace PASS。旧17账没有被声明为全语义或科学重放。

仅使用隔离合成短材料。临时北京时间18:00至次日09:00及每请求fresh官方闲时是本轮调度配置，不代表接入真实项目。没有自动付费重试或fallback；失败、LENGTH、unknown、未开始和原始错误均保留。Guide关于Receipt发布的解释有内容局限，接口成功不使其表述自动正确。

## 确定性与安装验证

| Root运行范围 | 实际结果与口径 |
|---|---|
| 最新全 entry | 81 tests / 144.636s / OK，一次完整套；预期负例CLI ERROR尾行保留 |
| Runtime Bundle | 13 tests / 2.423s / PASS；其后仅请求baseline变化，不重复叠加计数 |
| Profile + pure wire | 64 tests / OK，skip1为Windows symlink不可用；0.590s为已保留该次日志 |
| API budget | 8 tests / PASS，3.659s；offline、没有Key或实际请求 |
| Trace + bridge 合跑 | 前64 Trace通过、后6 bridge受同时build重生成resources影响失败；原70项日志保留FAILED |
| bridge 修正顺序后重跑 | 6 tests / 51.668s / PASS；不把原70项标成全通过 |
| 最新wheel020安装 | build→install→已安装site-packages RuntimeResources→2 CLI tests / 3.739s / OK；pip check无broken requirements、installed entry help成功 |
| 独立边界检查 | synthetic readonly handler4项、overnight6边界均PASS，不是额外真实API或通用OS沙箱证明 |
| 文档与交付检查 | 81个workstream Markdown、255个本地target，无缺失链接/anchor或机器路径；3项documentation tests / 0.375s / OK；git diff --check通过 |

重复子套不累加为唯一总数；结构通过不证明科学正确性。此前安装/78项等历史结果在原报告保留其时点。

第一次staged whitespace检查发现三个新Handoff末尾多余空行；Root只规范public文本为LF及去掉这些末尾空行，原收到bytes与前后SHA保存在ignored `.rwb/entry-archive/public-text-originals-020/`。通信中的旧SHA仍指收到时原件；下表固定最终public bytes，不把格式整理记为新增API或源码测试。

## 仍需后续的接口与接受

非空 required Skill loader/package pin/实际使用、正式 Skill 评价准入、正式 Source资格、黄毅具名live接受、自由需求规划质量、真实复杂研究和Guide解释质量未闭合。候选factory的 planning_action_id 下游selector缺口保留；当前使用支持的 versioned action_ref。Driver对全部truthy非字符串、空白或未匹配output contract的派发前拒绝尚未闭合，本轮使用已选有效contract，不能推广为所有malformed输入都在派发前拒绝。

M5-008四臂/64-slot/Pilot及净价值评价未完成；M1-010/M2-009/M11-008为PR141分支READY定义，原DONE行不改。M12/自动恢复、GUI、科学或人类接受均未由本轮产生，停在M5-004前。源、Role/Supply身份及权限继续沿用独立核对，不用selected自证actual，不创造Release/Supply或具名接受。

## 当前 source 与报告 pins

代码继承提交 `d630f8e174846f4932d05a7a0d69076930b53ee1`，本次后续文件按下表bytes固定；最终提交SHA由PR/Git记录。历史Handoff pins属于当时版本，不冒充当前pins。没有把机器绝对路径、Key或认证头写入本清单。

| Repo-relative文件 | SHA256 |
|---|---|
| `schemas/v0.1.0/provider-api-profile.schema.json` | `5d097d2b75db1d931005cc623de4d5a10ca1f6e3a0db7ff65f4533d14725bec0` |
| `src/research_workbench/adapters/models/profile_configuration.py` | `70c259e096d82124823d9313df75359ac72f62c8a7960307e7b8ff63f0a4e652` |
| `src/research_workbench/adapters/models/wire_codecs.py` | `fdf1c14ed6be7abee7be02f3cc8e11b1f5eb523d1ec33c50d0def1657959a427` |
| `src/research_workbench/entry/intake_call.py` | `03717b2d7cb0bf6267e7082301697fa2eef3b41ab0c80f1319bb28bdeee9f913` |
| `src/research_workbench/entry/driver.py` | `9f1beba886947509bbd2ce77a1acc8b9191d1d37461eb6a500cc225b542130aa` |
| `src/research_workbench/entry/executor.py` | `39c4507cd93607eddd0177e5aff4599fd1f0913088e90a595c48a420d56bfe3f` |
| `src/research_workbench/entry/roles.py` | `8aefb70782c8b091fe7f75305b6c38f0ee4a4a3971621135a55614f63cf5fbd9` |
| `src/research_workbench/entry/workflow.py` | `5b70ed862c22a46535581bcbd407e3034ff8c1edfd52d74a8de6a0f30c6e2f5e` |
| `src/research_workbench/execution/runtime_bundle.py` | `f9a5b38d50772c354a69de230533ea05a37c1daabd8bfa5a43313632a87005a5` |
| `src/research_workbench/observability/trace.py` | `31c60dcd8ed61d8d6437f5001c9072f8c4a234197db487ed1f919d51c465bed5` |
| `tests/entry_chain_support.py` | `ee428e98fd0e11f4d899464f0075b4934aaf201ac4a50d67061faecd9db9c884` |
| `tests/test_entry_bridge_flow.py` | `ee0f9aa090d274da7397fdf10bb899e5213eb77ffb0aecf3ca0a1fca3d8c272e` |
| `tests/test_entry_intake_call.py` | `3a4d3c1bc98c4232729efc194ababad204b7d881f62f47e316dc8b47807f251d` |
| `tests/test_agent_trace.py` | `11a930d9be9b955f626db5722c66ed0d9241fa1feb0f4632a91e6209756491c4` |
| `tests/test_entry_executor.py` | `fdf6eeaf437c47363f52d06fb5b963ff5c86bc94ef71e4389a5aea3f7b5228c0` |
| `tests/test_entry_roles.py` | `3ceb75b0d3cc10c19e9cca6d958962da11574d81d668ce4acd0d30f5c2f40afd` |
| `tests/test_entry_workflow.py` | `8f1078d3e365ce2f739f304b1d9c05ea32374035db5365b6058fe6f90e4e7dd6` |
| `tests/test_provider_profile_configuration.py` | `59d1d8e42168258aebdff62607977134542254f95226f804688436e43c576983` |
| `tests/test_runtime_bundle.py` | `5651e277846a510c5b33ebba078943d1e1146bafbcd4ee9a768ae2b80d766e53` |
| `chain-proof-002/README.md` | `8ad36bee75ccf5d582b95b2440471fd67616d0bbd2dca76d292fd1e56670573f` |
| `chain-proof-002/USAGE.md` | `443488764e0ce6e21c99a3188a97854337ac20eb13edf62b95065b14ce835ee3` |
| `chain-proof-002/ROOT_REPORT.md` | `468c0e97e96f3fe33e97bd8f602995d775eaad6f9728dfb6e035c1aeba29ac48` |
| `chain-proof-002/API_RESULTS.md` | `2fef87f6c2da6fda3324e4067616e025bbdc09cda5e277e6caee940acc99c9fc` |
| `chain-proof-002/COVERAGE.md` | `aa888ccef37199e9a7d9c9da2aaf82e219a17fad92ca66159630f20e76c8d740` |
| `chain-proof-002/ROLE_REVIEW.md` | `675364896151a4ccd2b70e52ee78b909a2312a38aaa257e9c6feba9ea684a2cf` |
| `chain-proof-002/TRACE_REVIEW.md` | `3a1f9933ca0cd6a2dabb2afc131d10094ba8c749bf011c1ff6a6511fd0f33259` |
| `chain-proof-002/NARROW_REVIEW.md` | `e7dda014bbb98dfce550e2f3ab66c4a50bd37cdbe75dd4ccbce76dcccc5cb3a0` |
| `chain-proof-002/runtime/api_budget.py` | `97c8a6459d66775a9d2148690a0342cfc49a1bc20c93b82bd12b8a2191317e54` |
| `chain-proof-002/runtime/api_factory.py` | `14448a39c4d7c67d42df11eb5a1f0b7c2e8beb372ddb3375099ed3eb03feae84` |
| `chain-proof-002/runtime/synthetic_tool.py` | `c10fc9eee696873e8e2aebf146d81f7239cf73b77127803abe97ac1c7fa18a66` |

public chain-proof tree（不含本DELIVERY与Python cache）共61文件，按repo-relative path排序，每条为`path\tsha256\n` UTF-8，aggregate SHA256：`9f6dba128bf30df66c1bd0ef59c7a4c56e4b6bf7917dec5edbcd8ce3b1abf10c`。其中assets共13文件，同法aggregate SHA256：`86fea23b883cbb1cbf7cdc11ee3660cfcb60fab44e8cc267b8ca0ffbe5c22705`。这是候选资产存在/hash记录，不是正式Skill装载或接受证明。

## Root保留的原日志 pins

以下ignored原件不随PR公开，评审人从上面可读报告核对结论；需要逐项审计时再沿精确引用查原件。使用仓库相对路径，保留失败日志，记录实际bytes而非换行归一化文本。

| 原件路径 | SHA256 |
|---|---|
| `.rwb/entry-archive/chain-020-all-entry-final.log` | `5059f6b09fa367672f682b6577d41bf5a4a1a579a2e433fad09aca9651a35e08` |
| `.rwb/entry-archive/chain-020-wheel.log` | `9a230d66bf460d82c4b7fa2841e7d99954163ad7c6a13dc65f36c6602f1db30c` |
| `.rwb/entry-archive/chain-020-installed.log` | `1e7cbdb1a00fd5f97928d8962123659df612cf908b9efd123075403dfeecbb12` |
| `.rwb/entry-archive/chain-020-installed-cli.log` | `58807fe0a9c2dcb9e6de090a74268bf6d00dec5c324bb6a91e15582ee8706785` |
| `.rwb/entry-archive/chain-020-installed-help.log` | `15149f97d85d16d004dfdb3b1cdc8103d266d204f2476eeecee96da63a5e2ba8` |
| `.rwb/entry-archive/chain-020-documentation.log` | `fe242e0cd3f73fa0e7734a2a131addac81828e162939122faae57d02bda8e1a7` |
| `.rwb/entry-archive/chain-015-cold-receipts.log` | `cbd8b55b2b1f9cab4195a1c992f18d5134d12502676c6183de971e0367e952ae` |
| `.rwb/entry-archive/chain-015-cold-tools.log` | `0442b15de3f0e4280a3423743a464d8b868618c13eff0bac5b8380bb0bb4edad` |
| `.rwb/entry-archive/actual-facts-15.json` | `6266b2e2b2706cce1cc447c0d2435f7f78de51368b8bbfe8ff8fee424b720588` |
| `.rwb/entry-archive/chain-014-trace-and-bridge-fixed-runner.log` | `c87af242c35170a753091a5ea4d705a7c8774abaf009ffa47796422577ac02be` |
| `.rwb/entry-archive/chain-014-bridge-after-build.log` | `793712a0d3986bd32f1305142022aeba339e4454309a80c2e69e7e1433695306` |
| `.rwb/entry-archive/wheels-020/research_agent_workbench-0.1.0-py3-none-any.whl` | `54736b3be518f6eb5b7c832861597d61b99a8e89ea2fcf919a39c12644f711e2` |
