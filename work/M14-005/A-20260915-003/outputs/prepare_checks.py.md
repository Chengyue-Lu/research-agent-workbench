# Evidence helper source

```python
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / '.rwb/m14-source-ci'
BASE = '0bebafd81f0116a8269c63ac97378038a1eb2a5d'

def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, encoding='utf-8').strip()

head = git('rev-parse', 'HEAD')
assert git('rev-parse', 'origin/develop') == BASE
before = git('show', BASE + ':docs/TASKS.md')
after = (ROOT / 'docs/TASKS.md').read_text(encoding='utf-8')
rows = lambda text: '\n'.join(line for line in text.splitlines() if re.match(r'^\| M\d+-\d+ \|', line))
assert rows(before) == rows(after) and '| M14-005 | BLOCKED |' in after
primary = ROOT.parent / 'research-agent-workbench'
assert git('rev-parse', 'HEAD', cwd=primary) == '11c3b57dfbf8af0dc2587fc421d097e2544941c3'
assert git('branch', '--show-current', cwd=primary) == 'develop' and not git('status', '--porcelain', cwd=primary)
assert not git('diff', BASE, head, '--', 'src', 'schemas', 'registry', 'pyproject.toml', '.github/release-surface.yml',
               '.github/governance-policy.json', 'work/M14-005/A-20260914-001', 'work/M14-005/A-20260914-002')
scope = dict(observed_at=datetime.now(timezone.utc).isoformat(), baseline=BASE, head=head,
             canonical_tasks_unchanged=True, task_rows_sha256=hashlib.sha256(rows(after).encode()).hexdigest(),
             m14_005_state='BLOCKED', source_ci_implementation=True, live_positive_protected_push='pending integration',
             product_schema_registry_release_policy_topology_and_frozen_archives_unchanged=True,
             primary_clean_unchanged=True, changed_paths=git('diff', '--name-only', BASE, head).splitlines())
(OUT / 'scope.json').write_text(json.dumps(scope, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
body_path = OUT / 'PR_BODY.md'
if not body_path.exists():
    body_path.write_text('''## 治理元数据

- **PR 类型**: feature
- **任务 ID**: M14-005
- **风险等级**: R2
- **责任人**: @Chengyue-Lu
- **工作流目录**: docs/workstreams/chengyue-lu/M14-CURATED-RELEASE

## 范围与非目标

闭合 source-CI producer/consumer 的实现缺口：develop push 在 CI 内重验实际 squash delta 的治理；在线 observer 核验仓库、workflow、run、attempt、job、check App 的身份和成功状态。同步 PR #78/#79 已接受状态与后续真实 push 验收路径。

## 契约与权威影响

- **共享契约**: yes
- **权威、权限或数据边界**: yes

新增 source governance 只在 develop push 上名为 governance；其他事件使用独立 inactive 名称，保留现有 PR-only governance 门禁。生产端读取唯一 exact merged PR 的当前 metadata，重验 parent→source 与 reviewed/integrated tree 一致；消费端不接受 PR/dispatch rehearsal 或旧 attempt，逐项绑定 GitHub Actions app 15368 和 run check suite，分页不全、重复/缺失/失败/skipped job、rerun 竞态均 fail closed。

## TASKS 状态变更

none。M14-005 保持 BLOCKED；canonical Task identity、状态、依赖、验收不变。Runtime、Schema、Registry、Skill admission、release policy 和 dormant topology 不变。

## 验证证据

M14-005 implementation slice: IMPLEMENTATION_HEAD。
15 个 source-CI fixture / identity matrix / CLI / workflow checks PASS；新增 critical observer line 100% / branch 100%，95/90 与独立正反证据映射已纳入 coverage policy。
在线负例：旧的绿色 develop@0bebafd CI 34939526577 因缺少 governance 被明确拒绝。该 run 不能冒充已完成 source attestation。
Repository 186/0/0；联合 focused、最终 head full/coverage/package/governance 及 Trace 回执见后续更新。

## 剩余风险与后续

首个真实 source_governance job 只有在本 PR 被 R2 接受并合入 develop 后才会运行；当前 PR CI 不能替代那条 protected push 证据。合入后在该 source checkout 调用 observer 并核对 producer receipt，再接 release-only workflow/checks、policy include 与 atomic cutover。具名首发版本/范围决定、fresh ruleset readback、freeze/source-parent、projection/prospective-tree equality、R2 release PR 和 tag/artifact closure 仍需独立闭合。

Observer 每次在线读取 GitHub，输出 JSON 只作证据；最终受保护 release caller 须自己调用在线 observer。仅靠保存的 JSON、PR body、candidate manifest 不授予信任。历史 PR metadata 若被后续改为不兼容内容，producer 重跑可能 fail closed；记录明确它读取的是当前 merged PR body。

## 权威依据

Issue #57、ADR-0021、已接受 PR #78 readiness preparation，以及维护者本轮指令“继续推进M14-005”。本 PR 为 develop-side preparation，不代作 Human first-release decision，不创建发布分支、tag 或真实发布，不改变远端权限。

## 对抗性证据

真实 Git fixture 重验 squash parent、reviewed tree 与实际治理器，拒绝无关联/多关联/未合并/跨仓 PR、错误 parent/tree 和非法治理元数据。API matrix 拒绝跨仓/错 workflow/错 SHA、PR/dispatch run、旧 attempt、非 Actions App、同名伪 check、分页缺口及观察期间 rerun。测试验证 inactive source job 不与 PR governance 共名。

实施细节与合入后步骤：docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/SOURCE_CI.md。Refs #57。
'''.replace('IMPLEMENTATION_HEAD', head), encoding='utf-8', newline='\n')
body = body_path.read_text(encoding='utf-8')
sys.path.insert(0, str(ROOT / '.github/scripts'))
from plan_ci import make_plan, canonical
from check_pr_governance import check_pull_request
repo = 'Chengyue-Lu/research-agent-workbench'
event = {'repository': {'full_name': repo}, 'pull_request': {
    'base': {'ref': 'develop', 'sha': BASE, 'repo': {'full_name': repo}},
    'head': {'ref': 'feature/m14-005-source-ci', 'sha': head, 'repo': {'full_name': repo}},
    'body': body, 'mergeable': True}}
(OUT / 'pr-event.json').write_bytes(canonical(event))
report = check_pull_request(event)
report.emit()
assert not report.has_errors
plan = make_plan(ROOT, base=BASE, head=head, target=head, repository=repo, body=body)
(OUT / 'ci-plan.json').write_bytes(canonical(plan))
print(json.dumps({'head': head, 'plan_id': plan['plan_id'], 'behavioral': plan['behavioral_scope'],
                  'coverage': plan['coverage_scope'], 'package': plan['package_smoke'], 'blocked': plan['blocked_reasons']}))
assert not plan['blocked_reasons']

```
