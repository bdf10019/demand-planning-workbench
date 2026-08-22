[CmdletBinding()]
param(
    [string]$PythonExecutable = ".\.venv\Scripts\python.exe",
    [int]$TopSkus = 12
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    $workbook = Get-ChildItem -LiteralPath "data\raw\uci-online-retail-ii" -Filter *.xlsx |
        Select-Object -First 1
    if ($null -eq $workbook) {
        throw "Dataset workbook is missing. Run scripts/download-uci-dataset.ps1 first."
    }
    & $PythonExecutable tools/prepare_uci.py $workbook.FullName `
        "data/raw/uci-online-retail-ii/daily-sales.csv" --top-skus $TopSkus
    if ($LASTEXITCODE -ne 0) { throw "Dataset preparation failed." }
}
finally {
    Pop-Location
}
