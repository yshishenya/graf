# Standalone actual WebView2Host.attach fixture; no GRAF installation or real account.
# Run in an x64 VS developer PowerShell with generated WinRT headers and runtime DLLs.
# Certificate/key inputs must be synthetic. Failed runs retain their own diagnostic directory.
param(
  [Parameter(Mandatory=$true)][string]$GeneratedHeaders,
  [Parameter(Mandatory=$true)][string]$RuntimeDllDirectory,
  [Parameter(Mandatory=$true)][string]$Python,
  [Parameter(Mandatory=$true)][string]$SyntheticCertificate,
  [Parameter(Mandatory=$true)][string]$SyntheticPrivateKey,
  [ValidateNotNullOrEmpty()]
  [ValidateSet('initial200','login400','email503','cabinet401','cabinet503','login429','email429','email-json503','reselect','billing401','meeting401','transport-reset','tls-failure','login-post400')]
  [string[]]$Scenarios = @('initial200','login400','email503','cabinet401','cabinet503','login429','email429','email-json503','reselect','billing401','meeting401','transport-reset','tls-failure','login-post400')
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$out = Join-Path ([IO.Path]::GetTempPath()) ('graf-t103-native-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out | Out-Null
Write-Output ('T103_TEMP_DIRECTORY=' + $out)
$expected = @{
  initial200 = '1 0 0 0 0 0'; login400 = '0 1 0 0 0 0'; email503 = '1 0 1 0 0 0'
  cabinet401 = '1 1 0 1 0 0'; cabinet503 = '1 0 0 0 0 0'
  login429 = '0 1 0 0 0 0'; email429 = '1 0 1 0 0 0'; 'email-json503' = '1 0 1 0 0 0'
  reselect = '1 1 1 1 0 0'; billing401 = '1 1 0 1 0 0'; meeting401 = '1 1 0 1 0 0'
  'tls-failure' = '0 0 0 0 0 0'; 'login-post400' = '0 1 0 0 0 1'
}
$failed = $false
$runFailure = $null
$cleanupFailure = $null
$passed = 0
try {
  $common = @('/nologo','/c','/std:c++17','/permissive-','/EHsc','/MD','/W4','/WX','/utf-8','/bigobj','/await:strict','/DGRAF_WINDOWS_APP_SDK','/D_UNICODE','/DUNICODE','/DWIN32_LEAN_AND_MEAN','/DNOMINMAX','/D_WIN32_WINNT=0x0A00',"/I$GeneratedHeaders")
  $sources = @('RecApp\Web\WebView2Host.cpp','RecApp\Web\WebViewRoutePolicy.cpp','RecApp\Web\WebViewBridge.cpp','RecApp\Web\RecordingDeletionBridge.cpp','RecApp\Web\NativeSettingsBridge.cpp','RecApp\Upload\DesktopApiClient.cpp','RecApp\Storage\Sha256.cpp','Tests\GrafWindowsContractTests\WebView2AuthNativeTests.cpp')
  $objects = @()
  foreach ($source in $sources) {
    $object = Join-Path $out ([IO.Path]::GetFileNameWithoutExtension($source) + '.obj')
    & cl.exe @common "/Fo$object" (Join-Path $root $source)
    if ($LASTEXITCODE -ne 0) { throw "COMPILE_FAILED=$source" }
    $objects += $object
  }
  & link.exe /nologo /SUBSYSTEM:CONSOLE /MACHINE:X64 "/OUT:$out\T103Native.exe" @objects windowsapp.lib ole32.lib shell32.lib comdlg32.lib advapi32.lib user32.lib
  if ($LASTEXITCODE -ne 0) { throw 'LINK_FAILED' }
  foreach ($dll in @('Microsoft.Web.WebView2.Core.dll','WebView2Loader.dll','Microsoft.WindowsAppRuntime.Bootstrap.dll')) {
    Copy-Item -LiteralPath (Join-Path $RuntimeDllDirectory $dll) -Destination $out
  }
  Write-Output 'T103_NATIVE_FIXTURE_BUILD=PASS'
  foreach ($scenario in $Scenarios) {
    $caseRoot = Join-Path $out ('case-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path "$caseRoot\profile" | Out-Null
    Write-Output "T103_SCENARIO=$scenario CASE_DIRECTORY=$([IO.Path]::GetFileName($caseRoot))"
    Copy-Item -LiteralPath $SyntheticCertificate -Destination "$caseRoot\cert.pem"
    Copy-Item -LiteralPath $SyntheticPrivateKey -Destination "$caseRoot\key.pem"
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    try { $listener.Start(); $port = $listener.LocalEndpoint.Port }
    finally { $listener.Stop() }
    $server = $null; $fixture = $null; $caseFailure = $null
    $processCleanupFailed = $false
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
      $server = Start-Process $Python -ArgumentList @("`"$PSScriptRoot\WebView2AuthLoopback.py`"","`"$caseRoot`"",$scenario,$port) -PassThru -WindowStyle Hidden -RedirectStandardOutput "$caseRoot\server.out" -RedirectStandardError "$caseRoot\server.err"
      [void]$server.Handle
      for ($i=0; $i -lt 15 -and !(Test-Path -LiteralPath "$caseRoot\ready"); $i++) { Start-Sleep -Milliseconds 100 }
      if (!(Test-Path -LiteralPath "$caseRoot\ready")) { throw 'SYNTHETIC_SERVER_NOT_READY' }
      $fixture = Start-Process "$out\T103Native.exe" -ArgumentList @("`"$caseRoot\profile`"","https://graf.test:$port",$scenario,"`"$out\Microsoft.WindowsAppRuntime.Bootstrap.dll`"") -PassThru -WindowStyle Hidden -RedirectStandardOutput "$caseRoot\fixture.out" -RedirectStandardError "$caseRoot\fixture.err"
      [void]$fixture.Handle
      $remaining = [int][Math]::Max(0, [Math]::Min(32000, 35000 - $watch.ElapsedMilliseconds))
      if (!$fixture.WaitForExit($remaining)) { throw 'FIXTURE_DEADLINE' }
      $fixture.Refresh()
      $fixtureExitCode = $fixture.ExitCode
      Get-Content -LiteralPath "$caseRoot\fixture.out"
      Write-Output "FIXTURE_EXIT=$fixtureExitCode"
      [IO.File]::WriteAllText("$caseRoot\stop.request", 'stop')
      $remaining = [int][Math]::Max(0, [Math]::Min(3000, 35000 - $watch.ElapsedMilliseconds))
      if (!$server.WaitForExit($remaining)) { throw 'SERVER_DRAIN_DEADLINE' }
      $server.Refresh()
      $serverExitCode = $server.ExitCode
      Write-Output "SYNTHETIC_SERVER_EXIT=$serverExitCode"
      if ($null -eq $serverExitCode) { throw 'SYNTHETIC_SERVER_EXIT_UNAVAILABLE' }
      if ($serverExitCode -ne 0) { throw 'SERVER_DRAIN_FAILED' }
      # The server has joined all writers and exited; never read a live receipt.
      $row = Get-Content -LiteralPath "$caseRoot\final-counts.txt" -Raw
      Write-Output "SYNTHETIC_COUNTS=$row"
      if ($null -eq $fixtureExitCode) { throw 'FIXTURE_EXIT_UNAVAILABLE' }
      if ($scenario -eq 'transport-reset') {
        Write-Output 'T103_COUNTS_BOUND=LOGIN_GET_1_TO_3_OTHER_FIVE_ZERO'
        $countsMatch = $row -cmatch '\A0 [1-3] 0 0 0 0\z'
      } else { $countsMatch = $row -ceq $expected[$scenario] }
      $pass = $fixtureExitCode -eq 0 -and $countsMatch -and (Get-Item -LiteralPath "$caseRoot\server.err").Length -eq 0 -and $watch.ElapsedMilliseconds -le 35000
      Write-Output "T103_CASE=$scenario PASS=$pass FINAL_COUNTS=$row"
      if ($pass) { $passed++ } else { $failed = $true }
    } catch { $caseFailure = $_ }
    finally {
      # Only the two processes started for this case; never enumerate/kill browsers.
      foreach ($ownedProcess in @($fixture, $server)) {
        if (!$ownedProcess) { continue }
        try {
          if (!$ownedProcess.HasExited) { Stop-Process -InputObject $ownedProcess -Force }
          if (!$ownedProcess.WaitForExit(1000)) { $processCleanupFailed = $true }
        } catch {
          $processCleanupFailed = $true
          Write-Output "T103_PROCESS_CLEANUP_ERROR=$($_.Exception.GetType().FullName)/$($_.Exception.HResult.ToString('X8'))"
        } finally {
          try { $ownedProcess.Dispose() }
          catch { $processCleanupFailed = $true; Write-Output 'T103_PROCESS_DISPOSE=FAIL' }
        }
      }
      $watch.Stop()
      Write-Output "T103_CASE_ELAPSED_MS=$($watch.ElapsedMilliseconds)"
      if ($processCleanupFailed) { Write-Output 'T103_OWNED_PROCESS_CLEANUP=FAIL' }
    }
    if ($caseFailure) { throw $caseFailure }
    if ($processCleanupFailed) { throw 'T103_OWNED_PROCESS_CLEANUP_FAILED' }
  }
} catch { $runFailure = $_ }
finally {
  if ($runFailure -or $failed) {
    Write-Output "T103_DIAGNOSTICS_PRESERVED=$out"
  } else {
    # Delete only this run's fresh GUID directory, and only after all cases passed.
    $cleaned = $false
    for ($attempt=0; $attempt -lt 20; $attempt++) {
      try {
        Remove-Item -LiteralPath $out -Recurse -Force -ErrorAction Stop
        $cleaned = !(Test-Path -LiteralPath $out)
        if ($cleaned) { break }
        throw 'T103_TEMP_DIRECTORY_REMAINS'
      } catch {
        $cleanupFailure = $_
        if ($attempt -eq 0) { Write-Output "T103_TEMP_CLEANUP_FIRST_ERROR=$($_.Exception.GetType().FullName)/$($_.Exception.HResult.ToString('X8'))" }
        Start-Sleep -Milliseconds 250
      }
    }
    if ($cleaned) { Write-Output 'T103_TEMP_CLEANUP=PASS' }
    else {
      Write-Output "T103_TEMP_CLEANUP_ERROR=$($cleanupFailure.Exception.GetType().FullName)/$($cleanupFailure.Exception.HResult.ToString('X8'))"
      Write-Output "T103_DIAGNOSTICS_PRESERVED=$out"
      Write-Output 'T103_TEMP_CLEANUP=FAIL'
    }
  }
}
Write-Output "T103_CASES_PASSED=$passed REQUESTED=$($Scenarios.Count)"
if ($runFailure) { throw $runFailure }
if ($failed) { exit 1 }
if (!$cleaned) { throw $cleanupFailure }
Write-Output 'T103_CASES=PASS'
exit 0
