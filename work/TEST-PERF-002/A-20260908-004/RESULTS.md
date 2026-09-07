# Imported execution aliases in local contracts

Task TEST-PERF-002 revision 16; owner Chengyue-Lu; cross-owner let778750-cpu; R2.

The self-audit reproduced a gap: a function using a module-level subprocess alias
was accepted as a local edit because detached-function analysis lost that alias.
The guard now preserves module/class import and capability-binding context while
stripping unrelated function bodies. Direct imports, from-import aliases, runpy
aliases and assigned execution capabilities retain the conservative graph closure.
An unrelated execution function does not prevent a pure digest-body edit.

A real Git fixture proves the planner restores both behavioral and impact consumer
closure for an aliased execution body. [Focused evidence](checks/summary.json)
records 115 passing tests, critical floors and changed statements/branches 100/100
on implementation `4c04db6cd0a639e367100f3205a732fee041ab9f`.

The consumer fingerprint is refreshed with the additional adversarial tests. New
full dual-Python CI and a fresh pinned witness are required for the updated PR head.
Three-module hosted measurements are refreshed on the repaired implementation;
the unchanged shared before suite continues without duplicate baseline execution.
Formal M4/M14 branches and merge/release authority remain with their owners.
