[CmdletBinding()]
param(
    [string]$PythonExecutable = ".\.venv\Scripts\python.exe",
    [string]$PnpmExecutable = "pnpm"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    & $PythonExecutable -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Python dependency check failed." }
    & $PythonExecutable -m compileall -q src tools
    if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }
    & $PythonExecutable -m ruff check src tests tools
    if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }
    & $PythonExecutable -m mypy src
    if ($LASTEXITCODE -ne 0) { throw "Mypy failed." }
    & $PythonExecutable -m pytest --cov=demand_workbench --cov-report=term-missing
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }

    Push-Location frontend
    try {
        & $PnpmExecutable install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency install failed." }
        & $PnpmExecutable typecheck
        if ($LASTEXITCODE -ne 0) { throw "Frontend typecheck failed." }
        & $PnpmExecutable test
        if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
        & $PnpmExecutable build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
    }
    finally { Pop-Location }

    & $PythonExecutable -m demand_workbench doctor
    if ($LASTEXITCODE -ne 0) { throw "Runtime diagnostics failed." }
    & (Join-Path $PSScriptRoot "privacy-check.ps1")
    if ($LASTEXITCODE -ne 0) { throw "Privacy check failed." }
    Write-Host "All verification stages passed."
}
finally {
    Pop-Location
}
