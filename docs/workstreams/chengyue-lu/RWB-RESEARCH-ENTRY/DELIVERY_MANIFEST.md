# 交付文件与检查

**历史交付清单：PR140 `d630f8e174846f4932d05a7a0d69076930b53ee1` 的 65 项离线入口套、零付费 API/生产 Tool 快照。** 以下 hash 和验证事实只定位该次交付；本次新增顶部标签及后续文件不由这些历史 pins 认证。最新结果见 [ROOT_REPORT](chain-proof-002/ROOT_REPORT.md)，[API_RESULTS](chain-proof-002/API_RESULTS.md) 和 [DELIVERY](chain-proof-002/DELIVERY.md) 待 Root 交付并冻结。本文没有提前验证后两份文件存在或 hash。候选尚未合并，资格及科研接受仍各自未完成。

2026-10-07；isolated branch candidate，base d3c4d23206339ebc7f18b5621f3aa5453f96335e。

11个预先声明的source/planning handoff pins一致；137个内部Markdown file targets存在；机器绝对路径0。链接检查不认证网页、anchor语义或科学正确性。最终源码验证：入口65 PASS、原消费者53 PASS、candidate wheel实际安装与CLI2 PASS；原R1～R4限定独立复查闭合。

## 公开定位归一化

完整可见原件在本地ignored `.rwb/entry-archive/originals/`按原仓库路径独占保存；公开通信将机器checkout前缀换为 `.`，并统一LF/清理末尾空白以符合Git文档检查。以下列归一化前/公开版SHA，原消息事实、输出和限制不变；其余文件bytes未改。该原件归档不是生产Attempt或公开发布附件。

| 文件 | 原SHA256 | 公开版SHA256 |
|---|---|---|
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/control/COMMUNICATIONS.md | 2339fffb6b10b8cc92f62f5c428bb2ff7e17eb0e2c001c0c01a26d8995babd71 | d9dd51cc801308851d75a8f3424163fedc52bd4a3886b2e731d270f8b99bce68 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/frontend/COMMUNICATIONS.md | fde81b02ebfb0ad2a264278f47b8cdb4347ae0c22705944e4039b8891e7c24e9 | 60eae2a6677b315207f1d51ef4bfdca04be9f7b25cf1a6a03200a77f5ce00221 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/m12/PLAN.md | e8e0fdbd1e6e261a653d2e8e4d12e200195e421de02ef80c77e6b69b29aff1fc | 9d9ff23c8df69147ffa94f93cd977c552108616f9831eee70204390a6dc29595 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/runtime/COMMUNICATIONS.md | c6db90e6001b11f0317a967a0767a5322ee98899a9286cc2783596f3be45f2ed | da294170d20a9259b0a6db6a96fe6d9c924e9e6e7f80a8a36d68fdf4586ff640 |

## 最终交付 pins

下表排除本manifest自身，避免self-hash循环。后续若仅改PR交付记录，变更文件由新增Git提交固定，未改源码仍按这些pins验证。

| 文件 | SHA256 |
|---|---|
| docs/STATUS.md | 87bc4a372e1132218fcf024e59f834d4a804579915fd979566666105a71ceb8c |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/binding/COMMUNICATIONS.md | 5b9deb4ed6aee27a9e5a1b05fa7d569e567262c33b9876c5f5a072b38d75b0d6 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/binding/HANDOFF.md | 353339b94ca10b1311f9c28512193cde0555e4ad69bcef69f9f4e53e135240b1 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/binding/HANDOFF_JOINT.md | 5d3a15d9b1d4a1788eb579916dcb53efa360b8e3b1d863c1c338b3623a99e969 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/COMMUNICATIONS.md | 9a075f1964e1dabee5b1c523ae36825911ffaf6cc195910b1a80eefe1e93b3f3 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/COMPLETION.md | 1fd5bb92aba17a7a0447d2fa98cf1c322b5758071945606458303c01c7a2d3ae |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/control/COMMUNICATIONS.md | d9dd51cc801308851d75a8f3424163fedc52bd4a3886b2e731d270f8b99bce68 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/control/HANDOFF.md | 93c3c89a312c2ee20305407aad77d3406cedeca07337ac9adf83cb5c9b0b72fe |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/control/HANDOFF_FIX.md | 31c227d97d5a352244cc88433bd544ba868f7b1f8b0aee695c831eed41589bdf |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/frontend/COMMUNICATIONS.md | 60eae2a6677b315207f1d51ef4bfdca04be9f7b25cf1a6a03200a77f5ce00221 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/frontend/PLAN.md | 5e6380a92de3fe07f268ed7ff4cf3791cd264613cfad201b3b8525ebb31d97c9 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/m12/COMMUNICATIONS.md | d7512cd599fc9c694d05dba462ff97671fe1881d7219ac229418d19a366860f9 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/m12/PLAN.md | 9d9ff23c8df69147ffa94f93cd977c552108616f9831eee70204390a6dc29595 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/README.md | a9cf67dcddfd05aba4698a20b173220b6f16c985134a214ae6461446c8b657b7 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/review/FIX_VERIFICATION.md | 9b0475913fe99bcb667922188c47d34654f848e48449d8300a837b89919c0602 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/review/RUNTIME_REVIEW.md | bacd275a44a689ee3e7be857b0906c438cce2ededed38d0f8ffe04aed2f26db0 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/RISK_LEDGER.md | 972dbc1c469a0987a25e335a78abad1bb82cf4d50581a32cb7e410d23b2c13d2 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/runtime/COMMUNICATIONS.md | da294170d20a9259b0a6db6a96fe6d9c924e9e6e7f80a8a36d68fdf4586ff640 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/runtime/HANDOFF.md | deec5f7313d7f5d7b884da79ff53f48280870a37d8df4866a0536d8ce614fa73 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/TASK_PACKET.md | a8a4b8a71f539fdb044f0fb2eb049c11e9ac3afc77888af439f26da07c41ffe2 |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/USAGE.md | bd7f4a1e765d4ba83966b3b005999a39f4ef28df0b251327114351e375e71e0d |
| docs/workstreams/chengyue-lu/RWB-RESEARCH-ENTRY/WORKLOG.md | 4a0635c7b99ade7fc6fb4b630dff25d8cfccd73ddbd9b799ffbcbc66d5808291 |
| src/research_workbench/cli.py | 890318b2fcb8e0f1f6c6094ccb0237a9aba8cc0606537b78ab63455ac114aab9 |
| src/research_workbench/entry/__init__.py | 6239337b7a08a722819d9f028c642ad19569a47e85e4e138972fdcc2d19411f3 |
| src/research_workbench/entry/binding.py | c8b5811d9d5eca08affac3292658c989ff3f001aafd14176de9fca3fd0dc991c |
| src/research_workbench/entry/driver.py | c1a140cf1f0720db79fe73fc7273a809125466ee3ef33cc99bf34ec01711e4b8 |
| src/research_workbench/entry/executor.py | 6f1924bbef590df87b3f7539e2e30c3c7f7deafb3b739fd3b9302682e03d7987 |
| src/research_workbench/entry/guide.py | 8bfcf458acfaf6900e421ea0cacd10e6da783267080ba7652b7b7e7487e8b4c9 |
| src/research_workbench/entry/intake.py | b76021ee66fd39e579ab05533f546b639afb07ceefb98317f48ff35dd978fbcf |
| src/research_workbench/entry/roles.py | 083d2b619053fcce77df0b9896fc5eeba407e82d5fabce86e9f7a4bc417b017d |
| src/research_workbench/entry/state.py | 15faeba426aa7d701918c3a8243332c51dc082afafdeecf64ab290439233b262 |
| src/research_workbench/entry/workflow.py | d2d1f64971da72df808d084274156a70b0d640a572467e77f99f913c38979c92 |
| tests/test_entry_binding.py | 31d24156850735927503b89e9974128d67738f4de36da19c9d2497b54643c80a |
| tests/test_entry_cli.py | db39b19625e7e15a5a1dd1f4e06675f0d479588218005a567146b65f6151b2fa |
| tests/test_entry_control_chain.py | ca26e5df83c2fe59190d640eac4d136046e564641db20274eba7f1affbe44930 |
| tests/test_entry_driver.py | 0093ab715a804a2a3992f3da5dedf7d383f9bb08d834312dc9ecc0cbbc590857 |
| tests/test_entry_executor.py | 143e356977fea48b058dbed42c31ea1ea8c5c3c4cb8446ed654792829588809c |
| tests/test_entry_guide.py | 2a3c6c7b23f5919c0fd5f1a379ad33e66b1fdc971d12934ab26c64805211d583 |
| tests/test_entry_intake.py | 46285080eea141f953522682518da7fd1997e6bc8121a6dbebf7dc603e015700 |
| tests/test_entry_roles.py | bdad0c1ffe161b19624b3f39080fefeac0b769d716564652c5542f2bb932a5a6 |
| tests/test_entry_state.py | 8d5f6b68658290f96dd4eaa139979bab821e88b2ee97d763b9bd0380b1d992f4 |
| tests/test_entry_workflow.py | e6833e3118c3fd736da44afda1f81149472b5e11c05d415eb7bfdd98e72e2288 |
