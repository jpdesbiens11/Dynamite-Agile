"""0.60.71 (D-O-077): behind Traefik, the new address and the old ones it keeps serving (links already shared) --
install_traefik.sh run against stub docker / getent / systemctl in a scratch folder: nothing of the host is touched."""
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STUBS = {
    "docker": """#!/bin/sh
case "$*" in
  "compose version") exit 0 ;;
  ps\\ --format*) echo "traefik-1 traefik:v3" ;;
  *"join .Args"*) echo "--certificatesresolvers.mytls.acme.email=x --entrypoints.websecure.address=:443" ;;
  *"compose -f"*" logs"*) echo "Listening on 0.0.0.0:8080" ;;
  *"compose -f"*" ps -q"*) echo abc ;;
  *".State.Status"*) echo running ;;
esac
exit 0
""",
    "getent": "#!/bin/sh\necho \"203.0.113.10 $2\"\n",
    "systemctl": "#!/bin/sh\nexit 0\n",
}


class TraefikAliasesTest(unittest.TestCase):
    def run_install(self, *args):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        (tmp / "app" / "deploy").mkdir(parents=True)
        shutil.copy(BASE / "deploy" / "install_traefik.sh", tmp / "app" / "deploy")
        (tmp / "bin").mkdir()
        for name, body in STUBS.items():
            path = tmp / "bin" / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        env = dict(os.environ, PATH="{}:/usr/bin:/bin".format(tmp / "bin"), DA_STACK_DIR=str(tmp / "stack"))
        done = subprocess.run(["bash", str(tmp / "app" / "deploy" / "install_traefik.sh"), *args], env=env,
                              capture_output=True, text=True, timeout=60)
        compose = tmp / "stack" / "docker-compose.yml"
        return done, compose.read_text() if compose.exists() else ""

    def test_new_address_and_old_one_kept(self):
        done, compose = self.run_install("demo.dynamiteagile.ca", "dynamite.srv1.hstgr.cloud")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("rule=Host(`demo.dynamiteagile.ca`) || Host(`dynamite.srv1.hstgr.cloud`)", compose)
        self.assertIn("certresolver=mytls", compose)

    def test_one_address_as_before(self):
        done, compose = self.run_install("demo.dynamiteagile.ca")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("rule=Host(`demo.dynamiteagile.ca`)\n", compose)

    def test_extra_address_without_dns_refused(self):  # 0.60.78 (D-O-084): checked like the main address
        stub = STUBS["getent"]
        STUBS["getent"] = '#!/bin/sh\ncase "$2" in *nodns*) exit 2 ;; esac\necho "203.0.113.10 $2"\n'
        try:
            done, compose = self.run_install("demo.dynamiteagile.ca", "nodns.exemple.ca")
        finally:
            STUBS["getent"] = stub
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("nodns.exemple.ca", done.stdout + done.stderr)
        self.assertEqual(compose, "")

    def test_bad_extra_address_refused(self):
        done, compose = self.run_install("demo.dynamiteagile.ca", "x`) || PathPrefix(`/")
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(compose, "")

    def test_install_sh_passes_the_extra_addresses(self):
        script = (BASE / "deploy" / "install.sh").read_text(encoding="utf-8")
        self.assertIn('ALSO="${*:3}"', script)
        self.assertIn('install_traefik.sh" "$DOMAIN" ${ALSO:-}', script)


if __name__ == "__main__":
    unittest.main()
