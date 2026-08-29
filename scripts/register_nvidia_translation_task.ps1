Set-StrictMode -Version 3.0
$ErrorActionPreference = 'Stop'

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$projectRoot = 'D:\04_yixiPrivate\03_myToolApps\daily_paper'
$taskScript = Join-Path $projectRoot 'scripts\run_nvidia_translation_task.ps1'
$pwshExecutable = 'C:\Users\yixi0\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$taskName = 'Daily Paper NVIDIA Translation'
$taskPath = '\'

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) {
    throw ('Project root is missing: {0}' -f $projectRoot)
}
if (-not (Test-Path -LiteralPath $taskScript -PathType Leaf)) {
    throw ('Scheduled task script is missing: {0}' -f $taskScript)
}
if (-not (Test-Path -LiteralPath $pwshExecutable -PathType Leaf)) {
    throw ('PowerShell executable is missing: {0}' -f $pwshExecutable)
}
$userApiKey = [Environment]::GetEnvironmentVariable('NVIDIA_API_KEY', 'User')
if ([string]::IsNullOrWhiteSpace($userApiKey)) {
    throw 'Set NVIDIA_API_KEY as a user environment variable before registering the scheduled task.'
}

$actionArguments = '-NoLogo -NoProfile -NonInteractive -File "{0}" -Execute' -f $taskScript
$action = New-ScheduledTaskAction -Execute $pwshExecutable -Argument $actionArguments -WorkingDirectory $projectRoot
$today = [DateTime]::Today
$trigger0330 = New-ScheduledTaskTrigger -Daily -At $today.AddHours(3).AddMinutes(30)
$trigger0630 = New-ScheduledTaskTrigger -Daily -At $today.AddHours(6).AddMinutes(30)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 4)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $action -Trigger @($trigger0330, $trigger0630) -Settings $settings -Principal $principal -Description 'Translate Daily Paper pending articles through the NVIDIA OpenAI-compatible API.' -Force | Out-Null

$registered = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath
$registeredAction = @($registered.Actions)
$registeredTriggers = @($registered.Triggers)
if ($registeredAction.Count -ne 1) {
    throw ('Expected one registered action; actual={0}' -f $registeredAction.Count)
}
if ($registeredAction[0].Execute -ne $pwshExecutable) {
    throw ('Registered action executable mismatch: {0}' -f $registeredAction[0].Execute)
}
if ($registeredTriggers.Count -ne 2) {
    throw ('Expected two daily triggers; actual={0}' -f $registeredTriggers.Count)
}

[ordered]@{
    task_name = $taskName
    task_path = $taskPath
    action_executable = $registeredAction[0].Execute
    action_arguments = $registeredAction[0].Arguments
    trigger_count = $registeredTriggers.Count
    trigger_times = @(
        $registeredTriggers | ForEach-Object {
            ([DateTime]$_.StartBoundary).ToString('HH:mm')
        }
    )
    multiple_instances = $registered.Settings.MultipleInstances
    user = $registered.Principal.UserId
} | ConvertTo-Json -Depth 5
