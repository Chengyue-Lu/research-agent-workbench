# 来源清单

```yaml
retrieved_at: "2026-08-23T18:05:24+08:00"
rwb_main_evidence_baseline: "b1d5a5a5850e0e7541e4c460f15384cd45357ab2"
rwb_develop_integration_baseline: "5991cafdb7f536cd7b871508de9055d02b558728"
head_semantics: "retrieval snapshot only; claim evidence remains pinned to evidence_commit"
verification_scope: "canonical repository, default-branch HEAD and path-scoped license"
```

`evidence_commit` 决定正文证据；`retrieved_head` 只显示检索时默认分支是否移动。此清单
没有对每个上游主张做逐行重放，具体内容仍须由 `CLAIM_LEDGER.md` 的固定链接支持。

## RWB 与候选分支

| Source ID | Scope | Revision | Authority | 用途与限制 |
|---|---|---|---|---|
| `RWB-MAIN-001` | main | `b1d5a5a5850e0e7541e4c460f15384cd45357ab2` | accepted docs、planning、implementation 各按自身表面解释 | Runtime 和研究控制实际行为证据基线 |
| `RWB-DEVELOP-001` | develop | `5991cafdb7f536cd7b871508de9055d02b558728` | PR #25 已集成的治理候选线 | 当前目标 PR 基线；新增治理/审计/CI，不代表 Runtime 行为变化 |
| `RWB-PR20-001` | candidate only | head `a908bc2cf32eac0bff48a0e9b06d76743e1708bd`；matrix `734a4e77283c6b3fc3a91b02f89975c87dc4959e`；reconstruction `af71534` | PR 候选证据 | 不能证明 main 已具备 request reconstruction |
| `RWB-M8-002-CANDIDATE` | candidate only | `d3f3407` | 未合并实现候选 | 仅正式化 Mode Action；不含 Method Resolution、Skill/Tool binding 或 Runtime |
| `RWB-HUANGYI-DRAFT-001` | private working paper | SHA-256 `4C33CF931AE660EB42627D450794A905674C92B653A7E7ED8767288F5101FB79` | human-attested working paper | 只提炼主张；原文不提交，不能改变项目状态 |

## 核心 Harness

| Source ID | 项目 | 默认分支 | Evidence commit | Retrieved HEAD | 许可证 | 状态 |
|---|---|---|---|---|---|---|
| `HARNESS-DEEPSEEK-001` | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | `master` | [`b150a551b8d465e31e418e1b2eaf5e79bbb7d28e`](https://github.com/deepseek-ai/deepseek-harness/tree/b150a551b8d465e31e418e1b2eaf5e79bbb7d28e) | 同 evidence commit | [MIT](https://github.com/deepseek-ai/deepseek-harness/blob/b150a551b8d465e31e418e1b2eaf5e79bbb7d28e/LICENSE) | `VERIFIED` |
| `HARNESS-CODEX-001` | [Codex](https://github.com/openai/codex) | `main` | [`343074d4207d572809bd8cea15f4be1d09d98e0b`](https://github.com/openai/codex/tree/343074d4207d572809bd8cea15f4be1d09d98e0b) | [`83d1fe0e67b1323f71febc2925817732b449f1d9`](https://github.com/openai/codex/tree/83d1fe0e67b1323f71febc2925817732b449f1d9) | [Apache-2.0](https://github.com/openai/codex/blob/83d1fe0e67b1323f71febc2925817732b449f1d9/LICENSE) | `VERIFIED_HEAD_MOVED` |
| `HARNESS-OPENCODE-001` | [OpenCode](https://github.com/anomalyco/opencode) | `dev` | [`3a31c4ea801915c0b050df4b3842997ea62b6e93`](https://github.com/anomalyco/opencode/tree/3a31c4ea801915c0b050df4b3842997ea62b6e93) | 同 evidence commit | [MIT](https://github.com/anomalyco/opencode/blob/3a31c4ea801915c0b050df4b3842997ea62b6e93/LICENSE) | `VERIFIED` |
| `HARNESS-PI-001` | [Pi](https://github.com/earendil-works/pi) | `main` | [`c49906ec77788625aacbdc53ebca6fbe65bd20f5`](https://github.com/earendil-works/pi/tree/c49906ec77788625aacbdc53ebca6fbe65bd20f5) | [`c1279a65b3ef6b0b19950ed1771d5933241c240f`](https://github.com/earendil-works/pi/tree/c1279a65b3ef6b0b19950ed1771d5933241c240f) | [MIT](https://github.com/earendil-works/pi/blob/c1279a65b3ef6b0b19950ed1771d5933241c240f/LICENSE) | `VERIFIED_HEAD_MOVED` |
| `HARNESS-CLINE-001` | [Cline](https://github.com/cline/cline) | `main` | [`1de61b178aec844e0aa362474274ccbf6acf9403`](https://github.com/cline/cline/tree/1de61b178aec844e0aa362474274ccbf6acf9403) | [`be8b984d10d1ad0e9a3917e051ac697f592587d2`](https://github.com/cline/cline/tree/be8b984d10d1ad0e9a3917e051ac697f592587d2) | [Apache-2.0](https://github.com/cline/cline/blob/be8b984d10d1ad0e9a3917e051ac697f592587d2/LICENSE) | `VERIFIED_HEAD_MOVED` |

## 补充 Harness

| Source ID | 项目 | 默认分支 | Evidence commit / Retrieved HEAD | 许可证 | 状态 |
|---|---|---|---|---|---|
| `HARNESS-GOOSE-001` | [Goose](https://github.com/aaif-goose/goose) | `main` | [`8d844eecbdfd65626a881c9e8784ae8dc6093f1d`](https://github.com/aaif-goose/goose/tree/8d844eecbdfd65626a881c9e8784ae8dc6093f1d) | [Apache-2.0](https://github.com/aaif-goose/goose/blob/8d844eecbdfd65626a881c9e8784ae8dc6093f1d/LICENSE) | `VERIFIED_REDIRECT`；旧组织名已重定向 |
| `HARNESS-AIDER-001` | [Aider](https://github.com/Aider-AI/aider) | `main` | [`5dc9490bb35f9729ef2c95d00a19ccd30c26339c`](https://github.com/Aider-AI/aider/tree/5dc9490bb35f9729ef2c95d00a19ccd30c26339c) | [Apache-2.0](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/LICENSE.txt) | `VERIFIED` |
| `HARNESS-SWEAGENT-001` | [SWE-agent](https://github.com/SWE-agent/SWE-agent) | `main` | [`3ea751c087f32b16e039a2233dd6eefecef325d5`](https://github.com/SWE-agent/SWE-agent/tree/3ea751c087f32b16e039a2233dd6eefecef325d5) | [MIT](https://github.com/SWE-agent/SWE-agent/blob/3ea751c087f32b16e039a2233dd6eefecef325d5/LICENSE) | `VERIFIED` |
| `HARNESS-CONTINUE-001` | [Continue](https://github.com/continuedev/continue) | `main` | [`5522c6f44ca0ac3528b37244818fbfa39b5af470`](https://github.com/continuedev/continue/tree/5522c6f44ca0ac3528b37244818fbfa39b5af470) | [Apache-2.0](https://github.com/continuedev/continue/blob/5522c6f44ca0ac3528b37244818fbfa39b5af470/LICENSE) | `VERIFIED` |
| `HARNESS-OPENHANDS-001` | [OpenHands](https://github.com/OpenHands/OpenHands) | `main` | evidence `4bf8dd3aaf1217916b2ce8a6f9168fa7633a26f8`；[HEAD `2f5bd24f00e3111449ec6b1f6e6b4ec1033f3a59`](https://github.com/OpenHands/OpenHands/tree/2f5bd24f00e3111449ec6b1f6e6b4ec1033f3a59) | [根目录 MIT](https://github.com/OpenHands/OpenHands/blob/2f5bd24f00e3111449ec6b1f6e6b4ec1033f3a59/LICENSE)；[`enterprise/` 为 PolyForm Free Trial](https://github.com/OpenHands/OpenHands/blob/2f5bd24f00e3111449ec6b1f6e6b4ec1033f3a59/enterprise/LICENSE) | `VERIFIED_HEAD_MOVED_SCOPED_LICENSE` |
| `HARNESS-OPENSCIENCE-001` | Open Science | 未确定 | 原稿 SHA `b51714d007834053c7d0c0dbd1794478ebde931e`，不登记 HEAD | 不登记 | `UNVERIFIED_IDENTITY_MISMATCH` |

## Open Science 身份冲突

原稿没有记录规范 URL。其 SHA 可以解析到
[`ai4s-research/open-science`](https://github.com/ai4s-research/open-science/commit/b51714d007834053c7d0c0dbd1794478ebde931e)，
但同时存在描述相似的 [`aipoch/open-science`](https://github.com/aipoch/open-science)，且该 SHA
不能在后者解析。未获得黄毅最初使用的 URL 前，不选择其中任意一个，也不让该材料支持
正式结论。

## 核验接口

仓库、HEAD 和许可证元数据通过 GitHub 官方 REST 表面核验：

```text
https://api.github.com/repos/{owner}/{repo}
https://api.github.com/repos/{owner}/{repo}/commits/{default_branch}
https://api.github.com/repos/{owner}/{repo}/license?ref={sha}
```
