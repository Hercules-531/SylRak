$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv313\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($Uv) {
        & $Uv.Source venv --python 3.13 .venv313
        & $Uv.Source pip install --python $Python -r backend\requirements.txt
    } else {
        py -3.13 -m venv .venv313
        & $Python -m pip install -r backend\requirements.txt
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "node_modules"))) {
    npm ci
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "assets\map\delhi.pmtiles")) -or
    -not (Test-Path -LiteralPath (Join-Path $ProjectRoot "assets\models\yolov8n.pt"))) {
    throw "Offline map or model assets are missing. Restore the project's assets folder before presenting."
}

Write-Host "Building SylRak dashboard..." -ForegroundColor Cyan
npm run build

$Healthy = $false
try {
    $Status = Invoke-RestMethod -Uri "http://127.0.0.1:8010/api/v1/health" -TimeoutSec 2
    $Healthy = $Status.service -eq "sylrak"
} catch {}

if (-not $Healthy) {
    $Server = Start-Process -FilePath $Python -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8010") -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath (Join-Path $ProjectRoot "runtime\sylrak.pid") -Value $Server.Id
    for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $Status = Invoke-RestMethod -Uri "http://127.0.0.1:8010/api/v1/health" -TimeoutSec 2
            if ($Status.service -eq "sylrak") { $Healthy = $true; break }
        } catch {}
    }
}
if (-not $Healthy) { throw "SylRak did not start. Run .\.venv313\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8010 to see the error." }

Write-Host ""
Write-Host "SylRak is ready: http://127.0.0.1:8010" -ForegroundColor Green
Write-Host "Opens directly. No username or password is required."
Write-Host "Quick demo searches: KL22L9038 and DL8CAF2041"
Write-Host "Description demo: white / car / mid-size / Honda City"
Start-Process "http://127.0.0.1:8010"
