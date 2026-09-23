$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ProjectRoot "runtime\sylrak.pid"
if (Test-Path -LiteralPath $PidFile) {
    $ServerId = [int](Get-Content -LiteralPath $PidFile -Raw)
    $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $ServerId" -ErrorAction SilentlyContinue
    $ExpectedPython = Join-Path $ProjectRoot '.venv313\Scripts\python.exe'
    if ($Process) {
        if ($Process.ExecutablePath -ne $ExpectedPython -or $Process.CommandLine -notmatch 'backend\.main:app' -or $Process.CommandLine -notmatch '--port 8010') {
            throw 'The recorded process does not match this SylRak server. It was not stopped.'
        }
        # Windows virtual-environment Python may launch a child interpreter and worker.
        $AllProcesses = @(Get-CimInstance Win32_Process)
        $OwnedIds = [System.Collections.Generic.List[int]]::new()
        $OwnedIds.Add($ServerId)
        for ($Index = 0; $Index -lt $OwnedIds.Count; $Index++) {
            foreach ($Child in $AllProcesses) {
                if ($Child.ParentProcessId -eq $OwnedIds[$Index] -and -not $OwnedIds.Contains([int]$Child.ProcessId)) {
                    $OwnedIds.Add([int]$Child.ProcessId)
                }
            }
        }
        for ($Index = $OwnedIds.Count - 1; $Index -ge 0; $Index--) {
            Stop-Process -Id $OwnedIds[$Index] -ErrorAction SilentlyContinue
        }
    }
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "SylRak stopped."
} else {
    Write-Host "No SylRak process started by Start-SylRak.ps1 was recorded."
}
