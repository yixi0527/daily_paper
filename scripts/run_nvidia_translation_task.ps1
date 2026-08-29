param(
    [switch]$Execute,
    [switch]$AssumeTriggerTime
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

if (-not $Execute) {
    Write-Output 'Pass -Execute when launching the scheduled translation task.'
    exit 0
}

$projectRoot = 'D:\04_yixiPrivate\03_myToolApps\daily_paper'
$pythonExecutable = 'D:\01_apps\miniconda3\envs\main\python.exe'
$pythonLibraryBin = 'D:\01_apps\miniconda3\envs\main\Library\bin'
$orchestrator = Join-Path $projectRoot 'scripts\run_daily_nvidia_translation.py'
$gitExecutable = 'C:\Program Files\Git\cmd\git.exe'
$ghExecutable = 'C:\Users\yixi0\AppData\Local\Programs\GitHub CLI\gh.exe'
$ruffExecutable = 'D:\01_apps\miniconda3\envs\main\Scripts\ruff.exe'
$pytestExecutable = 'D:\01_apps\miniconda3\envs\main\Scripts\pytest.exe'
$npmExecutable = 'C:\Users\yixi0\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64\npm.cmd'
$nodeDirectory = Split-Path -Path $npmExecutable -Parent

foreach ($directory in @($projectRoot, $pythonLibraryBin, $nodeDirectory)) {
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        throw ('Required directory is missing: {0}' -f $directory)
    }
}
foreach ($file in @(
        $pythonExecutable,
        $orchestrator,
        $gitExecutable,
        $ghExecutable,
        $ruffExecutable,
        $pytestExecutable,
        $npmExecutable
    )) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw ('Required file is missing: {0}' -f $file)
    }
}
if ([string]::IsNullOrWhiteSpace($env:NVIDIA_API_KEY)) {
    throw 'NVIDIA_API_KEY is not available to the scheduled task user.'
}

$env:PATH = '{0};{1};{2};{3}' -f $pythonLibraryBin, $nodeDirectory, (Split-Path -Path $ghExecutable -Parent), $env:PATH
Set-Location -LiteralPath $projectRoot

$arguments = @(
    '-X',
    'utf8',
    $orchestrator,
    '--project-root',
    $projectRoot,
    '--python-executable',
    $pythonExecutable,
    '--git-executable',
    $gitExecutable,
    '--gh-executable',
    $ghExecutable,
    '--ruff-executable',
    $ruffExecutable,
    '--pytest-executable',
    $pytestExecutable,
    '--npm-executable',
    $npmExecutable,
    '--workers',
    '4',
    '--batch-size',
    '1',
    '--timeout',
    '300',
    '--max-tokens',
    '4096',
    '--wait-seconds',
    '1800'
)
if ($AssumeTriggerTime) {
    $arguments += '--assume-trigger-time'
}
& $pythonExecutable @arguments
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw ('Daily NVIDIA translation automation failed with exit code {0}' -f $exitCode)
}
