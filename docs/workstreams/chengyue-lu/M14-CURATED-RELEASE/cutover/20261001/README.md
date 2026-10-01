# Complete cutover review data

Owner: Chengyue-Lu. These are complete authenticated maintainer API observations,
captured for independent review of PR116 candidate830 / source1ac / policy1.5.0.
Technical readiness review5376540205 is accepted; complete cutover acceptance is pending.

All four raw rulesets include bypass_actors; their canonical SHA256 values match
manifest.json. The .http files retain the corresponding GET response status, selected safe headers and
JSON body; no authentication header or credential is captured. Both effective-rule
views, the exact before/cutover payloads and source-CI observation are included.
candidate-binding.json binds the candidate, body, pins and original CI attempts.
evidence-index.json pins every included file's SHA256 and byte length.

The proposed change is one PUT to existing main hard ruleset23305460, replacing
only required contexts with release preflight (3.11)/(3.13), both App15368.
Hard bypass remains empty; strict, merge methods, review/Code Owner/stale/last-push,
conversation and force/delete protections are retained. This data does not apply it.

From a clean accepted source1ac checkout, treat this audit commit as Git data:
load the four JSON objects, run accepted release_ruleset_cutover.validate_ruleset
with each exact branch/layer/ID, compare canonical digest to manifest.json, then
derive payloads(main-hard) and compare the full before/cutover JSON and hashes.
Compare effective views with the exact union of hard/review rules. Re-read every
currently visible live field and declare any unobservable field explicitly.

GitHub limits bypass_actors visibility to callers with write access to the ruleset:
https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset
The repository is personally owned; its owner and collaborators have different rights.
The reviewer is a collaborator and cannot independently see bypass_actors in the API.
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository
These files make the complete observations downloadable and independently recomputable;
they do not pretend to grant that account independent live visibility. Permission
changes require an explicit maintainer decision. Complete cutover R2 acceptance,
named one-update authorization, fresh pre-write checks and post-write verification
remain required. PR116 stays Draft; no rule update, main merge, tag or publication.

This M14 audit branch does not change frozen product source or candidate bytes and
does not need to be merged into develop before the cutover review. Existing frozen
attempts and primary develop/config/AGENTS are preserved.

Run the included byte/closure/raw-field/payload check from the clean accepted source:

```shell
python /path/to/audit/verify-evidence.py --source-root /path/to/clean-source1ac
```

Inputs: [index](evidence-index.json), [candidate binding](candidate-binding.json),
[complete cutover payload](cutover.json). The script makes no remote request and does
not certify live fields absent from the reviewer account; that limitation must be
explicit in the complete-cutover acceptance.
