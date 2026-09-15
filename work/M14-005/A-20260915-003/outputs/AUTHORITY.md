# Authority and capture boundary

Chengyue-Lu instructed: “继续推进M14-005”. Prior PR #78 accepted MIT/readiness preparation;
PR #79 accepted the independent review-exception mechanism. This slice implements source-CI preparation
under ADR-0021. It does not create a named first-release decision or authorize merge of its own new PR.

An initial fixture assertion compared six expected gh arguments with a seven-element slice; it was corrected.
A live API probe showed the repository endpoint rejects a trailing slash; the transport now emits the canonical
repository path and has a regression check. Final focused/native observer checks pass. Early transient outputs
were not all retained; the capture-gap declarations remain explicit.
