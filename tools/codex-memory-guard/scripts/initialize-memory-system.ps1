param(
    [Parameter(Mandatory = $true)][string]$Root,
    [switch]$SingleProject
)

$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$templateRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\assets\templates'))

function Copy-TemplateIfMissing([string]$Project, [string]$Template, [string]$Destination) {
    $target = Join-Path $Project $Destination
    if (Test-Path -LiteralPath $target) { return $false }
    $parent = Split-Path -Parent $target
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    $content = [System.IO.File]::ReadAllText((Join-Path $templateRoot $Template), [System.Text.Encoding]::UTF8)
    [System.IO.File]::WriteAllText($target, $content, $utf8)
    return $true
}

$resolvedRoot = [System.IO.Path]::GetFullPath($Root)
if (-not (Test-Path -LiteralPath $resolvedRoot -PathType Container)) { throw "Root directory does not exist: $resolvedRoot" }
$projects = if ($SingleProject) { @(Get-Item -LiteralPath $resolvedRoot) } else { @(Get-ChildItem -LiteralPath $resolvedRoot -Directory -Force) }

$map = [ordered]@{
    'MEMORY_WORKFLOW.md' = 'MEMORY_WORKFLOW.md'
    'HANDOFF.md' = 'HANDOFF.md'
    'DECISIONS.md' = 'DECISIONS.md'
    'LESSONS.md' = 'LESSONS.md'
    'PRE_COMPACTION_CHECKLIST.md' = 'PRE_COMPACTION_CHECKLIST.md'
    'MEMORY_README.md' = 'memory\README.md'
    'DATE_MEMORY.md' = ('memory\{0}.md' -f [DateTime]::Today.ToString('yyyy-MM-dd'))
    'AGENTS.md' = 'AGENTS.md'
}

$rows = foreach ($project in $projects) {
    $created = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $map.GetEnumerator()) {
        if (Copy-TemplateIfMissing $project.FullName $entry.Key $entry.Value) { $created.Add($entry.Value) }
    }
    [System.IO.Directory]::CreateDirectory((Join-Path $project.FullName 'memory\inbox')) | Out-Null
    [pscustomobject]@{ Project = $project.FullName; Created = $created.Count; Preserved = $map.Count - $created.Count }
}

$rows
