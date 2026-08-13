# ADR-0004：M1 使用最小依赖 Python 基线

状态：Accepted
日期：2026-08-13

## 背景

实施计划最初建议 Pydantic、Typer、pytest 和可选 Hypothesis。M1 的首个切片只需要不可变引用、少量数据对象、YAML/JSON 读取、确定性校验和本地 CLI。此时引入完整框架会先增加环境、升级与供应链成本，而尚未证明能降低科研契约复杂度。

## 决策

- Python 版本保持 3.11+。
- 核心对象使用标准库 `dataclasses`；Provider 端口使用 `typing.Protocol`。
- CLI 使用 `argparse`，测试使用 `unittest`。
- PyYAML 用于读取人类编辑的 YAML；JSON 继续作为 Registry 交换格式。
- M1 开始执行版本化 JSON Schema 后，引入 `jsonschema` 的 Draft 2020-12 验证器。项目不自行实现不完整的 Schema 子集。
- 当 CLI 可用性或属性测试出现经测试的明确成本时，再分别评估 Pydantic、Typer、pytest 或 Hypothesis。

## 后果

首版只有 PyYAML 与 jsonschema 两个运行依赖，且 Provider Adapter 不依赖任何厂商 SDK。版本化 Schema 和错误定位由标准实现负责，内部对象仍保持轻量 dataclass。
