# CHAIN-DEV4-008：pure codec Profile limits 漏接

Root真复测31 Profile tests：30项中原其余通过/1 dependency skip，新增256 Profile→257 pure wire回归实际FAIL（没有抛出）。根因是wire _Profile没有保留implementation.limits，codec preflight ProviderCapabilities漏传limits。ConfiguredProvider另有preflight，但纯encoder也需要原Profile实际上限，不能更换测试为宽松通过。

Profile bounded implementation worker；required-Skills=[]；ownership仅 src/research_workbench/adapters/models/wire_codecs.py 与本目录DEV4_WIRE_HANDOFF/COMMUNICATIONS；黄毅接口/路诚钺预算，未正式接受。读域本Packet、007 handoff、wire_codecs _Profile/_profile/_validate_request、base preflight与port ProviderCapabilities limits接口、上述31测试失败的新用例。预算5分钟1轮。

最小修复：_Profile保留已有validated implementation.limits的不可变mapping，pure preflight snapshot传原Profile limits。不得放宽profile/metadata/continuation/Tool/权限/Source binding或修改Registry/fixture旧bytes。使用已验证limits，不拿本轮1024作为全部Profile默认。不改Key/transport请求映射或计费语义。

你不独自在代码库，保留他人内容。仅静态AST/compile，禁止测试/API/Tool/Key/账/安装/Git/primary memory；Root唯一测试者。第一次真实Attempt已关闭：intake成功7388tokens，随后Root Supply枚举拼写拒绝，累计63002held0。新Attempt待这个明确接点修复及Root检查后开始。给sourcehash和静态handoff后立即停。
