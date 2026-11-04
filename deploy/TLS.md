# HTTPS et mTLS sur votre serveur — guide d'installation

Lot noyau v0.24 (0.46.0, D-B-090). La plateforme chiffre elle-même l'échange navigateur ↔ serveur, avec le module
`ssl` de la bibliothèque standard Python : aucun reverse proxy nécessaire, aucune dépendance ajoutée.

**Pourquoi :** un mot de passe ou une session ne doit jamais traverser un réseau en clair, même un réseau d'école ou
un VPN. On ne fait pas confiance au réseau (Zero Trust) : chaque saut est chiffré.

## 1. Ce que fait le serveur

| Mesure | Réglage (`data/config.json`) | Défaut |
|---|---|---|
| TLS 1.3 seulement (AEAD, ECDHE : forward secrecy), sans compression ni renégociation | `tls_min_version` | `"1.3"` (`"1.2"` : repli ECDHE + AES-GCM / ChaCha20 seulement) |
| Certificat serveur | `tls_cert`, `tls_key` (chemins absolus ou relatifs à `data/`) | vide = HTTP |
| **Fail closed** : en production, refus de démarrer sans certificat, sauf si `host` = `127.0.0.1` | — | toujours |
| HSTS `max-age=31536000; includeSubDomains` (jamais en `dev_mode`) | `hsts_max_age` | 1 an |
| Cookie de session `__Host-da_session` : `Secure`, `HttpOnly`, `SameSite=Strict` | — | dès HTTPS |
| mTLS : CA qui signe les certificats clients | `tls_client_ca` | vide = mTLS désactivé |
| mTLS obligatoire (sans certificat valide, pas de handshake) | `tls_client_required` | `false` = vérifié s'il est présenté |
| CRL des certificats clients révoqués (PEM) | `tls_client_crl` | vide |
| Session liée au certificat client (cookie volé refusé depuis un autre poste) | `tls_bind_session` | `true` |
| Port HTTP qui ne fait que rediriger vers `https://` (jamais de contenu ; une écriture en clair reçoit 403) | `http_redirect_port`, `public_name` | `0` = fermé |

État en direct : **Admin → Sécurité réseau** (version et suite de cette connexion, certificat, expiration avec alerte à
30 jours, mode mTLS, OpenSSL).

## 2. Mise en service (production)

1. **Certificat serveur** — générer la clé et la CSR sur le serveur (la clé ne quitte jamais le serveur) :

   ```sh
   openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
     -keyout /srv/dynamite/data/tls/server.key -out server.csr \
     -subj "/O=Mon équipe/CN=dynamite.exemple.org" -addext "subjectAltName=DNS:dynamite.exemple.org"
   chmod 600 /srv/dynamite/data/tls/server.key
   ```

   Faire signer `server.csr` par l'autorité de votre organisation (usage `serverAuth`, durée ≤ 397 jours), ou obtenir
   un certificat public (par exemple Let's Encrypt, avec `certbot certonly --standalone`), puis déposer `server.crt`
   (chaîne complète : serveur puis intermédiaire) dans `data/tls/`.

2. **Configuration** (`data/config.json`) :

   ```json
   {
     "host": "0.0.0.0",
     "port": 443,
     "dev_mode": false,
     "tls_cert": "tls/server.crt",
     "tls_key": "tls/server.key",
     "http_redirect_port": 80,
     "public_name": "dynamite.exemple.org"
   }
   ```

   Les ports < 1024 demandent `AmbientCapabilities=CAP_NET_BIND_SERVICE` dans le service systemd, ou garder 8443 / 8080.

3. **Vérifier** depuis un poste : `https://dynamite.exemple.org` sans avertissement ; Admin → Sécurité réseau :
   HTTPS Actif, TLS 1.3, HSTS Actif. Depuis le serveur : `openssl s_client -connect localhost:443 -tls1_2` doit échouer.

## 3. mTLS (optionnel, quand une autorité émet des certificats clients)

1. Émettre un certificat client par personne ou par poste (usage `clientAuth`) : autoenrollment AD CS dans le magasin
   Windows, ou carte à puce. Le navigateur (Edge, Chrome) propose le certificat automatiquement.
2. **Phase pilote** : `"tls_client_ca": "tls/clients_ca.crt"` — le certificat est vérifié s'il est présenté,
   les autres postes entrent encore. Admin → Sécurité réseau montre « Votre certificat ».
3. **Obligatoire** : `"tls_client_required": true` — sans certificat client valide, la connexion TLS échoue avant
   même la page de connexion. Ajouter `"tls_client_crl"` et la tenir à jour (révocation d'un poste perdu).
4. Redémarrer le service après chaque changement de `config.json`, de certificat ou de CRL.

## 4. Couches réseau (selon votre hébergement)

| Couche | Attendu |
|---|---|
| VPN | WireGuard ou IPsec IKEv2, avec MFA |
| Segmentation | VLAN dédié au serveur |
| Firewall | Allow-list : port HTTPS (et 80 de redirection si voulu), depuis les adresses de l'équipe ; `nftables` sur l'hôte |
| 802.1X | Ports filaires et Wi-Fi authentifiés |
| Post-quantique | OpenSSL ≥ 3.5 sur le serveur : échange de clés hybride `X25519MLKEM768` par défaut, sans réglage |

Hors de ce guide : les données au repos (base, pièces jointes) relèvent du miroir chiffré, réservé (FONDATIONS §4).

## 5. Développement et tests

**Partager le serveur de développement avec un collègue (0.47.0, D-B-091)** : `Lancer_dev_reseau.bat` (ou
`python lancer_dev.py reseau`, F5 dans Spyder avec `MODE = "reseau"`) — HTTPS sur le port 8443 avec la CA de
développement (créée seule, au nom des adresses réseau du poste), `http://localhost:8080` redirigé, réseaux privés
seulement (`--allow <ip>` pour un seul poste), admin / admin refusé depuis un autre poste. Le pare-feu Windows doit
autoriser Python sur les réseaux privés. Ce n'est pas la production.


`python tools/make_dev_ca.py --client <utilisateur> --write-config` crée dans `data/tls/` une CA de développement,
un certificat serveur (localhost) et un `.p12` client (mot de passe `dynamitedev`). Faire confiance à `data/tls/ca.crt`
sur le poste de test. **Jamais en production.** En `dev_mode`, HSTS n'est pas envoyé (il resterait collé à
`localhost` pendant un an).
