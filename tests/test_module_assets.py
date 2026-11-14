"""0.60.100 (D-O-107): a module's scripts are loaded when its tab is first opened, with the modules it requires, at a
versioned address the browser keeps a year -- no longer the ~110 files of every module, revalidated at each sign-in.

- every module that uses a namespace defined by another module's scripts (DA.agile, DA.gt…) names it in REQUIRES,
  otherwise its first screen would break when it is the first tab opened;
- the session manifest gives each file its token, the one the server checks before saying « keep it a year ».
"""
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import auth, db, modules, router, startup, static_cache  # noqa: E402
from core.config import load_config  # noqa: E402

STATIC = BASE_DIR / "static"
DEFINES = re.compile(r"\bDA\.([A-Za-z_]+)\s*=(?!=)")
USES = re.compile(r"\bDA\.([A-Za-z_]+)\b")


def scripts_of(entry):
    return [STATIC / url.lstrip("/") for url in entry.get("scripts", [])]


def core_namespaces():
    """Namespaces the core scripts define themselves (always there, whatever module is loaded)."""
    found = set()
    for path in list((STATIC / "js").glob("*.js")) + list((STATIC / "js" / "tools").glob("*.js")):
        found |= set(DEFINES.findall(path.read_text("utf-8")))
    return found | {"api", "el", "clear", "views", "registerModule", "loadModuleAssets", "prefetchModuleAssets"}


class ManifestTest(unittest.TestCase):
    def test_01_requires_are_real_modules_without_cycle(self):
        keys = {e["key"] for e in modules.MODULE_MANIFEST}
        for key, needs in modules.REQUIRES.items():
            self.assertIn(key, keys)
            for need in needs:
                self.assertIn(need, keys)
                self.assertNotIn(key, modules.REQUIRES.get(need, ()), "cycle {} <-> {}".format(key, need))

    def test_02_every_cross_module_namespace_is_required(self):
        built = [e for e in modules.MODULE_MANIFEST if e["module"] is not None and e.get("scripts")]
        core = core_namespaces()
        owner = {}
        for e in built:
            for path in scripts_of(e):
                for ns in DEFINES.findall(path.read_text("utf-8")):
                    if ns not in core:
                        owner.setdefault(ns, e["key"])
        for e in built:
            needed = set()
            for path in scripts_of(e):
                for ns in USES.findall(path.read_text("utf-8")):
                    if ns in owner and owner[ns] != e["key"]:
                        needed.add(owner[ns])
            missing = needed - set(modules.REQUIRES.get(e["key"], ()))
            self.assertFalse(missing, "{} uses the scripts of {}: add them to core.modules.REQUIRES".format(e["key"], missing))

    def test_03_session_manifest_tokens(self):
        nav = {m["key"]: m for m in modules.nav_manifest()}
        diamond = nav["diamond"]
        self.assertEqual(diamond["requires"], ["agile"])
        self.assertIn("/js/diamond/diamond.js", diamond["scripts"])  # the plain addresses stay (other tests read them)
        for url in diamond["scripts"] + diamond["styles"]:
            entry = static_cache.get(STATIC / url.lstrip("/"))
            self.assertEqual(diamond["v"][url], static_cache.token(entry))
            self.assertRegex(diamond["v"][url], r"^[0-9a-f]{12}$")
        self.assertEqual(nav["about"]["requires"], [])


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = Path(cls.tmp.name)
        cfg = load_config(data_dir)
        cfg["port"] = 0
        db.init_db(data_dir / "s.db", modules.registered_schema(), modules.registered_migrations())
        with db.connect() as conn:
            auth.ensure_initial_admin(conn, data_dir, dev_password="admin")
        startup.run(data_dir, cfg)
        cls.server = router.create_server(cfg, STATIC, data_dir)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:{}".format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def head(self, path):
        try:
            with urllib.request.urlopen(self.url + path) as r:
                return r.status, r.headers["Cache-Control"], r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers["Cache-Control"], e.read()

    def test_01_versioned_address_is_kept_a_year(self):
        url = "/js/diamond/tree.js"
        token = modules.nav_manifest()[[m["key"] for m in modules.nav_manifest()].index("diamond")]["v"][url]
        raw = (STATIC / "js" / "diamond" / "tree.js").read_bytes()
        status, cache, body = self.head(url + "?v=" + token)
        self.assertEqual((status, cache, body), (200, "private, max-age=31536000, immutable", raw))
        self.assertEqual(self.head(url)[1], "no-cache")  # the plain address is revalidated, as before
        self.assertEqual(self.head(url + "?v=000000000000")[1], "no-cache")  # an old token: never kept
        self.assertEqual(self.head(url + "?v=" + token + "&v=x")[1], "no-cache")


if __name__ == "__main__":
    unittest.main()
