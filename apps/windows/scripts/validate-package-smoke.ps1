[CmdletBinding()]
param(
    [string]$Package,
    [switch]$UiMatrix,
    [ValidatePattern('\A[0-9a-fA-F]{64}\z')][string]$ExpectedPackageSha256,
    [switch]$VerifyInstalled,
    [switch]$RequireRunning
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Feature 200 package validation requires a Windows host.' }
if ($RequireRunning -and -not $VerifyInstalled) { throw '-RequireRunning requires -VerifyInstalled.' }
if ($VerifyInstalled -and -not $ExpectedPackageSha256) { throw '-VerifyInstalled requires an independently recorded -ExpectedPackageSha256.' }
if (-not $Package) {
    if ($ExpectedPackageSha256) { throw '-ExpectedPackageSha256 requires -Package.' }
    Write-Output 'Package path is not supplied; clean-image install/update/rollback and WebView2 repair remain pending host evidence.'
    exit 0
}
if (-not (Test-Path -LiteralPath $Package -PathType Leaf)) { throw "Package does not exist: $Package" }
if ([IO.Path]::GetExtension($Package) -ne '.msix') { throw "Expected an MSIX package: $Package" }

Add-Type -AssemblyName System.IO.Compression
function Read-Package([IO.Compression.ZipArchive]$Archive, [switch]$ReadExecutable) {
    $manifestEntry = $archive.GetEntry('AppxManifest.xml')
    if (-not $manifestEntry) { throw 'MSIX does not contain AppxManifest.xml' }
    if ($ReadExecutable -and @($archive.Entries | Where-Object { $_.FullName -ieq 'AppxManifest.xml' }).Count -ne 1) {
        throw 'MSIX does not contain exactly one manifest.'
    }
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

    $languages = @($manifest.SelectNodes('/a:Package/a:Resources/a:Resource/@Language', $ns) | ForEach-Object Value)
    if ('ru' -notin $languages -and 'ru-RU' -notin $languages) {
        throw 'MSIX has no Russian resource language (ru or ru-RU).'
    }

    $forbiddenEntries = @($archive.Entries | Where-Object {
        $_.FullName -match '(?i)(\.sys$|\.msi$|service|driver|elevat|setup\.exe$)'
    })
    if ($forbiddenEntries.Count -gt 0) { throw "Package contains forbidden driver/service/elevation entries: $($forbiddenEntries.FullName -join ', ')" }
    $managedWebView = @($archive.Entries | Where-Object {
        $_.FullName -match '(?i)(^|[/\\])Microsoft\.Web\.WebView2\.Core\.Projection\.dll$'
    })
    if ($managedWebView.Count -gt 0) { throw "Native package contains a managed WebView2 projection: $($managedWebView.FullName -join ', ')" }
    $executableSha = $null
    if ($ReadExecutable) {
        $executables = @($Archive.Entries | Where-Object { $_.FullName -ieq $entryPoint })
        if ($executables.Count -ne 1 -or $executables[0].FullName -cne $entryPoint -or $executables[0].Length -le 0) {
            throw 'MSIX does not contain exactly one expected executable.'
        }
        $payload = $executables[0].Open()
        try { $executableSha = (Get-FileHash -InputStream $payload -Algorithm SHA256).Hash }
        finally { $payload.Dispose() }
    }
    return [pscustomobject]@{
        Name = $packageName
        EntryPoint = $entryPoint
        Publisher = $identity.GetAttribute('Publisher')
        Version = $identity.GetAttribute('Version')
        Architecture = $identity.GetAttribute('ProcessorArchitecture')
        ResourceId = $identity.GetAttribute('ResourceId')
        ExecutableSha = $executableSha
    }
}

$packagePath = (Resolve-Path -LiteralPath $Package).ProviderPath
if ($ExpectedPackageSha256) {
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($packagePath))
    if ($drive.DriveType -ne 'Fixed' -or $drive.DriveFormat -ne 'NTFS') {
        throw 'Verify an exact package from a local NTFS directory.'
    }
    $file = Get-Item -LiteralPath $packagePath -Force
    if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'MSIX path contains a reparse point.' }
    for ($parent = $file.Directory; $parent; $parent = $parent.Parent) {
        if ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'MSIX path contains a reparse point.' }
    }
}
# Read the same MSIX bytes for the digest, archive and signature, without
# permitting a writer or replacement while the checks are in progress.
$packageFile = [IO.File]::Open($packagePath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
try {
    if ($ExpectedPackageSha256) {
        $packageSha = (Get-FileHash -InputStream $packageFile -Algorithm SHA256).Hash
        if ($packageSha -ine $ExpectedPackageSha256) { throw 'MSIX does not match the expected package SHA-256.' }
        $packageFile.Position = 0
    }
    $archive = [IO.Compression.ZipArchive]::new($packageFile, [IO.Compression.ZipArchiveMode]::Read, $true)
    try { $facts = Read-Package -Archive $archive -ReadExecutable:([bool]$ExpectedPackageSha256) }
    finally { $archive.Dispose() }
    $signature = Get-AuthenticodeSignature -LiteralPath $packagePath
    if (-not $signature.SignerCertificate) { throw 'MSIX has no embedded signing certificate.' }
    if ($signature.Status -ne 'Valid') { throw "MSIX signature is not valid on this host: $($signature.Status)" }
    if ($ExpectedPackageSha256 -and (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash -ine $packageSha) {
        throw 'MSIX path changed during signature verification.'
    }
} finally {
    $packageFile.Dispose()
}
Write-Output ("MSIX static smoke passed: identity={0}, entryPoint={1}, signatureStatus={2}" -f $facts.Name, $facts.EntryPoint, $signature.Status)
if ($VerifyInstalled) {
    $registrations = @(Get-AppxPackage -Name $facts.Name -PackageTypeFilter Main)
    if ($registrations.Count -ne 1) { throw 'Expected exactly one GRAF registration for the current user.' }
    $registered = $registrations[0]
    if ($registered.Name -cne $facts.Name -or $registered.Publisher -cne $facts.Publisher -or
        [string]$registered.Version -cne $facts.Version -or [string]$registered.Architecture -ine $facts.Architecture -or
        [string]$registered.ResourceId -cne $facts.ResourceId -or $registered.IsDevelopmentMode -ne $false -or
        [string]$registered.Status -ne 'Ok' -or -not $registered.InstallLocation) {
        throw 'Installed GRAF registration does not match the verified MSIX.'
    }
    $exePath = Join-Path $registered.InstallLocation $facts.EntryPoint
    $installedSha = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash
    if ($installedSha -ine $facts.ExecutableSha) { throw 'Installed GRAF executable does not match the MSIX payload.' }

    if ($RequireRunning) {
        if (-not ('GrafInstalledWindowProof' -as [type])) {
            Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

public static class GrafInstalledWindowProof {
    [DllImport("kernel32.dll", ExactSpelling = true, CharSet = CharSet.Unicode)]
    static extern int GetPackageFullName(IntPtr process, ref uint size, StringBuilder name);
    [DllImport("advapi32.dll")]
    static extern bool OpenProcessToken(IntPtr process, uint access, out SafeFileHandle token);
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll")]
    static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")]
    static extern IntPtr GetAncestor(IntPtr window, uint flags);
    [DllImport("user32.dll", ExactSpelling = true, CharSet = CharSet.Unicode)]
    static extern int GetClassNameW(IntPtr window, StringBuilder name, int capacity);
    [DllImport("user32.dll", ExactSpelling = true)]
    static extern IntPtr SendMessageTimeoutW(IntPtr window, uint message, UIntPtr wParam,
        IntPtr lParam, uint flags, uint timeoutMs, out UIntPtr result);

    static bool OwnedWindow(IntPtr window, uint pid) {
        uint actualPid;
        if (window == IntPtr.Zero || !IsWindowVisible(window) || GetAncestor(window, 2) != window ||
            GetWindowThreadProcessId(window, out actualPid) == 0 || actualPid != pid) return false;
        // A MessageBox from wWinMain's startup failure also answers WM_NULL.
        var name = new StringBuilder(256);
        return GetClassNameW(window, name, name.Capacity) > 0 && name.ToString() != "#32770";
    }

    public static bool Matches(IntPtr process, IntPtr window, uint pid, string expectedPackage, string expectedSid) {
        uint size = 0;
        if (GetPackageFullName(process, ref size, null) != 122 || size == 0 || size > 512) return false;
        var name = new StringBuilder((int)size);
        if (GetPackageFullName(process, ref size, name) != 0 || name.ToString() != expectedPackage) return false;
        SafeFileHandle token;
        if (!OpenProcessToken(process, 8, out token)) return false;
        using (token)
        using (var user = new WindowsIdentity(token.DangerousGetHandle())) {
            if (user.User == null || user.User.Value != expectedSid) return false;
        }
        // Probe the same HWND whose owner we checked, without changing its state.
        UIntPtr ignored;
        return OwnedWindow(window, pid) &&
            SendMessageTimeoutW(window, 0, UIntPtr.Zero, IntPtr.Zero, 0x23, 1000, out ignored) != IntPtr.Zero &&
            OwnedWindow(window, pid);
    }
}
'@
        }
        $session = (Get-Process -Id $PID).SessionId
        if ($session -eq 0) { throw 'Verify the GRAF window in an interactive Windows session.' }
        function Get-CandidateProcesses {
            Get-Process -Name ([IO.Path]::GetFileNameWithoutExtension($facts.EntryPoint)) -ErrorAction SilentlyContinue |
                Where-Object { $_.SessionId -eq $session -and $_.Path -ieq $exePath }
        }
        $running = @(Get-CandidateProcesses)
        if ($running.Count -ne 1) {
            throw 'No single responding window from the verified installed GRAF in this session.'
        }
    }
    $current = @(Get-AppxPackage -Name $facts.Name -PackageTypeFilter Main)
    if ($current.Count -ne 1 -or $current[0].PackageFullName -cne $registered.PackageFullName -or
        [string]$current[0].ResourceId -cne $facts.ResourceId -or $current[0].IsDevelopmentMode -ne $false -or
        $current[0].InstallLocation -ine $registered.InstallLocation -or [string]$current[0].Status -ne 'Ok') {
        throw 'GRAF registration changed during verification.'
    }
    if ($RequireRunning) {
        $process = $running[0]
        $process.Refresh()
        $window = $process.MainWindowHandle
        $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        if ($process.HasExited -or $process.SessionId -ne $session -or $process.Path -ine $exePath -or $window -eq [IntPtr]::Zero -or
            -not [GrafInstalledWindowProof]::Matches($process.Handle, $window, [uint32]$process.Id,
                $registered.PackageFullName, $sid)) {
            throw 'No single responding window from the verified installed GRAF in this session.'
        }
        $currentProcesses = @(Get-CandidateProcesses)
        $process.Refresh()
        if ($currentProcesses.Count -ne 1 -or $currentProcesses[0].Id -ne $process.Id -or
            $process.HasExited -or $process.MainWindowHandle -ne $window) {
            throw 'GRAF process or window changed during verification.'
        }
    }
    Write-Output ([pscustomobject]@{
        identity = $facts.Name
        version = $facts.Version
        architecture = $facts.Architecture
        package_sha256 = $packageSha.ToLowerInvariant()
        installed_executable_sha256 = $installedSha.ToLowerInvariant()
        running_window = if ($RequireRunning) { 'observed' } else { 'not_checked' }
    } | ConvertTo-Json -Compress)
}
if ($UiMatrix) {
    Write-Output 'UI matrix remains a clean-image gate: first launch, WebView2 repair, update interruption, rollback and uninstall are not claimed here.'
}
