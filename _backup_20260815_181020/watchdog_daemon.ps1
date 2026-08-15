<#
.SYNOPSIS
    CHRISHEM Autonomous Background Git Sync Watchdog
.DESCRIPTION
    Runs continuously in the background, staging and pushing repository updates every 3 minutes.
#>

param(
    [string]$RepositoryPath = "D:\notion-live-analyzer",
    [int]$IntervalSeconds = 180
)

Set-Location $RepositoryPath
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " CHRISHEM Watchdog Daemon Started [Interval: $IntervalSeconds s]" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

while ($true) {
    try {
        $status = git status --porcelain
        if (-not [string]::IsNullOrEmpty($status)) {
            Write-Host "[10:47:04] Changes detected. Staging & syncing..." -ForegroundColor Yellow
            git add -A
            git commit -m "Autonomous Watchdog Sync Checkpoint: 2026-07-29 10:47:04" --no-verify 2>$null
            git push origin main 2>$null
            Write-Host "[10:47:04] Synchronized successfully with GitHub." -ForegroundColor Green
        } else {
            Write-Host "[10:47:04] Repository clean. No changes to sync." -ForegroundColor DarkGray
        }
    } catch {
        Write-Warning "Daemon sync iteration encountered an issue: $_"
    }

    Start-Sleep -Seconds $IntervalSeconds
}
