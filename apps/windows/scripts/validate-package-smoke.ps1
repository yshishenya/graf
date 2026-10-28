[CmdletBinding()]
param([string]$Package, [switch]$UiMatrix)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Feature 200 package validation requires a Windows host.' }
if (-not $Package) {
    Write-Output 'Package path is not supplied; clean-image install/update/rollback and WebView2 repair remain pending host evidence.'
    exit 0
}
if (-not (Test-Path -LiteralPath $Package -PathType Leaf)) { throw "Package does not exist: $Package" }
if ([IO.Path]::GetExtension($Package) -ne '.msix') { throw "Expected an MSIX package: $Package" }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Package).Path)
try {
    $manifestEntry = $archive.GetEntry('AppxManifest.xml')
    if (-not $manifestEntry) { throw 'MSIX does not contain AppxManifest.xml' }
    $reader = New-Object IO.StreamReader($manifestEntry.Open(), [Text.Encoding]::UTF8)
    try { $manifest = [xml]$reader.ReadToEnd() } finally { $reader.Dispose() }

    $ns = New-Object System.Xml.XmlNamespaceManager($manifest.NameTable)
    $ns.AddNamespace('a', 'http://schemas.microsoft.com/appx/manifest/foundation/windows10')
    $identity = $manifest.SelectSingleNode('/a:Package/a:Identity', $ns)
    $application = $manifest.SelectSingleNode('/a:Package/a:Applications/a:Application', $ns)
    if (-not $identity -or -not $application) { throw 'MSIX manifest has no Identity or Application.' }
    $packageName = $identity.GetAttribute('Name')
    $entryPoint = $application.GetAttribute('Executable')
    if ($packageName -ne 'com.graf.desktop') { throw "Unexpected package identity: $packageName" }
    if ($entryPoint -ne 'GrafWindowsApp.exe') { throw "Unexpected entry point: $entryPoint" }

    $capabilities = @($manifest.SelectNodes('/a:Package/a:Capabilities/*/@Name', $ns) | ForEach-Object Value)
    $allowedCapabilities = @('internetClient', 'microphone', 'runFullTrust')
    $unexpectedCapabilities = @($capabilities | Where-Object { $_ -notin $allowedCapabilities })
    if ($unexpectedCapabilities.Count -gt 0) { throw "Unexpected capabilities: $($unexpectedCapabilities -join ', ')" }
    foreach ($required in @('internetClient', 'microphone', 'runFullTrust')) {
        if ($required -notin $capabilities) { throw "Required capability is missing: $required" }
    }

    $forbiddenEntries = @($archive.Entries | Where-Object {
        $_.FullName -match '(?i)(\.sys$|\.msi$|service|driver|elevat|setup\.exe$)'
    })
    if ($forbiddenEntries.Count -gt 0) { throw "Package contains forbidden driver/service/elevation entries: $($forbiddenEntries.FullName -join ', ')" }
} finally {
    $archive.Dispose()
}

$signature = Get-AuthenticodeSignature -LiteralPath $Package
if (-not $signature.SignerCertificate) { throw 'MSIX has no embedded signing certificate.' }
Write-Output ("MSIX static smoke passed: identity={0}, entryPoint={1}, signatureStatus={2}" -f $packageName, $entryPoint, $signature.Status)
if ($UiMatrix) {
    Write-Output 'UI matrix remains a clean-image gate: first launch, WebView2 repair, update interruption, rollback and uninstall are not claimed here.'
}
