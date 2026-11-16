#requires -Version 5.1
# Offline release-input checks only. This tool neither signs nor installs packages.
[CmdletBinding(DefaultParameterSetName = 'Prepare')]
param(
    [Parameter(Mandatory = $true)][string]$ReleaseInputs,
    [Parameter(Mandatory = $true)][string]$Package,
    [Parameter(Mandatory = $true)][string[]]$DependencyPackage,
    [Parameter(Mandatory = $true, ParameterSetName = 'Prepare')][string]$OutputDirectory,
    [Parameter(Mandatory = $true, ParameterSetName = 'Validate')][string]$AppInstaller
)
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
$script:failureReason = 'io_or_format'
$heldFiles = New-Object 'System.Collections.Generic.List[System.IO.Stream]'
$foundation = 'http://schemas.microsoft.com/appx/manifest/foundation/windows10'
$installerNamespace = 'http://schemas.microsoft.com/appx/appinstaller/2017'
function Fail([string]$Reason) { $script:failureReason = $Reason; throw $Reason }
function Require([bool]$Condition, [string]$Reason) { if (-not $Condition) { Fail $Reason } }
function Shape($Value, [string[]]$Keys) {
    Require ($Value -is [System.Collections.IDictionary]) 'input_shape'
    Require ($Value.psbase.Count -eq $Keys.Count) 'input_shape'
    foreach ($key in $Keys) { Require ($Value.Contains($key)) 'input_shape' }
}
function Text($Value, [bool]$AllowEmpty = $false) {
    Require ($Value -is [string]) 'input_type'
    Require ($Value.Length -le 4096 -and ($AllowEmpty -or $Value.Length -gt 0) -and $Value -notmatch '[\x00-\x1f\x7f]') 'input_text'
}
function Quad($Value) {
    Text $Value
    Require ($Value -cmatch '^\d+\.\d+\.\d+\.\d+$') 'input_version'
    foreach ($part in $Value.Split('.')) { Require ([long]$part -le 65535) 'input_version' }
    return [version]$Value
}
function Https($Value) {
    Text $Value
    Require ($Value.Length -le 2084) 'input_uri'
    $uri = $null
    Require ([Uri]::TryCreate($Value, [UriKind]::Absolute, [ref]$uri)) 'input_uri'
    Require ($Value -cmatch '^https://' -and $uri.Host -and $uri.AbsolutePath -ne '/' -and
        -not $uri.UserInfo -and -not $uri.Query -and -not $uri.Fragment -and
        $Value -notmatch '[\\\s?#]' -and $Value -notmatch '(?i)%0[ad]') 'input_uri'
}
function IdentityInput($Value, [bool]$Main) {
    $keys = @('Name', 'Publisher', 'Version', 'Architecture', 'Uri', 'Sha256')
    if ($Main) { $keys += @('ResourceId', 'ExecutableSha256') }
    Shape $Value $keys
    foreach ($key in $keys) { Text $Value[$key] ($key -eq 'ResourceId') }
    Require ($Value.Name -cmatch '^[A-Za-z0-9][A-Za-z0-9.-]{2,49}$') 'input_identity'
    Require ($Value.Architecture -ceq 'x64') 'input_architecture'
    Require ($Value.Publisher.Trim() -ine 'CN=GRAF') 'development_publisher'
    $null = Quad $Value.Version
    Https $Value.Uri
    Require ($Value.Sha256 -match '^[0-9a-fA-F]{64}$') 'input_hash'
    if ($Main) {
        Require ($Value.ResourceId -ceq '') 'input_resource'
        Require ($Value.ExecutableSha256 -match '^[0-9a-fA-F]{64}$') 'input_hash'
    }
}
function HoldFile([string]$Path) {
    Require ([IO.File]::Exists($Path)) 'local_file_missing'
    $file = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $heldFiles.Add($file)
    return $file
}
function HashStream([IO.Stream]$Stream) { return (Get-FileHash -InputStream $Stream -Algorithm SHA256).Hash.ToLowerInvariant() }
function Xml([IO.Stream]$Stream, [long]$Limit) {
    $settings = New-Object System.Xml.XmlReaderSettings
    $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    $settings.XmlResolver = $null
    $settings.MaxCharactersInDocument = $Limit
    $settings.CloseInput = $false
    $reader = [System.Xml.XmlReader]::Create($Stream, $settings)
    try { $doc = New-Object System.Xml.XmlDocument; $doc.XmlResolver = $null; $doc.Load($reader); return ,$doc }
    finally { $reader.Dispose() }
}
# .NET Framework ZipArchive does not expose/check entry CRC32. Read only the
# central-directory CRC metadata; ZipArchive still owns decompression and XML.
function ZipCrcs([IO.Stream]$File) {
    $tailCount = [int][Math]::Min($File.Length, 65557)
    $tail = New-Object byte[] $tailCount
    $File.Position = $File.Length - $tailCount
    Require ($File.Read($tail, 0, $tail.Length) -eq $tail.Length) 'zip_format'
    $end = -1
    for ($i = $tail.Length - 22; $i -ge 0; --$i) {
        if ([BitConverter]::ToUInt32($tail, $i) -eq 0x06054b50 -and
            $i + 22 + [BitConverter]::ToUInt16($tail, $i + 20) -eq $tail.Length) { $end = $i; break }
    }
    Require ($end -ge 0) 'zip_format'
    $count = [BitConverter]::ToUInt16($tail, $end + 10)
    $size = [BitConverter]::ToUInt32($tail, $end + 12)
    $offset = [BitConverter]::ToUInt32($tail, $end + 16)
    Require ([BitConverter]::ToUInt32($tail, $end + 4) -eq 0 -and
        [BitConverter]::ToUInt16($tail, $end + 8) -eq $count -and $count -lt 65535 -and
        $size -le 16777216 -and [long]$offset + $size -eq $File.Length - $tailCount + $end) 'zip_format'
    $File.Position = $offset
    $reader = [IO.BinaryReader]::new($File, [Text.Encoding]::UTF8, $true)
    $crcs = New-Object 'System.Collections.Generic.List[uint32]'
    try {
        for ($i = 0; $i -lt $count; ++$i) {
            Require ($reader.ReadUInt32() -eq 0x02014b50) 'zip_format'
            $header = $reader.ReadBytes(42); Require ($header.Length -eq 42) 'zip_format'
            Require (([BitConverter]::ToUInt16($header, 4) -band 1) -eq 0) 'zip_format'
            $crcs.Add([BitConverter]::ToUInt32($header, 12))
            $skip = [int][BitConverter]::ToUInt16($header, 24) + [BitConverter]::ToUInt16($header, 26) + [BitConverter]::ToUInt16($header, 28)
            $File.Position += $skip
            Require ($File.Position -le [long]$offset + $size) 'zip_format'
        }
        Require ($File.Position -eq [long]$offset + $size) 'zip_format'
    } finally { $reader.Dispose() }
    return ,$crcs
}
function EntryHash($Entry, [uint32]$ExpectedCrc, [IO.Stream]$CopyTo = $null) {
    $entryStream = $Entry.Open(); $hash = [Security.Cryptography.SHA256]::Create()
    $crc = [uint32]::MaxValue; $total = [long]0; $buffer = New-Object byte[] 16384
    try {
        while (($read = $entryStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $total += $read; Require ($total -le $Entry.Length) 'zip_format'
            $null = $hash.TransformBlock($buffer, 0, $read, $buffer, 0)
            if ($null -ne $CopyTo) { $CopyTo.Write($buffer, 0, $read) }
            for ($j = 0; $j -lt $read; ++$j) { $crc = ($crc -shr 8) -bxor $script:crcTable[($crc -bxor $buffer[$j]) -band 255] }
        }
        Require ($total -eq $Entry.Length -and ($crc -bxor [uint32]::MaxValue) -eq $ExpectedCrc) 'zip_crc'
        $null = $hash.TransformFinalBlock($buffer, 0, 0)
        return ([BitConverter]::ToString($hash.Hash)).Replace('-', '').ToLowerInvariant()
    } finally { $entryStream.Dispose(); $hash.Dispose() }
}
function ReadPackage([string]$Path, $Expected, [bool]$Main, [IO.Stream]$Held = $null) {
    Require ([IO.Path]::GetExtension($Path) -in @('.appx', '.msix') -and (-not $Main -or [IO.Path]::GetExtension($Path) -eq '.msix')) 'package_form'
    $file = $Held; if ($null -eq $file) { $file = HoldFile $Path }
    $file.Position = 0
    $digest = HashStream $file; Require ($digest -ieq $Expected.Sha256) 'package_hash'
    $file.Position = 0; $crcs = ZipCrcs $file; $file.Position = 0
    $archive = [IO.Compression.ZipArchive]::new($file, [IO.Compression.ZipArchiveMode]::Read, $true)
    try {
        Require ($archive.Entries.Count -eq $crcs.Count) 'zip_format'
        $names = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
        $manifestIndex = -1
        for ($i = 0; $i -lt $archive.Entries.Count; ++$i) {
            $name = $archive.Entries[$i].FullName
            Require ($name -and $name -notmatch '(^/|\\|(^|/)\.\.?(/|$)|[:\x00-\x1f\x7f])' -and $names.Add($name)) 'zip_entry'
            if ($name -ieq 'AppxManifest.xml') { Require ($name -ceq 'AppxManifest.xml') 'zip_entry'; $manifestIndex = $i }
        }
        Require ($manifestIndex -ge 0) 'manifest_missing'
        $entry = $archive.Entries[$manifestIndex]; Require ($entry.Length -gt 0 -and $entry.Length -le 1048576) 'manifest_size'
        $memory = New-Object IO.MemoryStream
        try { $null = EntryHash $entry $crcs[$manifestIndex] $memory; $memory.Position = 0; $doc = Xml $memory 1048576 }
        finally { $memory.Dispose() }
        $ns = New-Object System.Xml.XmlNamespaceManager($doc.NameTable); $ns.AddNamespace('a', $foundation)
        Require ($doc.DocumentElement.LocalName -ceq 'Package' -and $doc.DocumentElement.NamespaceURI -ceq $foundation) 'manifest_identity'
        $ids = @($doc.SelectNodes('/a:Package/a:Identity', $ns)); Require ($ids.Count -eq 1) 'manifest_identity'
        foreach ($field in @('Name', 'Publisher', 'Version', 'ProcessorArchitecture', 'ResourceId')) {
            $key = $field; if ($field -eq 'ProcessorArchitecture') { $key = 'Architecture' }
            $wanted = ''; if ($Expected.Contains($key)) { $wanted = $Expected[$key] }
            Require ($ids[0].GetAttribute($field) -ceq $wanted) 'manifest_identity'
        }
        Require ($doc.SelectNodes('/a:Package/a:Dependencies', $ns).Count -eq 1) 'dependency_form'
        $families = @($doc.SelectNodes('/a:Package/a:Dependencies/a:TargetDeviceFamily', $ns))
        Require ($families.Count -eq 1) 'manifest_os'
        $min = Quad $families[0].GetAttribute('MinVersion')
        if ($Main) { Require ($families[0].GetAttribute('Name') -ceq 'Windows.Desktop' -and $min -eq [version]'10.0.19045.0') 'manifest_os' }
        else { Require ($families[0].GetAttribute('Name') -in @('Windows.Desktop', 'Windows.Universal') -and $min -le [version]'10.0.19045.0') 'manifest_os' }
        $resources = @($doc.SelectNodes('/a:Package/a:Properties/a:ResourcePackage', $ns))
        Require ($resources.Count -le 1 -and ($resources.Count -eq 0 -or $resources[0].InnerText -ceq 'false')) 'framework_shape'
        $framework = @($doc.SelectNodes('/a:Package/a:Properties/a:Framework', $ns))
        Require ($framework.Count -le 1) 'framework_shape'
        if ($Main) { Require ($framework.Count -eq 0 -or $framework[0].InnerText -ceq 'false') 'framework_shape' }
        else { Require ($framework.Count -eq 1 -and $framework[0].InnerText -ceq 'true') 'framework_shape' }
        $exeHash = $null
        if ($Main) {
            $apps = @($doc.SelectNodes('/a:Package/a:Applications/a:Application', $ns)); Require ($apps.Count -eq 1) 'main_application_count'
            $executable = $apps[0].GetAttribute('Executable'); Require ($executable -ceq 'GrafWindowsApp.exe') 'main_launch_executable'
            $exeIndex = -1
            for ($i = 0; $i -lt $archive.Entries.Count; ++$i) { if ($archive.Entries[$i].FullName -ceq $executable) { $exeIndex = $i } }
            Require ($exeIndex -ge 0 -and $archive.Entries[$exeIndex].Length -gt 0) 'main_executable_entry'
            $exeHash = EntryHash $archive.Entries[$exeIndex] $crcs[$exeIndex]
            Require ($exeHash -ieq $Expected.ExecutableSha256) 'main_executable_hash'
        }
        $dependencies = @(); $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
        foreach ($node in $doc.SelectNodes('/a:Package/a:Dependencies/*', $ns)) {
            if ($node.LocalName -ceq 'TargetDeviceFamily' -and $node.NamespaceURI -ceq $foundation) { continue }
            Require ($node.LocalName -ceq 'PackageDependency' -and $node.NamespaceURI -ceq $foundation -and $node.ChildNodes.Count -eq 0) 'dependency_form'
            foreach ($attr in $node.Attributes) { Require ($attr.NamespaceURI -eq '' -and $attr.Name -cin @('Name','Publisher','MinVersion','ProcessorArchitecture')) 'dependency_form' }
            $name = $node.GetAttribute('Name'); $publisher = $node.GetAttribute('Publisher')
            Require ($name -and $publisher -and $seen.Add($name)) 'dependency_declaration'
            Require (-not $node.HasAttribute('ProcessorArchitecture') -or $node.GetAttribute('ProcessorArchitecture') -ceq 'x64') 'dependency_form'
            $dependencies += @{ Name = $name; Publisher = $publisher; MinVersion = (Quad $node.GetAttribute('MinVersion')) }
        }
        return @{ Expected = $Expected; Sha256 = $digest; ExecutableSha256 = $exeHash; Dependencies = $dependencies }
    } finally { $archive.Dispose() }
}
function CheckElement($Node, [string]$Name, $Attributes, [string[]]$Children) {
    Require ($Node.LocalName -ceq $Name -and $Node.NamespaceURI -ceq $installerNamespace) 'appinstaller_shape'
    $count = 0
    foreach ($attr in $Node.Attributes) {
        if ($attr.NamespaceURI -eq 'http://www.w3.org/2000/xmlns/') { Require ($attr.Value -ceq $installerNamespace) 'appinstaller_shape'; continue }
        Require ($attr.NamespaceURI -eq '' -and $attr.Name -cin @($Attributes.Keys)) 'appinstaller_shape'
        Require ($attr.Value -ceq $Attributes[$attr.Name]) 'appinstaller_value'; ++$count
    }
    Require ($count -eq $Attributes.Count) 'appinstaller_shape'
    foreach ($child in $Node.ChildNodes) {
        if ($child -is [System.Xml.XmlElement]) { Require ($child.NamespaceURI -ceq $installerNamespace -and $child.LocalName -cin $Children) 'appinstaller_shape' }
        else { Require ($child -is [System.Xml.XmlWhitespace] -or $child -is [System.Xml.XmlComment]) 'appinstaller_shape' }
    }
}
function PackageAttributes($Expected, [bool]$Main) {
    $attrs = [ordered]@{ Name=$Expected.Name; Publisher=$Expected.Publisher; Version=$Expected.Version; ProcessorArchitecture=$Expected.Architecture; Uri=$Expected.Uri }
    if ($Main -and $Expected.ResourceId) { $attrs.ResourceId = $Expected.ResourceId }
    return $attrs
}
function CheckInstaller($Doc, $Inputs) {
    $root = $Doc.DocumentElement
    CheckElement $root 'AppInstaller' ([ordered]@{ Version=$Inputs.AppInstallerVersion; Uri=$Inputs.AppInstallerUri }) @('MainPackage','Dependencies')
    $children = @($root.ChildNodes | Where-Object { $_ -is [System.Xml.XmlElement] })
    $main = @($children | Where-Object LocalName -CEQ 'MainPackage'); $deps = @($children | Where-Object LocalName -CEQ 'Dependencies')
    Require ($children.Count -eq 2 -and $main.Count -eq 1 -and $deps.Count -eq 1) 'appinstaller_shape'
    CheckElement $main[0] 'MainPackage' (PackageAttributes $Inputs.Package $true) @()
    CheckElement $deps[0] 'Dependencies' ([ordered]@{}) @('Package')
    $packages = @($deps[0].ChildNodes | Where-Object { $_ -is [System.Xml.XmlElement] })
    Require ($packages.Count -eq $Inputs.Dependencies.Count) 'appinstaller_dependencies'
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    foreach ($node in $packages) {
        $match = @($Inputs.Dependencies | Where-Object { $_.Name -ceq $node.GetAttribute('Name') })
        Require ($match.Count -eq 1 -and $seen.Add($node.GetAttribute('Name'))) 'appinstaller_dependencies'
        CheckElement $node 'Package' (PackageAttributes $match[0] $false) @()
    }
}
try {
    Add-Type -AssemblyName System.IO.Compression
    $script:crcTable = New-Object uint32[] 256
    $polynomial = [Convert]::ToUInt32('EDB88320', 16)
    for ($i = 0; $i -lt 256; ++$i) {
        $crc = [uint32]$i
        for ($bit = 0; $bit -lt 8; ++$bit) { if ($crc -band 1) { $crc = ($crc -shr 1) -bxor $polynomial } else { $crc = $crc -shr 1 } }
        $script:crcTable[$i] = $crc
    }
    Require ([IO.Path]::GetExtension($ReleaseInputs) -eq '.psd1') 'input_shape'
    $inputFile = HoldFile $ReleaseInputs; Require ($inputFile.Length -gt 0 -and $inputFile.Length -le 65536) 'input_size'
    $inputHash = HashStream $inputFile
    # Import-PowerShellDataFile uses the restricted constant-data evaluator.
    $script:failureReason = 'input_data'; $inputs = Import-PowerShellDataFile -LiteralPath $ReleaseInputs; $script:failureReason = 'io_or_format'
    Shape $inputs @('SchemaVersion','Channel','SourceSha','ReleaseVersion','ExpectedPackageFamilyName','SigningMethod','MinimumWindowsVersion','AppInstallerUri','AppInstallerVersion','Package','Dependencies')
    Require ($inputs.SchemaVersion -is [int] -and $inputs.SchemaVersion -eq 1) 'input_schema'
    foreach ($key in @('Channel','SourceSha','ReleaseVersion','ExpectedPackageFamilyName','SigningMethod','MinimumWindowsVersion','AppInstallerUri','AppInstallerVersion')) { Text $inputs[$key] }
    Require ($inputs.Channel -ceq 'direct-msix' -and $inputs.MinimumWindowsVersion -ceq '10.0.19045.0') 'input_baseline'
    Require ($inputs.SourceSha -match '^[0-9a-fA-F]{40}$') 'input_source'
    Require ($inputs.ReleaseVersion -cmatch '^v?[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*$') 'input_release_version'
    $null = Quad $inputs.AppInstallerVersion; Https $inputs.AppInstallerUri
    IdentityInput $inputs.Package $true
    Require ($inputs.ExpectedPackageFamilyName.StartsWith($inputs.Package.Name + '_', [StringComparison]::Ordinal) -and
        $inputs.ExpectedPackageFamilyName.Length -gt $inputs.Package.Name.Length + 1) 'input_family'
    Require ($inputs.Dependencies -is [array] -and $inputs.Dependencies.Count -ge 2 -and $inputs.Dependencies.Count -le 64) 'input_dependencies'
    $approved = @{}
    foreach ($dep in $inputs.Dependencies) { IdentityInput $dep $false; Require (-not $approved.ContainsKey($dep.Name)) 'input_dependencies'; $approved[$dep.Name] = $dep }
    Require ($approved.ContainsKey('Microsoft.VCLibs.140.00.UWPDesktop') -and $approved.ContainsKey('Microsoft.WindowsAppRuntime.2')) 'input_dependencies'
    Require ($DependencyPackage.Count -eq $approved.Count) 'dependency_paths'
    $main = ReadPackage $Package $inputs.Package $true
    $frameworks = @{}
    foreach ($path in $DependencyPackage) {
        # Match independent digest using the same held file used for ZIP inspection.
        $dependencyFile = HoldFile $path; $dependencyDigest = HashStream $dependencyFile
        $found = $null
        foreach ($dep in $inputs.Dependencies) {
            if ($dep.Sha256 -ieq $dependencyDigest) { Require ($null -eq $found) 'dependency_paths'; $found = $dep }
        }
        Require ($null -ne $found -and -not $frameworks.ContainsKey($found.Name)) 'dependency_hash'
        $frameworks[$found.Name] = ReadPackage $path $found $false $dependencyFile
    }
    $reachable = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::Ordinal)
    $pending = New-Object 'System.Collections.Generic.Queue[object]'; $pending.Enqueue($main)
    while ($pending.Count) {
        $parent = $pending.Dequeue()
        foreach ($requirement in $parent.Dependencies) {
            Require ($frameworks.ContainsKey($requirement.Name)) 'dependency_missing'
            $target = $frameworks[$requirement.Name]
            Require ($target.Expected.Name -ceq $requirement.Name -and $target.Expected.Publisher -ceq $requirement.Publisher -and
                [version]$target.Expected.Version -ge $requirement.MinVersion) 'dependency_requirement'
            if ($reachable.Add($requirement.Name)) { $pending.Enqueue($target) }
        }
    }
    Require ($reachable.Count -eq $frameworks.Count) 'dependency_extra'
    $xmlMemory = New-Object IO.MemoryStream
    try {
        if ($PSCmdlet.ParameterSetName -eq 'Prepare') {
            $settings = New-Object System.Xml.XmlWriterSettings; $settings.Encoding = [Text.UTF8Encoding]::new($false); $settings.Indent = $true
            $writer = [System.Xml.XmlWriter]::Create($xmlMemory, $settings)
            try {
                $writer.WriteStartDocument(); $writer.WriteStartElement('AppInstaller', $installerNamespace)
                $writer.WriteAttributeString('Version', $inputs.AppInstallerVersion); $writer.WriteAttributeString('Uri', $inputs.AppInstallerUri)
                $writer.WriteStartElement('MainPackage', $installerNamespace)
                $attrs = PackageAttributes $inputs.Package $true
                foreach ($key in $attrs.Keys) { $writer.WriteAttributeString($key, $attrs[$key]) }; $writer.WriteEndElement()
                $writer.WriteStartElement('Dependencies', $installerNamespace)
                foreach ($dep in $inputs.Dependencies) {
                    $writer.WriteStartElement('Package', $installerNamespace); $attrs = PackageAttributes $dep $false
                    foreach ($key in $attrs.Keys) { $writer.WriteAttributeString($key, $attrs[$key]) }; $writer.WriteEndElement()
                }
                $writer.WriteEndElement(); $writer.WriteEndElement(); $writer.WriteEndDocument(); $writer.Flush()
            } finally { $writer.Dispose() }
            $xmlMemory.Position = 0; $doc = Xml $xmlMemory 65536
        } else {
            $xmlFile = HoldFile $AppInstaller; Require ($xmlFile.Length -gt 0 -and $xmlFile.Length -le 65536) 'appinstaller_size'
            $doc = Xml $xmlFile 65536
        }
        CheckInstaller $doc $inputs
        if ($PSCmdlet.ParameterSetName -eq 'Prepare') {
            $xmlMemory.Position = 0; $xmlHash = HashStream $xmlMemory
            $packageEvidence = @(@{ Name=$inputs.Package.Name; Sha256=$main.Sha256; ExecutableSha256=$main.ExecutableSha256 })
            foreach ($dep in $inputs.Dependencies) { $packageEvidence += @{ Name=$dep.Name; Sha256=$frameworks[$dep.Name].Sha256 } }
            $receipt = [ordered]@{ schema=1; validation='static_inputs_and_xml_only'; public_release_ready=$false;
                source_sha_declared=$inputs.SourceSha; release_version_declared=$inputs.ReleaseVersion;
                owner_legal_name_approved='ИП Шишеня Ян Александрович'; expected_family_declared=$inputs.ExpectedPackageFamilyName;
                signing_method_declared=$inputs.SigningMethod; family_registration='not_checked'; signature_chain='not_checked';
                trusted_timestamp='not_checked'; served_https_mime_redirects='not_checked'; installed_association='not_checked';
                t112_approval='not_created'; inputs_sha256=$inputHash; appinstaller_sha256=$xmlHash; packages=$packageEvidence }
            Require (-not [IO.Directory]::Exists($OutputDirectory) -and -not [IO.File]::Exists($OutputDirectory)) 'output_exists'
            # DirectoryInfo.Create is not an exclusive mkdir: use a unique owned
            # staging directory and a no-overwrite same-parent rename to publish.
            $fullOutput = [IO.Path]::GetFullPath($OutputDirectory)
            $parent = [IO.Path]::GetDirectoryName($fullOutput); Require ([IO.Directory]::Exists($parent)) 'output_parent'
            $stage = [IO.Path]::Combine($parent, '.graf-release-' + [guid]::NewGuid().ToString('N'))
            $null = New-Item -ItemType Directory -Path $stage -ErrorAction Stop
            try {
                [IO.File]::WriteAllBytes([IO.Path]::Combine($stage,'release.appinstaller'), $xmlMemory.ToArray())
                [IO.File]::WriteAllText([IO.Path]::Combine($stage,'release-input-validation.json'), ($receipt | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
                [IO.Directory]::Move($stage, $fullOutput)
            } finally {
                if ([IO.Directory]::Exists($stage)) {
                    foreach ($name in @('release.appinstaller','release-input-validation.json')) {
                        $owned = [IO.Path]::Combine($stage, $name); if ([IO.File]::Exists($owned)) { [IO.File]::Delete($owned) }
                    }
                    [IO.Directory]::Delete($stage, $false)
                }
            }
        }
    } finally { $xmlMemory.Dispose() }
    Write-Output 'T124_STATIC_VALID public_release_ready=false'
} catch { throw ('T124:' + $script:failureReason) }
finally { foreach ($file in $heldFiles) { $file.Dispose() } }
