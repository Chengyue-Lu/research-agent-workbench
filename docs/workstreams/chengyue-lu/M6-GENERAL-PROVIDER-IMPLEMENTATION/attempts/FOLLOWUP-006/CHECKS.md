# FOLLOWUP-006 检查

产品 source `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`，develop base27cbf860，Python3.11.16。
本轮修复预算 intent 持久化后的发送检查窗口；同一 Draft PR128，未代填接受或合并。
后续证据提交只新增本 CHECKS/HANDOFF，产品及测试字节与上述 source 相同。

| 检查 | 实际结果 | 范围 |
|---|---|---|
| 旧实现反例 | 5/5 FAIL；root fake-only 复现 | delayed intent 跨 deadline、guard 拒绝、timeout 过期、model/body 漂移；真实网络0 |
| owner transport | 17/17 PASS，0.800s | 修复后直接发送边界；不能释放已持久化 intent 的预占 |
| root source focused | 64/64 PASS，375.030s，0fail/error/skip | transport、driver、bound integration、source closure |
| fresh installed focused | 41/41 PASS，369.195s，0fail/error/skip | transport17、bound integration7、source closure17；独立非 editable 新 venv |
| installed smoke/pip | 8/8 PASS，11.828s；pipcheck PASS | 既有安装探针，源码目录外运行 |
| wheel byte equality | 177资源 /119 tracked模块全等 | 对照 source Git blobs；SHA256 `a0d1b6fc2726ae6c4f82683df0dd05096489626717bc169996cb9126bd344d03` |
| repository | validated202 / errors0 / warnings0 | examples、registry |
| independent source review | 范围内无阻断 | 只读复核；owner测试与root集成证据分别归属，不等于human接受 |
| actual policy DAG | PASS | 原policy/history不变，无export、release或tag动作 |
| preparation binding | 80模块cold/actual匹配 | 新安装产物的config/profile/manifest/graph；仅离线实例观察 |

`persist_send_intent` 完成后再次检查既有 `send` guard、请求体和剩余 deadline，并重新裁剪
timeout。guard 可在同一个 send stage 重复调用；Provider/HTTP 调用次数没有因此增加。
拒绝时保留 durable intent 与全部 token 预占，不伪造 HTTP entry，不改成 before-send 零消耗。
已有 driver 的 uncertain-failure 路径保留不确定事实并阻止后续调用；无自动 retry/fallback。
caller guard 诱发的 helper 漂移拒绝与原无绑定路径保持。

先前 exact headaa2466d hosted component37053620400 已 SUCCESS：843项、1213.932s；
governance37053621136 SUCCESS。这些是旧head结果，不覆盖本轮新head CI；旧982安装路径ERROR
仍留存。未运行本轮完整组件、full suite或global coverage；CI选择不是执行结果。
docs/public和localR2治理由最终提交的本地回执记录，具名审批独立。

FOLLOWUP-005 原 source9efe754 的非执行准备包、官方实体/时间窗、Windows/helper静态观察及
delayed-intent反例保持原样；本轮重新冻结source/config/80模块绑定并链接原观察时间。
26个直接source/Schema引用再次与新安装和Git字节核对；原OS/helper库存没有冒充新运行观察。
staging journal 为独立 offline-only namespace，禁止用于真实累计预算。

真实API/Key/presence/bridge0。M6-009 IN_PROGRESS、M6-010 BLOCKED、NOT_EXECUTABLE。
完整implementation、输入预占依据、逐请求time/authorization guard与clock、child argv/sink/
inherited environment、唯一真实累计历史与fresh输出、dated exact-run/data边界仍待冻结/接受。
产品拒绝窗口的修复不代表Windows、socket发送、账户serving revision、远端strict或账单认证。

用户成功/失败input+output累计≤10,000,000，精确Flash，每request北京18+及官方idle；unknown
金额非阻断，unknown tokens保留预占并STOP。每Attempt≤3call/1pureTool/256output/120秒，
至多3个分别修复/refreeze的fresh Attempts。M5/A4/Pilot/科研/发布权威独立。
完整平台事件导出不可得，capture gap保留；机器路径、原始日志和私有receipt仅本地保存。
