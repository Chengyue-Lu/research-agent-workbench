# FOLLOWUP-026 检查

2026-10-04。源基线为实际 developede2bc1；仅文档、既有脱敏证据和 M6-010 状态更新。

- 独立 review006 的原 auditor 在 fresh 输出目录重复运行，仍仅 stdlib SQLite
  `mode=ro&immutable=1` / `query_only=ON`；40 checkpoints、原25events+grant26、DB/anchor
  bytes、三个当前calls与每一 durable usage、四个断言、原失败、parent/entry/selection refs 一致。
  4 durable /5native /7responses /10slots /1744tokens /held0；没有 journal.open 或真实写入。
- 原 installed002 Python3.11.16 的 exact pure reader source SHA9ebf038e... 冷读报告 PASS；
  report1.2 completed、`live_qualified=false` / `remote_strict_claim=false` 原样。
- 公开 report 是原文件逐字节副本，SHA
  `1f0bef0cbf1bea5f9b1744a8801f62c7aac3e05c86f34b9b9e8b76781cda70d8`；
  公开索引24个private refs逐一从原件计算size/hash，额外检查portable paths与禁止原始载荷字段。
- `git diff source66..developede -- src assets` 只有 profile_conformance 和 conformance_journal
  两个已修复模块，具体 delta 及离线反例见[收口记录](../../M6-010_COMPLETION.md)。未重绑原 live。
- 原报告writer/read-only checker不授予具名接受；本次在报告外部记录用户直接收口指令。
  M6-010 DONE 候选不修改其定义/依赖/验收，不激活 M5 pilot / A4 / OpenAI /科研/发布。
- 浏览器两次 direct official open 返回400 Timeout，原结果保留；随后官方域名搜索确认 Flash
  alias/Responses/effort资料仍可定位。没有因此改变原run的 dated official receipt，也未发新真实请求。
- 几次只读定位命令包含不存在的root文档、文件名或Windows glob；改为现存 docs/入口或准确文件名，
  原诊断保留。不存在的summary.json未读取，真实Session文件为summary.jsonl；未改变原证据。

当前 focused documentation、repository、治理、diff 与 hosted checks 在后续验证节按实际结果补充；
未执行全量/coverage/新API/原生凭据链，不能把先前594component或本次只读检查称为这些范围通过。
develop full37168512882 的3.13 compatibility失败和3.11 coverage当时运行中已另通知开发2。

## 当前候选验证

- documentation：10/10 PASS，0.567s；真实 Markdown 链接、公开文档/build closure 检查均包含。
  首次 `py -3.11` 未找到注册runtime（exit103，零测试）；第二次使用历史 installed002 的纯
  runtime执行时缺 test-only `markdown_it`，10项中的1项ERROR。两次原诊断保留，未修改旧安装；
  改用已存在的 doc-check-venv 后正常通过，未删除反例或安装/修改原 frozen runtime。
- repository：当前源码 `validate examples registry --root .`，validated202 / errors0 / warnings0。
- diff：`git diff --check` PASS；只允许 M6-010 状态字节由 BLOCKED→DONE，定义/依赖/验收与base
  相同。显式stage排除 `.codex/config.toml`，其原SHA90069309...保持。

本地治理和实际PR/hosted检查结果随后按各自source身份记录。
