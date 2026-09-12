$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ProjectRoot "runtime\sylrak.pid"
if (Test-Path -LiteralPath $PidFile) {
    $ServerId = [int](Get-Content -LiteralPath $PidFile -Raw)
    $Process = Get-Process -Id $ServerId -ErrorAction SilentlyContinue
    if ($Process) { Stop-Process -Id $ServerId }
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "SylRak stopped."
} else {
    Write-Host "No SylRak process started by Start-SylRak.ps1 was recorded."
}
