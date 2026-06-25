# Creates Desktop + Start Menu shortcuts for the File Portal widget and tries to pin it to the
# taskbar. Re-run after a `npm run tauri build` to repoint the shortcuts at a fresh binary.
#
# Easiest way to run: double-click `install-shortcuts.cmd` in this same folder.

$ErrorActionPreference = "Stop"

# Repo root is two levels up from scripts/windows/.
$RepoRoot  = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$TargetDir = Join-Path $RepoRoot "windows-widget\src-tauri\target"
$IconPath  = Join-Path $RepoRoot "windows-widget\src-tauri\icons\icon.ico"

# Prefer a release build, fall back to debug. (productName "File Portal" for the bundled exe,
# crate name "file-portal-widget" for the raw cargo output.)
$exe = @(
    "release\File Portal.exe",
    "release\file-portal-widget.exe",
    "debug\File Portal.exe",
    "debug\file-portal-widget.exe"
) | ForEach-Object { Join-Path $TargetDir $_ } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $exe) {
    Write-Host "No built File Portal binary found under:" -ForegroundColor Yellow
    Write-Host "  $TargetDir"
    Write-Host ""
    Write-Host "Build it first, then re-run this script:"
    Write-Host "  cd windows-widget"
    Write-Host "  npm install"
    Write-Host "  npm run tauri build      # or `npm run tauri dev` once for a debug build"
    exit 1
}

if ($exe -match '\\target\\debug\\') {
    Write-Host ""
    Write-Host "WARNING: only a DEBUG build was found." -ForegroundColor Yellow
    Write-Host "The debug binary loads the UI from the dev server, so double-clicking it shows" -ForegroundColor Yellow
    Write-Host "'Hmm, can't reach this page' unless 'npm run tauri dev' is running." -ForegroundColor Yellow
    Write-Host "For a standalone app, build a release binary first:" -ForegroundColor Yellow
    Write-Host "  cd windows-widget; npm run tauri build" -ForegroundColor Yellow
    Write-Host "then re-run this script. Linking the debug build for now..." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Linking shortcuts to:"
Write-Host "  $exe"

$workDir = Split-Path $exe
$icon    = if (Test-Path $IconPath) { $IconPath } else { $exe }

function New-Shortcut([string]$LinkPath) {
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($LinkPath)
    $sc.TargetPath       = $exe
    $sc.WorkingDirectory = $workDir
    $sc.IconLocation     = $icon
    $sc.Description       = "File Portal - drag-and-drop file widget"
    $sc.WindowStyle      = 1
    $sc.Save()
}

$desktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "File Portal.lnk"
$startLink   = Join-Path ([Environment]::GetFolderPath("Programs")) "File Portal.lnk"

New-Shortcut $desktopLink
Write-Host "  Desktop:    $desktopLink"
New-Shortcut $startLink
Write-Host "  Start Menu: $startLink"

# Best-effort taskbar pin. Windows 10/11 deliberately blocks scripted pinning, so treat failure
# as expected and fall back to a one-click manual instruction.
$pinned = $false
try {
    $sh   = New-Object -ComObject Shell.Application
    $item = $sh.Namespace((Split-Path $desktopLink)).ParseName((Split-Path $desktopLink -Leaf))
    $verb = $item.Verbs() | Where-Object { ($_.Name -replace '&','') -match 'Pin to taskbar' }
    if ($verb) { $verb.DoIt(); $pinned = $true }
} catch { }

Write-Host ""
if ($pinned) {
    Write-Host "Pinned to the taskbar." -ForegroundColor Green
} else {
    Write-Host "Couldn't pin to the taskbar automatically (Windows blocks this for scripts)." -ForegroundColor Yellow
    Write-Host "To pin it: right-click the new Desktop 'File Portal' icon -> Pin to taskbar."
    Write-Host "On Windows 11 that's: right-click -> Show more options -> Pin to taskbar."
}
Write-Host ""
Write-Host "Done. Double-click the Desktop icon to launch."
