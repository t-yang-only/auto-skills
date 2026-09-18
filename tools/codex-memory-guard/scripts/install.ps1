param(
    [string]$ProjectRoot,
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' })
)

$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$CodexHome = [System.IO.Path]::GetFullPath($CodexHome)
$hookDir = Join-Path $CodexHome 'hooks'
$installedHook = Join-Path $hookDir 'codex-memory-guard.ps1'
$installedValidator = Join-Path $hookDir 'validate-handoff.ps1'
$hooksFile = Join-Path $CodexHome 'hooks.json'
$agentsFile = Join-Path $CodexHome 'AGENTS.md'
$globalAgentsTemplate = Join-Path $PSScriptRoot '..\assets\templates\GLOBAL_AGENTS_BLOCK.md'
[System.IO.Directory]::CreateDirectory($hookDir) | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'codex-memory-guard.ps1') -Destination $installedHook -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'validate-handoff.ps1') -Destination $installedValidator -Force

if (Test-Path -LiteralPath $hooksFile) {
    $backup = "$hooksFile.backup-$([DateTime]::Now.ToString('yyyyMMdd-HHmmssfff'))"
    Copy-Item -LiteralPath $hooksFile -Destination $backup
    $config = Get-Content -LiteralPath $hooksFile -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $config = [pscustomobject]@{ description = 'Codex lifecycle hooks'; hooks = [pscustomobject]@{} }
}
if (-not $config.PSObject.Properties['hooks']) { $config | Add-Member NoteProperty hooks ([pscustomobject]@{}) }

$command = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$installedHook`""
foreach ($spec in @(
    @{ Event = 'PreCompact'; Matcher = 'manual|auto'; Mode = 'PreCompact'; Message = 'Registering pre-compaction memory evidence' },
    @{ Event = 'SessionStart'; Matcher = 'compact'; Mode = 'SessionStart'; Message = 'Restoring pre-compaction memory task' }
)) {
    $eventName = $spec.Event
    $existing = @($config.hooks.$eventName | Where-Object { $null -ne $_ })
    $needle = "-Mode $($spec.Mode)"
    $already = $false
    foreach ($group in $existing) {
        foreach ($handler in @($group.hooks | Where-Object { $null -ne $_ })) {
            $handlerCommand = if ($handler.commandWindows) { [string]$handler.commandWindows } else { [string]$handler.command }
            if ($handlerCommand.Contains('codex-memory-guard.ps1') -and $handlerCommand.Contains($needle)) { $already = $true }
        }
    }
    if (-not $already) {
        $handler = [pscustomobject]@{ type = 'command'; commandWindows = "$command -Mode $($spec.Mode)"; command = "$command -Mode $($spec.Mode)"; timeout = 10; statusMessage = $spec.Message }
        if ($eventName -eq 'SessionStart') { $handler | Add-Member NoteProperty additionalContextLimit 1200 }
        $group = [pscustomobject]@{ matcher = $spec.Matcher; hooks = @($handler) }
        $updated = @($existing) + @($group)
        if ($config.hooks.PSObject.Properties[$eventName]) { $config.hooks.$eventName = $updated } else { $config.hooks | Add-Member NoteProperty $eventName $updated }
    }
}

[System.IO.File]::WriteAllText($hooksFile, ($config | ConvertTo-Json -Depth 12), $utf8)

$startMarker = '<!-- codex-memory-guard:start -->'
$endMarker = '<!-- codex-memory-guard:end -->'
$managedBlock = [System.IO.File]::ReadAllText([System.IO.Path]::GetFullPath($globalAgentsTemplate), [System.Text.Encoding]::UTF8).Trim()
$existingAgents = if (Test-Path -LiteralPath $agentsFile) {
    Copy-Item -LiteralPath $agentsFile -Destination "$agentsFile.backup-$([DateTime]::Now.ToString('yyyyMMdd-HHmmssfff'))"
    [System.IO.File]::ReadAllText($agentsFile, [System.Text.Encoding]::UTF8)
} else {
    ''
}

$startIndex = $existingAgents.IndexOf($startMarker, [System.StringComparison]::Ordinal)
$endIndex = $existingAgents.IndexOf($endMarker, [System.StringComparison]::Ordinal)
if (($startIndex -ge 0) -xor ($endIndex -ge 0) -or ($startIndex -ge 0 -and $endIndex -lt $startIndex)) {
    throw "Malformed codex-memory-guard block in $agentsFile"
}
if ($startIndex -ge 0) {
    $afterIndex = $endIndex + $endMarker.Length
    $updatedAgents = $existingAgents.Substring(0, $startIndex) + $managedBlock + $existingAgents.Substring($afterIndex)
} elseif ([string]::IsNullOrWhiteSpace($existingAgents)) {
    $updatedAgents = $managedBlock + [Environment]::NewLine
} else {
    $updatedAgents = $existingAgents.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + $managedBlock + [Environment]::NewLine
}
[System.IO.File]::WriteAllText($agentsFile, $updatedAgents, $utf8)

if ($ProjectRoot) { & (Join-Path $PSScriptRoot 'initialize-memory-system.ps1') -Root $ProjectRoot -SingleProject }
[pscustomobject]@{ InstalledHook = $installedHook; InstalledValidator = $installedValidator; HooksFile = $hooksFile; GlobalAgentsFile = $agentsFile; NextAction = 'Open /hooks in Codex and trust both handlers.' }
