# Latest-base and M14/M5 propagation validation

TEST-PERF-002; owner Chengyue-Lu; R2; Skills []. User request: rebase PR101 to
latest develop, validate M14-005 and M5-007 propagation and stop at Ready for
review. Base `97d3b3d3141419b34ad47e0f42d9f01d0dfbd535`, local implementation `7c2bc7fc627be7b9dde02fbdc2f879d062fdee6d`. No merge authority.

Ten original PR101 patches were replayed without conflicts, preserving their
nonoverlapping blobs and A001-A005. The accepted H4b and CI policies were combined
without lowering global90, critical95/90 or changed100/100. An independent review
found that the inherited fingerprint no longer matched the H4b inventory. Only
that field was refreshed, with432 input records independently verified; the
original conservative fallback and its cause remain recorded.

Both Python versions passed32 scoped composition tests (29 plus3 nonoverlapping
checks). These are local rebase checks; exact final-head hosted obligations remain
separate. M14/M5 reports distinguish original whole implementation changes, small
source edits, tests and shared inputs. Plans and inventories were reconstructed
without running broad suites solely to count them. Bounded fault probes retain
their actual executions separately from collection evidence.

The three diagnostic contracts in PR101 do not authorize M14 or M5 business
boundaries. Their remaining opaque execution paths and associated smoke/coverage
obligations are explicit follow-up work; this archive does not claim production
business reduction or use the earlier diagnostic timing ratio for these modules.
No business owner branch, source implementation, release/tag/main or quality
threshold was changed by this verification.

- [Summary](checks/summary.json), [manifest](checks/manifest.json), [raw evidence](checks/raw-evidence.zip)

The ZIP retains `m14-probes/REPORT.md`, `m5-probes/REPORT.md` and
`rebase-independent/REPORT.md` with their original adjacent raw evidence.

The earlier official36253369103 and three-pair36253369146 retain their original
d4e94e2/base5bf identities in the preceding work. They are not proofs for this
new base. Trace capture below honestly records prior capture gaps. The next
steps are final committed-head checks, one current-target hosted execution and
Ready for review; formal approval and merge remain external.
