"""Development certificates for HTTPS and mTLS (core lot v0.24, D-B-090) -- NEVER for production.

Creates in data/tls/ (never in git) a development CA, a server certificate and, on request, client certificates
(.p12 to import in Windows / the browser), with the `openssl` command line (Anaconda ships it in Library/bin).
In production, the certificates come from your organisation (or a public CA such as Let's Encrypt): deploy/TLS.md.

    python tools/make_dev_ca.py                        CA + server certificate (localhost, 127.0.0.1, this computer)
    python tools/make_dev_ca.py --name dynamite-dev.local   + an extra DNS name of the server
    python tools/make_dev_ca.py --ip 192.168.1.23      + an IP address of the server (lancer_dev.py reseau does it)
    python tools/make_dev_ca.py --client jp.desbiens   + a client certificate (mTLS) jp.desbiens.p12
    python tools/make_dev_ca.py --write-config         + data/config.json: tls_cert / tls_key (and tls_client_ca)

Then trust data/tls/ca.crt on the test computer (Windows: certmgr.msc → Autorités de certification racines de
confiance → Importer) and open https://localhost:8080.
"""
import argparse
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CURVE = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes"]


def find_openssl():
    found = shutil.which("openssl")
    if found:
        return found
    for candidate in (Path(sys.prefix) / "Library" / "bin" / "openssl.exe", Path(sys.prefix) / "bin" / "openssl"):
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("openssl introuvable. Sous Anaconda, lancez ce script depuis l'Anaconda Prompt.")


def run(openssl, *args):
    subprocess.run([openssl] + [str(a) for a in args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def make_ca(openssl, out):
    if (out / "ca.crt").exists():
        return False
    run(openssl, "req", "-x509", *CURVE, "-keyout", out / "ca.key", "-out", out / "ca.crt", "-days", 1825,
        "-subj", "/O=Dynamite DEV/CN=Dynamite Dev Root CA (development only)",
        "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    return True


def sign(openssl, out, stem, subject, extensions, days):
    ext = out / (stem + ".ext")
    ext.write_text("\n".join(extensions) + "\n", encoding="ascii")
    run(openssl, "req", *CURVE, "-keyout", out / (stem + ".key"), "-out", out / (stem + ".csr"), "-subj", subject)
    run(openssl, "x509", "-req", "-in", out / (stem + ".csr"), "-CA", out / "ca.crt", "-CAkey", out / "ca.key",
        "-CAcreateserial", "-out", out / (stem + ".crt"), "-days", days, "-sha256", "-extfile", ext)
    (out / (stem + ".csr")).unlink()
    ext.unlink()


def make_server(openssl, out, names, ips=()):
    dns = sorted({"localhost", socket.gethostname()} | set(names))
    addresses = ["127.0.0.1", "::1"] + [ip for ip in ips if ip not in ("127.0.0.1", "::1")]
    san = ",".join(["DNS:" + n for n in dns] + ["IP:" + ip for ip in addresses])
    sign(openssl, out, "server", "/O=Dynamite DEV/CN=" + dns[0],
         ["basicConstraints=critical,CA:FALSE", "keyUsage=critical,digitalSignature", "extendedKeyUsage=serverAuth",
          "subjectAltName=" + san], 397)  # 397 days: the browsers' maximum for a server certificate
    return dns


def make_client(openssl, out, username, password):
    stem = "client-" + username
    sign(openssl, out, stem, "/O=Dynamite DEV/CN=" + username,
         ["basicConstraints=critical,CA:FALSE", "keyUsage=critical,digitalSignature", "extendedKeyUsage=clientAuth"], 397)
    run(openssl, "pkcs12", "-export", "-in", out / (stem + ".crt"), "-inkey", out / (stem + ".key"),
        "-certfile", out / "ca.crt", "-name", username + " (Dynamite dev)", "-out", out / (username + ".p12"),
        "-passout", "pass:" + password)
    return out / (username + ".p12")


def write_config(data_dir, with_client_ca):
    path = data_dir / "config.json"
    cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cfg.update({"tls_cert": "tls/server.crt", "tls_key": "tls/server.key"})
    if with_client_ca:
        cfg["tls_client_ca"] = "tls/ca.crt"  # optional mode: tls_client_required stays as it is (false by default)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-dir", type=Path, default=BASE / "data")
    parser.add_argument("--name", action="append", default=[], help="extra DNS name of the server (repeatable)")
    parser.add_argument("--ip", action="append", default=[], help="extra IP address of the server (repeatable)")
    parser.add_argument("--client", action="append", default=[], help="username of a client certificate (repeatable)")
    parser.add_argument("--p12-password", default="dynamitedev", help="password of the .p12 files (default: dynamitedev)")
    parser.add_argument("--write-config", action="store_true", help="write tls_cert / tls_key in data/config.json")
    args = parser.parse_args(argv)
    openssl = find_openssl()
    out = args.data_dir / "tls"
    out.mkdir(parents=True, exist_ok=True)
    try:
        created = make_ca(openssl, out)
        dns = make_server(openssl, out, args.name, args.ip)
        p12 = [make_client(openssl, out, user, args.p12_password) for user in args.client]
    except subprocess.CalledProcessError as exc:
        raise SystemExit("openssl a échoué : " + (exc.stderr or b"").decode(errors="replace").strip())
    print(("CA de développement créée : " if created else "CA de développement existante : ") + str(out / "ca.crt"))
    print("Certificat serveur : " + str(out / "server.crt") + "  (" + ", ".join(dns) + ")")
    for path in p12:
        print("Certificat client  : " + str(path) + "  (mot de passe : " + args.p12_password + ")")
    if args.write_config:
        print("Configuration mise à jour : " + str(write_config(args.data_dir, bool(args.client))))
    else:
        print('Dans data/config.json : "tls_cert": "tls/server.crt", "tls_key": "tls/server.key"'
              + (', "tls_client_ca": "tls/ca.crt"' if args.client else ""))
    print("Faites confiance à ca.crt sur le poste de test, puis ouvrez https://localhost:<port>. Jamais en production.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
