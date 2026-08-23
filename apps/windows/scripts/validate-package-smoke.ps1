[CmdletBinding()]
param([string]$Package, [switch]$UiMatrix)

$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'Feature 200 package validation requires a Windows host.' }
if ($Package -and -not (Test-Path $Package)) { throw "Package does not exist: $Package" }
if ($Package) { Get-AppxPackage -Path $Package | Out-Null }
Write-Output 'Package smoke requires signed x64 MSIX, clean-image install/update/rollback and WebView2 repair evidence.'
