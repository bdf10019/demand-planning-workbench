[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$rawRoot = (Resolve-Path (Join-Path $projectRoot "data\raw")).Path
$target = Join-Path $rawRoot "uci-online-retail-ii"
$archive = Join-Path $target "online-retail-ii.zip"
$url = "https://archive.ics.uci.edu/static/public/502/online%2Bretail%2Bii.zip"

if (-not $target.StartsWith($rawRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Resolved dataset target escaped data/raw."
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
if ($Force -or -not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest -Uri $url -OutFile $archive
}
if ((Get-Item -LiteralPath $archive).Length -lt 1MB) {
    throw "Downloaded archive is unexpectedly small."
}
Expand-Archive -LiteralPath $archive -DestinationPath $target -Force
$workbook = Get-ChildItem -LiteralPath $target -Filter *.xlsx | Select-Object -First 1
if ($null -eq $workbook) { throw "The downloaded archive did not contain an XLSX workbook." }
Write-Host "Dataset workbook: $($workbook.FullName)"
Write-Host "The dataset remains under data/raw and is ignored by Git."
