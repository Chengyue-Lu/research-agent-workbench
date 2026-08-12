# ADR-0004：M1 使用最小依赖 Python 基线

状态：Accepted
日期：2026-08-13

## 背景

实施计划最初建议 Pydantic、Typer、pytest 和可选 Hypothesis。M1 的首个切片只需要不可变引用、少量数据对象、YAML/JSON 读取、确定性校验和本地 CLI。此时引入完整框架会先增加环境、升级与供应链成本，而尚未证明能降低科研契约复杂度。

## 决策

- Python 版本保持 3.11+。
- 核心对象使用标准库 `dataclasses`；Provider 端口使用 `typing.Protocol`。
- CLI 使用 `argparse`，测试使用 `unittest`。
- 唯一运行依赖为 PyYAML，用于读取人类编辑的 YAML；JSON 继续作为 Registry 交换格式。
- 当 Schema 生成、复杂联合验证或 CLI 可用性出现经测试的明确成本时，再分别评估 Pydantic、jsonschema、Typer、pytest 或 Hypothesis。

## 后果

首版可在较少依赖下运行，且 Provider Adapter 不依赖任何厂商 SDK。代价是 M1 仍需显式实现版本化 JSON Schema 与更完整的错误定位；本 ADR 不取消这些交付物。
