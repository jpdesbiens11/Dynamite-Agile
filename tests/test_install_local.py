"""0.60.44 (D-O-053): the installation page asks where the tool runs (online, local Linux server, Windows PC) and which
computer the person types on; install.sh --local serves the team's network with the team's own certificate authority."""
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class InstallLocalTest(unittest.TestCase):
    def test_01_install_sh_local_mode(self):
        sh = (BASE_DIR / "deploy" / "install.sh").read_text("utf-8")
        self.assertEqual(subprocess.run(["bash", "-n", str(BASE_DIR / "deploy" / "install.sh")]).returncode, 0)
        self.assertIn('elif [ "${1:-}" = "--local" ]; then MODE=local', sh)
        self.assertIn("tools/make_team_ca.py", sh)
        for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"):
            self.assertIn(net, sh)  # the team's network only
        self.assertIn('elif mode == "local"', sh)
        self.assertIn("openssl", sh.split("say \"2/7")[0])

    def test_02_pages_follow_place_and_computer(self):
        subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build_site.py")], check=True, capture_output=True)
        for rel in ("site/installation.html", "site/en/installation.html"):
            page = (BASE_DIR / rel).read_text("utf-8")
            for part in ('data-dest="local"', 'data-pc="win"', 'data-pc="mac"', 'data-pc="linux"', 'data-pc="unix"',
                         "--local", "icacls", "chmod 600", "hstgr.cloud", "security add-trusted-cert", "update-ca-certificates"):
                self.assertIn(part, page, (rel, part))
            steps = {d: page.count('data-dest="{}"'.format(d)) for d in ("online", "local", "windows")}
            self.assertEqual(steps, {"online": 4, "local": 4, "windows": 4})  # step 1 + four steps = 5 for each place


if __name__ == "__main__":
    unittest.main()
