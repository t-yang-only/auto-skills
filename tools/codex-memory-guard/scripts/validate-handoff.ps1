param(
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$RecommendedMax = 1000,
    [int]$HardMax = 1500,
    [switch]$NoFail
)

$ErrorActionPreference = 'Stop'
if ($RecommendedMax -lt 1 -or $HardMax -lt $RecommendedMax) { throw 'Character limits are invalid.' }
$resolved = [System.IO.Path]::GetFullPath($Path)
$exists = Test-Path -LiteralPath $resolved -PathType Leaf
$issues = [System.Collections.Generic.List[string]]::new()
if (-not $exists) {
    $issues.Add('handoff_missing')
    [pscustomobject]@{
        Path = $resolved
        Exists = $false
        Characters = 0
        RecommendedMax = $RecommendedMax
        HardMax = $HardMax
        Status = 'missing'
        RecoveryRequired = $true
        Issues = @($issues)
        LastWriteAt = $null
        Sha256 = $null
    }
    if (-not $NoFail) { exit 1 }
    return
}

$content = [System.IO.File]::ReadAllText($resolved, [System.Text.Encoding]::UTF8)
$count = $content.Length
if ($count -gt $HardMax) { $issues.Add('over_hard_limit') }

$sections = @([regex]::Matches($content, '(?ms)^##\s+[^\r\n]+\s*\r?\n(?<body>.*?)(?=^##\s+|\z)'))
if ($sections.Count -lt 6) { $issues.Add('required_sections_missing') }

function Get-SectionBullets([int]$Index) {
    if ($sections.Count -le $Index) { return @() }
    return @([regex]::Matches($sections[$Index].Groups['body'].Value, '(?m)^-\s+(.+?)\s*$') | ForEach-Object { $_.Groups[1].Value.Trim() })
}

$goalBullets = Get-SectionBullets 0
$milestoneBullets = Get-SectionBullets 2
$nextBullets = Get-SectionBullets 4
if ($goalBullets.Count -ne 1) { $issues.Add('current_goal_must_have_one_item') }
if ($nextBullets.Count -ne 1) { $issues.Add('next_action_must_have_one_item') }
if ($milestoneBullets.Count -gt 3) { $issues.Add('too_many_recent_milestones') }
$requiredText = ($goalBullets + $nextBullets) -join "`n"
$fullWidthOpenParen = [char]0xFF08
if ($requiredText.Contains([string]$fullWidthOpenParen) -or $requiredText.Contains('(TODO)')) { $issues.Add('required_placeholder_present') }

$status = if ($issues.Contains('over_hard_limit')) { 'over_hard_limit' } elseif ($issues.Count -gt 0) { 'invalid' } elseif ($count -gt $RecommendedMax) { 'over_recommended_limit' } else { 'ready' }
$fileInfo = Get-Item -LiteralPath $resolved
$sha256 = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()

[pscustomobject]@{
    Path = $resolved
    Exists = $true
    Characters = $count
    RecommendedMax = $RecommendedMax
    HardMax = $HardMax
    Status = $status
    RecoveryRequired = $issues.Count -gt 0
    Issues = @($issues)
    LastWriteAt = $fileInfo.LastWriteTimeUtc.ToString('o')
    Sha256 = $sha256
}

if ($issues.Count -gt 0 -and -not $NoFail) { exit 1 }
