# Phase C Runner-owned Bounded Gate（M10-003）

状态：bounded implementation candidate；machine Gate 已实现，Human semantic review、R2 closeout 与
Phase C closeout 仍独立 pending。

## 1. 权威数据流

```text
source manifest（仓库 exact path + byte SHA）
  → runner 校验 kind / identity / byte pin / whole closure
  → 按原仓库相对路径复制到一次性 staging root
  → runner 生成 actor manifest（不含 source manifest 或 oracle）
  → 新 Python 进程消费 actor manifest + staged exact closure
  → actor 输出 compact answer + exact case-data read/write surface + declared trusted runtime/schema surface
  → actor 退出后 runner 首次读取 private oracle
  → runner 生成 manifest/oracle/closure hash-bound machine Gate report
```

调用者不能提交现成 report 冒充 Gate；CLI 只接受两组 source manifest/private oracle，并拒绝覆盖已有
output。两案必须恰好覆盖 `evidence-synthesis` 与 `simulation-negative`，case identity 不得重复。

## 2. Runner-owned closure

source manifest 对每个文档声明 alias、kind、durable identity/revision 与 repository-relative fileRef。
runner 从同一次 byte read 计算 SHA、解析文档并验证 kind/identity，然后保持原相对路径 staging，使
Attempt file pin、Task pin 和 Method Trace closure 继续按实际文件字节闭合。重复 alias、identity、path，
路径逃逸、错误 pin/kind/identity 以及把 private oracle 列入 closure 都在 actor 启动前阻断。

每案 report 固定 source-manifest SHA、private-oracle SHA 与按 alias 排序的 exact input-closure digest；
顶层 `gate_input_sha256` 再绑定两案 pins。相同 Gate ID 下的替换 manifest/oracle 因而不会与 owner 审过的
输入不可区分。oracle SHA 仍只在 actor 退出后首次读取并计算。

## 3. Fresh actor 与读取隔离

actor 在独立 PID 中启动，不扫描目录。进程内 audit hook 只允许读取 runner 生成的 actor manifest、
staged allowlist 和作为可信运行时代码的版本化 Schema 目录；只允许写 fresh output。未列明文件读取、
输入覆盖和其他写入均抛出 `PermissionError`。report 分开记录 exact case-data read surface 与 declared
trusted runtime/schema surface；前者可逐文件证明，后者是显式信任边界，不冒充完整进程读取审计。

这是有界的进程内 Python 文件访问策略，不声称 OS sandbox、容器隔离、网络隔离或对恶意原生扩展的
安全证明。它证明当前固定 consumer 没有读取 session/oracle/unlisted data，也没有覆盖 staged input。

## 4. Oracle 最小强度

private oracle 不进入 actor 参数、manifest、环境变量或 staging；runner 只在 actor 成功退出后读取。
oracle 必须精确检查 active State、Method Trace、Mode/Action、Evidence/Human Decision refs、open/
invalidated items、Known Failure、candidate classification、actual-binding gap、固定 authority limits 与 exact
case-data read surface。predicate 词表由 runner 固定；simulation-negative 案必须证明 known-failed path 被避免，
推荐路径不重复该 Failure。

## 5. 不构成的结论

machine PASS 只证明两份 canonical fixture 在当前 exact closure 上满足结构和隔离不变量。report Schema
固定以下边界：不证明 reviewer reconstruction，不证明科学正确性，不完成 Human semantic review 或 R2
closeout，不完成 Phase C closeout，也不批准 Topic 5 recovery/salvage/multi-Agent 实现。
