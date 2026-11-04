/* Admin → Sécurité réseau (core lot v0.24, D-B-090): what protects the client/server exchange, read from the server
   (GET /api/admin/transport) -- HTTPS, TLS version, certificate and its expiry, mTLS, session binding, HSTS -- plus
   the network layers of the hosting. Read-only: the settings live in data/config.json (deploy/TLS.md). */
(function () {
  "use strict";
  const { api, el, badge, table } = DA;

  const MTLS = {
    off: ["Désactivé", "neutral", "Aucun certificat client demandé. S'active avec « tls_client_ca » dès que la PKI de l'IT est prête."],
    optional: ["Optionnel", "warn", "Le certificat client est vérifié s'il est présenté (phase pilote). Passer à « tls_client_required »: true ensuite."],
    required: ["Obligatoire", "ok", "Sans certificat client valide de votre autorité, la connexion est refusée avant même la page de connexion."],
  };
  const LAYERS = [  // network layers, owned by IT (FONDATIONS §6)
    ["VPN", "WireGuard ou IPsec IKEv2, avec MFA ; chiffre jusqu'à la passerelle seulement"],
    ["Segmentation", "VLAN dédié au serveur ; le LAN n'est pas une zone de confiance (Zero Trust)"],
    ["Firewall", "Allow-list : port HTTPS seulement, depuis les adresses de l'équipe"],
    ["802.1X", "Authentification des ports filaires et du Wi-Fi : un appareil inconnu n'entre pas sur le réseau"],
    ["PKI", "Certificat serveur ≤ 1 an, root CA poussée par GPO ; certificats clients (autoenrollment ou carte à puce), CRL"],
    ["Post-quantique", "X25519MLKEM768 par défaut si l'OpenSSL du serveur Linux est ≥ 3.5 (« harvest now, decrypt later »)"],
  ];

  function row(label, value, note) {
    return el("tr", null, el("th", { scope: "row" }, label), el("td", null, value), el("td", { class: "muted" }, note || ""));
  }

  function alerts(s) {
    const out = [];
    const days = s.server_cert.days_left;
    if (!s.https) out.push(["off", "HTTP sans TLS : les échanges sont lisibles sur le réseau. Acceptable seulement en développement ou sur 127.0.0.1."]);
    if (days != null && days < 0) out.push(["off", "Le certificat serveur est expiré depuis le " + s.server_cert.not_after + " : les navigateurs refusent la connexion."]);
    else if (days != null && days <= s.expiry_warn_days) out.push(["warn", "Le certificat serveur expire dans " + days + " jour(s) (" + s.server_cert.not_after + ") : demander le renouvellement à l'IT."]);
    if (s.https && s.dev_mode) out.push(["warn", "Mode développement : HSTS n'est pas envoyé. Passer « dev_mode » à false en production."]);
    return out;
  }

  DA.adminTransport = {
    async render(body) {
      const s = await api.get("/api/admin/transport");
      const c = s.connection || {};
      const cert = s.server_cert || {};
      const days = cert.days_left;
      const [mtlsLabel, mtlsKind, mtlsNote] = MTLS[s.mtls] || MTLS.off;
      body.append(el("p", { class: "muted", "data-new": "0.46.0-admin-transport" }, "Ce qui protège l'échange entre les navigateurs et le "
        + "serveur. Lecture seule : les réglages sont dans data/config.json, décrits dans deploy/TLS.md (guide d'installation)."));
      alerts(s).forEach(([kind, text]) => body.append(el("p", { class: "tr-alert tr-" + kind, role: "status" }, badge(kind === "off" ? "Risque" : "À faire", kind), " ", text)));
      body.append(el("h2", null, "Protocole d'échange"), table(["", "État", "Détail"], [
        row("HTTPS", badge(s.https ? "Actif" : "Inactif", s.https ? "ok" : "off"), s.https ? "Toute la plateforme est servie en TLS." : "Indiquer « tls_cert » et « tls_key »."),
        row("Version minimum", s.min_version, s.min_version === "TLS 1.3" ? "AEAD, ECDHE : forward secrecy" : "Repli 1.2 : ECDHE + AES-GCM / ChaCha20 seulement"),
        row("Cette connexion", s.https ? (c.version || "?") + " · " + (c.cipher || "?") + (c.bits ? " (" + c.bits + " bits)" : "") : "HTTP clair", ""),
        row("Certificat serveur", cert.subject || "—", cert.issuer ? "Émis par " + cert.issuer + (cert.san && cert.san.length ? " · SAN : " + cert.san.join(", ") : "") : ""),
        row("Expiration", days == null ? "—" : badge(cert.not_after + " · " + days + " j", days < 0 ? "off" : days <= s.expiry_warn_days ? "warn" : "ok"), "Alerte à " + s.expiry_warn_days + " jours"),
        row("HSTS", badge(s.hsts ? "Actif" : "Inactif", s.hsts ? "ok" : "neutral"), "Le navigateur n'accepte plus jamais ce serveur en HTTP"),
        row("Cookie de session", s.cookie, "HttpOnly, SameSite=Strict" + (s.https ? ", Secure (préfixe __Host-)" : "")),
        row("Redirection HTTP", s.redirect_port ? "Port " + s.redirect_port + " → HTTPS" : "Aucune", "Le port HTTP ne sert jamais de contenu"),
        s.lan_share ? row("Partage réseau (dev)", badge("Actif", "warn"), (s.lan_allow.length ? "Postes permis : " + s.lan_allow.join(", ")
          : "Réseaux privés et sous-réseau de ce poste") + " · admin / admin sur ce poste seulement (Lancer_dev_reseau.bat)") : null,
        row("OpenSSL", s.openssl, s.pq_default ? "Échange de clés hybride post-quantique par défaut" : "Post-quantique : OpenSSL ≥ 3.5 requis"),
      ]));
      body.append(el("h2", null, "Certificats clients (mTLS)"), table(["", "État", "Détail"], [
        row("mTLS", badge(mtlsLabel, mtlsKind), mtlsNote),
        row("CA des clients", s.client_ca || "—", s.crl ? "CRL chargée (certificats révoqués refusés)" : "Aucune CRL"),
        row("Votre certificat", c.client_subject ? c.client_subject : "Aucun", c.client_cert ? "SHA-256 " + c.client_cert.slice(0, 16) + "…" : ""),
        row("Session liée au certificat", badge(s.bind_session ? "Oui" : "Non", s.bind_session ? "ok" : "neutral"), "Un cookie volé ne s'ouvre pas depuis un autre poste"),
      ]));
      body.append(el("h2", null, "Couches réseau (IT)"), el("p", { class: "muted" }, "Hors du code de la plateforme : à valider avec l'IT."),
        table(["Couche", "Attendu"], LAYERS.map(([k, v]) => el("tr", null, el("th", { scope: "row" }, k), el("td", null, v)))));
    },
  };
})();
