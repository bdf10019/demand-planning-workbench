[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    $tracked = @(git ls-files)
    if ($LASTEXITCODE -ne 0) { throw "Git file listing failed." }
    if ($tracked.Count -eq 0) { throw "No tracked files were found; stage files before scanning." }

    $sensitiveExtensions = '\.(pem|p12|pfx|key|sqlite|sqlite3|db|bak|dump)$'
    $sensitiveNames = '(^|/)(\.env|credentials\.json|secrets?\.(json|ya?ml))$'
    $blocked = @(
        $tracked | Where-Object {
            $_ -match $sensitiveExtensions -or
            ($_ -match $sensitiveNames -and $_ -ne '.env.example')
        }
    )
    if ($blocked.Count -gt 0) {
        Write-Error "Sensitive file names are tracked: $($blocked -join ', ')"
    }

    $oversized = @()
    foreach ($relativePath in $tracked) {
        $objectSize = git cat-file -s ":$relativePath"
        if ($LASTEXITCODE -ne 0) { throw "Could not inspect staged file: $relativePath" }
        if ([long]$objectSize -gt 1MB) { $oversized += $relativePath }
    }
    if ($oversized.Count -gt 0) {
        Write-Error "Tracked files exceed 1 MiB: $($oversized -join ', ')"
    }

    $patterns = @(
        'sk-[A-Za-z0-9_-]{20,}',
        'sk-ant-[A-Za-z0-9_-]{16,}',
        'AIza[0-9A-Za-z_-]{20,}',
        'gh[pousr]_[A-Za-z0-9]{20,}',
        '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'C:\\Users\\',
        'jobsource=',
        'joblist_'
    )
    $secretPattern = '(' + ($patterns -join '|') + ')'
    $matches = @(git grep -I -l -E $secretPattern -- ':!scripts/privacy-check.ps1')
    if ($LASTEXITCODE -eq 0 -and $matches.Count -gt 0) {
        Write-Error "Potential secret, private path, or source-specific identifier found in: $($matches -join ', ')"
    }
    if ($LASTEXITCODE -gt 1) { throw "Git content scan failed." }

    Write-Host "Privacy check passed: $($tracked.Count) tracked files scanned."
    exit 0
}
finally {
    Pop-Location
}
