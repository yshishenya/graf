[CmdletBinding()]
param(
    [switch]$Synthetic,
    [switch]$CustodyFaults
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Feature 200 Windows validation requires a Windows host.' }
$root = Split-Path -Parent $PSScriptRoot
$build = Join-Path $root 'out\build\x64\Release'
if (-not (Test-Path $build)) { throw "Build output is missing: $build" }
$patterns = @()
if ($Synthetic -or $CustodyFaults) { $patterns += 'Timeline|AudioNormalizer|CaptureFaultState|AEC3|Writer' }
if ($CustodyFaults) { $patterns += 'Custody|Queue|Upload' }
if ($patterns.Count -eq 0) { throw 'Select -Synthetic or -CustodyFaults. Hardware capture acceptance is manual.' }
foreach ($pattern in $patterns) {
    & ctest --test-dir $build -R $pattern --output-on-failure
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Output ('audio-contract validation passed: ' + ($patterns -join ', '))
