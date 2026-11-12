Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$projectRoot = Split-Path -Path $PSScriptRoot -Parent
$python = 'D:\01_apps\miniconda3\envs\main\python.exe'
$guard = 'C:\Users\yixi0\.codex\bin\CodexPowerShellGuard.exe'
$runtime = Join-Path $projectRoot 'data\site-workflow'
$logDirectory = Join-Path $runtime 'task-logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$runName = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fffffff')
$prepareOutput = Join-Path $logDirectory "$runName.prepare.json"
$stdoutPath = Join-Path $logDirectory "$runName.stdout.log"
$stderrPath = Join-Path $logDirectory "$runName.stderr.log"
& $python -X utf8 (Join-Path $projectRoot 'scripts\prepare_site_update.py') 1> $prepareOutput 2> $stderrPath
$prepareExit = $LASTEXITCODE
$taskExit = $prepareExit
$stage = 'prepare'
if ($prepareExit -eq 0) {
    $prepared = Get-Content -LiteralPath $prepareOutput -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
    if ($prepared['status'] -eq 'published') {
        $stage = 'already-published'
    } else {
        $stage = 'pipeline'
        $updateScript = Join-Path $prepared['checkout_path'] 'scripts\run_sites_update.ps1'
        & $guard --run-file $updateScript 1> $stdoutPath 2>> $stderrPath
        $taskExit = $LASTEXITCODE
        $statePath = Join-Path $runtime 'state.json'
        if (Test-Path -LiteralPath $statePath -PathType Leaf) {
            $state = Get-Content -LiteralPath $statePath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
            $stage = $state['stage']
            if ($state['status'] -eq 'published') { $stage = 'published' }
        }
    }
}
$result = [ordered]@{
    finished_at = [DateTime]::UtcNow.ToString('o')
    stage = $stage
    exit_code = $taskExit
    stdout = $stdoutPath
    stderr = $stderrPath
}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'automation-last-run.json') -Encoding utf8
$result | ConvertTo-Json
exit $taskExit
