# CHAIN-ROLE-019：child职责澄清静态审查

2026-10-08；Agent Profile targeted_reviewer；required-Skills=[]。本组只静态审查声明源码/测试段与写两份审查工件。结论：**未发现新增实质P级风险**。本次职责说明排除了“禁再委派等于禁执行自身Task”“初始空child_results就是缺口”的误解，未在所读代码中扩大权限、跨父Task边界或取消真实缺口判断。源码明确性不保证模型下一次一定遵循；不把本审查作为API/科学/Source/Human接受。

## 接点与必要条件

| 接点 | 静态核对 |
| --- | --- |
| roles.py:30–44，_COMMON | 明确Task/human limits；inputs[].text描述仅针对实际读Task.input_refs并核SHA/UTF-8/可选revision的snapshot，refs列表不是已经读文件，arbitrary caller_context不获此资格。复用已有snapshot无需二次open不授额外读、自动遍历或写权限；missing input/authority/budget/capability仍须stop。 |
| roles.py:70–81，child baseline | 明确执行本child Task而非父Task；delegation=false仅禁止创建新child，初始空child_results正常。complete仅在bounded work done时且delegations为空；actual missing Task prerequisite仍blocked，不能靠该说明吞Task明确要求的输入/资格/权限等缺口。末句仍禁止改project truth或越Task再委派。 |
| workflow.py:25–33、63–73 | RoleInvocation明确role/task/context与预算，默认instructions是CONTROL_INSTRUCTIONS。完整control JSON仅允许complete/delegate/blocked/human-review；非delegate不带delegations，child结果是actual observations不是authority；complete是拟议Task处置，非Human/Claim/Skill/Release接受。generic consume-child-results要求与child初始无结果说明可共存：不存在的初始列表不产生必备子结果，已返回的真实结果不得忽略。 |
| workflow.py:270–316、334–380 | invoke深拷贝本node/context并保留whole-chain和node的跨Session预算。node_run初始送phase plan-or-execute+child_results=[]；只有decision delegate进入子Task校验/执行，359给child自己的Task和role child；347仍调用既有_validate_child，不绕过父边界。367–377保存child disposition/limitations/实际execution status/usage/artifact与receipt refs；378用父node fresh invocation消费outcomes，不把child blocked机械改写complete。 |
| executor.py:52–85、103–115 | validated Bundle/View中的frozen Task必须与invocation.task exact一致，阻止Task替换。builder只传当前context与invocation.instructions；role使用invocation.role，不把child调用变成main或载入父私有聊天。已有selected Supply前置仅作context说明、不grant。 |

“blocked only for an actual missing Task prerequisite”应结合_COMMON的missing authority/budget/capability和Task约束理解；它不能证明某Task已经满足。若具体Task明确要求未提供的前序结果，这仍是actual missing prerequisite，不因一般初始[]说明免除。此处没有新增Core语义、资格对象、权限或Task完成验收捷径。

## 新增测试的实际断言范围

只读tests/test_entry_roles.py两新增用例：

- 59–83：实际request payload.inputs与同一source bytes的text/SHA一致，input_snapshot_sha256绑定request user text、baseline_sha256绑定system文本；所有角色baseline含“已读snapshot”和“不扩大读取/仅payload.inputs”说明。
- 89–100：用role child、明确delegation false/depth0/parallel0、phase初始/empty child_results生成请求，断言payload中的delegation false/[]、input text、baseline不禁止自身执行和metadata.entry_role=child。

测试正文提供本次Role request assembly/说明条件的窄consumer证据。本组未运行它们；它们不证明模型真实输出会从blocked改成complete，也不覆盖所有真实Task缺口、Tool行为或科学质量。Root反馈14roles+Guide PASS 9.295s是Root执行结果，不冒充本组验证。

## 旧运行与资格边界

Root提供Attempt13实际6 API full route完成、Tool1/child1/main回接/checkpoint/Guide COMPLETE unchanged、累计207671/held0/13closed32HTTP及13 receipts/两Toolproof冷PASS，全部为其可见反馈；本组没有读取原请求/response/账/实际project或Receipt，不独立核这些数字。

旧Attempt child输出blocked因误解delegation=false/初始[]，fresh main消费实际观测后complete，不能因本次baseline更新改写旧原件或宣称旧child disposition本来complete。整体工程route completed/实际receipt结构验收与child模型处置、Task科学正确、Human接受须各保留范围。结构通过不等于科学正确。新baseline的实际模型遵循仍由Root后续授权验证，未据静态文本宣称全链资格接受。

## 实际读域与source pins

符号定位后窄读roles.py _COMMON/ROLE_BASELINES30–98；workflow CONTROL_INSTRUCTIONS25–33、RoleInvocation63–75、invoke270–316和node_run334–393（包含必要预算/结果消费）；executor52–85、103–115的binding/装配；tests/test_entry_roles.py44–112（两新增用例59–83/89–100及相邻现有request/隔离断言）。一次批量输出截断，RoleInvocation/node_run与必要invoke消费者已窄读补齐。source hash固定整个文件bytes，不表示全文解释性阅读。未扩大至其他源码/测试/实际材料或运行目录。

| Repo-relative source | SHA-256 |
| --- | --- |
| src/research_workbench/entry/roles.py | 17cdf60f91a67eedb030e98c9b8d5c7a23586c8d16498e54a65bf0ccc2a4de11 |
| src/research_workbench/entry/workflow.py | 5b70ed862c22a46535581bcbd407e3034ff8c1edfd52d74a8de6a0f30c6e2f5e |
| src/research_workbench/entry/executor.py | 0a068d3b579646f56ddeece27dc38c0febd38a45309cb13231263642cf684f15 |
| tests/test_entry_roles.py | e0d2b8c27afee06664a76cc036ea07915af5bba8f5b9c5bf5a18a9ca80d11660 |

可见Packet/回传见[ROLE_COMMUNICATIONS.md](ROLE_COMMUNICATIONS.md)。仅文档静态引用存在性/hash检查，无source修改、测试/API/Tool/Key/账/actualproject/Git/记忆/再委派；Root唯一执行测试。源码/行为已清楚，落盘SHA后停止。

## CHAIN-PUBLISH-021：pending publication接点窄审（2026-10-08）

Agent Profile targeted_reviewer；required-Skills=[]；只静态读声明源码/新增断言，追加本报告/通信。本次新增publication说明未发现扩大权限或用selected Supply自证actual的路径；发现一项已有Driver contract预派发门槛的P2残余，须限定“bad contract preprovider拒绝”的结论。

### [P2] 非空但非法类型的 output_contract 不在当前Driver构造期拒绝

定位：entry/driver.py:155–158只检查 `if not output_contract`。truthy非字符串（如True或非空对象）以及纯空白字符串会通过；之后369作为artifact.contract原样输出。executor.py:85–86将binding.output_contract原样放入pending context，112–113同一值送Driver。不能据这段源码声称这些malformed contract在Provider前已经拒绝；派发和消耗可能先发生，后续schema/closeout才失败。

这是旧Driver门槛残余，不是本次context授了权限。最小修复：在Driver构造期先要求output_contract为非空白str（不创造新contract Registry或改变Core语义），并补counterexample证明ModelProvider requests为0。若“bad contract”仅指None/空字符串，当前158确在Provider前拒绝；完整Task输出contract的语义匹配未在本次限定读域闭合，不能额外承诺任意非空未匹配名字都派发前拒绝。

### 已核安全/实际consumer接点

- executor.py:52–71通过validated Bundle/View与frozen_task==invocation.task，pending publication取trusted factory的实际调用binding.output_path/output_contract（82–88），后续options112–113送同一execute_role_slice参数。context由plain(invocation.context)复制，接着直接赋保留键，所以同名不可信值被整条可信记录覆盖，不merge permission_grant/publication_complete真值。publisher=SessionExecutionDriver描述当前将调用的确定类，status=pending与两个False界限明确；并非已发布证据或actual Provider/Supply结论。
- 新record不取View selected Supply作为发布成功证明。实际Provider观察仍由Driver._observe/_check_use254–258独立检查；publish record只说明待尝试的路径/contract，不能代替Host/Trace/实际output hash/Receipt。
- roles.py:30–57 的_COMMON明确仅在存在该record时交Driver尝试发布、subject既有admission/I/O；不是权限或completed publication。无file-write Tool本身不阻止返回受限文本，仍需真实Receipt才声称成功，实际权限/I/O失败必须停止。无record不推定Driver发布，Guide独立只读、intake自身compiler。Supply ref/Tool name/capability identity属不同类型，字符串不同本身既不授权限亦不定失败；仍交既有admission检查，未忽略真正identity/权限差异。
- Driver._scope_path79–87依据有效View permission roots与root containment拒越界/只读，execute_role_slice407–417还拒已存在/与archive保留文件碰撞；均在Provider前。440–445构造Driver后455调用Host，再运行Session。实际输出由Driver362–369在最终响应存在时独占open('x')写文件、hash与Trace revision/artifact，故“模型需要写Tool才能返回report”与现有发布职责不同。输出存在亦不独立证明complete：361完成状态和Host/receipt仍另判，失败Session也可保留观测输出。

### 新增断言与未覆盖范围

test_entry_executor.py:59–96正例断言captured actual request publication与binding路径/contract一致、publisher/pending/False边界、实际output文件/Receipt存在（72–79），Task completion仍False（80）；Guide payload无publication/caller_context且文件集不变（94–96）。test_entry_roles.py:85–101断言无写Tool仍可生成request、pending/real Receipt/I/O stop/conditional说明、常规无context时无record；127–134验证intake自身compiler与context=None。

本轮这两个文件的新增断言未实际注入同名forged invocation.context来证明覆盖，也未加入invalidpath/malformedcontract的counterexample；覆盖行为本身已在executor75–88静态确认，path拒绝已在Driver确认，不把缺测试说成当前存在权限绕过。建议Root补窄反例：forged同名键被actual binder整条覆盖；越界path/空与非str/空白contract全部Provider requests=0、无成功Receipt；新条件不会给Guide/intake附record。禁止从正例断言存在推断这些负例已PASS。

### 读域/source pins与验证限制

实际窄读executor52–123、roles_COMMON30–59、Driver63–98/148–172/254–273/354–378/401–461的路径/contract/发布consumer，tests/test_entry_executor.py40–121相关setup/positive/Guide段与函数索引、test_entry_roles.py85–102/126–135；批量输出截断后补关键Driver及测试段。原报告尾部仅用于追加。没有实际账/运行原件读取，也未运行任何产品或测试。

| Repo-relative source | 本次SHA-256 |
| --- | --- |
| src/research_workbench/entry/executor.py | 39c4507cd93607eddd0177e5aff4599fd1f0913088e90a595c48a420d56bfe3f |
| src/research_workbench/entry/roles.py | 8aefb70782c8b091fe7f75305b6c38f0ee4a4a3971621135a55614f63cf5fbd9 |
| src/research_workbench/entry/driver.py | 9f1beba886947509bbd2ce77a1acc8b9191d1d37461eb6a500cc225b542130aa |
| tests/test_entry_executor.py | fdf6eeaf437c47363f52d06fb5b963ff5c86bc94ef71e4389a5aea3f7b5228c0 |
| tests/test_entry_roles.py | 3ceb75b0d3cc10c19e9cca6d958962da11574d81d668ce4acd0d30f5c2f40afd |

Root A14 main Tool成功但误判无写Tool、实际Driver已负责发布，累计221998/held0/14closed35HTTP、14Receipt/3Tool冷PASS等只作Root反馈，见通信原文；本组未读/复验对应原件。本次新说明不能回写旧模型观测。最终entry套仍在跑，无已完成结果，不提前写PASS。仅静态引用/hash，无source写入/测试/API/Tool/Key/账/Git/actualproject/记忆/再委派。structural pass不等于科学正确/Source/Human接受。落盘后停止。

### Root范围确认：本轮chosen contract与既有通用caller边界

Root随后明确：本轮actual binding使用已选Task/View的deterministic-check-report；badpath与empty/falsy contract在Driver preprovider拒绝，其他truthy/non-string/未匹配contract仅由Host required_outputs事后核对。后者是Root给出的既有路径说明，本组未扩大读域去审Host。

因此上项P2保留为已指出的通用public输入门槛边界，**不作为021新增publication说明的阻断，不要求本轮扩矩阵或改代码**；本轮使用的明确有效contract未暴露该反例。不得把chosen valid contract的本轮结果推广成“所有bad contract均preprovider拒绝”，也不能把pending/subject-existing-checks当发布保证。正式后续caller通用化可另行收窄该输入。此范围限定与原观测均保留，最终source套仍由Root运行，尚无新的PASS反馈。
