Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$projectRoot = Split-Path -Path $PSScriptRoot -Parent
$python = 'D:\01_apps\miniconda3\envs\main\python.exe'
$env:PATH = "D:\01_apps\miniconda3\envs\main\Library\bin;$env:PATH"
$env:PYTHONPATH = Join-Path $projectRoot 'apps\api'
$git = 'C:\Program Files\Git\cmd\git.exe'
$gitCommon = & $git -C $projectRoot rev-parse --git-common-dir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not [System.IO.Path]::IsPathRooted($gitCommon)) { $gitCommon = Join-Path $projectRoot $gitCommon }
$projectHome = Split-Path -Path (Get-Item -LiteralPath $gitCommon -Force).FullName -Parent
$runtime = Join-Path $projectHome 'data\site-workflow'
$env:DAILY_PAPER_RUNTIME_DIR = $runtime
$database = (Join-Path $runtime 'library.sqlite').Replace('\', '/')
$env:DATABASE_URL = "sqlite:///$database"
$env:APP_DEBUG = 'false'
$env:NVIDIA_API_KEY = [Environment]::GetEnvironmentVariable('NVIDIA_API_KEY', 'User')
Set-Location -LiteralPath $projectRoot
$statePath = Join-Path $runtime 'state.json'
$readyToPublish = $false
if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $state = Get-Content -LiteralPath $statePath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
    $readyToPublish = $state['status'] -eq 'ready'
}
if (-not $readyToPublish) {
    & $python -X utf8 (Join-Path $projectRoot 'scripts\site_workflow.py')
    $updateExit = $LASTEXITCODE
    if ($updateExit -ne 0) { exit $updateExit }
}
& $python -X utf8 (Join-Path $projectRoot 'scripts\publish_github_pages.py')
exit $LASTEXITCODE
