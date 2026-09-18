param([string]$ScratchRoot = (Join-Path ([System.IO.Path]::GetTempPath()) 'codex-memory-guard-test'))

$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $ScratchRoot) { throw "ScratchRoot already exists; choose an empty path: $ScratchRoot" }
[System.IO.Directory]::CreateDirectory($ScratchRoot) | Out-Null
try {
    $firstInit = & (Join-Path $PSScriptRoot 'initialize-memory-system.ps1') -Root $ScratchRoot -SingleProject
    $secondInit = & (Join-Path $PSScriptRoot 'initialize-memory-system.ps1') -Root $ScratchRoot -SingleProject
    if ($firstInit.Created -ne 8 -or $secondInit.Created -ne 0) { throw 'Initialization idempotency test failed.' }
    $dateMemory = 'memory\{0}.md' -f [DateTime]::Today.ToString('yyyy-MM-dd')
    foreach ($required in @('HANDOFF.md', 'DECISIONS.md', 'LESSONS.md', 'memory\README.md', $dateMemory)) {
        if (-not (Test-Path -LiteralPath (Join-Path $ScratchRoot $required))) { throw "Missing memory artifact: $required" }
    }

    $handoffPath = Join-Path $ScratchRoot 'HANDOFF.md'
    $handoffContent = "# Handoff`n`n## Goal`n`n- Validate the pre-compaction check.`n`n## State`n`n- Active.`n`n## Milestones`n`n- Initialized.`n`n## Blockers`n`n- None.`n`n## Next`n`n- Run isolated regression.`n`n## Files`n`n- HANDOFF.md`n"
    [System.IO.File]::WriteAllText($handoffPath, $handoffContent, [System.Text.UTF8Encoding]::new($false))

    $payload = @{ session_id = 'smoke'; transcript_path = (Join-Path $ScratchRoot 'rollout.jsonl'); cwd = $ScratchRoot; hook_event_name = 'PreCompact'; model = 'test'; turn_id = 'turn'; trigger = 'auto' } | ConvertTo-Json -Compress
    $inputFile = Join-Path $ScratchRoot 'precompact.json'
    [System.IO.File]::WriteAllText($inputFile, $payload, [System.Text.UTF8Encoding]::new($false))
    $output = cmd /d /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\codex-memory-guard.ps1`" -Mode PreCompact < `"$inputFile`""
    $result = $output | ConvertFrom-Json
    $pending = Join-Path $ScratchRoot 'memory\inbox\pending-smoke.json'
    if (-not $result.continue -or -not (Test-Path -LiteralPath $pending)) { throw 'PreCompact smoke test failed.' }
    $pendingRecord = Get-Content -LiteralPath $pending -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($pendingRecord.PSObject.Properties['transcript_content']) { throw 'Pending record copied transcript content.' }
    if ($pendingRecord.schema_version -ne 2 -or $pendingRecord.handoff_check.status -ne 'ready' -or $pendingRecord.handoff_check.recovery_required) { throw 'Ready HANDOFF pre-compaction check failed.' }
    if ([string]::IsNullOrWhiteSpace([string]$pendingRecord.handoff_check.sha256) -or [string]::IsNullOrWhiteSpace([string]$pendingRecord.handoff_check.last_write_at)) { throw 'HANDOFF evidence metadata is incomplete.' }

    $resumePayload = @{ session_id = 'smoke'; transcript_path = (Join-Path $ScratchRoot 'rollout.jsonl'); cwd = $ScratchRoot; hook_event_name = 'SessionStart'; model = 'test'; turn_id = 'turn-2'; source = 'compact' } | ConvertTo-Json -Compress
    $resumeInput = Join-Path $ScratchRoot 'sessionstart.json'
    [System.IO.File]::WriteAllText($resumeInput, $resumePayload, [System.Text.UTF8Encoding]::new($false))
    $resumeOutput = cmd /d /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\codex-memory-guard.ps1`" -Mode SessionStart < `"$resumeInput`""
    $resumeResult = $resumeOutput | ConvertFrom-Json
    $context = [string]$resumeResult.hookSpecificOutput.additionalContext
    if (-not $context.Contains('HANDOFF.md first') -or -not $context.Contains('passed the pre-compaction check') -or -not $context.Contains('without loading the transcript')) { throw 'Ready HANDOFF resume test failed.' }

    $invalidRoot = Join-Path $ScratchRoot 'invalid-project'
    [System.IO.Directory]::CreateDirectory($invalidRoot) | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $invalidRoot 'MEMORY_WORKFLOW.md'), '# marker', [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $invalidRoot 'HANDOFF.md'), "# Handoff`n`n## Goal`n`n- (TODO)`n", [System.Text.UTF8Encoding]::new($false))
    $invalidPayload = @{ session_id = 'invalid'; transcript_path = (Join-Path $invalidRoot 'rollout.jsonl'); cwd = $invalidRoot; hook_event_name = 'PreCompact'; turn_id = 'turn'; trigger = 'manual' } | ConvertTo-Json -Compress
    $invalidInput = Join-Path $ScratchRoot 'invalid-precompact.json'
    [System.IO.File]::WriteAllText($invalidInput, $invalidPayload, [System.Text.UTF8Encoding]::new($false))
    cmd /d /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\codex-memory-guard.ps1`" -Mode PreCompact < `"$invalidInput`"" | Out-Null
    $invalidPending = Join-Path $invalidRoot 'memory\inbox\pending-invalid.json'
    $invalidRecord = Get-Content -LiteralPath $invalidPending -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $invalidRecord.handoff_check.recovery_required -or @($invalidRecord.handoff_check.issues).Count -eq 0) { throw 'Invalid HANDOFF was not marked for recovery.' }
    $invalidResumePayload = @{ session_id = 'invalid'; transcript_path = (Join-Path $invalidRoot 'rollout.jsonl'); cwd = $invalidRoot; hook_event_name = 'SessionStart'; turn_id = 'turn-2'; source = 'compact' } | ConvertTo-Json -Compress
    $invalidResumeInput = Join-Path $ScratchRoot 'invalid-sessionstart.json'
    [System.IO.File]::WriteAllText($invalidResumeInput, $invalidResumePayload, [System.Text.UTF8Encoding]::new($false))
    $invalidResumeOutput = cmd /d /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\codex-memory-guard.ps1`" -Mode SessionStart < `"$invalidResumeInput`""
    $invalidContext = [string](($invalidResumeOutput | ConvertFrom-Json).hookSpecificOutput.additionalContext)
    if (-not $invalidContext.Contains('validation failed') -or -not $invalidContext.Contains('repair HANDOFF.md before continuing')) { throw 'Recovery-required resume test failed.' }

    $validationOutput = & (Join-Path $PSScriptRoot 'validate-handoff.ps1') -Path (Join-Path $ScratchRoot 'HANDOFF.md')
    if ($validationOutput.Status -ne 'ready' -or $validationOutput.RecoveryRequired) { throw 'Valid HANDOFF structure test failed.' }

    $oversized = Join-Path $ScratchRoot 'oversized-handoff.md'
    [System.IO.File]::WriteAllText($oversized, ('x' * 1501), [System.Text.UTF8Encoding]::new($false))
    $validator = Join-Path $PSScriptRoot 'validate-handoff.ps1'
    & powershell -NoProfile -ExecutionPolicy Bypass -File $validator -Path $oversized | Out-Null
    if ($LASTEXITCODE -ne 1) { throw 'HANDOFF hard-limit failure test failed.' }

    $fakeCodexHome = Join-Path $ScratchRoot '.codex'
    [System.IO.Directory]::CreateDirectory($fakeCodexHome) | Out-Null
    $existingHooks = @{
        description = 'Existing test hooks'
        hooks = @{
            Stop = @(@{
                matcher = '*'
                hooks = @(@{ type = 'command'; command = 'existing-stop-handler'; timeout = 5 })
            })
        }
    } | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText((Join-Path $fakeCodexHome 'hooks.json'), $existingHooks, [System.Text.UTF8Encoding]::new($false))
    $agentsPath = Join-Path $fakeCodexHome 'AGENTS.md'
    [System.IO.File]::WriteAllText($agentsPath, "# Existing global rules`r`n`r`nKEEP-USER-RULE`r`n", [System.Text.UTF8Encoding]::new($false))

    & (Join-Path $PSScriptRoot 'install.ps1') -CodexHome $fakeCodexHome -ProjectRoot $ScratchRoot | Out-Null
    & (Join-Path $PSScriptRoot 'install.ps1') -CodexHome $fakeCodexHome -ProjectRoot $ScratchRoot | Out-Null
    $installedConfig = Get-Content -LiteralPath (Join-Path $fakeCodexHome 'hooks.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if (@($installedConfig.hooks.Stop).Count -ne 1) { throw 'Existing Hook preservation test failed.' }
    if (@($installedConfig.hooks.PreCompact).Count -ne 1 -or @($installedConfig.hooks.SessionStart).Count -ne 1) { throw 'Hook installation idempotency test failed.' }
    if (-not (Test-Path -LiteralPath (Join-Path $fakeCodexHome 'hooks\validate-handoff.ps1'))) { throw 'Installed Hook validator is missing.' }
    $installedAgents = [System.IO.File]::ReadAllText($agentsPath, [System.Text.Encoding]::UTF8)
    if (-not $installedAgents.Contains('KEEP-USER-RULE')) { throw 'Global AGENTS merge removed user content.' }
    if (($installedAgents.Split(@('<!-- codex-memory-guard:start -->'), [System.StringSplitOptions]::None).Count - 1) -ne 1) { throw 'Global AGENTS installation is not idempotent.' }
    if (-not $installedAgents.Contains('compare each new input with that goal before estimating duration')) { throw 'Global AGENTS lacks relevance-first boundary evaluation.' }
    if (-not $installedAgents.Contains('even if it may take only one or two turns')) { throw 'Global AGENTS incorrectly exempts unrelated short topics.' }
    if (-not $installedAgents.Contains('suppress repeats for that boundary')) { throw 'Global AGENTS lacks boundary reminder suppression.' }

    & (Join-Path $PSScriptRoot 'uninstall.ps1') -CodexHome $fakeCodexHome | Out-Null
    $uninstalledConfig = Get-Content -LiteralPath (Join-Path $fakeCodexHome 'hooks.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if (@($uninstalledConfig.hooks.Stop).Count -ne 1) { throw 'Uninstall removed an unrelated Hook.' }
    if (@($uninstalledConfig.hooks.PreCompact | Where-Object { $null -ne $_ }).Count -ne 0 -or @($uninstalledConfig.hooks.SessionStart | Where-Object { $null -ne $_ }).Count -ne 0) { throw 'Uninstall left Skill handlers behind.' }
    if (Test-Path -LiteralPath (Join-Path $fakeCodexHome 'hooks\validate-handoff.ps1')) { throw 'Uninstall left the Hook validator behind.' }
    $uninstalledAgents = [System.IO.File]::ReadAllText($agentsPath, [System.Text.Encoding]::UTF8)
    if (-not $uninstalledAgents.Contains('KEEP-USER-RULE')) { throw 'Uninstall removed user AGENTS content.' }
    if ($uninstalledAgents.Contains('codex-memory-guard:start')) { throw 'Uninstall left the managed AGENTS block behind.' }

    [pscustomobject]@{
        Passed = $true
        Pending = $pending
        InitializationIdempotent = $true
        SelectiveResume = $true
        PreCompactHandoffCheck = $true
        RecoveryRequiredResume = $true
        HandoffLimit = $true
        InstallMerge = $true
        InstallIdempotent = $true
        UninstallScoped = $true
        GlobalAgentsMerge = $true
        GlobalAgentsIdempotent = $true
        GlobalAgentsUninstallScoped = $true
        Note = 'Scratch directory intentionally retained for inspection.'
    }
} catch { throw }
