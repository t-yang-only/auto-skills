param([string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }))

$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$hooksFile = Join-Path ([System.IO.Path]::GetFullPath($CodexHome)) 'hooks.json'
$installedHook = Join-Path ([System.IO.Path]::GetFullPath($CodexHome)) 'hooks\codex-memory-guard.ps1'
$installedValidator = Join-Path ([System.IO.Path]::GetFullPath($CodexHome)) 'hooks\validate-handoff.ps1'
$agentsFile = Join-Path ([System.IO.Path]::GetFullPath($CodexHome)) 'AGENTS.md'

if (Test-Path -LiteralPath $hooksFile) {
    Copy-Item -LiteralPath $hooksFile -Destination "$hooksFile.backup-$([DateTime]::Now.ToString('yyyyMMdd-HHmmssfff'))"
    $config = Get-Content -LiteralPath $hooksFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($eventName in @('PreCompact', 'SessionStart')) {
        if (-not $config.hooks.PSObject.Properties[$eventName]) { continue }
        $groups = [System.Collections.Generic.List[object]]::new()
        foreach ($group in @($config.hooks.$eventName | Where-Object { $null -ne $_ })) {
            $kept = @($group.hooks | Where-Object {
                $handlerCommand = if ($_.commandWindows) { [string]$_.commandWindows } else { [string]$_.command }
                -not $handlerCommand.Contains('codex-memory-guard.ps1')
            })
            if ($kept.Count -gt 0) {
                $group.hooks = $kept
                $groups.Add($group)
            }
        }
        $config.hooks.$eventName = @($groups)
    }
    [System.IO.File]::WriteAllText($hooksFile, ($config | ConvertTo-Json -Depth 12), $utf8)
}
if (Test-Path -LiteralPath $installedHook) { Remove-Item -LiteralPath $installedHook -Force }
if (Test-Path -LiteralPath $installedValidator) { Remove-Item -LiteralPath $installedValidator -Force }

$globalAgentsBlockRemoved = $false
if (Test-Path -LiteralPath $agentsFile) {
    $startMarker = '<!-- codex-memory-guard:start -->'
    $endMarker = '<!-- codex-memory-guard:end -->'
    $agentsContent = [System.IO.File]::ReadAllText($agentsFile, [System.Text.Encoding]::UTF8)
    $startIndex = $agentsContent.IndexOf($startMarker, [System.StringComparison]::Ordinal)
    $endIndex = $agentsContent.IndexOf($endMarker, [System.StringComparison]::Ordinal)
    if (($startIndex -ge 0) -xor ($endIndex -ge 0) -or ($startIndex -ge 0 -and $endIndex -lt $startIndex)) {
        throw "Malformed codex-memory-guard block in $agentsFile"
    }
    if ($startIndex -ge 0) {
        Copy-Item -LiteralPath $agentsFile -Destination "$agentsFile.backup-$([DateTime]::Now.ToString('yyyyMMdd-HHmmssfff'))"
        $afterIndex = $endIndex + $endMarker.Length
        $before = $agentsContent.Substring(0, $startIndex).TrimEnd()
        $after = $agentsContent.Substring($afterIndex).TrimStart()
        $remaining = if ($before -and $after) { $before + [Environment]::NewLine + [Environment]::NewLine + $after } elseif ($before) { $before + [Environment]::NewLine } elseif ($after) { $after } else { '' }
        [System.IO.File]::WriteAllText($agentsFile, $remaining, $utf8)
        $globalAgentsBlockRemoved = $true
    }
}

[pscustomobject]@{ RemovedHook = $installedHook; GlobalAgentsFile = $agentsFile; GlobalAgentsBlockRemoved = $globalAgentsBlockRemoved; PreservedProjectMemory = $true }
