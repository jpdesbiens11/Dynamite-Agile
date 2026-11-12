"""0.60.97 (D-O-103): the scripts the website serves (curl … | sudo bash) are exactly the reviewed ones of deploy/ --
tools/build_site.py copies them; a hand edit of site/install.* alone would ship unreviewed code to every new server.

    python -m unittest tests.test_install_copies -v
"""
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class InstallCopiesTest(unittest.TestCase):
    def test_site_serves_the_deploy_scripts(self):
        for name in ("install.sh", "install.ps1"):
            self.assertEqual((BASE_DIR / "site" / name).read_bytes(), (BASE_DIR / "deploy" / name).read_bytes(),
                             "site/{0} differs from deploy/{0}: run python3 tools/build_site.py".format(name))


if __name__ == "__main__":
    unittest.main()
