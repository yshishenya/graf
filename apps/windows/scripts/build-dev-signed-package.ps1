#Requires -Version 5.1
<#
.SYNOPSIS
    Signs a GRAF Windows MSIX with a locally generated development certificate.

.DESCRIPTION
    Feature 200 / T070. The public release is out of scope for this slice, so the
    package is signed with a self-signed development certificate. The certificate
    subject must match Publisher in Installer/Package.appxmanifest exactly, which
    is why the default is CN=GRAF.

    The private key is written only to a directory outside the repository and is
    never committed. The public certificate is imported into the machine trust
    store because a sideloaded MSIX is rejected until its chain is trusted.

    This script never contacts the network: no timestamp authority is used, so
    the signature carries no RFC 3161 counter-signature.

.PARAMETER Package
    Path to the unsigned .msix produced by Installer/GrafWindows.Package.wapproj.

.PARAMETER CertificateSubject
    Certificate subject. Must equal the Publisher value in the manifest.

.PARAMETER SecretsDirectory
    Directory that receives graf-dev.cer and graf-dev.pfx.

.PARAMETER SkipTrust
    Sign only; do not import the certificate into the machine trust store.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Package,
    [string]$CertificateSubject = 'CN=GRAF',
    [string]$SecretsDirectory = "$env:USERPROFILE\graf-dev-signing",
    [switch]$SkipTrust
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Feature 200 package signing requires a Windows host.' }
if (-not (Test-Path -LiteralPath $Package -PathType Leaf)) { throw "Package does not exist: $Package" }
if ([IO.Path]::GetExtension($Package) -ne '.msix') { throw "Expected an MSIX package: $Package" }

New-Item -ItemType Directory -Path $SecretsDirectory -Force | Out-Null
$secrets = (Resolve-Path -LiteralPath $SecretsDirectory).Path
$cerPath = Join-Path $secrets 'graf-dev.cer'
$pfxPath = Join-Path $secrets 'graf-dev.pfx'
$pfxPassword = 'graf-dev-local'

$certificate = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.Subject -eq $CertificateSubject -and $_.HasPrivateKey } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1
if (-not $certificate) {
    # 1.3.6.1.5.5.7.3.3 is the Code Signing extended key usage. Basic constraints
    # are written empty so the certificate can never act as an issuing CA.
    $certificate = New-SelfSignedCertificate -Type Custom -Subject $CertificateSubject `
        -KeyUsage DigitalSignature -KeyAlgorithm RSA -KeyLength 2048 `
        -FriendlyName 'GRAF dev package signing' `
        -CertStoreLocation 'Cert:\CurrentUser\My' `
        -NotAfter (Get-Date).AddYears(3) `
        -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')
}

Export-Certificate -Cert $certificate -FilePath $cerPath -Force | Out-Null
$securePassword = ConvertTo-SecureString -String $pfxPassword -Force -AsPlainText
Export-PfxCertificate -Cert $certificate -FilePath $pfxPath -Password $securePassword -Force | Out-Null

if (-not $SkipTrust) {
    # Trusted People is the documented store for sideloaded packages. The
    # certificate is not added to the root store, so it cannot vouch for anything
    # other than this development identity.
    Import-Certificate -FilePath $cerPath -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople' | Out-Null
}

$signTool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $signTool) { throw 'signtool.exe was not found in the installed Windows SDK.' }

& $signTool.FullName sign /fd SHA256 /f $pfxPath /p $pfxPassword $Package
if ($LASTEXITCODE -ne 0) { throw "signtool failed with exit code $LASTEXITCODE." }

$signature = Get-AuthenticodeSignature -LiteralPath $Package
if ($signature.Status -ne 'Valid') { throw "Signed package is not valid: $($signature.Status)" }
if ($signature.SignerCertificate.Subject -ne $CertificateSubject) {
    throw "Signed by the wrong subject: $($signature.SignerCertificate.Subject)"
}

Write-Output ("Signed development MSIX: {0}" -f (Resolve-Path -LiteralPath $Package).Path)
Write-Output ("Signature: {0}; subject {1}; thumbprint {2}" -f `
    $signature.Status, $signature.SignerCertificate.Subject, $certificate.Thumbprint)
Write-Output ("Private key kept outside the repository: {0}" -f $pfxPath)
