# FOLLOWUP-011 检查

本切片修复本地启动准备的进程归属、运行时 callable 身份和等待时长问题，并归档同一 Draft PR128 的当前组件 CI。产品 source `cb3fa4a71972cfc287f79b8dd18437da37bae5b7`保持；这些启动候选仍在本地准备 archive，尚未接入产品入口。M6-009 IN_PROGRESS、M6-010 BLOCKED/NOT_EXECUTABLE，完整 implementation/exact-run/native/history 接受仍 null。

| 检查 | 结果 | 范围 |
|---|---|---|
| 进程树生命周期原型 | 10 fake tests PASS | 旧ed04 factory的有界接口；确认单独终止父进程可能留下子进程，不代表原生Job验证 |
| Windows backend 初版 | 20 fake-FFI tests PASS，0.005s | 旧a1e版本的ABI参数、closed env、HANDLE_LIST、JOB_LIST和资源释放；后继独立审查发现等待余量问题，原结果保留 |
| 独立旧等待反例 | 1个反例断言PASS | guard消耗20秒仍等待120秒，合成清理时刻140秒；这是缺陷复现，不是候选通过 |
| 等待修复 | 39/39 PASS，0.009s | 新factory10/backend20/deadline9；原五项BEFORE FAIL与精确旧源保留，guard后按同一deadline重算/min/floor，不足1ms拒绝 |
| 最终连接层 | 14/14 PASS，0.656s | 强引用身份复验、固定factory/backend pins、guard后复验及捕获entry；四个genuine三模块fake-FFI案例与四个运行时mutation子案例分别保留 |
| 独立修复复验 | 2/2 PASS，0.001s | 复用旧clock反例：耗20秒后实际Wait参数100000ms；耗尽120秒时0Wait。未执行原生方法 |
| 当前head组件CI | 855/855 PASS，0 skip，1288.913s | 同一run37076119255、trigger c78ee4c5，实际merge checkout3422c7ac；installed smoke八步成功11.680s |

最终factory SHA `bef79c801bea1c7dd37283a96a07551c4568ceb394e7c8b3213c7c1ef71f6c4c`，backend SHA `c0c4e4a83d2b8a89afc1e106d71e99790676f7dc0ca34a4dbcbc1dccfe11579d`，connection launcher SHA `f83b33c2aabc5905c515edcf5722a71421330b9e854c31d4603278de0be8c40e`。等待修复owner receipt SHA `e36381399e8b24a6de06ca8efc8f7cd031d5d4f8685a66e8872cdf6fe8081207`，连接层receipt SHA `a7599811c698973d6b11803e04667fa81c8c7824d81d2562beb2f2695fc94a00`。

外层持有独占、非继承、unnamed KILL_ON_CLOSE Job，创建时用JOB_LIST纳入PowerShell parent，并用HANDLE_LIST仅继承三个NUL句柄；没有Start后Assign或parent-only subprocess回退。原009 bridge15e231和010 launcher068保持字节不变，bridge只作为新外层包含的inner，旧launcher不能独立激活。先前bootstrap合同的subprocess.run默认与必须换inner bridge的假设由新connection delta替代，旧文档留作阶段证据。

加载模块的磁盘pins之外，新连接层捕获strong-reference namespace/class/method/code/defaults/kwdefaults及ABI signatures。外部callback返回后再次检查，实际消费捕获的factory entry；method替换、同结构新code对象与signature改写在资源创建前拒绝。stdlib/native/显式FFI/monotonic和可信callback仍属于实际上下文边界，这不是hostile Python或OS证明。原独立review receipt `b0cf268588113c2e95cb72b92e424fba17a29815eebb1a544789d51cb836ae4e`保持两个缺陷结论；后继修复review单独保存。

后继独立修复review receipt SHA `ab5bfbdb630aa27165353d49edfdc3b76c1f31e3d74014508c5d8686f3402439`只认证bef79/c0c4/f83b三个精确源的具体缺陷修复。两项fake-FFI复验由reviewer独立执行，连接层身份修复由reviewer静态核查；不借owner39或root14计数冒称独立重跑。reviewer的receipt表达式写入错误及不完整bytes保留，修正为严格重建并读取核对，不是源码/测试失败。

工厂的120秒wall deadline在Job准备前开始；backend在自己的guard之后重新读取同一remaining callback，等待参数只能缩短，毫秒向下取整。不重建deadline、不使用Job user-mode time替代wall time、不增加cleanup/model grace。正常父进程退出后仍关闭Job，cleanup失败为STOP/unknown，已有持久用量和in-flight预占不得清零。真实Windows支持、嵌套层级、句柄继承、外层异步死亡和实际终止延迟仍需独立原生验证。

当前CI evidence receipt SHA `bc7cce76e5e31c97e8200b1250020d974365e22cf03d0cd29bd3da8a4b78a649`。三个原生ZIP摘要与远端digest一致，实际checkout父提交为base27cbf860/headc78ee4c5；Component job111066354423、CI result111071826848均SUCCESS。plan有65 module entries，native result有72 selection entries、实际records覆盖68 modules，计数不混称。coverage not-collected/diagnostic-only，merge_eligible false，不是full/global coverage或人工审核。旧head5d/1b及失败、取消结果各归原身份，新文档head另核，不手动rerun。

真实API、Key/presence、Provider环境、vault/bridge、native DLL/method/process/Job和实际history/budget claim均0。测试只有显式fake process/clock/FFI，未重复已通过的长kernel。用户成功/失败input+output累计≤10,000,000，精确Flash每request北京18+且当前official idle；unknown钱非阻断、unknown tokens held-STOP，无自动retry/fallback。实际三process-local bootstrap/guard、依赖初始化、ordinary值、唯一history/fresh输出、dated model/window/data及具名接受尚需闭合。M5/A4/Pilot/科学/发布边界保持，未ready/merge。可见Task/messages/stages/失败留档；完整平台导出不可得与metadata缺失capture-gap如实保留，不保存隐藏思考或秘密。
