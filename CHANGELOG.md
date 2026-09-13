# Changelog

本页记录面向使用者的变化。能力成熟度与限制统一见[支持能力与证据边界](docs/SUPPORTED_FEATURES.md)。

## Unreleased

- README、上手指南、支持矩阵和公开模块导航使用同一组源码文档；源码发行面包含构建后端、Runtime catalog 声明和 no-Skill 示例。
- 安装后可在源码目录外创建完整 no-Skill 项目、校验项目与资源 pin；上手指南串联 offline-demo 的证据定位、Run 检查、独立进程重建与报告验证。

## 0.1.0 — 开发版本 / technical alpha

- 提供 Task、Method、Capability、Handoff、Evidence、Claim、Decision 与 Trace 的文件契约及确定性验证。
- 安装包包含 hash-pinned Schema、Mode/Action、Authority、Requirement、Protocol Profile 与空 Projection index；资源、项目文件和平台配置使用各自的显式根。
- Runtime Bundle → Resolved Execution View → Thin Host → Receipt 支持 bounded no-Skill/direct-tool 契约闭包。
- 来源准入、工件提升、Claim 证据定位与 Run 重建提供结构验证及固定合成案例证据。
- 可选 Skill publication/mapping 仅有契约与 synthetic fixture 证明，当前包内没有发布的 Skill。
- 维护者 Registry、Provider、模型与平台配置由调用方显式提供。真实 Provider conformance、科研对照评估与首次正式发行仍待独立验收。
