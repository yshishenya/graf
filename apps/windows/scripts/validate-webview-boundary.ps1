[CmdletBinding()]
param([switch]$Contract)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Feature 200 WebView2 validation requires a Windows host.' }
$build = Join-Path (Split-Path -Parent $PSScriptRoot) 'out\build\x64\Release'
if (-not (Test-Path $build)) { throw "Build output is missing: $build" }
& ctest --test-dir $build -R 'WebView|Bridge|Route' --output-on-failure
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output 'WebView2 boundary validation passed.'
