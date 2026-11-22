# Build the same native WebView2 host for the auth and payment fixtures.
param(
  [Parameter(Mandatory=$true)][string]$GeneratedHeaders,
  [Parameter(Mandatory=$true)][string]$RuntimeDllDirectory,
  [Parameter(Mandatory=$true)][string]$FixtureSource,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [Parameter(Mandatory=$true)][string]$ExecutableName
)
$ErrorActionPreference = 'Stop'
$common = @('/nologo','/c','/std:c++17','/permissive-','/EHsc','/MD','/W4','/WX','/utf-8','/bigobj','/await:strict','/DGRAF_WINDOWS_APP_SDK','/D_UNICODE','/DUNICODE','/DWIN32_LEAN_AND_MEAN','/DNOMINMAX','/D_WIN32_WINNT=0x0A00',"/I$GeneratedHeaders")
# Keep the SDK host and its current dependencies identical to the app project.
# Only the app entry point and the unused production AEC adapter are excluded.
$projectDirectory = (Resolve-Path -LiteralPath "$PSScriptRoot\..\..\RecApp").Path
[xml]$project = Get-Content -LiteralPath (Join-Path $projectDirectory 'GrafWindowsApp.vcxproj') -Raw
$namespaces = [Xml.XmlNamespaceManager]::new($project.NameTable)
$namespaces.AddNamespace('msbuild', 'http://schemas.microsoft.com/developer/msbuild/2003')
$excluded = @{'AppMain.cpp' = 0; '..\Native\GrafAEC3\GrafAEC3WebRtcAdapter.cpp' = 0}
$sources = @($project.SelectNodes('/msbuild:Project/msbuild:ItemGroup/msbuild:ClCompile[@Include]', $namespaces) | ForEach-Object {
  $include = $_.GetAttribute('Include')
  if ($_.HasAttribute('Condition') -or $_.ParentNode.HasAttribute('Condition') -or $include -match '[$*?;]') {
    throw 'NON_LITERAL_PROJECT_SOURCE'
  }
  $include = $include.Replace('/', '\')
  if ($excluded.ContainsKey($include)) { $excluded[$include]++ }
  else { (Resolve-Path -LiteralPath (Join-Path $projectDirectory $include)).Path }
})
if ($excluded.Values.Where({$_ -ne 1}).Count) { throw 'PROJECT_SOURCE_EXCLUSIONS_CHANGED' }
$sources += (Resolve-Path -LiteralPath $FixtureSource).Path
$objectNames = @{}
foreach ($source in $sources) {
  $name = [IO.Path]::GetFileNameWithoutExtension($source)
  if ($objectNames.ContainsKey($name)) { throw "DUPLICATE_OBJECT_NAME=$name" }
  $objectNames[$name] = $true
}
$objects = @()
foreach ($source in $sources) {
  $object = Join-Path $OutputDirectory ([IO.Path]::GetFileNameWithoutExtension($source) + '.obj')
  & cl.exe @common "/Fo$object" $source
  if ($LASTEXITCODE -ne 0) { throw "COMPILE_FAILED=$source" }
  $objects += $object
}
& link.exe /nologo /SUBSYSTEM:CONSOLE /MACHINE:X64 "/OUT:$OutputDirectory\$ExecutableName" @objects windowsapp.lib ole32.lib shell32.lib comdlg32.lib comctl32.lib uuid.lib advapi32.lib user32.lib bcrypt.lib winhttp.lib gdi32.lib ws2_32.lib mfplat.lib mfreadwrite.lib mfuuid.lib oleaut32.lib avrt.lib wintrust.lib crypt32.lib uiautomationcore.lib
if ($LASTEXITCODE -ne 0) { throw 'LINK_FAILED' }
foreach ($dll in @('Microsoft.Web.WebView2.Core.dll','WebView2Loader.dll','Microsoft.WindowsAppRuntime.Bootstrap.dll')) {
  Copy-Item -LiteralPath (Join-Path $RuntimeDllDirectory $dll) -Destination $OutputDirectory
}
