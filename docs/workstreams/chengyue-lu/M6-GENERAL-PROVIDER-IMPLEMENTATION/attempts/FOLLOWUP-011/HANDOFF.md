# FOLLOWUP-011 Compact Handoff

同一 Draft PR128继续M6-009，产品source cb3fa4a保持。当前c78ee4c5的组件run37076119255已SUCCESS：855 PASS、0skip、1288.913s，installed smoke八步11.680s，实际merge3422c7ac及base27cb/headc78父关系与三个ZIP digest已核。coverage未采集；新文档head须独立观察。

启动链补齐本地Windows Job backend和固定连接层。独立审查发现loaded callable身份漂移、guard后stale wait两个具体缺陷；最终强引用身份复验和同deadline余量重算已修，factory/backend39PASS、连接层14PASS，独立复用旧等待反例2PASS。原五项BEFORE FAIL、140秒反例、初版及原review保持。范围与hash见[检查](CHECKS.md)。

旧bridge15e231只作为外层Job包含的inner，不独立启动旧launcher068。固定新factory/backend在创建时包含parent，关闭唯一Job handle处理剩余进程树；原生Windows支持、实际层级/继承/owner死亡/终止延迟尚未验证。所有测试是fake process/clock/FFI，实际API/Key/presence/Provider环境/vault/bridge/native/history/claim0。

下一步先验证有界、无凭据的原生生命周期，再冻结实际三个process-local可信bootstrap与依赖启动顺序、exe/ordinary/CWD/source/Windows context。完整implementation审核与唯一真实累计history/namespace/DB/anchor、fresh输出、dated官方Flash/idle/data和exact-run接受保持独立；既有Task/guard接口不解释JSON批准，不由hash或测试生成权威。

M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE，实际接受仍null。只精确Flash、每request北京18+且official idle，成功失败input+output累计≤10m；unknown钱非阻断、unknown tokens held-STOP，失败归档/修复/refreeze后fresh Attempt，无自动retry/fallback。未ready/merge，不推进M5/A4/Pilot/科学/发布。共享项目摘要写前重读并保留其他窗口内容；全平台导出capture-gap保留。
