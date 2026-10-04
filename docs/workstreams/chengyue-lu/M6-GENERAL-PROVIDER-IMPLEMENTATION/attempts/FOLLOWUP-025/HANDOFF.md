# FOLLOWUP-025 交接

责任：本窗口RWB开发(3)负责PR131 required CI，RWB开发(2)负责全量CI单test高耗时独立PR。CI code/workflow及新extended测试由Root维护，两个旧Provider测试通过开发2精确提交7d19接入，互斥修改范围及可见传递在私有collaboration档案保留。

日常component确定性四分片及native0.2库存完整性、metadata有界等待见[CI_REPAIR](CI_REPAIR.md)。现行62项消费者为61PASS+1 Windows skip；固定实现提交bdecc98的31项真实普通/extended binding、graph和aggregate组合31/31 PASS、wall344.094秒。完整Git计划45模块/594项collection仅证明库存，原失败及各检查范围见[CHECKS](CHECKS.md)。最终hosted CI仍待当前候选自身核验，不能借旧head绿色。

开发2已通过独立Draft [PR132](https://github.com/Chengyue-Lu/research-agent-workbench/pull/132)交付全量单test优化，两个Provider测试的7d19切片已精确接入本PR；M5独立切片未接入。base3579的旧全量coverage与3.13失败另存，不宣称本轮全量修复或missing case提速。

当前写入不涉及Provider产品/Schema/真实Key/native launcher/真实累计预算。source66历史结果、1744真实累计tokens、M6-010 BLOCKED与后续具名接受保持原范围；没有merge。下一步完成本地文档/治理/仓库收尾并一次推送，再消费最终head必需检查与新的独立审查；PR保持Draft。最终远端回执保存在当前PR body/checks与本地忽略FOLLOWUP-025档案，避免以记录CI结果的新提交替换已检查head。
