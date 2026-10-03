[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [string]$SourceDirectory = "",
    [string]$BuildDirectory = "",
    [ValidateSet("x64", "ARM64")]
    [string]$Architecture = "x64",
    [switch]$VerifyBuildArtifacts,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$windowsRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$lockPath = Join-Path $windowsRoot "apps\windows\Native\GrafAEC3\upstream.lock"
$crossFile = Join-Path $windowsRoot "apps\windows\Native\GrafAEC3\x64.cross"
$sourceDirectory = if ($SourceDirectory) {
    (Resolve-Path $SourceDirectory).Path
} else {
    Join-Path $windowsRoot "apps\windows\Native\GrafAEC3\vendor\webrtc-audio-processing"
}

$isWindowsHost = $env:OS -eq "Windows_NT"
if (-not $isWindowsHost) {
    throw "GrafAEC3 Windows build must run on a Windows host with the approved C++ toolchain."
}
if (-not (Test-Path $lockPath)) {
    throw "AEC3 source lock is missing: $lockPath"
}
if (-not (Test-Path $sourceDirectory)) {
    throw "Provide a verified upstream checkout with -SourceDirectory: $sourceDirectory"
}
if (-not (Test-Path $crossFile)) {
    throw "The x64 Meson cross file is missing: $crossFile"
}

$lock = @{}
Get-Content $lockPath | Where-Object { $_ -match "^(?<key>[^=]+)=(?<value>.*)$" } | ForEach-Object {
    $lock[$Matches.key] = $Matches.value
}

if ($Architecture -notin ($lock.architectures -split ",")) {
    throw "AEC3 architecture is not validated by upstream.lock: $Architecture"
}

$revision = & git -C $sourceDirectory rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "Could not verify AEC3 source revision." }
$actualCommit = ($revision -join "").Trim()
if ($actualCommit -ne $lock.webrtc_audio_processing_commit) {
    throw "AEC3 source revision mismatch. Expected $($lock.webrtc_audio_processing_commit), got $actualCommit"
}
$sourceChanges = & git -C $sourceDirectory status --porcelain --untracked-files=no
if ($LASTEXITCODE -ne 0 -or $sourceChanges) {
    throw "AEC3 tracked source must match the pinned clean checkout."
}

$licenseFiles = $lock.license_files -split ","
foreach ($relativePath in $licenseFiles) {
    if (-not (Test-Path (Join-Path $sourceDirectory $relativePath))) {
        throw "Required upstream license file is missing: $relativePath"
    }
}

$buildDirectory = if ($BuildDirectory) { $BuildDirectory } else {
    Join-Path $windowsRoot "apps\windows\out\aec3\$Configuration"
}
$provenancePath = Join-Path $buildDirectory "graf-aec3-provenance.json"

function Get-ArtifactHashes {
    $root = [IO.Path]::GetFullPath($buildDirectory).TrimEnd('\', '/')
    @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object {
        $_.Extension -in '.a', '.lib', '.h', '.hpp', '.hh', '.inc', '.inl', '.def'
    } | Sort-Object FullName | ForEach-Object {
        [ordered]@{ path = $_.FullName.Substring($root.Length + 1); sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    })
}

function Get-TextDigest([string]$Text) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-', '') }
    finally { $sha.Dispose() }
}

function Get-TreeDigest([string]$Directory) {
    $root = [IO.Path]::GetFullPath($Directory).TrimEnd('\', '/')
    $lines = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($root.Length + 1).Replace('\', '/')
        if ($relative -notmatch '^\.git/' -and $relative -notmatch '^subprojects/packagecache/' -and
            $_.Name -ne '.meson-subproject-wrap-hash.txt') {
            $relative + ':' + (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    })
    Get-TextDigest ($lines -join "`n")
}

function Assert-AbseilSource {
    $subprojects = Join-Path $sourceDirectory 'subprojects'
    $wrap = Join-Path $subprojects 'abseil-cpp.wrap'
    $archive = Join-Path $subprojects "packagecache\abseil-cpp-$($lock.abseil_version).tar.gz"
    $patch = Join-Path $subprojects "packagecache\abseil-cpp_$($lock.abseil_wrap_patch_version)_patch.zip"
    # The lock hashes the Git LF text; a clean Windows checkout may use CRLF.
    # Only line endings are normalized. Archive and source-tree hashes are binary.
    $wrapDigest = Get-TextDigest ([IO.File]::ReadAllText($wrap).Replace("`r`n", "`n"))
    if ($wrapDigest -ine $lock.abseil_wrap_file_sha256 -or
        (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ine $lock.abseil_source_sha256 -or
        (Get-FileHash -LiteralPath $patch -Algorithm SHA256).Hash -ine $lock.abseil_wrap_patch_sha256) {
        throw 'Abseil wrap/archive/patch does not match upstream.lock.'
    }
    $expectedRoot = Join-Path ([IO.Path]::GetTempPath()) ('graf-abseil-verify-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $expectedRoot | Out-Null
    try {
        # Only hash-verified pinned archives are extracted, never caller-supplied archives.
        & tar.exe -xf $archive -C $expectedRoot
        if ($LASTEXITCODE -ne 0) { throw 'Could not unpack pinned Abseil source.' }
        Expand-Archive -LiteralPath $patch -DestinationPath $expectedRoot -Force
        $name = "abseil-cpp-$($lock.abseil_version)"
        if ((Get-TreeDigest (Join-Path $expectedRoot $name)) -cne (Get-TreeDigest (Join-Path $subprojects $name))) {
            throw 'Unpacked Abseil source differs from the pinned archive and patch.'
        }
    } finally {
        # This invocation owns this unique temporary directory, not the source checkout.
        Remove-Item -LiteralPath $expectedRoot -Recurse -Force
    }
}

function Get-BuildIdentity {
    [ordered]@{
        sourceCommit = $actualCommit
        architecture = $Architecture
        configuration = $Configuration
        lockSha256 = (Get-FileHash -LiteralPath $lockPath -Algorithm SHA256).Hash
        crossSha256 = (Get-FileHash -LiteralPath $crossFile -Algorithm SHA256).Hash
        recipeSha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
    }
}

function Assert-BuildArtifacts {
    $info = Get-Content (Join-Path $buildDirectory "meson-info\meson-info.json") -Raw | ConvertFrom-Json
    $machines = Get-Content (Join-Path $buildDirectory "meson-info\intro-machines.json") -Raw | ConvertFrom-Json
    if ([IO.Path]::GetFullPath($info.directories.source).TrimEnd('\', '/') -ine $sourceDirectory.TrimEnd('\', '/')) {
        throw "AEC3 build cache belongs to a different source directory."
    }
    if ($machines.host.system -ne "windows" -or $machines.host.cpu_family -ne "x86_64") {
        throw "AEC3 build cache is not the validated Windows x64 architecture."
    }
    $libraryDirectory = Join-Path $buildDirectory "webrtc\modules\audio_processing"
    if (-not ((Test-Path (Join-Path $libraryDirectory "libwebrtc-audio-processing-2.a")) -or
              (Test-Path (Join-Path $libraryDirectory "libwebrtc-audio-processing-2.lib")))) {
        throw "AEC3 compiled library is missing."
    }
}

if ($VerifyBuildArtifacts) {
    Assert-BuildArtifacts
    if (-not (Test-Path -LiteralPath $provenancePath)) {
        throw "AEC3 cache has no build provenance; rebuild it with this script."
    }
    $provenance = Get-Content -LiteralPath $provenancePath -Raw | ConvertFrom-Json
    $identity = Get-BuildIdentity
    foreach ($key in $identity.Keys) {
        if ($provenance.identity.$key -cne $identity[$key]) {
            throw "AEC3 cache provenance mismatch ($key); rebuild it."
        }
    }
    if ($provenance.sourceDigest -cne (Get-TreeDigest $sourceDirectory)) {
        throw 'AEC3 source/header tree differs from the verified build inputs; rebuild it.'
    }
    $artifacts = @(Get-ArtifactHashes)
    if ($artifacts.Count -ne $provenance.artifacts.Count -or $artifacts.Count -eq 0) {
        throw "AEC3 cache artifact inventory changed; rebuild it."
    }
    for ($index = 0; $index -lt $artifacts.Count; $index++) {
        if ($artifacts[$index].path -cne $provenance.artifacts[$index].path -or
            $artifacts[$index].sha256 -cne $provenance.artifacts[$index].sha256) {
            throw "AEC3 cache artifact hash mismatch; rebuild it."
        }
    }
}
if ($VerifyOnly -or $VerifyBuildArtifacts) {
    Write-Output "GrafAEC3 source and license identity verified: $actualCommit"
    exit 0
}

if (-not (Get-Command meson -ErrorAction SilentlyContinue)) {
    throw "Meson is required to build the pinned AEC3 source."
}
if (-not (Get-Command ninja -ErrorAction SilentlyContinue)) {
    throw "Ninja is required to build the pinned AEC3 source."
}

$buildType = $Configuration.ToLowerInvariant()
$buildTypeOption = [string]::Concat("-Dbuildtype=", $buildType)
$buildIdentity = Get-BuildIdentity
# An interrupted or failed rebuild must not retain a successful attestation.
if (Test-Path -LiteralPath $provenancePath) { Remove-Item -LiteralPath $provenancePath }
if (Test-Path (Join-Path $buildDirectory "build.ninja")) {
    meson setup --wipe --cross-file $crossFile $buildDirectory $sourceDirectory --default-library=static --wrap-mode=forcefallback -Db_lto=false -Dcpp_std=c++20 $buildTypeOption
} else {
    meson setup --cross-file $crossFile $buildDirectory $sourceDirectory --default-library=static --wrap-mode=forcefallback -Db_lto=false -Dcpp_std=c++20 $buildTypeOption
}
if ($LASTEXITCODE -ne 0) { throw "AEC3 Meson setup failed ($LASTEXITCODE)." }
Assert-AbseilSource
$sourceDigest = Get-TreeDigest $sourceDirectory
meson compile -C $buildDirectory
if ($LASTEXITCODE -ne 0) { throw "AEC3 compilation failed ($LASTEXITCODE)." }
Assert-BuildArtifacts
$finalRevision = & git -C $sourceDirectory rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or ($finalRevision -join '').Trim() -cne $actualCommit) { throw 'AEC3 revision changed during build.' }
$finalChanges = & git -C $sourceDirectory status --porcelain --untracked-files=no
if ($LASTEXITCODE -ne 0 -or $finalChanges) { throw 'AEC3 tracked source changed during build.' }
$finalIdentity = Get-BuildIdentity
foreach ($key in $buildIdentity.Keys) {
    if ($buildIdentity[$key] -cne $finalIdentity[$key]) { throw "AEC3 build input changed during compilation ($key)." }
}
if ($sourceDigest -cne (Get-TreeDigest $sourceDirectory)) { throw 'AEC3 source/header tree changed during compilation.' }
[ordered]@{ identity = $buildIdentity; sourceDigest = $sourceDigest; artifacts = @(Get-ArtifactHashes) } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $provenancePath -Encoding UTF8
