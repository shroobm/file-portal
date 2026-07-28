#Requires -RunAsAdministrator
# Gate 1 — enable OpenSSH Server on the Desktop, scoped to the tailnet AT BIRTH.
# See docs/17-remote-access-runbook.md §4 (Gate 1) for the full contract + rollback.
#
# Run from an ELEVATED, UNPACKAGED PowerShell (Start menu -> Windows PowerShell ->
# "Run as administrator"). Never from a shell opened through the Claude desktop app:
# that surface is MSIX-sandbox-redirected and its system writes can be silently
# virtualized into the app container (docs/17 §1). This script refuses to run there.
#
# Deliberately NOT done here: disabling password authentication. That is Gate 2,
# and only after a key login has been proven (lockout-safe ordering, docs/17 §2 #4).

$ErrorActionPreference = 'Stop'
Start-Transcript -Path "$env:USERPROFILE\Desktop\gate1-bootstrap-transcript.txt" -Append

# 0) refuse a sandboxed (MSIX-packaged) shell
$probe = Join-Path $env:APPDATA 'gate1-sandbox-probe.txt'
Set-Content -Path $probe -Value probe
$redirected = Test-Path "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\gate1-sandbox-probe.txt"
Remove-Item $probe -ErrorAction SilentlyContinue
if ($redirected) {
    Stop-Transcript
    throw 'This shell is MSIX-sandbox-redirected. Use an unpackaged elevated PowerShell (Start menu).'
}

# 1) OpenSSH Server capability (resolve the exact name; do not hardcode the version tail)
$cap = Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Server*' } | Select-Object -First 1
if (-not $cap) { Stop-Transcript; throw 'OpenSSH.Server capability not found on this image.' }
if ($cap.State -ne 'Installed') { Add-WindowsCapability -Online -Name $cap.Name | Out-Null }
"capability: $($cap.Name) -> Installed"

# 2) service: start now + every boot (first start generates C:\ProgramData\ssh\* incl. host keys)
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# 3) PowerShell 5.1 as the SSH shell (the machine standard)
if (-not (Test-Path 'HKLM:\SOFTWARE\OpenSSH')) { New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null }
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell `
    -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -PropertyType String -Force | Out-Null

# 4) firewall: scope AT BIRTH. The capability install auto-creates an allow-any rule;
#    disabling it is what makes the scoped rule mean anything (docs/17 §2 #3).
try { Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction Stop | Disable-NetFirewallRule } catch {
    try { Get-NetFirewallRule -DisplayName '*OpenSSH*' -ErrorAction Stop | Disable-NetFirewallRule } catch {}
}
if (-not (Get-NetFirewallRule -DisplayName 'SSH (Tailscale only)' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'SSH (Tailscale only)' -Direction Inbound -Protocol TCP `
        -LocalPort 22 -RemoteAddress 100.64.0.0/10 -Action Allow | Out-Null
}

# 5) the record: host-key fingerprints (Gate 2 pins these on the ThinkPad's first connect)
''
'=== RECORD THESE HOST-KEY FINGERPRINTS (password manager / photo) ==='
Get-ChildItem C:\ProgramData\ssh\ssh_host_*.pub | ForEach-Object { ssh-keygen -lf $_.FullName }
''
"sshd: $((Get-Service sshd).Status) / $((Get-Service sshd).StartType)  |  tailnet IP: $(tailscale ip -4)"
'NEXT (Gate 2, docs/17): install the ThinkPad public key with gate2-lockdown.ps1 -PubKey ...,'
'PROVE a key login from the ThinkPad, then rerun gate2-lockdown.ps1 -DisablePasswordAuth.'
Stop-Transcript
