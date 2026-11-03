[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Package smoke tests require Windows.' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.IO.Compression
$testDirectory = Join-Path ([IO.Path]::GetTempPath()) ('graf-package-smoke-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($testDirectory) | Out-Null
$testPackage = Join-Path $testDirectory 'fixture.msix'
$archive = [IO.Compression.ZipFile]::Open($testPackage, [IO.Compression.ZipArchiveMode]::Create)
try {
    $writer = New-Object IO.StreamWriter($archive.CreateEntry('AppxManifest.xml').Open())
    try {
        $writer.Write(@'
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10">
  <Identity Name="com.graf.desktop" Publisher="CN=GRAF" Version="0.1.0.0" />
  <Resources><Resource Language="ru-RU" /></Resources>
  <Applications><Application Executable="GrafWindowsApp.exe" /></Applications>
  <Capabilities><Capability Name="internetClient" /><Capability Name="microphone" /><Capability Name="runFullTrust" /></Capabilities>
</Package>
'@)
    } finally { $writer.Dispose() }
} finally { $archive.Dispose() }

# Simulate only the OS signature result. The real validator still opens and
# checks the fixture archive. This is not a signed-package or clean-image test.
function Get-AuthenticodeSignature {
    param([string]$LiteralPath)
    if ($LiteralPath -ne $testPackage) { throw 'Unexpected signature target in test.' }
    return $testSignatureResult
}

try {
    $cases = @(
        @{ Status = 'Valid'; Certificate = $true; Pass = $true },
        @{ Status = 'NotTrusted'; Certificate = $true; Pass = $false },
        @{ Status = 'HashMismatch'; Certificate = $true; Pass = $false },
        @{ Status = 'UnknownError'; Certificate = $true; Pass = $false },
        @{ Status = 'NotSigned'; Certificate = $false; Pass = $false },
        @{ Status = 'Valid'; Certificate = $false; Pass = $false }
    )
    foreach ($case in $cases) {
        $testSignatureResult = [pscustomobject]@{
            Status = $case.Status
            SignerCertificate = if ($case.Certificate) { [pscustomobject]@{ Subject = 'CN=GRAF' } } else { $null }
        }
        $passed = $true
        $failure = ''
        try { & (Join-Path $PSScriptRoot 'validate-package-smoke.ps1') -Package $testPackage | Out-Null }
        catch { $passed = $false; $failure = $_.Exception.Message }
        if ($passed -ne $case.Pass) { throw "Incorrect signature gate: status=$($case.Status), certificate=$($case.Certificate), accepted=$passed; $failure" }
    }
    Write-Output "Package signature gate tests: $($cases.Count)/$($cases.Count) PASS (simulated OS results)."
    $testSignatureResult = [pscustomobject]@{
        Status = 'Valid'
        SignerCertificate = [pscustomobject]@{ Subject = 'CN=GRAF' }
    }
    # A native COM host must not ship the C#/WinRT projection, even when the
    # archive has a trusted signature. Test root and nested/case variants.
    $projectionPaths = @('Microsoft.Web.WebView2.Core.Projection.dll', 'nested/MICROSOFT.WEB.WEBVIEW2.CORE.PROJECTION.DLL')
    foreach ($projectionPath in $projectionPaths) {
        $archive = [IO.Compression.ZipFile]::Open($testPackage, [IO.Compression.ZipArchiveMode]::Update)
        try { $archive.CreateEntry($projectionPath) | Out-Null } finally { $archive.Dispose() }
        $failure = ''
        try { & (Join-Path $PSScriptRoot 'validate-package-smoke.ps1') -Package $testPackage | Out-Null }
        catch { $failure = $_.Exception.Message }
        if ($failure -notlike 'Native package contains a managed WebView2 projection:*') {
            throw "Managed WebView2 projection was not rejected: $projectionPath"
        }
        $archive = [IO.Compression.ZipFile]::Open($testPackage, [IO.Compression.ZipArchiveMode]::Update)
        try { $archive.GetEntry($projectionPath).Delete() } finally { $archive.Dispose() }
    }
    Write-Output "Native WebView2 payload tests: $($projectionPaths.Count)/$($projectionPaths.Count) PASS."
    $archive = [IO.Compression.ZipFile]::OpenRead($testPackage)
    try {
        $reader = New-Object IO.StreamReader($archive.GetEntry('AppxManifest.xml').Open())
        try { $fixtureManifest = $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $archive.Dispose() }
    $languageCases = @(
        @{ Language = 'en-US'; Pass = $false },
        @{ Language = $null; Pass = $false },
        @{ Language = ''; Pass = $false },
        @{ Language = 'ru'; Pass = $true },
        @{ Language = 'RU-ru'; Pass = $true },
        @{ Language = 'ru-RU'; Pass = $true }
    )
    foreach ($case in $languageCases) {
        $archive = [IO.Compression.ZipFile]::Open($testPackage, [IO.Compression.ZipArchiveMode]::Update)
        try {
            $archive.GetEntry('AppxManifest.xml').Delete()
            $writer = New-Object IO.StreamWriter($archive.CreateEntry('AppxManifest.xml').Open())
            $language = if ($null -eq $case.Language) { '' } else { 'Language="' + $case.Language + '"' }
            try { $writer.Write($fixtureManifest.Replace('Language="ru-RU"', $language)) }
            finally { $writer.Dispose() }
        } finally { $archive.Dispose() }
        $passed = $true
        try { & (Join-Path $PSScriptRoot 'validate-package-smoke.ps1') -Package $testPackage | Out-Null }
        catch { $passed = $false }
        if ($passed -ne $case.Pass) { throw "Package resource language gate failed: $($case.Language)" }
    }
    Write-Output "Package resource language tests: $($languageCases.Count)/$($languageCases.Count) PASS."
} finally {
    # Only the exact generated fixture and its now-empty directory are removed.
    [IO.File]::Delete($testPackage)
    [IO.Directory]::Delete($testDirectory)
}
