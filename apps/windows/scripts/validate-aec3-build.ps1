[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceDirectory,
    [Parameter(Mandatory)][string]$BuildDirectory,
    [Parameter(Mandatory)][string]$MSBuild,
    [string]$Executable = "",
    [string]$ExpectedExecutableSha256 = ""
)
$ErrorActionPreference = "Stop"
$project = Join-Path $PSScriptRoot "..\RecApp\GrafWindowsApp.vcxproj"
$verify = Join-Path $PSScriptRoot "build-graf-aec3.ps1"
$fixture = Join-Path ([IO.Path]::GetTempPath()) ("graf-aec3-gate-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null

function Test-BuildGate([string]$Name, [bool]$ExpectedSuccess, [string[]]$Properties) {
    & $MSBuild $project /t:ValidateGrafAEC3 /p:Configuration=Release /v:minimal /nologo @Properties
    if (($LASTEXITCODE -eq 0) -ne $ExpectedSuccess) { throw "$Name returned an unexpected result." }
    Write-Output "$Name=PASS"
}

try {
    Test-BuildGate 'missing-backend' $false @('/p:Platform=x64', "/p:GrafAEC3Root=$fixture", "/p:GrafAEC3BuildRoot=$fixture")
    Test-BuildGate 'forced-availability' $false @('/p:Platform=x64', '/p:GrafAEC3Available=true', '/p:GrafAEC3Library=missing.a', "/p:GrafAEC3Root=$fixture", "/p:GrafAEC3BuildRoot=$fixture")
    Test-BuildGate 'unsupported-architecture' $false @('/p:Platform=ARM64', "/p:GrafAEC3Root=$SourceDirectory", "/p:GrafAEC3BuildRoot=$BuildDirectory")
    # An existing but different library must not bypass the selected-artifact check.
    Test-BuildGate 'alternate-library' $false @('/p:Platform=x64', '/p:GrafAEC3Library=libwebrtc_audio_processing_privatearch.a', "/p:GrafAEC3Root=$SourceDirectory", "/p:GrafAEC3BuildRoot=$BuildDirectory")
    & git -C $fixture init --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated revision fixture.' }
    & git -C $fixture -c user.name=Fixture -c user.email=fixture@example.invalid commit --allow-empty --quiet -m fixture
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated revision fixture commit.' }
    # Execute in a child PowerShell: build-graf-aec3 uses exit on success.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -SourceDirectory $fixture -VerifyOnly
    if ($LASTEXITCODE -eq 0) { throw 'Wrong source pin was accepted.' }
    Write-Output 'wrong-source-pin=PASS'
    $cacheFixture = Join-Path $fixture 'cache'
    $infoDirectory = Join-Path $cacheFixture 'meson-info'
    $libraryDirectory = Join-Path $cacheFixture 'webrtc\modules\audio_processing'
    New-Item -ItemType Directory -Path $infoDirectory,$libraryDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $BuildDirectory 'meson-info\meson-info.json') -Destination $infoDirectory
    Copy-Item -LiteralPath (Join-Path $BuildDirectory 'meson-info\intro-machines.json') -Destination $infoDirectory
    $libraryFixture = Join-Path $libraryDirectory 'libwebrtc-audio-processing-2.a'
    [IO.File]::WriteAllBytes($libraryFixture, [byte[]]@(1, 2, 3))
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -SourceDirectory $SourceDirectory -BuildDirectory $cacheFixture -VerifyBuildArtifacts
    if ($LASTEXITCODE -eq 0) { throw 'Cache without provenance was accepted.' }
    Write-Output 'missing-provenance=PASS'
    $provenance = Get-Content -LiteralPath (Join-Path $BuildDirectory 'graf-aec3-provenance.json') -Raw | ConvertFrom-Json
    # Keep the authentic identity and expected hash; supply different library bytes.
    $provenance.artifacts = @($provenance.artifacts | Where-Object { $_.path -eq 'webrtc\modules\audio_processing\libwebrtc-audio-processing-2.a' })
    if ($provenance.artifacts.Count -ne 1) { throw 'Expected main library provenance is missing.' }
    $fixtureProvenance = Join-Path $cacheFixture 'graf-aec3-provenance.json'
    $provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $fixtureProvenance -Encoding UTF8
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -SourceDirectory $SourceDirectory -BuildDirectory $cacheFixture -VerifyBuildArtifacts
    if ($LASTEXITCODE -eq 0) { throw 'Changed library bytes were accepted.' }
    Write-Output 'changed-library=PASS'
    $provenance.artifacts[0].sha256 = (Get-FileHash -LiteralPath $libraryFixture -Algorithm SHA256).Hash
    $provenance.identity.sourceCommit = '0000000000000000000000000000000000000000'
    $provenance | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $fixtureProvenance -Encoding UTF8
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -SourceDirectory $SourceDirectory -BuildDirectory $cacheFixture -VerifyBuildArtifacts
    if ($LASTEXITCODE -eq 0) { throw 'Stale source provenance was accepted.' }
    Write-Output 'stale-source-provenance=PASS'
    Test-BuildGate 'real-backend' $true @('/p:Platform=x64', "/p:GrafAEC3Root=$SourceDirectory", "/p:GrafAEC3BuildRoot=$BuildDirectory")
    if ($Executable) {
        if ($ExpectedExecutableSha256 -notmatch '^[0-9A-Fa-f]{64}$' -or
            (Get-FileHash -LiteralPath $Executable -Algorithm SHA256).Hash -ine $ExpectedExecutableSha256) {
            throw 'Provide the independently recorded build/package EXE SHA256; executable identity must match.'
        }
        $process = Start-Process -FilePath $Executable -ArgumentList '--verify-audio-backend' -PassThru
        if (-not $process.WaitForExit(30000)) {
            $process.Kill()
            throw 'Native audio backend verification timed out.'
        }
        if ($process.ExitCode -ne 73) { throw "Native audio backend self-check was not confirmed: $($process.ExitCode)" }
        Write-Output 'native-create-process=PASS'
    } else {
        Write-Output 'native-create-process=NOT_RUN (provide the built or installed executable)'
    }
} finally {
    # Only the unique fixture directory created by this invocation is removed.
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
