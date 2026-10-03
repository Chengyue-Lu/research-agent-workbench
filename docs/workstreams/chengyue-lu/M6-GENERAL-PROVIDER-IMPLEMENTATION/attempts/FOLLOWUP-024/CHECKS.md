# FOLLOWUP-024 检查

固定审查base3579e67/head92bb870，run32fe11c6-728b-4858-8334-90641ec73cc2两项P2已独立复现。
先加入五个回归方法：修复前5tests产生4errors（关闭账本、metadata故障、纯文本及Markdown子案例），
原REGRESSIONS_BEFORE日志保留；修复后5/5 PASS，1.620秒。

普通未扩限120秒路径在账本关闭时返回report1.0/blocked/accounting-failed/accounting=null；
零guard/credential presence/credential resolve/HTTP，失败报告通过既有Schema并可排他归档。
metadata读取的普通存储故障也返回脱敏block，已可读账本事实不归零，私密错误原文不进入报告。

用户授权原文经独立字节读取验证portable路径、SHA256及既有262144字节上限；
prefix/decision仍单独执行canonical JSON校验。UTF-8文本与CRLF、Markdown分别成功append grant、
重开账本和cold reader，原25events/anchor前缀/三组历史/1205tokens保持；篡改原文及
非canonical prefix/decision不追加事件。仍不认证引用文本的人类身份或授予具名接受。

Python3.11.16的budget/deadline/transport/driver/report78/78 PASS，21.357秒；
repository validation=202/errors=0/warnings=0。新source-bound消费者检查单独归档，
未以普通unit代替源码闭包或沿用历史live资格。真实Provider/Key/原生launcher/累计预算操作均0。
私有原始日志和receipt在项目忽略归档，平台完整未导出事件仍保留capture-gap边界。

修复后 source-bound extended/report消费者6/6 PASS，325.393秒；新grant-helper图成员及guard后
漂移拒绝、扩限后完整fake三调用/cold publication、已收响应后账本关闭或最终snapshot故障
保留用量等现行绑定谓词均通过。与上述78项合计84项Provider离线回归。
documentation/public-surface24/24 PASS，0.896秒；原环境只补用独立doc-deps，未改原installed环境。
本次源码及Schema/Task边界在提交前复核，原source66 live报告保持历史范围；不宣称新源码已live接受。
