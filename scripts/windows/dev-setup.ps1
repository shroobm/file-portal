# Bootstraps a Windows dev machine for working on windows-widget.
# Run from an elevated-not-required PowerShell prompt (winget/npm/rustup don't need admin for
# per-user installs, though winget itself may prompt UAC on first run depending on policy).

$ErrorActionPreference = "Stop"

function Test-CommandExists($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "node")) {
    Write-Host "Installing Node.js LTS via winget..."
    winget install -e --id OpenJS.NodeJS.LTS
} else {
    Write-Host "Node.js already installed: $(node --version)"
}

if (-not (Test-CommandExists "rustc")) {
    Write-Host "Installing Rust via winget (rustup)..."
    winget install -e --id Rustlang.Rustup
} else {
    Write-Host "Rust already installed: $(rustc --version)"
}

if (-not (Test-CommandExists "tailscale")) {
    Write-Host "Installing Tailscale via winget..."
    winget install -e --id tailscale.tailscale
} else {
    Write-Host "Tailscale already installed."
}

Write-Host "Installing Tauri CLI (cargo)..."
cargo install tauri-cli --version "^2"

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  1. Sign in to Tailscale (tray icon) and join your tailnet."
Write-Host "  2. cd windows-widget; npm install; npm run tauri dev"
Write-Host "  See docs/02-tailscale-setup.md and docs/07-development-guide.md for details."
