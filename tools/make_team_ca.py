"""HTTPS on a team's local network (0.60.10, D-O-022): the team's own certificate authority and the certificate of the
Windows PC that hosts Dynamite | Agile. Used by deploy/install.ps1; works on Linux and macOS too.

The server refuses to listen on the network without HTTPS (D-B-090, fail closed). A team without a domain name nor an
IT department signs its own certificate: this tool creates, in data/tls/ (never in git),
  ca.crt / ca.key   « Dynamite Équipe Root CA (<PC>) », 10 years -- ca.key never leaves the server PC;
  server.crt / .key the certificate of this PC (its name, name.local, its LAN addresses), 397 days -- the browsers' maximum;
and copies ca.crt to data/tls/partage/ca-dynamite.crt: each computer of the team trusts it once (deploy/install.ps1 prints
how). Run again: the CA is kept, the server certificate is renewed when it expires within 30 days, misses an address
of the PC, or with --renew. openssl comes with Git for Windows (C:\\Program Files\\Git\\usr\\bin\\openssl.exe).

    python tools/make_team_ca.py --data-dir C:\\DynamiteAgile\\data [--name atelier] [--ip 192.168.1.23] [--renew]
"""
import argparse
import datetime as dt
import shutil
import socket
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CURVE = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes"]
WINDOWS_OPENSSL = [Path(r"C:\Program Files\Git\usr\bin\openssl.exe"), Path(r"C:\Program Files\Git\mingw64\bin\openssl.exe"),
                   Path(r"C:\Program Files (x86)\Git\usr\bin\openssl.exe")]


def find_openssl():
    found = shutil.which("openssl")
    if found:
        return found
    for candidate in WINDOWS_OPENSSL + [Path(sys.prefix) / "Library" / "bin" / "openssl.exe"]:
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("openssl introuvable. Correctif : installez Git pour Windows (winget install -e --id Git.Git), "
                     "qui le fournit, puis relancez.")


def run(openssl, *args):
    try:
        return subprocess.run([openssl] + [str(a) for a in args], check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as exc:
        raise SystemExit("openssl a échoué : " + (exc.stderr or "").strip())


def lan_addresses():
    """IPv4 addresses of this PC on its networks (no loopback)."""
    found = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(info[4][0])
    except OSError:
        pass
    try:  # the address used to reach the network, even when the name does not resolve to it
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # TEST-NET: nothing is sent
            found.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ip for ip in found if not ip.startswith("127."))


def make_ca(openssl, out, host):
    if (out / "ca.crt").exists() and (out / "ca.key").exists():
        return False
    run(openssl, "req", "-x509", *CURVE, "-keyout", out / "ca.key", "-out", out / "ca.crt", "-days", 3650,
        "-subj", "/O=Dynamite Equipe/CN=Dynamite Equipe Root CA ({})".format(host),
        "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0", "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    return True


def server_needs(openssl, out, names, ips, renew):
    crt = out / "server.crt"
    if renew or not crt.exists() or not (out / "server.key").exists():
        return True
    text = run(openssl, "x509", "-in", crt, "-noout", "-enddate", "-ext", "subjectAltName")
    end = next((l.split("=", 1)[1] for l in text.splitlines() if l.startswith("notAfter=")), "")
    try:
        left = dt.datetime.strptime(end.strip(), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc) - dt.datetime.now(dt.timezone.utc)
    except ValueError:
        return True
    return left.days < 30 or any(("DNS:" + n) not in text for n in names) or any(("IP Address:" + ip) not in text for ip in ips)


def make_server(openssl, out, names, ips):
    san = ",".join(["DNS:" + n for n in names] + ["IP:" + ip for ip in ips])
    ext = out / "server.ext"
    ext.write_text("\n".join(["basicConstraints=critical,CA:FALSE", "keyUsage=critical,digitalSignature",
                              "extendedKeyUsage=serverAuth", "subjectAltName=" + san]) + "\n", encoding="ascii")
    run(openssl, "req", *CURVE, "-keyout", out / "server.key", "-out", out / "server.csr", "-subj", "/O=Dynamite Equipe/CN=" + names[0])
    run(openssl, "x509", "-req", "-in", out / "server.csr", "-CA", out / "ca.crt", "-CAkey", out / "ca.key", "-CAcreateserial",
        "-out", out / "server.crt", "-days", 397, "-sha256", "-extfile", ext)
    (out / "server.csr").unlink()
    ext.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Team CA and server certificate for HTTPS on a local network.")
    parser.add_argument("--data-dir", type=Path, default=BASE / "data")
    parser.add_argument("--name", action="append", default=[], help="Extra DNS name of the server PC (repeatable).")
    parser.add_argument("--ip", action="append", default=[], help="Extra IP address of the server PC (repeatable).")
    parser.add_argument("--renew", action="store_true", help="Renew the server certificate now.")
    args = parser.parse_args(argv)
    out = args.data_dir / "tls"
    out.mkdir(parents=True, exist_ok=True)
    host = socket.gethostname().split(".")[0]
    names = list(dict.fromkeys([host.lower(), host.lower() + ".local", "localhost"] + [n.lower() for n in args.name]))
    ips = list(dict.fromkeys(lan_addresses() + args.ip + ["127.0.0.1"]))
    openssl = find_openssl()
    created = make_ca(openssl, out, host)
    renewed = server_needs(openssl, out, names, ips, args.renew or created)
    if renewed:
        make_server(openssl, out, names, ips)
    share = out / "partage"
    share.mkdir(exist_ok=True)
    shutil.copyfile(out / "ca.crt", share / "ca-dynamite.crt")
    print("CA : {}".format("créée" if created else "conservée"))
    print("Certificat du serveur : {} ({})".format("créé" if renewed else "valide", ", ".join(names + ips)))
    print("À importer sur chaque poste de l'équipe : {}".format(share / "ca-dynamite.crt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
