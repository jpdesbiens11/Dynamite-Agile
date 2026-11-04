"""0.60.17 (D-O-029): installation behind Traefik -- install.sh --traefik hands over to install_traefik.sh, which
changes nothing of the host but its own container (no firewall, no Traefik setting) and trusts only Docker networks."""
import subprocess
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


class TraefikInstallTest(unittest.TestCase):
    def test_01_scripts(self):
        main = (BASE_DIR / "deploy" / "install.sh").read_text("utf-8")
        self.assertIn('elif [ "${1:-}" = "--traefik" ]; then MODE=traefik', main)
        self.assertIn('exec bash "$APP_DIR/deploy/install_traefik.sh" "$DOMAIN"', main)
        self.assertIn("iproute2", main)  # « ss » is missing on some images
        script = (BASE_DIR / "deploy" / "install_traefik.sh").read_text("utf-8")
        for needed in ("traefik.enable=true", "tls.certresolver=$RESOLVER", "loadbalancer.server.port=8080",
                       '"trusted_proxies": ["172.16.0.0/12", "192.168.0.0/16"]', '"dev_mode": False', "Listening on",
                       "INITIAL_ADMIN_PASSWORD.txt", "image: python:3.12-slim"):
            self.assertIn(needed, script, needed)
        for forbidden in ("ufw", "docker stop", "/docker/traefik", "ports:"):  # never touch the host's other applications
            self.assertNotIn(forbidden, script, forbidden)
        for path in ("deploy/install.sh", "deploy/install_traefik.sh"):
            self.assertEqual(subprocess.run(["bash", "-n", str(BASE_DIR / path)]).returncode, 0, path)

    def test_02_site(self):
        for page in ("site/installation.html", "site/en/installation.html"):
            self.assertIn("--traefik dynamite.srvXXXX.hstgr.cloud", (BASE_DIR / page).read_text("utf-8"), page)
        self.assertIn("--traefik", (BASE_DIR / "site" / "install.sh").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
