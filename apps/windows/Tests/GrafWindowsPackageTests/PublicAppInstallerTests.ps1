#requires -Version 5.1
# Run in Windows PowerShell 5.1. Synthetic ZIPs are never signed/installed/executed.
[CmdletBinding()]
param()
Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
$tool = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../scripts/prepare-public-appinstaller.ps1'))
$root = Join-Path ([IO.Path]::GetTempPath()) ('graf-appinstaller-tests-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $root
$script:cases = 0
function Assert([bool]$Value, [string]$Reason) { if (-not $Value) { throw ('TEST:' + $Reason) } }
function Literal($Value) {
    if ($Value -is [System.Collections.IDictionary]) {
        $parts = @(); foreach ($key in $Value.psbase.Keys) { $parts += ((Literal ([string]$key)) + '=' + (Literal $Value[$key])) }
        return ('@{' + ($parts -join ';') + '}')
    }
    if ($Value -is [array]) { return ('@(' + ((@($Value | ForEach-Object { Literal $_ })) -join ',') + ')') }
    if ($Value -is [bool]) { if ($Value) { return '$true' }; return '$false' }
    if ($Value -is [int]) { return [string]$Value }
    if ($null -eq $Value) { return '$null' }
    return ("'" + ([string]$Value).Replace("'", "''") + "'")
}
function SaveInputs($Fixture) {
    [IO.File]::WriteAllText($Fixture.InputPath, (Literal $Fixture.Inputs), [Text.UTF8Encoding]::new($true))
}
function Digest([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Pack($Record) {
    $file = [IO.File]::Open($Record.Path, [IO.FileMode]::Create, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    try {
        $zip = [IO.Compression.ZipArchive]::new($file, [IO.Compression.ZipArchiveMode]::Create, $true)
        try {
            $entries = @(@{ Name='AppxManifest.xml'; Bytes=[Text.Encoding]::UTF8.GetBytes($Record.Xml) })
            if ($Record.Main) { $entries += @{ Name='GrafWindowsApp.exe'; Bytes=[Text.Encoding]::UTF8.GetBytes($Record.Exe) } }
            $entries += $Record.Extra
            foreach ($item in $entries) {
                $stream = $zip.CreateEntry($item.Name).Open()
                try { $stream.Write($item.Bytes, 0, $item.Bytes.Length) } finally { $stream.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $file.Dispose() }
    $Record.Expected.Sha256 = Digest $Record.Path
}
function Manifest([string]$Name, [string]$Version, [bool]$Framework, [string]$Dependencies) {
    $property = ''; $application = ''
    if ($Framework) { $property = '<Framework>true</Framework>' }
    else { $application = '<Applications><Application Id="GRAF" Executable="GrafWindowsApp.exe" EntryPoint="Windows.FullTrustApplication" /></Applications>' }
    return ('<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"><Identity Name="' + $Name + '" Publisher="CN=Synthetic Fixture" Version="' + $Version + '" ProcessorArchitecture="x64" /><Properties>' + $property + '</Properties><Dependencies><TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19045.0" MaxVersionTested="10.0.26100.0" />' + $Dependencies + '</Dependencies>' + $application + '</Package>')
}
function Requirement([string]$Name, [string]$Version) { return ('<PackageDependency Name="' + $Name + '" Publisher="CN=Synthetic Fixture" MinVersion="' + $Version + '" />') }
function Expected([string]$Name, [string]$Version, [string]$Uri) {
    return @{ Name=$Name; Publisher='CN=Synthetic Fixture'; Version=$Version; Architecture='x64'; Uri=$Uri; Sha256=('0' * 64) }
}
function Fixture {
    $dir = Join-Path $root ([guid]::NewGuid().ToString('N')); $null = New-Item -ItemType Directory -Path $dir
    $vc = Expected 'Microsoft.VCLibs.140.00.UWPDesktop' '14.0.30035.0' 'https://release.invalid/vclibs.appx'
    $runtime = Expected 'Microsoft.WindowsAppRuntime.2' '2.0.0.0' 'https://runtime.invalid/runtime.msix'
    $main = Expected 'org.synthetic.desktop' '1.2.3.4' 'https://release.invalid/main.msix'
    $main.ResourceId = ''; $main.ExecutableSha256 = ''
    $records = @(
        @{ Main=$true; Path=(Join-Path $dir 'candidate.msix'); Expected=$main; Exe='nonexecutable synthetic payload'; Extra=@(); Xml=(Manifest $main.Name $main.Version $false ((Requirement $vc.Name $vc.Version) + (Requirement $runtime.Name $runtime.Version))) },
        @{ Main=$false; Path=(Join-Path $dir 'opaque-one.appx'); Expected=$vc; Extra=@(); Xml=(Manifest $vc.Name $vc.Version $true '') },
        @{ Main=$false; Path=(Join-Path $dir 'opaque-two.msix'); Expected=$runtime; Extra=@(); Xml=(Manifest $runtime.Name $runtime.Version $true '') }
    )
    foreach ($record in $records) { Pack $record }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $main.ExecutableSha256 = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($records[0].Exe)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
    return @{ Dir=$dir; Records=$records; Paths=@($records[1].Path,$records[2].Path); InputPath=(Join-Path $dir 'release.psd1'); XmlPath=$null;
        Inputs=@{ SchemaVersion=1; Channel='direct-msix'; SourceSha=('a' * 40); ReleaseVersion='2026.11.12.1';
            ExpectedPackageFamilyName='org.synthetic.desktop_declaredonly'; SigningMethod='synthetic untrusted declaration';
            MinimumWindowsVersion='10.0.19045.0'; AppInstallerUri='https://release.invalid/release.appinstaller'; AppInstallerVersion='1.0.0.0';
            Package=$main; Dependencies=@($vc,$runtime) } }
}
function InvokeTool($Fixture, [string]$Mode, [string]$Output) {
    if ($Mode -eq 'Prepare') {
        & $tool -ReleaseInputs $Fixture.InputPath -Package $Fixture.Records[0].Path -DependencyPackage @($Fixture.Paths) -OutputDirectory $Output
    } else {
        & $tool -ReleaseInputs $Fixture.InputPath -Package $Fixture.Records[0].Path -DependencyPackage @($Fixture.Paths) -AppInstaller $Fixture.XmlPath
    }
}
function PrepareFixture($Fixture) {
    SaveInputs $Fixture; $output = Join-Path $Fixture.Dir 'valid'
    $null = InvokeTool $Fixture 'Prepare' $output
    $Fixture.XmlPath = Join-Path $output 'release.appinstaller'
    return $output
}
function Snapshot([string]$Directory) {
    return ((@(Get-ChildItem -LiteralPath $Directory -Recurse -File | Sort-Object FullName | ForEach-Object { $_.FullName + ':' + (Digest $_.FullName) })) -join "`n")
}
function Positive([scriptblock]$Change) {
    $f = Fixture; & $Change $f
    $output = PrepareFixture $f
    $receipt = Get-Content -LiteralPath (Join-Path $output 'release-input-validation.json') -Raw | ConvertFrom-Json
    Assert ($receipt.public_release_ready -ceq $false -and $receipt.validation -ceq 'static_inputs_and_xml_only') 'not_public_ready'
    foreach ($field in @('signature_chain','trusted_timestamp','family_registration','installed_association','served_https_mime_redirects')) { Assert ($receipt.$field -ceq 'not_checked') ('unmeasured_' + $field) }
    Assert ($receipt.t112_approval -ceq 'not_created' -and $receipt.packages.Count -eq 3) 'receipt_set'
    foreach ($record in $f.Records) {
        $evidence = @($receipt.packages | Where-Object { $_.Name -ceq $record.Expected.Name })
        Assert ($evidence.Count -eq 1 -and $evidence[0].Sha256 -ieq $record.Expected.Sha256) 'actual_package_hash'
    }
    $mainEvidence = @($receipt.packages | Where-Object { $_.Name -ceq $f.Inputs.Package.Name })
    Assert ($mainEvidence[0].ExecutableSha256 -ieq $f.Inputs.Package.ExecutableSha256) 'actual_exe_hash'
    [xml]$xml = Get-Content -LiteralPath $f.XmlPath -Raw
    Assert ($xml.DocumentElement.NamespaceURI -ceq 'http://schemas.microsoft.com/appx/appinstaller/2017') 'xml_namespace'
    Assert ($xml.SelectNodes('/*/*[local-name()="Dependencies"]/*').Count -eq 2) 'both_frameworks'
    Assert (-not $xml.SelectSingleNode('//@ResourceId')) 'empty_resource_omitted'
    $snapshot = Snapshot $f.Dir
    $null = InvokeTool $f 'Validate' ''
    Assert ((Snapshot $f.Dir) -ceq $snapshot) 'validate_no_writes'
    $script:cases++
}
function Negative([string]$Name, [string]$Reason, [scriptblock]$Change, [bool]$RewriteInputs = $true) {
    $f = Fixture; $null = PrepareFixture $f
    & $Change $f
    if ($RewriteInputs) { SaveInputs $f }
    foreach ($mode in @('Prepare','Validate')) {
        $output = Join-Path $f.Dir 'rejected'; $caught = $false
        try { $null = InvokeTool $f $mode $output }
        catch { Assert ($_.Exception.Message -ceq ('T124:' + $Reason)) ($Name + ':' + $mode + ':wrong_reason'); $caught = $true }
        Assert $caught ($Name + ':' + $mode + ':accepted')
        Assert (-not [IO.Directory]::Exists($output)) ($Name + ':success_output_after_failure')
    }
    $script:cases++
}
function XmlNegative([string]$Name, [string]$Reason, [scriptblock]$Change) {
    $f = Fixture; $null = PrepareFixture $f
    [xml]$doc = Get-Content -LiteralPath $f.XmlPath -Raw; & $Change $doc
    $doc.Save($f.XmlPath); $snapshot = Snapshot $f.Dir; $caught = $false
    try { $null = InvokeTool $f 'Validate' '' }
    catch { Assert ($_.Exception.Message -ceq ('T124:' + $Reason)) ($Name + ':wrong_reason'); $caught = $true }
    Assert $caught ($Name + ':accepted'); Assert ((Snapshot $f.Dir) -ceq $snapshot) ($Name + ':validate_write')
    $script:cases++
}
try {
    Positive { param($f) }
    Positive { param($f)
        $prefix='https://release.invalid/'; $uri=$prefix+('x'*(2084-$prefix.Length))
        $f.Inputs.AppInstallerUri=$uri; $f.Inputs.Package.Uri=$uri
        foreach ($dep in $f.Inputs.Dependencies) { $dep.Uri=$uri }
    }
    Positive { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('<PackageDependency ','<PackageDependency ProcessorArchitecture="x64" '); Pack $f.Records[0] }
    Positive { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('14.0.30035.0','14.0.30000.0').Replace('MinVersion="2.0.0.0"','MinVersion="1.0.0.0"'); Pack $f.Records[0]; [array]::Reverse($f.Paths) }
    Positive { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace((Requirement $f.Records[1].Expected.Name '14.0.30035.0'),''); $f.Records[2].Xml=$f.Records[2].Xml.Replace('</Dependencies>',((Requirement $f.Records[1].Expected.Name '14.0.30035.0')+'</Dependencies>')); Pack $f.Records[0]; Pack $f.Records[2] }
    foreach ($key in @('SourceSha','ExpectedPackageFamilyName','AppInstallerUri')) {
        Negative ('missing_' + $key) 'input_shape' { param($f) $f.Inputs.Remove($key) }
    }
    foreach ($key in @('Publisher','Uri','Sha256')) {
        Negative ('missing_package_' + $key) 'input_shape' { param($f) $f.Inputs.Package.Remove($key) }
    }
    foreach ($extraKey in @('Other','Count','Keys')) { Negative 'unknown_key' 'input_shape' { param($f) $f.Inputs[$extraKey]=11 } }
    Negative 'schema_value' 'input_schema' { param($f) $f.Inputs.SchemaVersion=2 }
    Negative 'schema_type' 'input_schema' { param($f) $f.Inputs.SchemaVersion='1' }
    Negative 'publisher_type' 'input_type' { param($f) $f.Inputs.Package.Publisher=1 }
    Negative 'duplicate_data_key' 'input_data' { param($f) [IO.File]::WriteAllText($f.InputPath,"@{ SchemaVersion=1; SchemaVersion=1 }") } $false
    Negative 'missing_local' 'local_file_missing' { param($f) $f.Paths[0]=Join-Path $f.Dir 'absent.appx' }
    Negative 'bad_source' 'input_source' { param($f) $f.Inputs.SourceSha='no-source' }
    Negative 'bad_family' 'input_family' { param($f) $f.Inputs.ExpectedPackageFamilyName='other_family' }
    Negative 'main_digest' 'package_hash' { param($f) $f.Inputs.Package.Sha256='0'*64 }
    Negative 'dependency_digest' 'dependency_hash' { param($f) $f.Inputs.Dependencies[0].Sha256='0'*64 }
    foreach ($publisher in @('CN=GRAF',' cn=graf ')) { Negative 'development_publisher' 'development_publisher' { param($f) $f.Inputs.Package.Publisher=$publisher } }
    foreach ($architecture in @('x86','arm64')) { Negative 'architecture' 'input_architecture' { param($f) $f.Inputs.Package.Architecture=$architecture } }
    Negative 'changed_exe' 'main_executable_hash' { param($f) $f.Records[0].Exe+='changed'; Pack $f.Records[0] }
    foreach ($field in @('Name','Publisher','Version','ProcessorArchitecture','ResourceId')) {
        Negative ('foreign_' + $field) 'manifest_identity' { param($f)
            [xml]$doc=$f.Records[0].Xml; $node=$doc.SelectSingleNode('/*/*[local-name()="Identity"]'); $node.SetAttribute($field,'foreign'); $f.Records[0].Xml=$doc.OuterXml; Pack $f.Records[0]
        }
    }
    Negative 'foreign_launch' 'main_launch_executable' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('Executable="GrafWindowsApp.exe"','Executable="Other.exe"'); Pack $f.Records[0] }
    Negative 'missing_launch' 'main_launch_executable' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace(' Executable="GrafWindowsApp.exe"',''); Pack $f.Records[0] }
    Negative 'missing_application' 'main_application_count' { param($f) $f.Records[0].Xml=$f.Records[0].Xml -replace '<Applications>.*</Applications>',''; Pack $f.Records[0] }
    Negative 'duplicate_application' 'main_application_count' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('</Applications>','<Application Executable="GrafWindowsApp.exe" /></Applications>'); Pack $f.Records[0] }
    foreach ($entry in @('GrafWindowsApp.exe','grafwindowsapp.exe','appxmanifest.xml','../GrafWindowsApp.exe')) {
        Negative ('collision_' + $entry) 'zip_entry' { param($f) $f.Records[0].Extra=@(@{Name=$entry;Bytes=[byte[]]@(1,2,3)}); Pack $f.Records[0] }
    }
    Negative 'malformed_zip' 'zip_format' { param($f) [IO.File]::WriteAllBytes($f.Records[0].Path,[byte[]]@(1,2,3)); $f.Inputs.Package.Sha256=Digest $f.Records[0].Path }
    Negative 'malformed_manifest' 'io_or_format' { param($f) $f.Records[0].Xml='<Package>'; Pack $f.Records[0] }
    Negative 'manifest_dtd' 'io_or_format' { param($f) $f.Records[0].Xml='<!DOCTYPE Package [<!ENTITY bad "x">]>'+$f.Records[0].Xml; Pack $f.Records[0] }
    Negative 'manifest_oversize' 'manifest_size' { param($f) $f.Records[0].Xml='x'*1048577; Pack $f.Records[0] }
    Negative 'crc' 'zip_crc' { param($f)
        $bytes=[IO.File]::ReadAllBytes($f.Records[0].Path)
        for ($i=0; $i -lt $bytes.Length-20; ++$i) { if ([BitConverter]::ToUInt32($bytes,$i) -eq 0x02014b50) { $bytes[$i+16]=$bytes[$i+16] -bxor 1; break } }
        [IO.File]::WriteAllBytes($f.Records[0].Path,$bytes); $f.Inputs.Package.Sha256=Digest $f.Records[0].Path
    }
    foreach ($uri in @('http://release.invalid/main.msix','relative.msix','https://user@release.invalid/main.msix','https://release.invalid/main.msix?q=1','https://release.invalid/main.msix#x',"https://release.invalid/`nmain.msix",'https://release.invalid\main.msix')) {
         $reason='input_uri'; if ($uri -match '[\x00-\x1f\x7f]') { $reason='input_text' }; Negative 'bad_uri' $reason { param($f) $f.Inputs.Package.Uri=$uri }
    }
    foreach ($target in @('association','main','vclibs','runtime')) {
        Negative ('uri_2085_' + $target) 'input_uri' { param($f)
            $prefix='https://release.invalid/'; $uri=$prefix+('x'*(2085-$prefix.Length))
            if ($target -eq 'association') { $f.Inputs.AppInstallerUri=$uri }
            elseif ($target -eq 'main') { $f.Inputs.Package.Uri=$uri }
            elseif ($target -eq 'vclibs') { $f.Inputs.Dependencies[0].Uri=$uri }
            else { $f.Inputs.Dependencies[1].Uri=$uri }
        }
    }
    foreach ($keep in @(0,1)) { Negative 'dependency_path_count' 'dependency_paths' { param($f) $f.Paths=@($f.Paths[$keep]) } }
    Negative 'comma_joined_paths' 'dependency_paths' { param($f) $f.Paths=@($f.Paths -join ',') }
    Negative 'duplicate_paths' 'dependency_hash' { param($f) $f.Paths=@($f.Paths[0],$f.Paths[0]) }
    Negative 'nonframework' 'framework_shape' { param($f) $f.Records[1].Xml=$f.Records[1].Xml.Replace('<Framework>true</Framework>',''); Pack $f.Records[1] }
    Negative 'framework_x86' 'manifest_identity' { param($f) $f.Records[1].Xml=$f.Records[1].Xml.Replace('ProcessorArchitecture="x64"','ProcessorArchitecture="x86"'); Pack $f.Records[1] }
    Negative 'framework_publisher' 'manifest_identity' { param($f) $f.Records[1].Xml=$f.Records[1].Xml.Replace('CN=Synthetic Fixture','CN=Foreign'); Pack $f.Records[1] }
    Negative 'framework_below_minimum' 'dependency_requirement' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('MinVersion="14.0.30035.0"','MinVersion="14.0.40000.0"'); Pack $f.Records[0] }
    Negative 'framework_os' 'manifest_os' { param($f) $f.Records[1].Xml=$f.Records[1].Xml.Replace('MinVersion="10.0.19045.0"','MinVersion="10.0.22000.0"'); Pack $f.Records[1] }
    Negative 'duplicate_requirement' 'dependency_declaration' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('</Dependencies>',((Requirement $f.Records[1].Expected.Name '14.0.30035.0')+'</Dependencies>')); Pack $f.Records[0] }
    Negative 'missing_requirement_publisher' 'dependency_declaration' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace(' Publisher="CN=Synthetic Fixture" MinVersion',' MinVersion'); Pack $f.Records[0] }
    Negative 'unknown_dependency_form' 'dependency_form' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('</Dependencies>','<UnknownDependency /></Dependencies>'); Pack $f.Records[0] }
    Negative 'nested_dependency_form' 'dependency_form' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('MinVersion="2.0.0.0" />','MinVersion="2.0.0.0"><Unknown /></PackageDependency>'); Pack $f.Records[0] }
    Negative 'wrong_case_manifest_architecture' 'dependency_form' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace('<PackageDependency ','<PackageDependency processorarchitecture="x64" '); Pack $f.Records[0] }
    Negative 'missing_transitive' 'dependency_missing' { param($f) $f.Records[2].Xml=$f.Records[2].Xml.Replace('</Dependencies>',((Requirement 'org.synthetic.missing' '1.0.0.0')+'</Dependencies>')); Pack $f.Records[2] }
    Negative 'conflicting_transitive' 'dependency_requirement' { param($f) $f.Records[2].Xml=$f.Records[2].Xml.Replace('</Dependencies>',((Requirement $f.Records[1].Expected.Name '14.0.40000.0')+'</Dependencies>')); Pack $f.Records[2] }
    Negative 'unreachable_framework' 'dependency_extra' { param($f) $f.Records[0].Xml=$f.Records[0].Xml.Replace((Requirement $f.Records[1].Expected.Name '14.0.30035.0'),''); Pack $f.Records[0] }
    foreach ($tag in @('OnLaunch','AutomaticBackgroundTask','ForceUpdateFromAnyVersion','MainBundle','OptionalPackages','RelatedPackages','RepairUris','UpdateUris','Unknown')) {
        XmlNegative ('injected_' + $tag) 'appinstaller_shape' { param($doc) $node=$doc.CreateElement($tag,$doc.DocumentElement.NamespaceURI); $node.InnerText='false'; $null=$doc.DocumentElement.AppendChild($node) }
    }
    XmlNegative 'foreign_namespace' 'appinstaller_shape' { param($doc) $node=$doc.CreateElement('x','ForceUpdateFromAnyVersion','urn:synthetic:foreign'); $node.InnerText='false'; $null=$doc.DocumentElement.AppendChild($node) }
    XmlNegative 'duplicate_main' 'appinstaller_shape' { param($doc) $null=$doc.DocumentElement.AppendChild($doc.DocumentElement.FirstChild.CloneNode($true)) }
    XmlNegative 'unknown_attribute' 'appinstaller_shape' { param($doc) $doc.DocumentElement.SetAttribute('Unknown','false') }
    foreach ($field in @('Version','Uri')) {
        XmlNegative ('wrong_case_root_' + $field) 'appinstaller_shape' { param($doc)
            $node=$doc.DocumentElement; $value=$node.GetAttribute($field); $node.RemoveAttribute($field); $node.SetAttribute($field.ToLowerInvariant(),$value)
        }
    }
    XmlNegative 'root_version_alias_replaces_uri' 'appinstaller_shape' { param($doc) $node=$doc.DocumentElement; $node.RemoveAttribute('Uri'); $node.SetAttribute('version',$node.GetAttribute('Version')) }
    foreach ($field in @('Name','Publisher','Version','ProcessorArchitecture','Uri')) {
        XmlNegative ('wrong_case_main_' + $field) 'appinstaller_shape' { param($doc)
            $node=$doc.SelectSingleNode('/*/*[local-name()="MainPackage"]'); $value=$node.GetAttribute($field); $node.RemoveAttribute($field); $node.SetAttribute($field.ToLowerInvariant(),$value)
        }
    }
    foreach ($field in @('Publisher','Version','ProcessorArchitecture','Uri')) {
        XmlNegative ('wrong_case_dependency_' + $field) 'appinstaller_shape' { param($doc)
            $node=$doc.SelectSingleNode('/*/*[local-name()="Dependencies"]/*'); $value=$node.GetAttribute($field); $node.RemoveAttribute($field); $node.SetAttribute($field.ToLowerInvariant(),$value)
        }
    }
    foreach ($field in @('Uri','Version')) { XmlNegative ('stale_' + $field) 'appinstaller_value' { param($doc) $doc.DocumentElement.SetAttribute($field,'changed') } }
    foreach ($field in @('Name','Publisher','Version','ProcessorArchitecture')) { XmlNegative ('changed_main_' + $field) 'appinstaller_value' { param($doc) $doc.DocumentElement.FirstChild.SetAttribute($field,'changed') } }
    XmlNegative 'changed_main_uri' 'appinstaller_value' { param($doc) $doc.DocumentElement.FirstChild.SetAttribute('Uri','https://other.invalid/main.msix') }
    XmlNegative 'changed_dependency_uri' 'appinstaller_value' { param($doc) $doc.SelectSingleNode('/*/*[local-name()="Dependencies"]/*').SetAttribute('Uri','https://other.invalid/framework.appx') }
    XmlNegative 'missing_dependency' 'appinstaller_dependencies' { param($doc) $node=$doc.SelectSingleNode('/*/*[local-name()="Dependencies"]/*'); $null=$node.ParentNode.RemoveChild($node) }
    XmlNegative 'extra_dependency' 'appinstaller_dependencies' { param($doc) $node=$doc.SelectSingleNode('/*/*[local-name()="Dependencies"]/*'); $null=$node.ParentNode.AppendChild($node.CloneNode($true)) }
    $f=Fixture; $output=PrepareFixture $f; $before=Snapshot $f.Dir; $caught=$false
    try { $null=InvokeTool $f 'Prepare' $output } catch { Assert ($_.Exception.Message -ceq 'T124:output_exists') 'existing_output_reason'; $caught=$true }
    Assert ($caught -and (Snapshot $f.Dir) -ceq $before) 'existing_output_preserved'; $script:cases++
    $f=Fixture; $null=PrepareFixture $f; [IO.File]::WriteAllText($f.XmlPath, ('x'*65537)); $caught=$false
    try { $null=InvokeTool $f 'Validate' '' } catch { Assert ($_.Exception.Message -ceq 'T124:appinstaller_size') 'xml_size_reason'; $caught=$true }
    Assert $caught 'xml_size_accepted'; $script:cases++
    $f=Fixture; $null=PrepareFixture $f; $caught=$false
    try { $null=InvokeTool $f 'Prepare' (Join-Path $f.Dir 'missing-parent/release') } catch { Assert ($_.Exception.Message -ceq 'T124:output_parent') 'output_parent_reason'; $caught=$true }
    Assert ($caught -and -not [IO.Directory]::Exists((Join-Path $f.Dir 'missing-parent'))) 'output_parent_no_effect'; $script:cases++
    Write-Output ('PUBLIC_APPINSTALLER_TESTS cases=' + $script:cases + ' public_release_ready=false')
} finally { if ([IO.Directory]::Exists($root)) { Remove-Item -LiteralPath $root -Recurse -Force } }
