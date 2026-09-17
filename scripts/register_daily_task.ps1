param(
    [ValidatePattern("^([01]\d|2[0-3]):[0-5]\d$")]
    [string]$Time = "07:30"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$updateScript = Join-Path $PSScriptRoot "update_dashboard.ps1"
$powerShell = (Get-Command powershell.exe).Source
$taskName = "AI Research Dashboard - Daily Update"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$updateScript`""

$action = New-ScheduledTaskAction -Execute $powerShell -Argument $arguments -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "AI 뉴스, 논문, 학회 정보를 수집하고 Signal 대시보드를 갱신합니다." -Force
Write-Host "등록 완료: $taskName (매일 $Time)"
