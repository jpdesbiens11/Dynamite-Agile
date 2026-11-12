"""0.60.97 (D-O-103): the files of data/ that hold a secret are private from the moment they exist.

    python -m unittest tests.test_secret_files -v
"""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import mail  # noqa: E402

POSIX = os.name == "posix"


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


@unittest.skipUnless(POSIX, "file modes are POSIX")
class MailFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = os.umask(0o022)  # the usual umask: a plain write would give 0644
        self.addCleanup(os.umask, self.old)

    def test_mail_json_is_0600(self):
        mail._save(self.tmp.name, dict(mail.DEFAULTS, password="app-password-16ch"))
        self.assertEqual(mode(Path(self.tmp.name) / "mail.json"), 0o600)

    def test_created_0600_not_chmod_after(self):
        """Without any chmod, the file is already 0600: the password is never in a 0644 file, even briefly."""
        real_chmod = os.chmod
        os.chmod = lambda *a, **k: None
        try:
            mail._save(self.tmp.name, dict(mail.DEFAULTS, password="app-password-16ch"))
        finally:
            os.chmod = real_chmod
        self.assertEqual(mode(Path(self.tmp.name) / "mail.json"), 0o600)

    def test_stale_temp_file_made_private(self):
        """A mail.tmp left 0644 by an older version is made 0600 before the password goes in."""
        stale = Path(self.tmp.name) / "mail.tmp"
        stale.write_text("{}", encoding="utf-8")
        os.chmod(stale, 0o644)
        mail._save(self.tmp.name, dict(mail.DEFAULTS, password="app-password-16ch"))
        self.assertEqual(mode(Path(self.tmp.name) / "mail.json"), 0o600)
        self.assertEqual(mail.load(self.tmp.name)["password"], "app-password-16ch")


@unittest.skipUnless(POSIX, "file modes are POSIX")
class DataDirTest(unittest.TestCase):
    def test_data_dir_made_private_at_start(self):
        """data/ (database, backups, mail.json, TLS key) is 0700: files written 0644 below stay out of reach."""
        import app_dynamite_agile as app
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            os.chmod(data, 0o755)
            app.make_private(data)
            self.assertEqual(mode(data), 0o700)
            app.make_private(data)  # idempotent
            self.assertEqual(mode(data), 0o700)


if __name__ == "__main__":
    unittest.main()
