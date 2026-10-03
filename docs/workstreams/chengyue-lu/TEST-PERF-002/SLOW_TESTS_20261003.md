# 全量 CI 慢用例：针对性优化与配对实验

责任人：Chengyue-Lu。基线：`3579e67124836559d7932287591e4d77053a1e94`。
本轮沿用 TEST-PERF-002 的性能工作流，独立 Draft PR 只调整测试准备和合成文件表示。
[本轮证据与交接](../../../../work/TEST-PERF-002/A-20261003-001/README.md)。

## 实际全量 CI 的观察

读取 GitHub 原生 test results，并保留 run、Python、结果与执行耗时身份。失败 run 的耗时不能作为成功基线，coverage 与非 coverage 两条 job 的 runner/Python 也不相同。

| 执行 | 已核验结果 | 观察 |
| --- | --- | --- |
| [37001814011](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37001814011) | 整条 SUCCESS；3.11 coverage 1633 PASS | producer 3299.001 秒，case 累计 2864.625 秒；execution、evidence、analysis 分别约 498、471、362 秒 |
| [37106743428](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37106743428) | producer 2016 PASS；coverage job FAILURE | Provider graph/profile 两模块约占 case 累计 38.08%；未将 producer PASS 改称整条 CI PASS |
| [37108211033](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37108211033) | coverage producer 2014 PASS、2 FAIL | producer 6490.906 秒；两 Provider 模块约占 case 累计 34.91%，失败是原有时间预算断言 |
| [37130368701](https://github.com/Chengyue-Lu/research-agent-workbench/actions/runs/37130368701) | 最新基线全量执行，取样时仍 IN_PROGRESS | 3.13 compatibility 已 FAILURE；14 errors 为 `ProviderAdapterConfig.__repr__` 未声明运行时 callable，部分用例未执行；3.11 coverage 尚无终态 |

最后一条 run 的实时失败已交给负责 Provider 代码的开发窗口。这里不放宽安全校验，也不把漏跑用例产生的短时长算成优化。
原始全量工件在本地审计输入中保留；仓库内保存提取结果、来源身份和哈希索引。

## 本轮修改

### Provider：减少重复生产 fixture

`ProviderBindingGraphTests` 将完全相同的真实 graph staging 移到 class setup。每个测试仍使用独立临时目录、完整 `copytree`、新的 credential/transport/provider 与独立 reference 字典。
全部 11 个测试正文和 42 个断言调用保留；篡改、逐次 source consumption、冷回放仍通过真实实现执行。没有缓存 verification 结果。

Profile 成功路径删除紧挨真实 report writer 的重复成功 verification。writer 内部仍调用真实 checker 并写出其返回对象；原 JSON 读回等值断言保留。7 个测试及 5 个 mutation 校验没有删除。
Provider 修改单独提交，便于其他分支按自己的源代码组合验证。

### M5：让已用 JSON 写出的合成 bundle 使用 JSON 后缀

Harness 的合成 A4 documents 本来由 JSON writer 输出，却沿用 `.yaml` 文件名，反复进入 YAML parser。
给共享 fixture 增加可选 `document_suffix`；仅 Harness 选择 `.json`。默认 `None` 保持原 System Evaluation/Overlay 路径与 YAML 覆盖。
所有引用通过原 `path_map` 重写，实际文件哈希、manifest/import closure 和实际 loader 校验仍执行。
没有修改生产 parser，也没有删除 arm、slice、Attempt、retry 或冷回放。

## 序列化性能实验

所有计时包含 class setup 和原用例执行。使用同一台 Windows 主机、Python 3.11.16、coverage 7.16.1、jsonschema 4.26.0、PyYAML 6.0.3。
coverage 数据均检查实际 branch arcs；计时实验顺序执行，不与本轮其他 CPU 测试并跑。

| 实验 | before 秒 | after 秒 | 原用例结果 |
| --- | ---: | ---: | --- |
| Provider，1 组 4 个真实用例 | 197.072 | 182.099 | 两侧各 4 PASS |
| M5 第 1 组，YAML → JSON | 103.771 | 95.773 | 两侧各 2 PASS |
| M5 第 2 组，JSON → YAML 执行顺序 | 106.805 | 96.260 | 两侧各 2 PASS |
| M5 第 3 组，YAML → JSON | 107.660 | 95.110 | 两侧各 2 PASS |

Provider 这组减少 **7.60%**，其中实际 urllib/report/cold 路径 156.059 → 147.951 秒。只有一组，不能宣称稳定收益。
M5 三组分别在 fresh Python 进程中运行，同组只改变合成文件表示，配对降幅中位约 **9.87%**。
每侧都跑保留 fresh retry 的真实四臂执行、冷回放、缩短 Attempt 拒绝，以及 outer authority/clock 在 dispatch 前拒绝。
它是 candidate fixture 的表示对照，不是历史 accepted source 的重放。

Provider 两次 probe 间新增了未启用的 M5 参数和计时外 metadata 字段，runner/用例和计时区间未改，但不能声称 probe 源码哈希完全相同。
M5 三组使用冻结的同一 probe。主机外部负载未控制，因此这些都是局部观察，**不等于全量 CI 提速百分比**。

## 保留和放弃的检查

实际 loader 比较两侧各 124 个 fixture 文件、8 个 A4 documents 的规范化语义及引用/哈希；四臂顺序与 design 相同。JSON supply 仅改一字节即由真实 loader 拒绝，另一侧文件保持不变。
两个 Provider 副本的独立性通过实际篡改/拒绝/另副本正常验证检查；seed、凭据和 transport 未受污染。
未参与计时的 Provider 14 个原用例全部通过；加上 4 个 coverage 计时用例，两个受改动类的 18 个用例均已执行通过，分别保留回执身份。
最终实现 source 的 M5 Python 3.11 局部 4 PASS（346.996 秒），包含 analysis 冷回放、默认 Overlay、output hash drift 与 hash-consistent shortened run 拒绝；Python 3.13 局部 3 PASS（90.171 秒），包含四臂执行、fresh retry 与默认 Overlay。
这两条局部功能回归的 Python/范围不同，不能比较为提速；analysis 冷回放用例本身仍约 287.353 秒，是未消除的真实验证成本。

分析 unit fixture 的复制缓存方案被放弃：23 个用例通过，原 setUp 中位 0.106 秒，149 文件复制加 deepcopy 中位 0.131 秒，预计反而增加约 0.683 秒。
成功的单 retry cProfile 只用于定位，YAML 解析累计约 21.5 秒且与其他调用累计时间重叠，不相加、不作为正常吞吐测量。
生成 runtime 前的初次 profile setup 失败和 coverage 输出目录碰撞均保留，测试数为 0，不进入收益统计。

## 验收边界

普通 PR 沿已接受的 component CI 路由测试受影响组件；最终新 HEAD 的正式 plan、原生测试和 governance 另核。
本轮不改 component mapping、selection policy、工作流、生产模块、coverage 门槛、保护规则或发布状态。
保留现有 90/95/90 与 changed 100/100 的适用规则；本地局部 arcs 并不替代 repository coverage 证明。
最终全量 checkpoint 是否变快仍需同身份、成功、同范围的新运行证据；本轮没有无故重跑旧全量 CI。
Draft 是实验和评审入口，尚未请求 Ready、合并或业务 Task 接受。
