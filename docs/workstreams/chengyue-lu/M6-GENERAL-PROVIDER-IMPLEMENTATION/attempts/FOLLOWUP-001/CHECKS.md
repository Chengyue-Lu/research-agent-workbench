# FOLLOWUP-001 检查

基线 develop `27cbf860e48e9639bd3af32a58c12bfd88d87526`，源码候选 `b0f8ceefb94fb7d20b50ca741484795637e0742a`。
最终证据文档提交只更新本CHECKS/HANDOFF；源码、Schema、policy和测试Git blobs须与上述source全等。
它不继承PR127基础的审核接受，不声明整项M6-009或真实调用通过。

| 检查 | 实际结果及范围 |
| --- | --- |
| Python3.11.16 exact-source component | 560项，556 PASS、4 skip、0fail/0error，287.677s；unknown paths=0；coverage未采集 |
| repository validation | 199 validated / 0error / 0warning |
| docs/public/Schema修复后focused | 30/30 PASS；最终仅证据MD再验证docs/public与R2 metadata |
| 非editable安装、仓库外cwd、-I | 173资源/111默认Schemas，12profiles+11禁用配置；CLI只计划、禁用退出1、live_qualified=false |
| 当前wheel source绑定 | 173资源及6个改动安装模块与source Git blobs逐字节全等；pip check通过 |
| installed short smoke | 8/8 PASS，11.032s |
| Session owner | 90 PASS；独立38种边界及49policy/19default测试适用；LF后49policy PASS，默认AST未变 |
| driver owner | 修复后84联合PASS；23own PASS；已收到响应用量在capture/storage失败后保留 |
| catalog owner | 49项，48PASS+1Windows skip；13原profile/config字节不变、typed/hash闭合 |
| 独立driver/report/transport | 20driver案例、20层隐私注入、7transport/预算案例通过；47不同direct测试PASS，不累计重复runs |
| 基线source CI诊断修复 | 旧6项为5PASS+1FAIL；新7/7PASS；4真实consumer newline drift反例，原policy/pins不改 |
| build surface | 只append1.6.0与13exact输入；独立Git base/head核旧6policy不变；actual source完整DAG检查PASS，无export |

完整原始输出、dispatch、各owner/independent receipts和source pins保存在隔离worktree
`.rwb/m6-general-prototype/followup-001/`，没有把本地日志伪装成远端审核或运行接受。

当前wheel SHA256 `ce2bd8ad7f519e2881f9a2fdca8465bdb43d669b7d507b0de8f92831b53870ac`；manifest SHA256 `f9e9cc55b17f0dc9852e018f7292d07544765e584d11db43fc56b9ef2d13d614`。
可重现命令：

```text
python .github/scripts/run_component_ci.py plan --repo . --base 27cbf860e48e9639bd3af32a58c12bfd88d87526 --head b0f8ceefb94fb7d20b50ca741484795637e0742a --profile component --output <new-plan.json>
python .github/scripts/run_component_ci.py run --repo . --plan <new-plan.json> --output <new-result.json>
python -m research_workbench validate examples registry
python .github/scripts/ci_component_smoke.py --python <installed-wheel-python> --output <new-smoke.json> --timeout 120
```

组件skip原因保持测试原记录，未将skip当PASS：
[
  {
    "id": "test_ci_component_smoke.ComponentSmokeTests.test_cli_preserves_venv_interpreter_symlink",
    "reason": "POSIX venv interpreter symlink regression"
  },
  {
    "id": "test_critical_contract_branches.CriticalIntegrityBranchTests.test_directory_hash_refuses_symlinked_package_file",
    "reason": "symlink unavailable"
  },
  {
    "id": "test_provider_profile_configuration.ProviderProfileConfigurationTests.test_symlink_cannot_escape_allowed_root",
    "reason": "local Windows account cannot create a symlink"
  },
  {
    "id": "test_scaffold.ScaffoldTests.test_linked_destination_is_rejected_without_writing_target",
    "reason": "directory symlinks unavailable"
  }
]

保留的失败：基线source CI37022594303两处历史pin漂移；首次512项组件3FAIL/4skip
（13个build输入缺失引起两个失败、新Schema kind清单引起一个）；第二次560项1FAIL/4skip
为静态policy版本列表未更新，修后保留旧六版本canonical hash。Root Schema漏cost_status及
released-before-send、终态snapshot-null状态不一致原反例；各owner原codec/test/runner反例。
Root probe错误（把validate_catalog成功摘要当errors）、symbolic HEAD计划拒绝及一次无效patch
属于执行脚本诊断，已纠正，不计产品通过；所有早期证据保留原source身份。

Root及child可见dispatch、保存的工具输出和receipts是局部留痕；平台完整工具/通信事件没有导出，
capture gap明确保留，不补写隐藏推理或凭据。当前报告只保留数字、固定code和非秘密refs。

未关闭的运行资格：完整source/config/helper/runtime/Windows/time闭包、官方billable输入上界、
唯一实际预算path/namespace及具名接受。guard/input bounds caller-attested，入口仅delegate-entry，
source_refs仅两个模块。费用unknown不阻断；unknown token保留预占停止。
M6-009 IN_PROGRESS、M6-010 BLOCKED；真实API/Key/presence/bridge均0。无full/global coverage结论。
