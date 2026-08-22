[CmdletBinding()]
param([string]$PythonExecutable = ".\.venv\Scripts\python.exe")

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    & $PythonExecutable -m demand_workbench run --input examples/sales.csv `
        --horizon 14 --database outputs/demo.sqlite3 --output-dir outputs/demo
    if ($LASTEXITCODE -ne 0) { throw "Demo forecast failed." }
    & $PythonExecutable -m demand_workbench verify-output outputs/demo
    if ($LASTEXITCODE -ne 0) { throw "Demo output verification failed." }
}
finally {
    Pop-Location
}
