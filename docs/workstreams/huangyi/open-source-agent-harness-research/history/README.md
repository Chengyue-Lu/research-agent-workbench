# RESEARCH-HARNESS-001 Worklog

状态：实施中；合并 main 后在本页追加 closeout，不复制 raw 验证产物。

## 基线与责任

- 起始基线：`develop@b1d5a5a5850e0e7541e4c460f15384cd45357ab2`
- 当前集成基线：`develop@5991cafdb7f536cd7b871508de9055d02b558728`
- 工作分支：`codex/open-source-agent-harness-research`
- Owner：黄毅（`let778750-cpu` / `huangyi855`）
- Reviewer：路诚钺（`Chengyue-Lu`）
- Task：`RESEARCH-HARNESS-001`

## 2026-08-23

- 同步本地 develop 与 origin/develop；两者均为 `b1d5a5a`；
- 在仓库外保存黄毅目录的可恢复副本并核对 3 个文件哈希；
- 从最新 develop 创建独立研究分支，未继承 PR #23；
- 将 Harness 原稿迁入 ignored `sources/raw/`，迁移前后 SHA-256 一致；
- 固定 5 个核心与 5 个补充 Harness 的仓库、commit、HEAD 和许可证；
- 将 Open Science 标为身份错配，不纳入正式结论；
- 将原稿拆为 Fact/Inference/Proposal/Capture Gap；
- 完成 5 个 Codex 只读 Attempt，保留失败、部分成功、被替代和 canonical 结果；
- canonical Attempt 证明 Schema/握手/错误/实验 Gate，保留网络和外写 capture-gap；
- 将 ignored 临时 Home 无损压缩，避免上游 bundled Markdown 干扰本项目文档测试；
- 新建独立 `A-20260823-REPO-CHECKS`，本地完成 237 项无跳过测试、83.2174% 总覆盖率、
  92.9577% Trace 覆盖率、wheel 构建、clean install、24 个 Schema 和 59 个对象验证；
- PR #25 以 `5991caf` 合入 develop 后，重新获取远端并将研究分支成功 rebase 到该提交；
- 保留旧 Attempt 的 `b1d5a5a` 运行事实，另建 `A-20260823-REPO-CHECKS-02` 验证
  `5991caf` 新增的治理与文档测试，不把新结果伪装成旧运行；
- `REPO-CHECKS-02` 在 Python 3.12.13 下完成 264 项无跳过测试、24 项治理单测、
  83.2174% 总覆盖率、92.9577% Trace 覆盖率、wheel 与 clean install；
- 修正 canonical tracked JSON 的 CRLF 工作副本哈希，使其绑定 Git 中 LF 规范字节；
- 没有修改 TASKS、STATUS、ROADMAP、ADR、Schema、Registry 或 Runtime。

## 关键决定

- 稳定职责表暂不增加“开源 Harness 调研”职责；
- raw 物理保存在本 workstream，Git 只跟踪最小脱敏证据；
- Host/Team/Capability Snapshot v2只保留为 post-M8-003 提案；
- PR #20 只吸收经核验差异，不吸收整个研究包；
- PR #25 已进入 develop；本工作流继续服从其 PR 模板、跨 owner 审查和 CI 门禁。

## 待 closeout

- 由目标 PR CI 运行 Python 3.11/3.13 与真实 PR event 治理检查；
- 完成跨 owner review；
- squash merge 到 develop，并随完整 workstream 发布到 main；
- 发布后记录 merge SHA、最终验证与 PR #20 delta 状态。
