# FOLLOWUP-022 检查

本次为离线候选，真实API、Credential Manager 与真实预算写入均为0。
集中回归173/173 PASS（Python3.12.10，26.422秒）：ledger/journal/anchor/transport/driver/report、
扩限/deadline及CI路由。source-bound extended Attempt4、失败/未知accounting、冷读与扩限/时限组合
22/22 PASS（293.947秒）；该轮在最后transport观察字段修复之前，最终组合复验另行记录。

最终source-bound extended Attempt4/cold reader/writer、deadline、transport、docs/public组合
53/53 PASS（Python3.12.10，323.937秒）。包含最后entry观察分离、未grant360执行零调用拒绝、
closed后的bound report1.2和三份已收响应时accounting不可得。source/config/Schema source closure
真实派生，但urllib/凭据及临时预算是合成，不能外推当前Windows入口或真实Provider等待性能。
本次未采集full/全局coverage/新安装wheel/原生Windows全链或账单，远端CI由当前head独立执行。

作者扩限回归11/11 PASS，3.160秒：prefix/header/meta/identity不改、explicit reopen pin、Attempt4–10、
第11组拒绝、type/decision/stale/active/held拒绝、checkpoint中断STOP、容量拒绝与累计计数重算。
原独立review REQUEST_CHANGES 两项P2：累计计数清零仍过验；第一份fake响应后关闭journal丢失报告。
修复分别重算完整调用计数/序号/held/remaining，以及在执行前冻结已验证grant metadata供终态报告使用。

修复后独立review targeted PASS（receipt `7d00700713c27731c042ac7f4543b4cc68a3fdf69d77f4fe1adf1c380d62992f`）。
其追加反例是durable entry写失败漏记运行时delegate观察；现将entry_observed与entry_recorded分开，
closed后的单响应保留input5/output2、response1/entry1/Tool0与blocked/accounting-failed，
accounting不可得且资格false。持久结算仍只允许entry_recorded，不凭观察补写成功。原review不覆盖。

初始 deadline 回归中的两项fixture失败保留，原因是将实例send替换成普通函数违反bound-method约束；
修正为子类方法后六项PASS。初始source-bound集中测试0tests/1ERROR为另一作者并发修改reader，
loaded/source bytes不一致；冻结后重新验证，不能把该拒绝当通过。

本地明细保存在项目忽略归档 `.rwb/m6-general-prototype/followup-022/`：作者source freeze、
FOCUSED_005、独立review-001、EXTENDED_BINDING_001/002与Root可见事件/最终回执。
历史真实结果由 [PR #130](https://github.com/Chengyue-Lu/research-agent-workbench/pull/130) 单独留档。
可得瞬时失败和消息保留；平台未导出的完整工具事件与compaction前部分原文为明确capture gap。
Agent/CI通过不是具名人类审核、实际账本迁移、安装/Windows live验收或科学判断。
