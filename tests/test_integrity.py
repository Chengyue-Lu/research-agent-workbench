import hashlib
import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_directory


class IntegrityTests(unittest.TestCase):
    def test_directory_hash_uses_host_independent_posix_order(self) -> None:
        payloads = {
            "SKILL.md": b"skill\n",
            "agents/openai.yaml": b"agent\n",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, payload in payloads.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)

            digest = hashlib.sha256()
            for relative in sorted(payloads):
                encoded = relative.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
                digest.update(hashlib.sha256(payloads[relative]).digest())

            self.assertEqual(digest.hexdigest(), hash_directory(root))


if __name__ == "__main__":
    unittest.main()
