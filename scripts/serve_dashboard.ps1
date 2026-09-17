$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    & python "dashboard.py" serve
}
finally {
    Pop-Location
}
