# Historical Skill closeout source bytes

The two M11-007 proof archives pin source bytes from pre-squash implementation commits.
Those commits are not ancestors of develop and do not exist in a normal fresh clone.

`sources.zip` retains only the source blobs named by those existing proofs, keyed by their
original SHA-256 plus `.txt`. Both replay tests always read these offline bytes and still
verify every original proof hash. They never execute or extract the historical source.
Current installed validators continue to replay the unchanged archived cases; the rejected
one-stage candidate remains rejected under the current contract.

`INDEX.json` records the original proof hashes, historical commit/path/blob identities and
snapshot sizes. At capture, every byte was read from the named Git commit and independently
matched against the already-frozen proof hash. The old archives are unchanged. This snapshot
does not claim that the old commit is present in a fresh clone or that historical code is current.

ZIP timestamps/order are deterministic. These files are test-only data and remain outside the
curated release allowlist and packaged runtime resources.
