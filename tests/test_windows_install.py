"""0.60.10 (D-O-022): a Windows PC as the team's server on a local network -- deploy/install.ps1, the team's certificate
authority (tools/make_team_ca.py), tools/write_config.py, and the Windows path of the installation page."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import config  # noqa: E402

PS1 = BASE_DIR / "deploy" / "install.ps1"


class InstallScriptTest(unittest.TestCase):
    def test_01_powershell_script(self):
        raw = PS1.read_bytes()
        self.assertEqual(raw[:3], b"\xef\xbb\xbf")  # Windows PowerShell 5.1 reads the accents only with a BOM
        text = raw.decode("utf-8-sig")
        self.assertTrue(text.lstrip().startswith("#"))
        self.assertIn("param([string]$Dossier", text)
        for step in range(1, 8):
            self.assertIn('"{}/7 '.format(step), text)
        for needed in ("WindowsBuiltInRole]::Administrator", "Python.Python.3.12", "Git.Git", "make_team_ca.py",
                       "write_config.py", "dev_mode=false", "-Profile Domain, Private", '-UserId "SYSTEM"',
                       "New-ScheduledTaskTrigger -AtStartup", "-RestartCount", "Cert:\\LocalMachine\\Root",
                       "Cert:\\CurrentUser\\Root", "INITIAL_ADMIN_PASSWORD.txt", "$Desinstaller"):
            self.assertIn(needed, text, needed)
        self.assertNotIn("SkipCertificateCheck", text)  # never teach to bypass the certificate
        self.assertNotIn("-Profile Any", text)
        published = (BASE_DIR / "site" / "install.ps1").read_bytes()
        self.assertEqual(published[:3], b"\xef\xbb\xbf")
        self.assertIn(b"https://github.com/jpdesbiens11/Dynamite-Agile.git", published)

    def test_02_every_message_in_both_languages(self):
        """Each T "fr" "en" call carries two strings (D-O-017)."""
        import re
        text = PS1.read_text("utf-8-sig")
        calls = re.findall(r'\(T ("(?:[^"`]|`.)*")\s+("(?:[^"`]|`.)*")\)', text, re.S)
        self.assertGreater(len(calls), 30)
        single = re.findall(r'\(T "(?:[^"`]|`.)*"\)', text)
        self.assertEqual(single, [])


@unittest.skipUnless(shutil.which("openssl"), "openssl needed")
class TeamCaTest(unittest.TestCase):
    def test_03_ca_and_server_certificate(self):
        from tools import make_team_ca
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            self.assertEqual(make_team_ca.main(["--data-dir", str(data), "--name", "atelier", "--ip", "192.168.50.7"]), 0)
            tls = data / "tls"
            for name in ("ca.crt", "ca.key", "server.crt", "server.key", "partage/ca-dynamite.crt"):
                self.assertTrue((tls / name).is_file(), name)
            self.assertFalse((tls / "partage" / "ca.key").exists())  # only the public certificate is shared
            ok = subprocess.run(["openssl", "verify", "-CAfile", str(tls / "ca.crt"), str(tls / "server.crt")],
                                capture_output=True, text=True)
            self.assertIn("OK", ok.stdout)
            san = subprocess.run(["openssl", "x509", "-in", str(tls / "server.crt"), "-noout", "-ext", "subjectAltName"],
                                 capture_output=True, text=True).stdout
            for expected in ("DNS:atelier", "DNS:localhost", "IP Address:192.168.50.7", "IP Address:127.0.0.1"):
                self.assertIn(expected, san)
            ca_before, crt_before = (tls / "ca.crt").read_bytes(), (tls / "server.crt").read_bytes()
            make_team_ca.main(["--data-dir", str(data), "--name", "atelier", "--ip", "192.168.50.7"])
            self.assertEqual((tls / "ca.crt").read_bytes(), ca_before)       # the CA is kept
            self.assertEqual((tls / "server.crt").read_bytes(), crt_before)  # still valid: not renewed
            make_team_ca.main(["--data-dir", str(data), "--name", "atelier", "--ip", "10.0.0.9"])
            self.assertNotEqual((tls / "server.crt").read_bytes(), crt_before)  # a new address: renewed
            self.assertEqual((tls / "ca.crt").read_bytes(), ca_before)


class ConfigTest(unittest.TestCase):
    def test_04_write_config_and_bom(self):
        from tools import write_config
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "config.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"theme_note": "x"}).encode("utf-8"))
            write_config.main(["--data-dir", str(data), "host=0.0.0.0", "port=443", "dev_mode=false", "public_name=atelier"])
            raw = (data / "config.json").read_bytes()
            self.assertNotEqual(raw[:3], b"\xef\xbb\xbf")
            cfg = json.loads(raw)
            self.assertEqual((cfg["host"], cfg["port"], cfg["dev_mode"], cfg["public_name"], cfg["theme_note"]),
                             ("0.0.0.0", 443, False, "atelier", "x"))
            (data / "config.json").write_bytes(b"\xef\xbb\xbf" + raw)  # edited in Notepad: still read
            self.assertEqual(config.load_config(data)["port"], 443)
            with self.assertRaises(SystemExit):
                write_config.main(["--data-dir", str(data), "sans-egal"])


class SiteTest(unittest.TestCase):
    def test_05_windows_path_on_the_site(self):
        for page in ("site/installation.html", "site/en/installation.html"):
            html = (BASE_DIR / page).read_text("utf-8")
            self.assertIn('value="windows"', html, page)
            self.assertIn('data-dest="windows"', html, page)
            self.assertIn("/install.ps1 -OutFile", html, page)
            self.assertIn("Cert:\\CurrentUser\\Root", html, page)
        js = (BASE_DIR / "site" / "installation.html").read_text("utf-8")
        self.assertIn('["online", "windows"]', js)
        for guide in ("site/installer.md", "site/en/installer.md"):
            self.assertIn("install.ps1", (BASE_DIR / guide).read_text("utf-8"), guide)


if __name__ == "__main__":
    unittest.main()
