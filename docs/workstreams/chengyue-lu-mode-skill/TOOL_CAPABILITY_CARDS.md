# Action-driven Tool Capability Cards

- 责任人：路诚钺（能力契约）；黄毅（具体 Adapter 与执行验证）
- 状态：M7-008 provider-neutral baseline
- 日期：2026-08-18
- 上游需求：[Mode Action Requirements](MODE_ACTION_REQUIREMENTS.md)

这些卡只在 Mode action 已出现真实消费者后定义能力。它们不是 Tool Registry、Adapter 实现、MCP
选择、可用性声明或安装授权。具体执行必须提供 runtime capability snapshot；名称相同不代表满足卡。

## 1. 公共判定规则

每张卡必须在调用前回答：

- operation 是 read、write 还是 execute；
- 输入中的哪些数据会离开本机或项目边界；
- 凭据由谁持有，是否能在不读取凭据时先做 capability check；
- 本地写入、缓存、外部日志和其他副作用；
- 版本、数据快照、parser/source/tool drift 如何记录；
- wall time、结果量、输出量、资源和调用次数上限；
- partial、unavailable、policy-blocked、timeout 等失败如何返回；
- 哪些结果可确定验证，哪些仍需 Skill、Mode 或 Human Gate；
- fallback 是否经过 Task/Human 明确批准。

默认规则：无静默安装、登录、网络升级、Provider/Adapter 切换、query 改写或范围放宽。Tool 只执行
已冻结的方法输入；它不能选择研究方法、提高 Claim ceiling 或签署 Human Gate。

## 2. `document-read`

```yaml
tool_capability_id: document-read
purpose: Read an approved local or frozen document range and return locator-preserving fragments.
operation_kind: read
interfaces: [local-library, cli, mcp, remote-file-adapter]
determinism: parser-and-format-version-dependent
inputs: [file-ref-with-hash, approved-range, format-hint, data-boundary]
outputs: [document-fragments, stable-locators, source-hash, read-receipt]
data_egress:
  default: none
  remote_adapter: exact-approved-bytes-or-range
  forbidden_by_default: [private-full-text, unpublished-results, entire-directory]
credentials: adapter-owned-and-never-returned
permissions: [read-approved-input]
side_effects: [optional-task-local-cache]
budget: [max-bytes, max-pages, max-fragments, wall-time]
failure_semantics: [missing, hash-mismatch, unsupported-format, encrypted, ocr-required, partial, policy-blocked]
validation: [input-hash, locator-resolves, fragment-schema, parser-version, receipt]
fallback_policy: explicit-only; OCR or remote upload is a separate approved capability
consumers: [ES-A3, ES-A4, ES-A7, SIM-A5]
non_consumers: [literature-discovery, source-weight-approval, final-claim-acceptance]
```

边界：读取成功只证明获得了指定字节/页段，不证明解析正确、引用支持 Claim 或来源质量充分。

## 3. `literature-search`

```yaml
tool_capability_id: literature-search
purpose: Execute a frozen query plan inside declared bibliographic sources and return replayable results.
operation_kind: external-read
interfaces: [local-index, cli, mcp, remote-api]
determinism: source-snapshot-and-ranking-dependent
inputs: [query-plan, source-boundary, date-boundary, language-boundary, result-limit]
outputs: [normalized-search-results, source-specific-query, query-receipt, coverage-limitations]
data_egress:
  sends: [approved-query, bibliographic-identifiers]
  forbidden_by_default: [private-full-text, unpublished-results, unrelated-project-context]
credentials: adapter-owned-and-presence-checked-without-value-disclosure
permissions: [network-search]
side_effects: [provider-query-log, rate-limit-consumption]
budget: [max-sources, max-queries, max-results, wall-time]
failure_semantics: [unavailable, partial, rate-limited, source-drift, unsupported-query, policy-blocked]
validation: [result-schema, source-id, executed-query, timestamp-or-snapshot, query-receipt]
fallback_policy: no silent source switch, query expansion, retry loop, or boundary relaxation
consumers: [ES-A2]
non_consumers: [query-plan-design, source-weight-approval, evidence-extraction, final-synthesis]
```

边界：Tool 执行 search plan；`NEED-ES-SEARCH-PLAN` 是否需要 Skill 是独立问题。结果数量、排名或 DOI
存在不能证明覆盖充分。

## 4. `citation-resolve`

```yaml
tool_capability_id: citation-resolve
purpose: Resolve approved bibliographic identifiers to normalized metadata, status, and stable locators.
operation_kind: external-read
interfaces: [local-library, cli, mcp, remote-api]
determinism: registry-snapshot-dependent
inputs: [doi-or-title-or-source-id, approved-resolver-set, date-boundary]
outputs: [normalized-citation, resolution-status, correction-or-retraction-flags, resolver-receipt]
data_egress:
  sends: [bibliographic-identifiers, approved-title-fragment]
  forbidden_by_default: [private-full-text, manuscript-body, unrelated-citations]
credentials: adapter-owned-and-never-persisted-in-receipt
permissions: [network-bibliography-read]
side_effects: [provider-query-log, rate-limit-consumption]
budget: [max-identifiers, max-resolvers, wall-time]
failure_semantics: [not-found, ambiguous, conflicting-metadata, partial, rate-limited, policy-blocked]
validation: [identifier-normalization, resolver-source, response-snapshot-or-timestamp, receipt]
fallback_policy: alternate resolver requires an explicit ordered set; ambiguity is returned, not guessed
consumers: [ES-A3, ES-A7]
non_consumers: [claim-entailment, source-quality-weight, replacement-citation-decision]
```

边界：DOI 可解析、未发现撤回或元数据一致，都不能证明引用支持附近 Claim。

## 5. `bounded-compute`

```yaml
tool_capability_id: bounded-compute
purpose: Execute an approved local command or parameterized run inside a frozen work scope and resource budget.
operation_kind: local-execute
interfaces: [project-cli, sandboxed-process, notebook-runner, runtime-tool]
determinism: environment-input-seed-and-tool-version-dependent
inputs: [command-or-script-ref, input-lock, environment-lock, parameters, seed-policy, workdir, resource-budget]
outputs: [run-manifest, stdout-stderr-ref, output-refs-with-hash, execution-receipt]
data_egress:
  default: none
  forbidden_by_default: [network, telemetry, remote-notebook, package-install]
credentials: none-by-default; remote compute is a separate capability and approval
permissions: [execute-allowlisted-command, write-task-scope]
side_effects: [task-local-files, cpu-memory-disk-consumption]
budget: [wall-time, cpu, memory, disk, output-bytes, process-count, run-count]
failure_semantics: [nonzero-exit, timeout, resource-exhausted, environment-drift, output-overflow, partial, policy-blocked]
validation: [command-allowlist, input-hash, environment-id, seed-record, exit-status, output-hash, receipt]
fallback_policy: no install, network enablement, remote execution, tolerance change, or model substitution
consumers: [SIM-A2, SIM-A3, SIM-A4, SIM-A6]
non_consumers: [convergence-design, parameter-distribution-approval, model-validity, final-claim-acceptance]
```

边界：进程成功退出不等于数值收敛；可重放 Run 不等于模型代表现实。

## 6. `research-contract-check`

```yaml
tool_capability_id: research-contract-check
purpose: Deterministically validate repository Schemas, hashes, references, section coverage, and declared state transitions.
operation_kind: local-read-check
interfaces: [project-cli, library]
determinism: checker-and-schema-version-dependent
inputs: [document-refs, schema-version, checker-version, project-root]
outputs: [deterministic-check-report, checked-subject-hashes, risk-codes]
data_egress:
  default: none
  forbidden_by_default: [network, external-validation-service]
credentials: none
permissions: [read-declared-documents, write-check-report]
side_effects: [task-local-check-report]
budget: [max-documents, max-bytes, wall-time]
failure_semantics: [schema-fail, hash-mismatch, reference-missing, checker-error, unsupported-contract, partial]
validation: [checker-hash-or-version, subject-hashes, reproducible-exit, report-schema]
fallback_policy: no model judgment may overwrite a deterministic failure
consumers: [ES-A3, ES-A4, ES-A6, ES-A7, SIM-A2, SIM-A7, project-internal-closeout]
non_consumers: [semantic-entailment, scientific-correctness, source-weight, acceptable-error, Human-Gate-decision]
```

边界：该卡只是现有本地 validator/CLI 的能力名称，不要求新增一套 checker。结构 PASS 不能被描述为
Evidence 正确、Handoff 语义等价、模型有效或 Claim 已接受。

## 7. Adapter 绑定 Gate

具体 CLI/MCP/API 只有同时满足以下条件才能声称实现某张卡：

1. 给出版本化 capability snapshot，而不是依据工具名称推断；
2. 声明卡中每个输入、输出、数据出口、副作用、budget 和 failure semantic 的映射；
3. 无法表达的字段返回 capability gap，不由 Prompt 补成“支持”；
4. read/execute 前先完成本地权限与数据策略检查；
5. 用脱敏 fixture 验证成功、partial、policy-blocked 和 drift；
6. Adapter owner 黄毅确认实现与 API 测试；路诚钺只确认方法消费者和卡语义。

M7-008 到此只冻结 cards，不选择实现、不读取凭据、不调用网络，也不创建 `registry/tools/`。
