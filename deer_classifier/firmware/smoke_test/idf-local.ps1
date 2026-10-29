# Use the project-local ESP-IDF tools installed during development.
# For a normal ESP-IDF installation, use idf.py directly in its terminal instead.
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$env:IDF_PATH = Join-Path $taskRoot '.tools/esp-idf'
$env:IDF_TOOLS_PATH = Join-Path $taskRoot '.tools/idf-tools'
$idfPython = Get-ChildItem -Path (Join-Path $env:IDF_TOOLS_PATH 'python_env/*/Scripts/python.exe') | Select-Object -First 1 -ExpandProperty FullName
if (-not $idfPython -or -not (Test-Path -LiteralPath (Join-Path $env:IDF_PATH 'tools/idf.py'))) {
    throw 'Project-local ESP-IDF tools are missing. Install ESP-IDF 5.4.x and use its terminal.'
}
$toolExports = & $idfPython (Join-Path $env:IDF_PATH 'tools/idf_tools.py') export --format key-value
if ($LASTEXITCODE -ne 0) { throw 'ESP-IDF tool activation failed.' }
foreach ($line in $toolExports) {
    if ($line -match '^([A-Z_]+)=(.*)$') {
        $value = $Matches[2].Replace('%PATH%', $env:PATH)
        [Environment]::SetEnvironmentVariable($Matches[1], $value, 'Process')
    }
}
$env:IDF_TARGET = 'esp32s3'
Push-Location $PSScriptRoot
try {
    & $idfPython (Join-Path $env:IDF_PATH 'tools/idf.py') @args
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
