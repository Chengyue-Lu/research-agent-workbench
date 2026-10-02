# FOLLOWUP-004 检查

产品 source `9efe7541ab43bf4ff61836ae2cac6968ec4bee17`，base develop27cbf860；Python3.11.16。
同一 Draft PR128，未接受、ready、merge或真实调用。最终证据提交只新增本 CHECKS/HANDOFF，
产品/测试/Schema/CI/policy bytes 与上述source逐项等价；不称 fresh full。

| 检查 | 实际结果 | 范围 |
|---|---|---|
| source focused | 83/83 PASS，327.557s，0fail/error/skip | driver、bound integration、reports、source closure、catalog及CI登记 |
| fresh installed focused | 39/39 PASS，312.704s，0fail/error/skip | actual wheel-loaded driver7、reporting15、source-closure17；非editable新venv |
| installed smoke/pip | 8/8 PASS，11.484s；pipcheck PASS | 独立安装进程，resources/schema/init/negative等既有八探针 |
| wheel byte checks | 177资源、119tracked模块全等 | wheel与source Git blobs逐项核验；SHA256 `0e134500dc0c161c71f898c2bbd3317043eae1275db801cc6456655838db956c` |
| repository | validated202 / errors0 / warnings0 | examples及registry |
| docs/public | 24/24 PASS | 内部链接、公开入口与所有权 |
| local R2 governance | PASS | 当前声明、基线/head、任务定义及风险/权威/negative要求；不代表approval |
| actual policy DAG | PASS | 所有既有policy对象/history；本轮policy不改，无export/release |
| CI selection | 63模块、unknown paths0 | 新binding test及reportSchema直接消费者均选中；非执行结果 |

原head982c43e hosted run37048711145：831项中一项ERROR，实际wheel加载路径与checkout/src不同。
原raw日志留存。测试改用实际loaded module root，错误位置负例保持；本轮fresh installed17/17
验证修复，不重标旧CI绿色。新head远端CI独立观察。本轮未运行整个63模块组件/full/global coverage。

独立复核发现并修复两个P2：bound失败报告仍先读取实时source；输入上界未关联当次Attempt。
前者直接消费frozen refs，并在send guard触发helper/source-reader故障时保留报告；后者记录实际
start_attempt ordinal，核对该轮reservation count/local order/input/output，不借前轮历史。
明确failedAttempt1及freshAttempt2、false config/graph/source/policy/input和串用Attempt反例均通过。
配置漂移、无body/自定义delegate/归档漂移在Attempt或credential前拒绝；send guard后helper漂移
在intent前拒绝，未发送预占释放。所有HTTP/key对象均合成；真实API/Key/presence/bridge0。

owner最终report15/15 PASS（5.392s）；独立source复核两个P2 CLOSED，非human Task接受。
初版6bound tests/59legacy和原Python3.14 diagnostic保留，本轮以最终3.11精确文件为准；不声称3.14支持。
平台完整事件导出不可得，capture gap如实保留，不记录真实密钥或隐藏思考。

机器路径及私有receipt仅在本地archive保存；PR以本检查和Git记录为审查入口。
