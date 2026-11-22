[CmdletBinding()]
param(
    [string]$InstallDirectory = "$PSScriptRoot\..\out\ffmpeg-7.1.5-x64",
    [string]$BuildDirectory = "$PSScriptRoot\..\out\ffmpeg-7.1.5-work",
    [switch]$VerifyBuildArtifacts
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'FFmpeg dependency preparation requires Windows.' }
$dependency = [IO.Path]::GetFullPath("$PSScriptRoot\..\Native\GrafFFmpeg")
$manifestPath = Join-Path $dependency 'manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$prefix = [IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
$work = [IO.Path]::GetFullPath($BuildDirectory).TrimEnd('\')
$proofPath = Join-Path $prefix 'build-provenance.json'
$headerPath = Join-Path $prefix 'include\graf\GrafFFmpegBuildManifest.h'
$utf8 = New-Object Text.UTF8Encoding($false)

function Hash([string]$Path) {
    # .NET only: module autoloading is not guaranteed for the CMake verify
    # invocation, where Get-FileHash can be unavailable.
    $stream = [IO.File]::OpenRead($Path)
    try {
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
        } finally { $sha.Dispose() }
    } finally { $stream.Dispose() }
}
function Write-Utf8([string]$Path, [string]$Text) { [IO.File]::WriteAllText($Path, $Text, $utf8) }
function Shell-Path([string]$Path) { '/' + $Path.Substring(0, 1).ToLowerInvariant() + $Path.Substring(2).Replace('\', '/') }
function Inventory([string]$Root) {
    @(Get-ChildItem -LiteralPath $Root -Recurse -Force | Sort-Object FullName | ForEach-Object {
        if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Dependency tree contains a reparse point.' }
        if (!$_.PSIsContainer) {
            $relative = $_.FullName.Substring($Root.Length + 1).Replace('\', '/')
            if ($relative -notin @('build-provenance.json', 'include/graf/GrafFFmpegBuildManifest.h')) {
                [ordered]@{ path = $relative; bytes = $_.Length; sha256 = Hash $_.FullName }
            }
        }
    })
}
function Json($Value) { ConvertTo-Json -InputObject $Value -Depth 8 -Compress }
function Check-Parents([string]$Path) {
    for ($item = $Path; $item; $item = Split-Path $item -Parent) {
        if (Test-Path -LiteralPath $item) {
            if ((Get-Item -LiteralPath $item -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Dependency path contains a reparse point.'
            }
        }
    }
}
function Check-Payload {
    $dlls = @(Get-ChildItem -LiteralPath "$prefix\bin" -Filter '*.dll' -File | ForEach-Object Name | Sort-Object)
    if ((Json $dlls) -cne (Json @($manifest.dlls.name | Sort-Object))) { throw 'Unexpected FFmpeg DLL set.' }
    if (Get-ChildItem -LiteralPath "$prefix\bin" -Filter '*.exe' -File) { throw 'FFmpeg programs must not be installed.' }
    foreach ($dll in $manifest.dlls) {
        $file = [IO.File]::OpenRead((Join-Path "$prefix\bin" $dll.name))
        $reader = New-Object IO.BinaryReader($file)
        try {
            if ($reader.ReadUInt16() -ne 0x5a4d) { throw 'FFmpeg DOS header is missing.' }
            $file.Position = 0x3c; $offset = $reader.ReadUInt32()
            if ($offset -gt $file.Length - 26) { throw 'FFmpeg PE header is out of bounds.' }
            $file.Position = $offset
            if ($reader.ReadUInt32() -ne 0x4550 -or $reader.ReadUInt16() -ne 0x8664) { throw 'FFmpeg DLL is not x64.' }
            $file.Position = $offset + 24
            if ($reader.ReadUInt16() -ne 0x20b) { throw 'FFmpeg DLL is not PE32+.' }
        } finally { $reader.Dispose(); $file.Dispose() }
        $pe = Get-Content -LiteralPath "$prefix\share\graf\pe-$($dll.name).stdout.log" -Raw
        $imports = @([regex]::Matches($pe, '(?im)^\s+([a-z0-9_.-]+\.dll)\s*$') | ForEach-Object { $_.Groups[1].Value.ToLowerInvariant() } | Sort-Object -Unique)
        $required = switch ($dll.library) { 'avutil' { @() }; 'avcodec' { @('avutil-59.dll') }; 'avformat' { @('avutil-59.dll', 'avcodec-61.dll') } }
        foreach ($name in $required) { if ($name -notin $imports) { throw 'FFmpeg required DLL import is missing.' } }
        foreach ($name in $imports) {
            if ($name -notin $required -and $name -notmatch '^(kernel32|bcrypt|ucrtbase|vcruntime140(?:_1)?|api-ms-win-crt-[a-z0-9-]+)\.dll$') {
                throw "Unexpected FFmpeg DLL import: $name"
            }
        }
        foreach ($suffix in @('version', 'configuration', 'license')) {
            if ($pe -notmatch ('\b' + $dll.library + '_' + $suffix + '\b')) { throw 'FFmpeg metadata export is missing.' }
        }
    }
    $config = Get-Content -LiteralPath "$prefix\share\graf\config.h" -Raw
    $components = Get-Content -LiteralPath "$prefix\share\graf\config_components.h" -Raw
    foreach ($name in @('GPL', 'NONFREE', 'VERSION3', 'NETWORK', 'PROTOCOLS', 'STATIC', 'AVDEVICE', 'AVFILTER', 'SWSCALE', 'SWRESAMPLE')) {
        if ($config -notmatch "(?m)^#define CONFIG_$name 0\r?`$") { throw "Forbidden/missing FFmpeg config: $name" }
    }
    foreach ($name in @('AAC_ENCODER', 'IPOD_MUXER', 'MOV_MUXER')) {
        if ($components -notmatch "(?m)^#define CONFIG_$name 1\r?`$") { throw "Required FFmpeg component is missing: $name" }
    }
    foreach ($notice in $manifest.notices) {
        if ((Hash "$dependency\notices\$($notice.name)") -cne $notice.sha256 -or
            (Hash "$prefix\share\graf\$($notice.name)") -cne $notice.sha256) { throw 'FFmpeg license bytes differ.' }
    }
    foreach ($dll in $manifest.dlls) {
        $text = Get-Content -LiteralPath "$prefix\include\lib$($dll.library)\version.h" -Raw
        $majorPath = "$prefix\include\lib$($dll.library)\version_major.h"
        if (Test-Path -LiteralPath $majorPath) { $text += Get-Content -LiteralPath $majorPath -Raw }
        foreach ($part in @('major', 'minor', 'micro')) {
            $macro = 'LIB' + $dll.library.ToUpperInvariant() + '_VERSION_' + $part.ToUpperInvariant()
            if ($text -notmatch "(?m)^#define $macro +$($dll.$part)\r?`$") { throw 'FFmpeg headers have an unexpected ABI/version.' }
        }
    }
}
function Header($Proof) {
    $literal = $Proof.configuration_literal
    # Generated C string from this exact configure, not the historical prefix.
    if ($literal -notmatch '^"[^\r\n]*"$') { throw 'Invalid FFmpeg configuration literal.' }
    $configuration = ConvertFrom-Json -InputObject $literal
    $configurationBytes = [Text.Encoding]::UTF8.GetBytes($configuration)
    if (!$configurationBytes.Length -or $configurationBytes.Length -gt 16384) { throw 'FFmpeg configuration exceeds its runtime bound.' }
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $configurationHash = $hash.ComputeHash($configurationBytes) } finally { $hash.Dispose() }
    $configurationDigest = ($configurationHash | ForEach-Object { '0x' + $_.ToString('x2') }) -join ', '
    $rows = foreach ($dll in $manifest.dlls) {
        $artifact = @($Proof.artifacts | Where-Object path -CEQ ('bin/' + $dll.name))
        if ($artifact.Count -ne 1) { throw 'FFmpeg artifact descriptor missing.' }
        $version = ([int]$dll.major -shl 16) -bor ([int]$dll.minor -shl 8) -bor [int]$dll.micro
        $digest = ([regex]::Matches($artifact[0].sha256, '[0-9a-f]{2}') | ForEach-Object { '0x' + $_.Value }) -join ', '
        '    {L"' + $dll.name + '", ' + $version + 'U, ' + $artifact[0].bytes + 'ULL, {' + $digest + '}}'
    }
    @"
// Generated by build-graf-ffmpeg.ps1 after verification. Do not edit.
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
namespace graf::ffmpeg {
struct ModulePin { const wchar_t* filename; std::uint32_t version; std::uint64_t bytes; std::array<std::uint8_t, 32> sha256; };
inline constexpr std::array<ModulePin, 3> modules{{
$($rows -join ",`n")
}};
inline constexpr std::uint16_t machine = 0x8664;
inline constexpr char release[] = "$($manifest.version)";
inline constexpr char sourceArchiveSha256[] = "$($manifest.source.sha256)";
inline constexpr char provenanceSha256[] = "$(Hash $proofPath)";
inline constexpr std::size_t configurationBytes = $($configurationBytes.Length);
inline constexpr std::array<std::uint8_t, 32> configurationSha256{$configurationDigest};
inline constexpr char license[] = "LGPL version 2.1 or later";
}
"@
}
function Verify {
    Check-Parents $prefix
    $proof = Get-Content -LiteralPath $proofPath -Raw | ConvertFrom-Json
    if ($proof.schema_version -ne 1 -or $proof.architecture -cne 'x64' -or
        $proof.source_sha256 -cne $manifest.source.sha256 -or
        $proof.manifest_sha256 -cne (Hash $manifestPath) -or
        $proof.recipe_sha256 -cne (Hash $PSCommandPath) -or
        $proof.source_before_sha256 -cne $proof.source_after_sha256 -or
        $proof.source_before_sha256 -notmatch '^[a-f0-9]{64}$' -or
        $proof.toolchain.vctools_version -cne $manifest.toolchain.vctools_version -or
        $proof.toolchain.windows_sdk -cne $manifest.toolchain.windows_sdk) { throw 'FFmpeg build provenance is stale or incomplete.' }
    if ((Hash "$prefix\share\graf\$($manifest.source.name)") -cne $manifest.source.sha256) { throw 'FFmpeg corresponding source archive differs.' }
    if ((Json @(Inventory $prefix)) -cne (Json @($proof.artifacts))) { throw 'FFmpeg artifact inventory differs from the successful build.' }
    Check-Payload
    if ([IO.File]::ReadAllText($headerPath) -cne (Header $proof)) { throw 'FFmpeg generated pins are missing or stale.' }
    Write-Output 'Verified ordinary FFmpeg 7.1.5 x64 artifacts and compiled pins.'
}

if ($VerifyBuildArtifacts) { Verify; exit 0 }
if ($env:VSCMD_ARG_TGT_ARCH -notin @('x64', 'amd64') -or
    $env:VCToolsVersion.TrimEnd('\') -cne $manifest.toolchain.vctools_version -or
    $env:WindowsSDKVersion.TrimEnd('\') -cne $manifest.toolchain.windows_sdk) {
    throw 'Enter the pinned x64 MSVC/Windows SDK developer environment first.'
}
foreach ($path in @($work, $prefix)) {
    if ($path -notmatch '^[A-Za-z]:[\\/][A-Za-z0-9 _./\\:-]+$') { throw 'Use an absolute ASCII build path without shell metacharacters.' }
    Check-Parents $path
    if (Test-Path -LiteralPath $path) { throw 'Use fresh build/install directories; existing dependency data is never overwritten.' }
}
if ($work.StartsWith($prefix + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $prefix.StartsWith($work + '\', [StringComparison]::OrdinalIgnoreCase) -or $prefix -ieq $work) {
    throw 'Build and install directories must be separate.'
}
$null = New-Item -ItemType Directory -Path $work, $prefix
$null = New-Item -ItemType Directory -Path "$prefix\share\graf", "$prefix\include\graf"
function Run([string]$Exe, [string[]]$Arguments, [string]$Label, [int]$TimeoutSeconds = 1800) {
    # All arguments are fixed flags/validated paths; no command string or stdin.
    Write-Utf8 "$prefix\share\graf\$Label.command.json" (Json ([ordered]@{ executable = $Exe; sha256 = Hash $Exe; arguments = $Arguments; timeout_seconds = $TimeoutSeconds }))
    $elapsed = [Diagnostics.Stopwatch]::StartNew()
    Write-Host ("FFmpeg stage start name={0}" -f $Label)
    $process = New-Object Diagnostics.Process
    $timedOut = $false
    try {
        $process.StartInfo.FileName = $Exe
        $process.StartInfo.Arguments = ($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
        $process.StartInfo.UseShellExecute = $false
        $process.StartInfo.RedirectStandardOutput = $true
        $process.StartInfo.RedirectStandardError = $true
        # No step reads stdin; closing it prevents a silent wait on a console
        # handle that does not exist on a hosted runner.
        $process.StartInfo.RedirectStandardInput = $true
        if (!$process.Start()) { throw "Could not start $Label" }
        try { $process.StandardInput.Close() } catch { }
        Write-Host ("FFmpeg stage started name={0} pid={1}" -f $Label, $process.Id)
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        # A bounded wait keeps one stuck stage from consuming the whole job
        # budget without any evidence. Normal exits are unaffected.
        $nextProgress = 30
        while (-not $process.WaitForExit(1000)) {
            if ($TimeoutSeconds -gt 0 -and $elapsed.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
                $timedOut = $true
                # Windows PowerShell 5.1 has no Process.Kill(entireProcessTree);
                # taskkill /T ends compiler descendants that would otherwise
                # keep the redirected pipes open.
                $taskkill = Join-Path $env:SystemRoot 'System32\taskkill.exe'
                if (Test-Path -LiteralPath $taskkill) {
                    $null = & $taskkill /PID $process.Id /T /F 2>&1
                }
                try { $process.Kill() } catch { }
                $null = $process.WaitForExit(15000)
                break
            }
            if ($elapsed.Elapsed.TotalSeconds -ge $nextProgress) {
                # Safe liveness facts: a growing CPU time means slow work, while
                # near-zero CPU time points at a blocked process.
                $cpuMs = 0
                $memoryMb = 0
                try {
                    $process.Refresh()
                    $cpuMs = [int]$process.TotalProcessorTime.TotalMilliseconds
                    $memoryMb = [int]($process.WorkingSet64 / 1MB)
                } catch { }
                Write-Host ("FFmpeg stage progress name={0} elapsed_ms={1} cpu_ms={2} memory_mb={3}" -f $Label, $elapsed.ElapsedMilliseconds, $cpuMs, $memoryMb)
                $nextProgress += 30
            }
        }
        # Bound the drain as well: a stuck descendant must not block the
        # timeout record and the failure message.
        $outText = ''
        $errText = ''
        $drained = $true
        if ($stdout.Wait(15000)) { try { $outText = [string]$stdout.Result } catch { } } else { $drained = $false }
        if ($stderr.Wait(15000)) { try { $errText = [string]$stderr.Result } catch { } } else { $drained = $false }
        Write-Utf8 "$prefix\share\graf\$Label.stdout.log" $outText
        Write-Utf8 "$prefix\share\graf\$Label.stderr.log" $errText
        if ($timedOut) {
            Write-Host ("FFmpeg stage timeout name={0} elapsed_ms={1} limit_seconds={2}" -f $Label, $elapsed.ElapsedMilliseconds, $TimeoutSeconds)
            Write-Host ("FFmpeg stage output_bytes name={0} stdout={1} stderr={2} drained={3}" -f $Label, $outText.Length, $errText.Length, $drained)
            Write-Utf8 "$prefix\share\graf\$Label.terminal.json" (Json ([ordered]@{ timeout = $true; limit_seconds = $TimeoutSeconds }))
            throw "$Label exceeded $TimeoutSeconds seconds; logs retained in install directory."
        }
        Write-Host ("FFmpeg stage terminal name={0} exit={1} elapsed_ms={2}" -f $Label, $process.ExitCode, $elapsed.ElapsedMilliseconds)
        Write-Utf8 "$prefix\share\graf\$Label.terminal.json" (Json ([ordered]@{ exit = $process.ExitCode }))
        if ($process.ExitCode -ne 0) { throw "$Label failed with exit $($process.ExitCode); logs retained in install directory." }
    } finally { $process.Dispose() }
}
function Download($InputFile) {
    $path = Join-Path $work $InputFile.name
    $url = ([uri]$InputFile.url).GetComponents(
        ([UriComponents]::SchemeAndServer -bor [UriComponents]::Path), [UriFormat]::UriEscaped)
    $elapsed = [Diagnostics.Stopwatch]::StartNew()
    Write-Host ("FFmpeg download start name={0} url={1}" -f $InputFile.name, $url)
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $InputFile.url -OutFile $path -TimeoutSec 120
    } catch {
        Write-Host ("FFmpeg download failed name={0} elapsed_ms={1}" -f $InputFile.name, $elapsed.ElapsedMilliseconds)
        $cause = $_.Exception
        for ($depth = 0; $null -ne $cause -and $depth -lt 4; $depth++) {
            Write-Host ("FFmpeg download cause depth={0} type={1} hresult={2}" -f $depth, $cause.GetType().FullName, $cause.HResult)
            if ($cause -is [Net.WebException]) {
                Write-Host ("FFmpeg download web_status={0}" -f $cause.Status)
                if ($cause.Response -is [Net.HttpWebResponse]) {
                    Write-Host ("FFmpeg download http_status={0}" -f [int]$cause.Response.StatusCode)
                }
            }
            if ($cause -is [Net.Sockets.SocketException]) {
                Write-Host ("FFmpeg download socket_error={0} native_error={1}" -f [int]$cause.SocketErrorCode, $cause.NativeErrorCode)
            }
            $cause = $cause.InnerException
        }
        # Do not rethrow the original ErrorRecord: it may contain an HTTP error body.
        throw [InvalidOperationException]::new('Pinned dependency download failed; see safe diagnostic above.')
    }
    if ((Get-Item -LiteralPath $path).Length -ne $InputFile.bytes -or (Hash $path) -cne $InputFile.sha256) { throw 'Dependency download pin mismatch.' }
    Write-Host ("FFmpeg download verified name={0} elapsed_ms={1}" -f $InputFile.name, $elapsed.ElapsedMilliseconds)
    return $path
}

$originalPath = $env:PATH
try {
    $cl = (Get-Command cl.exe -CommandType Application | Select-Object -First 1).Source
    $link = (Get-Command link.exe -CommandType Application | Select-Object -First 1).Source
    $dumpbin = (Get-Command dumpbin.exe -CommandType Application | Select-Object -First 1).Source
    foreach ($tool in @($cl, $link, $dumpbin)) {
        if ($tool -notmatch ('[\\/]' + [regex]::Escape($manifest.toolchain.vctools_version) + '[\\/]bin[\\/]Host(?:x64|arm64)[\\/]x64[\\/]')) { throw 'Unexpected MSVC tool path.' }
    }
    foreach ($inputFile in @($manifest.source) + @($manifest.build_tools)) { $null = Download $inputFile }
    # Extraction writes thousands of files; a real-time scan can hold the
    # process without any CPU progress. Exclusions are best-effort metadata for
    # this disposable directory only.
    try {
        $addPreference = Get-Command Add-MpPreference -ErrorAction SilentlyContinue
        if ($null -ne $addPreference) {
            Add-MpPreference -ExclusionPath $work, $prefix -ErrorAction Stop
            Write-Host 'FFmpeg defender_exclusion=applied'
        }
    } catch {
        Write-Host 'FFmpeg defender_exclusion=unavailable'
    }
    # Bootstrap needs native Windows paths; PATH may resolve a POSIX tar.
    # The system tar can stop without any output on this large xz archive, so a
    # preinstalled 7-Zip is tried first when it is present. The pinned archive is
    # never modified; both paths extract the same verified bytes.
    $tar = Join-Path $env:SystemRoot 'System32\tar.exe'
    $sevenZip = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
    if (Test-Path -LiteralPath $sevenZip) {
        Write-Host 'FFmpeg extractor=7zip'
        $innerTar = "$work\msys2-base.tar"
        Run $sevenZip @('x', '-y', "-o$work", "$work\msys2-base.tar.xz") 'tools-extract-xz' 900
        if (!(Test-Path -LiteralPath $innerTar)) { throw '7-Zip did not produce the inner tar archive.' }
        Run $sevenZip @('x', '-y', "-o$work", $innerTar) 'tools-extract' 900
        Remove-Item -LiteralPath $innerTar -Force
    } else {
        Write-Host 'FFmpeg extractor=system-tar'
        Run $tar @('-xf', "$work\msys2-base.tar.xz", '-C', $work) 'tools-extract' 900
    }
    $msys = "$work\msys64"
    $env:PATH = "$msys\usr\bin;$originalPath"
    foreach ($name in @('make.pkg.tar.zst', 'diffutils.pkg.tar.zst')) {
        Run "$msys\usr\bin\tar.exe" @('-xf', (Shell-Path "$work\$name"), '-C', (Shell-Path $msys)) ('extract-' + $name) 600
    }
    Run "$msys\usr\bin\tar.exe" @('-xf', (Shell-Path "$work\$($manifest.source.name)"), '-C', (Shell-Path $work)) 'source-extract' 600
    $source = "$work\ffmpeg-$($manifest.version)"
    $before = Json @(Inventory $source)
    Write-Utf8 "$prefix\share\graf\source-before.json" $before
    $null = New-Item -ItemType Directory -Path "$work\build"
    # Keep the shell/configure fragment concrete; no source patch, packages,
    # global environment mutation or inherited compiler-flag customization.
    $shell = @'
set -euo pipefail
export LC_ALL=C
unset MSYS2_ARG_CONV_EXCL MSYS_NO_PATHCONV CFLAGS CXXFLAGS CPPFLAGS LDFLAGS CC CXX LD AR CL _CL_
export PATH="/usr/bin:$PATH"
work=$(cygpath -u "$GRAF_FFMPEG_WORK")
prefix=$(cygpath -m "$GRAF_FFMPEG_PREFIX")
cd "$work/build"
'@
    $shell += "`n`"`$work/ffmpeg-7.1.5/configure`" " + ($manifest.configure -join ' ') + ' --prefix="$prefix"' + "`nmake V=1 -j2`nmake install`n"
    Write-Utf8 "$work\build.sh" $shell
    $env:GRAF_FFMPEG_WORK = $work; $env:GRAF_FFMPEG_PREFIX = $prefix
    Run "$msys\usr\bin\bash.exe" @('--noprofile', '--norc', (Shell-Path "$work\build.sh")) 'build' 3600
    $after = Json @(Inventory $source)
    if ($after -cne $before) { throw 'FFmpeg source changed during the build.' }
    Copy-Item -LiteralPath "$work\$($manifest.source.name)" -Destination "$prefix\share\graf"
    foreach ($notice in $manifest.notices) {
        if ((Hash "$source\$($notice.name)") -cne $notice.sha256) { throw 'Upstream notice differs from its source pin.' }
        Copy-Item -LiteralPath "$source\$($notice.name)" -Destination "$prefix\share\graf"
    }
    foreach ($config in @('config.h', 'config_components.h')) { Copy-Item -LiteralPath "$work\build\$config" -Destination "$prefix\share\graf" }
    Copy-Item -LiteralPath "$work\build\ffbuild\config.mak" -Destination "$prefix\share\graf"
    foreach ($dll in $manifest.dlls) { Run $dumpbin @('/headers', '/imports', '/exports', "$prefix\bin\$($dll.name)") ('pe-' + $dll.name) }
    $objects = @(Get-ChildItem -LiteralPath "$work\build" -Recurse -Filter '*.o' -File | Sort-Object FullName)
    Write-Utf8 "$prefix\share\graf\objects.json" (Json @($objects | ForEach-Object { [ordered]@{ path = $_.FullName.Substring($work.Length + 1); bytes = $_.Length; sha256 = Hash $_.FullName } }))
    $sourceObjects = @($objects | Where-Object { $_.FullName -notmatch '[\\/]libav(?:codec|format|util)[\\/]av(?:codec|format|util)res\.o$' })
    if (!$sourceObjects.Count) { throw 'FFmpeg source-object inventory is empty.' }
    Write-Utf8 "$work\directives.rsp" (($sourceObjects | ForEach-Object { '"' + $_.FullName + '"' }) -join "`r`n")
    Run $dumpbin @('/directives', "@$work\directives.rsp") 'object-directives'
    Check-Payload
    $configText = Get-Content -LiteralPath "$prefix\share\graf\config.h" -Raw
    if ($configText -notmatch '(?m)^#define FFMPEG_CONFIGURATION ("[^\r\n]*")\r?$') { throw 'Missing configuration literal.' }
    $literal = $Matches[1]
    $proof = [ordered]@{
        schema_version = 1; architecture = 'x64'; source_sha256 = $manifest.source.sha256
        manifest_sha256 = Hash $manifestPath; recipe_sha256 = Hash $PSCommandPath
        source_before_sha256 = Hash "$prefix\share\graf\source-before.json"
        source_after_sha256 = Hash "$prefix\share\graf\source-before.json"
        configuration_literal = $literal
        toolchain = [ordered]@{ vctools_version = $env:VCToolsVersion.TrimEnd('\'); windows_sdk = $env:WindowsSDKVersion.TrimEnd('\'); cl = $cl; cl_sha256 = Hash $cl; link = $link; link_sha256 = Hash $link; dumpbin_sha256 = Hash $dumpbin }
        artifacts = @(Inventory $prefix)
    }
    # Only the successful, unmodified build can create this attestation/header.
    Write-Utf8 $proofPath (Json $proof)
    Write-Utf8 $headerPath (Header $proof)
    Verify
    # Work is fresh and owned by this invocation. Keep provenance, source tar
    # and logs in the verified prefix; do not preserve intermediate builds.
    Remove-Item -LiteralPath $work -Recurse -Force
} finally {
    $env:PATH = $originalPath
    Remove-Item Env:GRAF_FFMPEG_WORK, Env:GRAF_FFMPEG_PREFIX -ErrorAction SilentlyContinue
}
