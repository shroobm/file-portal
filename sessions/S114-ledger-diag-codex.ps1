# Independent read-only ledger diagnostic. Does not load Fable's census or relay parser.
# Run in PowerShell from the canonical checkout; outputs JSON, writes nothing.
# Authored by Codex for LEDGER-DIAG-S114.
param(
    [string]$Repository = 'C:/Users/Bndit/Projects/file-portal',
    [string]$Baseline = 'f764042',
    [string]$Current = '8c348498d8fc56e080e2a2601eb913940abd4367',
    [string]$LastClose = '14a526b',
    [string]$RemoteTip = '8bcc340'
)
$ErrorActionPreference = 'Stop'
function Read-Git([string[]]$Arguments) {
    $result = @(& git -c "safe.directory=$Repository" -C $Repository @Arguments)
    if ($LASTEXITCODE -ne 0) { throw "Git failed ($LASTEXITCODE): $($Arguments -join ' ')" }
    return $result
}
function Test-Ancestor([string]$Older, [string]$Newer) {
    & git -c "safe.directory=$Repository" -C $Repository merge-base --is-ancestor $Older $Newer
    if ($LASTEXITCODE -notin @(0, 1)) { throw 'Ancestry probe failed to execute' }
    return ($LASTEXITCODE -eq 0)
}
function Read-Ledger([string]$Revision) {
    $lines = @(Read-Git @('show', "${Revision}:CLAUDE_README.md"))
    $rows = @()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        # Deliberately census ledger-shaped rows across the whole file: later closes
        # were appended after the Session Log. Do not silently drop those rows.
        if ($lines[$i] -notmatch '^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(Desktop|ThinkPad)\s*\|') { continue }
        $date = $Matches[1]; $lane = $Matches[2]
        $cells = $lines[$i].Trim().Trim('|').Split('|')
        $session = $null
        if ($cells[2].Trim() -match '^S(\d+):') { $session = [int]$Matches[1] }
        $sha = $cells[-1].Trim().Trim('`')
        $resolved = @(& git -c "safe.directory=$Repository" -C $Repository rev-parse --verify "${sha}^{commit}" 2>$null)
        $valid = $LASTEXITCODE -eq 0
        $ancestor = if ($valid) { Test-Ancestor $sha $Revision } else { $false }
        $rows += [pscustomobject]@{line=$i+1; date=$date; lane=$lane; session=$session; sha=$sha; resolves=$valid; ancestor=$ancestor}
    }
    $desktop = @($rows | Where-Object { $_.lane -eq 'Desktop' -and $null -ne $_.session })
    $other = @($rows | Where-Object { $_.lane -ne 'Desktop' -and $null -ne $_.session })
    $unparsed = @($rows | Where-Object { $null -eq $_.session })
    $faults = @()
    for ($i=1; $i -lt $desktop.Count; $i++) {
        if ($desktop[$i].session -le $desktop[$i-1].session) { $faults += $desktop[$i] }
    }
    [pscustomobject]@{
        revision=@(Read-Git @('rev-parse',$Revision))[0]
        rows=$rows.Count; desktop_parsed=$desktop.Count; other_parsed=$other.Count; no_session=$unparsed.Count
        desktop_first=$desktop[0]; desktop_last=$desktop[-1]; other_rows=$other
        desktop_order_faults=$faults; unresolvable=@($rows | Where-Object { -not $_.resolves })
        nonancestor=@($rows | Where-Object { $_.resolves -and -not $_.ancestor })
        all_sha_tested=$rows.Count
    }
}
function Read-Commits([string]$Revision) {
    $ids = @(Read-Git @('rev-list','--reverse',"${LastClose}..${Revision}"))
    $records = @($ids | ForEach-Object {
        $id = $_
        $trailers = @(Read-Git @('show','-s','--format=%(trailers:key=Co-Authored-By,valueonly)',$id)) | Where-Object { $_.Trim() }
        $parents = (@(Read-Git @('show','-s','--format=%P',$id))[0]).Split(' ')
        [pscustomobject]@{sha=$id; parents=$parents.Count; trailers=@($trailers)}
    })
    $split = (@(Read-Git @('rev-list','--left-right','--count',"${RemoteTip}...${Revision}"))[0]).Trim() -split '\s+'
    [pscustomobject]@{
        revision=$Revision; since=$LastClose; total=$records.Count
        merges=@($records | Where-Object { $_.parents -gt 1 }).Count
        trailer_counts=@($records | ForEach-Object { $_.trailers } | Group-Object | ForEach-Object { [pscustomobject]@{trailer=$_.Name; commits=$_.Count} })
        codex=@($records | Where-Object { ($_.trailers -join ';') -match '^OpenAI Codex' } | ForEach-Object { $_.sha })
        remote_tip=$RemoteTip; behind=[int]$split[0]; ahead=[int]$split[1]
        remote_is_ancestor=(Test-Ancestor $RemoteTip $Revision)
    }
}
$baselineLedger=Read-Ledger $Baseline
$currentLedger=Read-Ledger $Current
# A descendant cannot be an ancestor of the frozen baseline: a real negative
# control using existing commits, without manufacturing or mutating history.
$negativeDetected = -not (Test-Ancestor $Current $Baseline)
if (-not $negativeDetected) { throw 'Negative control failed; choose a later Current revision' }
[pscustomobject]@{
    observed_utc=[DateTime]::UtcNow.ToString('o')
    baseline_ledger=$baselineLedger; current_ledger=$currentLedger
    baseline_commits=(Read-Commits $Baseline); current_commits=(Read-Commits $Current)
    negative_control=@{claim='Current is ancestor of Baseline'; rejected=$negativeDetected}
} | ConvertTo-Json -Depth 9
