# Durable hosted coverage artifacts

Task TEST-PERF-002; owner Chengyue-Lu. These lossless copies accompany the sealed
[validation archive](../../A-20260908-003/RESULTS.md) so GitHub artifact expiry does
not remove the original coverage measurements. The formal PR head is 4399400;
the before/after measurements have the exact conditional bases recorded there.

MANIFEST.json records the original and compressed SHA-256 values plus run IDs.
Each gzip stream decompresses to the exact uploaded coverage.json bytes, with no
field filtering or normalization. For example, from the repository root:

```python
import gzip
from pathlib import Path
root = Path("work/TEST-PERF-002/hosted-artifacts/4399400")
Path("coverage.json").write_bytes(gzip.decompress((root / "formal-pr-coverage.json.gz").read_bytes()))
```

The uncompressed formal artifact can be checked with check_coverage_policy.py and
the archived coverage-test-results.json using the policy at the exact PR head.
