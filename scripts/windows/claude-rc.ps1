# Starts a Claude Code session in this repo with Remote Control enabled, so the session can be
# driven from the Claude app on the phone or another machine (docs/14, docs/17 - the remote
# dispatch lane). The session lives in THIS console: leave the window open for as long as you
# want to reach it remotely, Ctrl-C / /exit ends it.
#
# Run it from anywhere - it always lands in the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\windows\claude-rc.ps1
#
# Verified against Claude Code 2.1.239: `claude --remote-control [name]`.

[CmdletBinding()]
param(
    # Remote Control session name, i.e. what you pick from the list in the app.
    # Default: file-portal-<machine>, so the Desktop and the ThinkPad lanes stay distinguishable.
    [string]$Name,

    # Continue the most recent conversation in this directory instead of starting a fresh one.
    [switch]$Continue,

    # Open the session by running the MUSTER bootstrap (memory + both clocks + relay).
    [switch]$Muster,

    # Opt-in: skip every permission prompt. Convenient when nobody is at the keyboard to
    # approve tool calls, but the session can then do anything without asking.
    [switch]$SkipPermissions,

    # Print the command that would run and exit, without launching anything.
    [switch]$DryRun,

    # Anything else is passed straight through to claude, e.g. --model opus --effort high.
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ClaudeArgs
)

$ErrorActionPreference = "Stop"

# Repo root is two levels up from scripts/windows/.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if (-not (Test-Path (Join-Path $RepoRoot "CLAUDE_README.md"))) {
    Write-Host "Not a File Portal checkout - no CLAUDE_README.md under:" -ForegroundColor Red
    Write-Host "  $RepoRoot"
    Write-Host "Keep this script at scripts\windows\claude-rc.ps1 inside the repo."
    exit 1
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Host "claude is not on PATH." -ForegroundColor Red
    Write-Host "Expected the native build at: $env:USERPROFILE\.local\bin\claude.exe"
    Write-Host "Install or repair it with:  irm https://claude.ai/install.ps1 | iex"
    exit 1
}

if (-not $Name) {
    # Lowercase the machine name and keep it to [a-z0-9-], so the label reads cleanly in the app.
    $machine = ($env:COMPUTERNAME).ToLower() -replace '[^a-z0-9-]', '-'
    if (-not $machine) { $machine = "unknown" }
    $Name = "file-portal-$machine"
}

$argv = @("--remote-control", $Name)
if ($Continue)        { $argv += "--continue" }
if ($SkipPermissions) { $argv += "--dangerously-skip-permissions" }
if ($ClaudeArgs)      { $argv += $ClaudeArgs }
# The prompt is positional and must come last.
if ($Muster)          { $argv += "MUSTER" }

Write-Host ""
Write-Host "Repo    : $RepoRoot"
Write-Host "Claude  : $($claude.Source)  ($($claude.Version))"
Write-Host "Session : $Name" -ForegroundColor Cyan
Write-Host "Command : claude $($argv -join ' ')"
if ($SkipPermissions) {
    Write-Host "WARNING : permission prompts are OFF for this session." -ForegroundColor Yellow
}
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run - nothing launched."
    exit 0
}

Write-Host "Pick '$Name' in the Claude app to drive this session. Keep this window open." -ForegroundColor DarkGray
Write-Host ""

Push-Location $RepoRoot
try {
    & $claude.Source @argv
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $code
