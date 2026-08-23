[CmdletBinding()]
param(
    [switch]$Synthetic,
    [switch]$HardwareMatrix,
    [switch]$CustodyFaults,
    [string]$Os,
    [string]$Inputs,
    [string]$Outputs
)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Feature 200 Windows validation requires a Windows host.' }
$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $root 'out\build\x64\Release'
if (-not (Test-Path $build)) { throw "Build output is missing: $build" }
$patterns = @('Timeline|AEC3|Writer')
if ($HardwareMatrix) { $patterns += 'Capture|Hardware' }
if ($CustodyFaults) { $patterns += 'Custody|Queue|Upload' }
foreach ($pattern in $patterns) {
    & ctest --test-dir $build -R $pattern --output-on-failure
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Output ('audio-contract validation passed: ' + ($patterns -join ', '))
