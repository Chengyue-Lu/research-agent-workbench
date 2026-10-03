# FOLLOWUP-021 检查

2026-10-03。完整执行与用量事实见[部件进度](../../M6-010_FLASH_COMPONENT_PROGRESS.md)。

- 最终真实 report：FAILED / deadline-exhausted；Tool shape/executed-once/text-exact 为 true，
  schema-exact 为 false，Schema 发送前停止。三组 durable Attempts、四次 native 启动分别计数。
- 独立报告/账本复核：PASS；四个响应累计 input 1,057 / output 148 = 1,205，held 0，
  七个 reservation slots、四个 HTTP delegate entries、25 个历史事件；缓存256不重复相加。
- 已消费 caller/child 的 sized-read 文件检查：最终12/12 PASS；原 fixture 错误保留。
  875 refs 读取6.938→1.188秒，只限同本机该测量。
- 最后一次入口 ordinal：128 AST cases PASS；production journal + FakeDelegate 回归 PASS，
  全局5/6/7可用，第四次调用与第四组 Attempt 仍拒绝。fake tokens 不并入真实账本。
- 失败后的 helper/per-pass AST 候选测量 PASS：129 pins 0.546→0.125秒；cold graph
  80 reads/相同完整字节，797→80 parses，2.328→1.078秒。只是离线候选，未修改产品。
- Pure source component profile PASS：80模块，AST0.187秒/compiled callable fingerprints0.094秒；
  不执行 loaded-runtime validator 或完整 contract validator，不解释为完整运行优化。

本次仓库修改仅文档。Python3.12.10 的 documentation/public-surface 检查24/24 PASS，0.797秒，
包含内部 Markdown 链接；原始 config/报告/累计快照 hash 核对通过，canonical M6-010 row 与
product/Schema/registry 未变。PR治理针对本次 commit 单独运行并记录在 PR，不借 PR128 的
868项结果、旧安装 smoke 或 Windows 合成结果声称当前文档 head 已完成真实 conformance。

文档检查首次两次因检查环境分别缺少 markdown-it/jsonschema，均11项/2个 import ERROR；
按项目既有依赖范围建立隔离环境后24项通过。初版纯 hash 核对错误地要求原始 config 文件的
hash 出现在规范化报告中，随后分别核对两者；此失败没有进入真实驱动或修改累计历史。

可见选定源、运行回执、原失败、角色交付与命令片段已保留在本地私有 archive。
完整平台工具导出及部分更早 inter-agent 原文不可得，capture gap 如实保留。
