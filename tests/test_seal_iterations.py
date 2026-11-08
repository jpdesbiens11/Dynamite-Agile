"""0.60.88 (D-O-094): the iteration count of a seal came from the package itself; a forged SEAL.json asking for
billions of PBKDF2 rounds held the server while the import checked it. Only the count the platform writes is accepted.

    python -m unittest tests.test_seal_iterations -v
"""
import json
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import seal  # noqa: E402
from core.errors import ApiError  # noqa: E402

PHRASE = "quatre mots bien longs"


class SealIterationsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "paquet.zip"
        seal.write(self.path, "data", [("data.json", b'{"ok": 1}')], PHRASE, {"author": "JP"})

    def test_a_package_of_the_platform_opens(self):
        z, manifest = seal.open_sealed(self.path, PHRASE, "data", "Données")
        z.close()
        self.assertEqual(manifest["format"], "data")

    def test_forged_iteration_count_refused_at_once(self):
        with zipfile.ZipFile(self.path) as z:
            members = {n: z.read(n) for n in z.namelist()}
        forged = json.loads(members[seal.SEAL_FILE])
        forged["iterations"] = 10 ** 10
        members[seal.SEAL_FILE] = json.dumps(forged).encode()
        with zipfile.ZipFile(self.path, "w") as z:
            for name, data in members.items():
                z.writestr(name, data)
        started = time.time()
        with self.assertRaises(ApiError) as caught:
            seal.open_sealed(self.path, PHRASE, "data", "Données")
        self.assertEqual(caught.exception.status, 403)
        self.assertLess(time.time() - started, 5)


if __name__ == "__main__":
    unittest.main()
