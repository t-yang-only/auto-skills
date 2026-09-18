param([ValidateSet('PreCompact', 'SessionStart')][string]$Mode)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$utf8 = [System.Text.UTF8Encoding]::new($false)

function Write-HookJson([hashtable]$Value) {
    [Console]::Out.Write(($Value | ConvertTo-Json -Depth 8 -Compress))
}

function Find-ProjectRoot([string]$Start) {
    $current = [System.IO.DirectoryInfo]::new([System.IO.Path]::GetFullPath($Start))
    while ($null -ne $current) {
        if (Test-Path -LiteralPath (Join-Path $current.FullName 'MEMORY_WORKFLOW.md')) { return $current.FullName }
        $current = $current.Parent
    }
    return [System.IO.Path]::GetFullPath($Start)
}

try {
    $inputData = ([Console]::In.ReadToEnd()) | ConvertFrom-Json
    $projectRoot = Find-ProjectRoot ([string]$inputData.cwd)
    $inbox = Join-Path $projectRoot 'memory\inbox'
    [System.IO.Directory]::CreateDirectory($inbox) | Out-Null
    $safeSession = ([string]$inputData.session_id) -replace '[^A-Za-z0-9._-]', '_'
    $pendingPath = Join-Path $inbox ("pending-{0}.json" -f $safeSession)

    if ($Mode -eq 'PreCompact') {
        $handoffPath = Join-Path $projectRoot 'HANDOFF.md'
        $handoffCheck = & (Join-Path $PSScriptRoot 'validate-handoff.ps1') -Path $handoffPath -NoFail
        $record = [ordered]@{
            schema_version = 2
            status = 'awaiting_extraction'
            captured_at = [DateTimeOffset]::Now.ToString('o')
            project_root = $projectRoot
            cwd = [string]$inputData.cwd
            session_id = [string]$inputData.session_id
            turn_id = [string]$inputData.turn_id
            trigger = [string]$inputData.trigger
            transcript_path = [string]$inputData.transcript_path
            handoff_check = [ordered]@{
                path = [string]$handoffCheck.Path
                exists = [bool]$handoffCheck.Exists
                status = [string]$handoffCheck.Status
                characters = [int]$handoffCheck.Characters
                last_write_at = $handoffCheck.LastWriteAt
                sha256 = $handoffCheck.Sha256
                recovery_required = [bool]$handoffCheck.RecoveryRequired
                issues = @($handoffCheck.Issues)
            }
        }
        [System.IO.File]::WriteAllText($pendingPath, ($record | ConvertTo-Json -Depth 6), $utf8)
        Write-HookJson @{ continue = $true; systemMessage = "Pre-compaction memory evidence registered: $pendingPath; HANDOFF status: $($handoffCheck.Status)" }
        exit 0
    }

    if ($Mode -eq 'SessionStart' -and (Test-Path -LiteralPath $pendingPath)) {
        $pending = [System.IO.File]::ReadAllText($pendingPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        $needsRecovery = [bool]$pending.handoff_check.recovery_required
        $recoveryInstruction = if ($needsRecovery) { "HANDOFF validation failed for: $(@($pending.handoff_check.issues) -join ', '). Search only relevant transcript fragments and repair HANDOFF.md before continuing." } else { 'HANDOFF passed the pre-compaction check. Continue from it without loading the transcript unless the current state conflicts or critical information is missing.' }
        $context = "Before continuing the user's task, read $pendingPath and the project's short HANDOFF.md first. $recoveryInstruction Keep HANDOFF.md to one current goal, one next action, at most three milestones, and no more than 1500 characters. Update today's memory/YYYY-MM-DD.md only when unconfirmed candidates need preservation. Promote only confirmed decisions or verified lessons, read back critical writes, never store secrets, then set the pending record to processed with processed_at and record whether HANDOFF was repaired."
        Write-HookJson @{ continue = $true; hookSpecificOutput = @{ hookEventName = 'SessionStart'; additionalContext = $context } }
        exit 0
    }

    Write-HookJson @{ continue = $true }
}
catch {
    Write-HookJson @{ continue = $true; systemMessage = "Codex Memory Guard failed: $($_.Exception.Message)" }
}
