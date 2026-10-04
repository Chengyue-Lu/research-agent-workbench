# 测试边界补丁独立只读复核（最终 v2）

结论：**PASS，限本次测试边界与已有原生回执的核对**。未发现把 M5/Provider 产品、用户归档使用或发布独立 witness 一并排除的问题。此次复核未执行测试、fixture、Provider、网络或 CI，未修改 worktree；不构成全量回归、生产覆盖率达标或提速证明。

身份：worktree `.`，当前 HEAD/base 均为 `ede2bc1d5e3496b4e4c72abb1f39f0a3ce00aedf`，审查对象为未提交 diff。父代理追加两项 M11 混合回放调整后，最终范围为 **8 个 tests 文件**（6 个测试模块和 2 个清单），不沿用先前七文件快照的最终身份。无关 `.codex/config.toml` 未审查。

## 删除与保留

独立用 `ast.parse` 比较 base 与当前文本，不导入测试模块。21 个真正删除的方法：catalog 历史 intake/candidate 记录 4 个；文档开发记录检查及全 docs 扫描 7 个；PR25 rollout 记录 1 个；冻结 M5/H4 capture adapter 8 个；冻结 M11 checker 1 个。M11-003 方法另有一次重命名，不能算作第 22 项功能删除。

| 模块 | base 方法 | 当前方法 | AST 完全相同 |
|---|---:|---:|---:|
| test_catalog | 6 | 2 | 0 |
| test_documentation | 10 | 3 | 3 |
| test_pr_governance | 90 | 89 | 89 |
| test_m5_trace_export | 8 | 0 | 0 |
| test_skill_execution_closeout | 33 | 32 | 31 |
| test_skill_closeout_review | 10 | 10 | 9 |
| 合计 | 157 | 136 | **132** |

最终有 4 个改写方法（两项 catalog、M11-002、重命名后的 M11-003）。原始集合差为 remove 22 / add 1；计入 rename 后为 delete 21 / rename 1。先前五模块的 124 个不变方法统计属于 v1，不能直接标为 v2。

删除对象按被测主体判断，而非目录名：M5/H4 八例的入口是两个 `docs/workstreams/.../export_capture.py` 冻结内部适配脚本；调用真实 `AgentTraceRecorder` 是该内部适配器的组成部分。此次确实取消了这些适配器自己的 payload/gap/escape/tamper 回归，不应声称现有四例真实 Trace 测试与它们功能等价。catalog 的四例断言固定 intake 数量、历史 source/hash/status 决策，不是用户提供归档的 parser/API 合约。没有修改 M5 harness、Provider 或其产品测试。

## 公开文档与 catalog 合约

移除全 `docs/**/*.md` 扫描后，`test_public_projection_documentation_and_build_closure` 仍调用 `selected_files`，按当前 release include 读取真实文件，再调用未改动的 `release_public.documentation_errors/build_input_errors`。当前 1.7.0 清单仍包括七个公开 Markdown 页面及完整 `src/research_workbench`、`schemas` 树。

未改动的 `test_public_surface.py` 仍有 14 个方法；已读其真实正反例：missing target/anchor、越界/非便携路径、reference/HTML/URI 编码、渲染实体/autolink、代码字面量、公开 Unicode anchor、用户项目 attempt 路径与仓库 archive 链接的区别，以及缺 license/runtime/catalog/action 输入的闭包拒绝。真实渲染器 `MarkdownIt("gfm-like")` 与 `HtmlLinks` 仍在。取消广扫不等于取消公开链接和渲染闭包验证。

catalog 两例通过临时 `candidates.json` 调用真实 `load_candidates → load_document → UTF-8 json.loads`，没有 parser/filter mock。quarantine 与 trial 分别筛选、两项结果及原列表等值仍断言；mode/capability 同时匹配，以两个不匹配对照记录排除漏筛，并保留 quarantine 状态、原列表等值及缺 source 文件前后均不存在。迁移不再证明历史仓库 candidate corpus 完整性，也没有新增 schema/hash 验证；这些不是该 parser 原来的行为。

## M11 混合回放与独立 witness

M11-002 保留 `proof['cases']` 全循环、每个 case 文件 hash、receipt path/hash 参数、blocked 结果等值和其余当前 `GenericCloseoutValidationError` 拒绝分支；只去掉旧 source ZIP 循环和历史 replay launcher SHA。M11-003 保留全 case 循环、文件 pins、receipt pins、结果等值及合法 `subject_refs` 的独立 checker 正向 witness；去掉旧 ZIP 循环及冻结 checker 的 missing/outside/changed 三负例。两文件仅额外移除不再使用的 `zipfile` import，其他方法 AST 不变。

这里保留归档作为当前回放案例输入，并未按 `work/` 路径一刀切。`tests/test_release_oracle_replay.py` 相对 base 无 diff；原审计记录中的 `test_frozen_oracle_reconstructs_pinned_blobs_and_prospective_tree` 及其独立 release oracle 输入仍保留。未再次读取冻结 replay/oracle 脚本或各 proof 的内容，因此不额外认证历史 archive pins、内部每个 subcase 的数量、全部 checker 实现或 oracle 的独立性；本次确认的是代码保留、真实方法回执及审计边界。

## 清单和原生证据

结构化比较确认：`ci_components.json` 仅从 `context_observability.tests` 删除 `test_m5_trace_export`；`coverage_policy.yaml` 仅从 coverage-quality modules 删除该模块并将版本 2.3.5→2.3.6。剩余顺序不变，source root、阈值、critical files、positive/negative evidence、exclusions 均无变化。生产 catalog/io、release include/validator/public helpers/public surface 测试均相对 base 无 diff。

已直接解析回执，不重跑：

| 证据 | 实际结果 | wall 秒 |
|---|---|---:|
| implementation/local-checks-complete/native-local.json | 64 方法：60 PASS、4 ERROR，successful=false | 1.278587 |
| implementation/trace-checks-complete/native-local.json | 仅上述四个 AgentTrace 方法再运行：4 PASS | 2.147582 |
| catalog-implementation/result.json | 两个改写 catalog 方法：2 PASS | 0.006796700 |
| implementation/replay-checks-complete/native-local.json | 两个最终 M11 回放方法：2 PASS | 20.442909 |

四个原错误均为 `No module named 'research_workbench._runtime_pin'`，旧失败文件仍在；父代理补生成运行资源后仅复跑这四例，回执 ID 与原错误对应。catalog 与 replay 的方法 ID 不在前 64 项中，因此当前证据支持 **68 unique PASS**，不是把重复复跑算为额外案例。资源生成过程未在本次只读范围内重做；这些回执没有采生产 coverage，不能作为 full CI/coverage/release 门槛通过证明，也没有可据此计算的新旧性能对照。

## 绑定 hash

| 文件 | SHA-256 |
|---|---|
| tests/test_catalog.py | `0da0ccc8c0ce9474c4f5ed22d445beb5918c589b6253defc6e204411c5a2beab` |
| tests/test_documentation.py | `c7bdaef4bee20a8d05c9c2762611a861b485ea60dace130e3f96a5bc25f6fbd6` |
| tests/test_pr_governance.py | `e13e05c7f4181fcb8b4160e99519fba38872959485ab89d5b985b6699c76ef1d` |
| tests/test_skill_execution_closeout.py（v2） | `e60b87ccae7b0429db6169b856ff897f29b62d77d28197fe824d4790ff2cf4af` |
| tests/test_skill_closeout_review.py（v2） | `07731410fa70c0172780da667b8e34360f603bb7ede9fad6a822d681b17724bb` |
| tests/ci_components.json | `606624b8bef52efbf92dd67382147126532fd559c1184f03c36843d9ff0b2a43` |
| tests/coverage_policy.yaml | `dd6a8eedef51f8c840db15bed1c06d6988d38077ee6623c58e466de9511f9fed` |
| local-checks-complete/native-local.json | `f3fe8da9f6f951b9284c4d47693651d1e3cce49ab9a93594b905aa0938b18270` |
| trace-checks-complete/native-local.json | `f09e8740bab3d40aeac7e8cfcbf225e01c46d521ccfc10acad993186bee6f31c` |
| catalog-implementation/result.json | `73fb766ab0a8e6a85f128b5f31ef3ce143b73535a9002c43d2dcb6c5e352e6ee` |
| replay-checks-complete/native-local.json | `f6346ee9128d620b957b9943fd6dcb79f343bebb0ec12b51aebac41aad4bdbb6` |

采用门槛：提交/发布时绑定上述最终源码身份；若之后继续变动，重新检查相应方法与回执。真实完整回归和生产 coverage 验证由主代理继续安排，此报告不代替这些验证。
