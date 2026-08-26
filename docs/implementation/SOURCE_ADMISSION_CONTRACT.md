# Source Admission Contract (M4-001)

状态：Active implementation contract

更新：2026-08-26

## 目的与边界

本契约只实现 M4 依赖链的第一层 `M4-001`：`sources/inbox/` 是不可引用的可变隔离区；
数据进入 `sources/raw/` 前必须形成可验证的 admission sidecar。Promotion、Claim trace 与 Run
manifest 分别属于 M4-002、M4-003、M4-004，不在本 PR 中实现或宣称完成。

## 可执行契约

`source-admission` Schema 固定 admission identity、原始文件名、admitted path、字节 SHA-256、
acquisition locator（URI/DOI/device 至少一项）、带时区时间戳、具名 operator、许可/数据使用
边界、解析器版本、敏感性、外传限制及可选 derivative pins。

- `rwb source admit` 生成确定性 sidecar；默认 dry-run，只有 `--execute` 才写入；
- 执行模式同时拒绝覆盖 admitted bytes 和 sidecar；
- `rwb source check` 与仓库级 `rwb validate` 校验 Schema、路径、字节 pin 和 provenance；
- 所有已被既有文档提取器识别的 FileReference/path-only 引用若落入完整
  `sources/inbox` 路径段，均以 `ARTIFACT-INBOX-CITED` 阻断；
- 分区判断基于规范化的完整路径段，`sources/raw-copy`、`sources/inbox-old` 不会被误判为
  `sources/raw`、`sources/inbox`。

这套确定性检查不判断来源可信度、许可法律效力、内容安全性或科学质量，也不抓取网页/API。

## 风险码与证据

本层只注册并消费 `ARTIFACT-HASH-MISMATCH`、`ARTIFACT-INBOX-CITED`、
`ARTIFACT-MISSING-PROVENANCE`；缺失文件继续复用 `REF-MISSING`。实现证据和负面用例见
[`M4-ARTIFACTS-PROVENANCE/VALIDATION.md`](../workstreams/huangyi/M4-ARTIFACTS-PROVENANCE/VALIDATION.md)。
