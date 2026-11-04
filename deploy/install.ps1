# Dynamite | Agile -- installation on a Windows PC that hosts the tool for a team on its local network (0.60.10, D-O-022).
#
# In PowerShell opened AS ADMINISTRATOR (Win + X -> Terminal (admin)), on the PC that will host the tool:
#   irm <site>/install.ps1 -OutFile $env:TEMP\install-dynamite.ps1; powershell -ExecutionPolicy Bypass -File $env:TEMP\install-dynamite.ps1
# Options: -Dossier D:\DynamiteAgile (default C:\DynamiteAgile), -Port 8443 (default 443), -Desinstaller.
# Messages in French by default, in English with $env:DA_LANG = "en".
#
# What it does (run it again to update: the data are kept): Python 3.12 and Git through winget, the code in the
# folder, the team's certificate authority and the HTTPS certificate of this PC (tools/make_team_ca.py, trusted on
# this PC), data\config.json for production (network, HTTPS, development mode off), a firewall rule for the private
# and domain networks only, a scheduled task « Dynamite Agile » that starts with Windows (account SYSTEM) and
# restarts the server if it stops, then the address to open and the first admin password.
# Readable on GitHub: deploy/install.ps1. Windows 10 / 11 or Windows Server 2019 and later.

param([string]$Dossier = "C:\DynamiteAgile", [int]$Port = 443, [switch]$Desinstaller)

$ErrorActionPreference = "Stop"
$EN = ($env:DA_LANG -eq "en")
$Repo = if ($env:DA_REPO) { $env:DA_REPO } else { "https://github.com/jpdesbiens11/Dynamite-Agile.git" }
$TaskName = "Dynamite Agile"
$RuleName = "Dynamite Agile (HTTPS)"

function T([string]$fr, [string]$en) { if ($EN) { $en } else { $fr } }
function Say([string]$message) { Write-Host ""; Write-Host ("== " + $message) -ForegroundColor Cyan }
function Fail([string]$message) {
    Write-Host ""
    Write-Host ((T "Erreur : " "Error: ") + $message) -ForegroundColor Red
    exit 1
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Find-Python {
    # The « python » of WindowsApps only opens the Microsoft Store: never use it.
    $candidates = @(Get-Command python -All -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" } |
        ForEach-Object { $_.Source })
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try { $candidates += (& py -3 -c "import sys; print(sys.executable)") } catch { }
    }
    $candidates += @("$env:ProgramFiles\Python312\python.exe", "$env:ProgramFiles\Python313\python.exe")
    foreach ($exe in $candidates) {
        if ($exe -and (Test-Path $exe)) {
            try { $ok = & $exe -c "import sys; print(sys.version_info >= (3, 10))" } catch { $ok = "" }
            if ($ok -eq "True") { return $exe }
        }
    }
    return $null
}
function Port-Owner([int]$number) {
    # Name of the program listening on this port ("" = free). PID 4 « System » is http.sys (IIS, another web service).
    $conn = Get-NetTCPConnection -LocalPort $number -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return "" }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) { return $proc.ProcessName } else { return "PID " + $conn.OwningProcess }
}
function Winget-Install([string]$id, [string]$label) {
    Write-Host ("  " + (T "Installation de " "Installing ") + $label + " (winget)…")
    # winget's exit codes differ between versions: the caller checks that the program is there afterwards.
    winget install -e --id $id --scope machine --silent --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-Path
}

# ---------- 0. administrator, Windows, winget ----------
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Fail (T "PowerShell n'est pas ouvert en administrateur. Correctif : Win + X → « Terminal (admin) », puis relancez la commande."
            "PowerShell is not running as administrator. Fix: Win + X → « Terminal (Admin) », then run the command again.")
}

if ($Desinstaller) {
    Say (T "Désinstallation (les données de $Dossier\data sont gardées)" "Uninstalling (the data in $Dossier\data are kept)")
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host ("  " + (T "Tâche et règle de pare-feu retirées. Supprimez le dossier à la main si vous ne gardez rien." "Task and firewall rule removed. Delete the folder by hand if you keep nothing."))
    exit 0
}

Say ("1/7 " + (T "Vérifications" "Checks"))
if ([Environment]::OSVersion.Version.Major -lt 10) { Fail (T "Windows 10, 11 ou Server 2019 et plus est requis." "Windows 10, 11 or Server 2019 and later is required.") }
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Fail (T "winget est introuvable. Correctif : installez « App Installer » depuis le Microsoft Store (ou installez Python 3.12 et Git pour Windows à la main), puis relancez."
            "winget not found. Fix: install « App Installer » from the Microsoft Store (or install Python 3.12 and Git for Windows by hand), then run again.")
}
$owner = Port-Owner $Port
if ($owner -and $owner -notlike "python*") {
    Fail (T "le port $Port est déjà pris par « $owner ». Correctif : arrêtez ce programme, ou relancez avec -Port 8443."
            "port $Port is already used by « $owner ». Fix: stop that program, or run again with -Port 8443.")
}
Write-Host ("  " + (T "Administrateur, Windows et winget : OK." "Administrator, Windows and winget: OK."))

# ---------- 2. Python and Git ----------
Say ("2/7 Python 3.12 " + (T "et" "and") + " Git")
$py = Find-Python
if (-not $py) { Winget-Install "Python.Python.3.12" "Python 3.12"; $py = Find-Python }
if (-not $py) { Fail (T "Python 3.10 ou plus récent reste introuvable (winget a peut-être échoué, message ci-dessus). Correctif : installez Python 3.12 depuis python.org en cochant « Add python.exe to PATH », fermez et rouvrez PowerShell en administrateur, puis relancez la commande." "Python 3.10 or newer still not found (winget may have failed, message above). Fix: install Python 3.12 from python.org ticking « Add python.exe to PATH », close and reopen PowerShell as administrator, then run the command again.") }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Winget-Install "Git.Git" "Git" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail (T "Git reste introuvable (winget a peut-être échoué, message ci-dessus). Correctif : installez Git pour Windows depuis git-scm.com, fermez et rouvrez PowerShell en administrateur, puis relancez." "Git still not found (winget may have failed, message above). Fix: install Git for Windows from git-scm.com, close and reopen PowerShell as administrator, then run again.") }
Write-Host ("  Python : " + $py)

# ---------- 3. the code ----------
Say ("3/7 " + (T "Le code dans " "The code in ") + $Dossier)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
if (Test-Path (Join-Path $Dossier ".git")) {
    git -C $Dossier pull --ff-only | Out-Host
    if ($LASTEXITCODE -ne 0) { Fail (T "git pull a échoué (fichiers modifiés à la main dans $Dossier ?). Correctif : git -C $Dossier status, puis relancez." "git pull failed (files edited by hand in $Dossier?). Fix: git -C $Dossier status, then run again.") }
} elseif ((Test-Path $Dossier) -and (Get-ChildItem $Dossier -Force | Where-Object { $_.Name -ne "data" })) {
    Fail ((T "le dossier $Dossier existe déjà et n'est pas un clone de Dynamite | Agile. Correctif : choisissez un autre dossier avec -Dossier D:\DynamiteAgile."
             "the folder $Dossier already exists and is not a clone of Dynamite | Agile. Fix: choose another folder with -Dossier D:\DynamiteAgile."))
} else {
    # A folder holding only data\ (an earlier attempt): set it aside, clone, put it back.
    $Aside = $null
    if (Test-Path (Join-Path $Dossier "data")) {
        $Aside = Join-Path $env:TEMP ("dynamite-data-" + (Get-Date -Format "yyyyMMddHHmmss"))
        Move-Item (Join-Path $Dossier "data") $Aside
        Remove-Item $Dossier -Force
    }
    git clone --depth 1 $Repo $Dossier | Out-Host
    $cloned = ($LASTEXITCODE -eq 0)
    if ($Aside) { New-Item -ItemType Directory -Force -Path $Dossier | Out-Null; Move-Item $Aside (Join-Path $Dossier "data") }
    if (-not $cloned) { Fail (T "git clone a échoué. Correctif : vérifiez la connexion Internet de ce PC, puis relancez." "git clone failed. Fix: check the Internet connection of this PC, then run again.") }
}
$Data = Join-Path $Dossier "data"
New-Item -ItemType Directory -Force -Path $Data | Out-Null

# ---------- 4. HTTPS: the team's certificate authority and the certificate of this PC ----------
Say ("4/7 " + (T "Certificat HTTPS de l'équipe" "The team's HTTPS certificate"))
& $py (Join-Path $Dossier "tools\make_team_ca.py") --data-dir $Data | Out-Host
if ($LASTEXITCODE -ne 0) { Fail (T "le certificat n'a pas pu être créé (message ci-dessus)." "the certificate could not be created (message above).") }
$Ca = Join-Path $Data "tls\partage\ca-dynamite.crt"
Import-Certificate -FilePath $Ca -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
Write-Host ("  " + (T "Autorité de l'équipe approuvée sur ce PC." "Team authority trusted on this PC."))

# ---------- 5. configuration ----------
Say "5/7 Configuration (data\config.json)"
$Redirect = if ($Port -eq 443) { 80 } else { 0 }
$owner80 = if ($Redirect) { Port-Owner 80 } else { "" }
if ($owner80 -and $owner80 -notlike "python*") {
    Write-Host ("  " + (T "Le port 80 est pris par « $owner80 » : pas de redirection http:// → https://, ouvrez directement https://."
                         "Port 80 is used by « $owner80 »: no http:// → https:// redirect, open https:// directly.")) -ForegroundColor Yellow
    $Redirect = 0
}
$PcName = $env:COMPUTERNAME.ToLower()
& $py (Join-Path $Dossier "tools\write_config.py") --data-dir $Data host=0.0.0.0 "port=$Port" tls_cert=tls/server.crt tls_key=tls/server.key `
    "http_redirect_port=$Redirect" "public_name=$PcName" dev_mode=false | Out-Host
if ($LASTEXITCODE -ne 0) { Fail (T "la configuration n'a pas pu être écrite." "the configuration could not be written.") }

# ---------- 6. firewall: private and domain networks only ----------
Say ("6/7 " + (T "Pare-feu (réseaux privés et de domaine seulement)" "Firewall (private and domain networks only)"))
Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
$Ports = if ($Redirect) { @("$Port", "$Redirect") } else { @("$Port") }
New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Protocol TCP -LocalPort $Ports -Action Allow -Profile Domain, Private | Out-Null
Write-Host ("  " + (T "Ports ouverts : " "Open ports: ") + ($Ports -join ", "))
$public = Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.NetworkCategory -eq "Public" }
if ($public) {
    Write-Host ("  " + (T "Attention : le réseau « " "Warning: the network « ") + $public[0].Name +
                (T " » est marqué Public, l'équipe n'y accédera pas. Correctif : Paramètres → Réseau → Propriétés → Réseau privé." " » is marked Public, the team will not reach the tool. Fix: Settings → Network → Properties → Private network.")) -ForegroundColor Yellow
}

# ---------- 7. the service: a scheduled task that starts with Windows and restarts the server ----------
Say ("7/7 " + (T "Service « $TaskName » (démarre avec Windows)" "Service « $TaskName » (starts with Windows)"))
$action = New-ScheduledTaskAction -Execute $py -Argument ('"' + (Join-Path $Dossier "app_dynamite_agile.py") + '"') -WorkingDirectory $Dossier
$trigger = New-ScheduledTaskTrigger -AtStartup
$account = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $account -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
$up = $false
foreach ($i in 1..20) {
    Start-Sleep -Seconds 1
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { $up = $true; break }
}
if (-not $up) {
    $log = Join-Path $Data "logs\server.log"
    if (Test-Path $log) { Get-Content $log -Tail 20 | Out-Host }
    Fail (T "le serveur ne démarre pas (journal ci-dessus : data\logs\server.log)." "the server does not start (log above: data\logs\server.log).")
}
Write-Host ("  " + (T "Service actif." "Service running."))

$Address = if ($Port -eq 443) { "https://$PcName" } else { "https://${PcName}:$Port" }
$Ips = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }).IPAddress
Write-Host ""
Write-Host ("== " + (T "C'est installé" "Installed")) -ForegroundColor Green
Write-Host ("  " + (T "Ouvrez, depuis n'importe quel poste du réseau : " "Open, from any computer on the network: ") + $Address +
            $(if ($Ips) { "  (" + (T "ou " "or ") + (($Ips | ForEach-Object { if ($Port -eq 443) { "https://$_" } else { "https://${_}:$Port" } }) -join ", ") + ")" } else { "" }))
$Initial = Join-Path $Data "INITIAL_ADMIN_PASSWORD.txt"
if (Test-Path $Initial) {
    Write-Host ("  " + (T "Compte administrateur (mot de passe temporaire, à changer à la première connexion) :" "Administrator account (temporary password, to change at first login):"))
    Get-Content $Initial | ForEach-Object { Write-Host ("    " + $_) }
} else {
    Write-Host ("  " + (T "Le compte admin existe déjà. Mot de passe oublié :" "The admin account already exists. Forgotten password:") +
                " & '$py' '$Dossier\app_dynamite_agile.py' --reset-password admin")
}
Write-Host ""
Write-Host ("  " + (T "Sur CHAQUE poste de l'équipe, une seule fois : copiez " "On EACH computer of the team, once: copy ") + $Ca +
            (T " (clé USB, partage, courriel), puis dans PowerShell (sans être administrateur) :" " (USB key, share, email), then in PowerShell (no administrator needed):"))
Write-Host "    Import-Certificate -FilePath .\ca-dynamite.crt -CertStoreLocation Cert:\CurrentUser\Root"
Write-Host ("  " + (T "macOS : double-cliquez le fichier, puis Trousseau → « Toujours approuver »." "macOS: double-click the file, then Keychain → « Always Trust »."))
Write-Host ""
Write-Host ("  " + (T "Mettre à jour plus tard : relancez la même commande (les données sont gardées)." "Updating later: run the same command again (the data are kept)."))
