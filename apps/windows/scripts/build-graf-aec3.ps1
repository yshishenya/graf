[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [string]$SourceDirectory = "",
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

$actualCommit = (& git -C $sourceDirectory rev-parse HEAD).Trim()
if ($actualCommit -ne $lock.webrtc_audio_processing_commit) {
    throw "AEC3 source revision mismatch. Expected $($lock.webrtc_audio_processing_commit), got $actualCommit"
}

$licenseFiles = $lock.license_files -split ","
foreach ($relativePath in $licenseFiles) {
    if (-not (Test-Path (Join-Path $sourceDirectory $relativePath))) {
        throw "Required upstream license file is missing: $relativePath"
    }
}

if ($VerifyOnly) {
    Write-Output "GrafAEC3 source and license identity verified: $actualCommit"
    exit 0
}

if (-not (Get-Command meson -ErrorAction SilentlyContinue)) {
    throw "Meson is required to build the pinned AEC3 source."
}
if (-not (Get-Command ninja -ErrorAction SilentlyContinue)) {
    throw "Ninja is required to build the pinned AEC3 source."
}

$buildDirectory = Join-Path $windowsRoot "apps\windows\out\aec3\$Configuration"
$buildType = $Configuration.ToLowerInvariant()
$buildTypeOption = [string]::Concat("-Dbuildtype=", $buildType)
if (Test-Path (Join-Path $buildDirectory "build.ninja")) {
    meson setup --wipe --cross-file $crossFile $buildDirectory $sourceDirectory --default-library=static --wrap-mode=forcefallback -Db_lto=false -Dcpp_std=c++20 $buildTypeOption
} else {
    meson setup --cross-file $crossFile $buildDirectory $sourceDirectory --default-library=static --wrap-mode=forcefallback -Db_lto=false -Dcpp_std=c++20 $buildTypeOption
}
meson compile -C $buildDirectory
