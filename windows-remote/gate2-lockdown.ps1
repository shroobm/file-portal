#Requires -RunAsAdministrator
# Gate 2 — install the ThinkPad public key for the admin account, then (second run,
# only after a PROVEN key login) lock out password auth. Two runs BY DESIGN — the
# split is the lockout guard the source brief lacked (docs/17 §2 #4).
#
#   1st run:  .\gate2-lockdown.ps1 -PubKey 'ssh-ed25519 AAAA... rab@archlinux'
#             installs the key into administrators_authorized_keys (admin accounts
#             IGNORE ~\.ssh\authorized_keys) and locks its ACL.
#   TEST:     ThinkPad:  ssh -o PreferredAuthentications=publickey desktop whoami
#             -> must print desktop-bndit\bndit with NO password prompt.
#   2nd run:  .\gate2-lockdown.ps1 -DisablePasswordAuth
#             backs up sshd_config, sets PasswordAuthentication no, restarts sshd.
#             Keep one working session open while you re-test from a second one.

param(
    [string]$PubKey,
    [switch]$DisablePasswordAuth
)
$ErrorActionPreference = 'Stop'
$ak  = 'C:\ProgramData\ssh\administrators_authorized_keys'
$cfg = 'C:\ProgramData\ssh\sshd_config'

if ($PubKey) {
    if ($PubKey -notmatch '^(ssh-ed25519|sk-ssh-ed25519|ecdsa-sha2|ssh-rsa) ') {
        throw 'That does not look like an OpenSSH public key line (expected "ssh-ed25519 AAAA... comment").'
    }
    # UTF-8 WITHOUT BOM is load-bearing: PS 5.1 Set-Content/Out-File both write encodings sshd rejects.
    [IO.File]::AppendAllText($ak, $PubKey.Trim() + "`n", (New-Object System.Text.UTF8Encoding($false)))
    icacls $ak /inheritance:r /grant 'SYSTEM:F' /grant 'BUILTIN\Administrators:F' | Out-Null
    'Key installed. NOW TEST from the ThinkPad:'
    '    ssh -o PreferredAuthentications=publickey desktop whoami'
    'Only after that works, rerun:  .\gate2-lockdown.ps1 -DisablePasswordAuth'
}

if ($DisablePasswordAuth) {
    if (-not (Test-Path $ak)) { throw 'No administrators_authorized_keys yet - install a key first (lockout guard).' }
    'Keys that are about to become the only door:'
    ssh-keygen -lf $ak
    Copy-Item $cfg "$cfg.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
    $text = [IO.File]::ReadAllText($cfg)
    $re = New-Object System.Text.RegularExpressions.Regex('(?m)^\s*#?\s*PasswordAuthentication\b.*$')
    if ($re.IsMatch($text)) {
        $text = $re.Replace($text, 'PasswordAuthentication no', 1)
    } else {
        # PREPEND, never append: the file ends in a "Match Group administrators" block and an
        # appended directive would silently scope itself to that block only.
        $text = "PasswordAuthentication no`r`n" + $text
    }
    [IO.File]::WriteAllText($cfg, $text, (New-Object System.Text.UTF8Encoding($false)))
    Restart-Service sshd
    'PasswordAuthentication no is live. Keep this session open and verify a FRESH key login'
    'from a second terminal before closing anything. Backup written next to sshd_config.'
}

if (-not $PubKey -and -not $DisablePasswordAuth) {
    'Usage:'
    "  .\gate2-lockdown.ps1 -PubKey 'ssh-ed25519 AAAA... comment'   # step 1: install key, then TEST"
    '  .\gate2-lockdown.ps1 -DisablePasswordAuth                    # step 2: only after the test passes'
}
