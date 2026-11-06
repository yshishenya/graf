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
  [ValidateSet('history-revalidation-no-anchor','history-revalidation-workspace-boundary','history-revalidation-token-boundary','history-revalidation-epoch-boundary','history-revalidation-post','history-revalidation-timeout-unknown','history-revalidation-timeout-reconfirmed','history-revalidation-close','history-revalidation-terminal','history-revalidation-preheaders','history-revalidation-before-start','shared-reader-session','history-get-repeated-url','history-host-ordinary-back','initial200','login400','email503','cabinet401','cabinet503','login429','email429','email-json503','reselect','billing401','meeting401','transport-reset','tls-failure','login-post400','history-get','history-post','history-entry','history-entry-same-url','cancel-before-start','history-host-same-url','cancel-history-host','cancel-history-script','history-same-document','history-host-get','history-host-quarantine','history-pending-read-fence','history-terminal-held','history-fresh-login-redirect','history-reset-stale-readback','history-reset-account-boundary','history-account-boundary-redirect-held')]
  [string[]]$Scenarios = @('initial200','login400','email503','cabinet401','cabinet503','login429','email429','email-json503','reselect','billing401','meeting401','transport-reset','tls-failure','login-post400','history-get','history-post','history-entry','history-entry-same-url','cancel-before-start','history-host-same-url','cancel-history-host','cancel-history-script','history-same-document'),
  [switch]$CompletionFailureDiagnostic
)
$ErrorActionPreference = 'Stop'
if ($CompletionFailureDiagnostic -and ($Scenarios.Count -ne 1 -or $Scenarios[0] -cne 'initial200')) {
  throw 'TEARDOWN_CONTROL_REQUIRES_INITIAL200_ONLY'
}
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$out = Join-Path ([IO.Path]::GetTempPath()) ('graf-t103-native-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out | Out-Null
Write-Output ('T103_TEMP_DIRECTORY=' + $out)
$expected = @{
  'history-revalidation-no-anchor' = '2 0 0 0 0 0'
  'history-revalidation-workspace-boundary' = '2 0 0 0 0 0'
  'history-revalidation-token-boundary' = '2 0 0 0 0 0'
  'history-revalidation-epoch-boundary' = '2 0 0 0 0 0'
  'history-revalidation-post' = '1 0 0 0 0 1'
  'history-revalidation-timeout-unknown' = '2 0 0 0 0 0'
  'history-revalidation-timeout-reconfirmed' = '2 0 0 0 0 0'
  'history-revalidation-close' = '2 0 0 0 0 0'
  'history-revalidation-terminal' = '2 0 0 0 0 0'
  'history-revalidation-preheaders' = '2 0 0 0 0 0'
  'history-revalidation-before-start' = '2 0 0 0 0 0'
  'shared-reader-session' = '3 0 0 0 0 0'
  initial200 = '1 0 0 0 0 0'; login400 = '0 1 0 0 0 0'; email503 = '1 0 1 0 0 0'
  cabinet401 = '1 1 0 1 0 0'; cabinet503 = '1 0 0 0 0 0'
  login429 = '0 1 0 0 0 0'; email429 = '1 0 1 0 0 0'; 'email-json503' = '1 0 1 0 0 0'
  reselect = '1 1 1 1 0 0'; billing401 = '1 1 0 1 0 0'; meeting401 = '1 1 0 1 0 0'
  'tls-failure' = '0 0 0 0 0 0'; 'login-post400' = '0 1 0 0 0 1'
  'history-fresh-login-redirect' = '2 1 0 1 0 0'
  'history-reset-stale-readback' = '4 0 0 0 0 1'
  'history-reset-account-boundary' = '4 0 0 0 0 1'
  'history-account-boundary-redirect-held' = '4 0 0 0 0 1'
}
$failed = $false
$runFailure = $null
$cleanupFailure = $null
$passed = 0
try {
  $common = @('/nologo','/c','/std:c++17','/permissive-','/EHsc','/MD','/W4','/WX','/utf-8','/bigobj','/await:strict','/DGRAF_WINDOWS_APP_SDK','/D_UNICODE','/DUNICODE','/DWIN32_LEAN_AND_MEAN','/DNOMINMAX','/D_WIN32_WINNT=0x0A00',"/I$GeneratedHeaders")
  # Keep the SDK host and its current dependencies identical to the app project.
  # Only the app entry point and the unused production AEC adapter are excluded.
  $projectDirectory = Join-Path $root 'RecApp'
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
  $sources += Join-Path $PSScriptRoot 'WebView2AuthNativeTests.cpp'
  $objectNames = @{}
  foreach ($source in $sources) {
    $name = [IO.Path]::GetFileNameWithoutExtension($source)
    if ($objectNames.ContainsKey($name)) { throw "DUPLICATE_OBJECT_NAME=$name" }
    $objectNames[$name] = $true
  }
  $objects = @()
  foreach ($source in $sources) {
    $object = Join-Path $out ([IO.Path]::GetFileNameWithoutExtension($source) + '.obj')
    & cl.exe @common "/Fo$object" $source
    if ($LASTEXITCODE -ne 0) { throw "COMPILE_FAILED=$source" }
    $objects += $object
  }
  & link.exe /nologo /SUBSYSTEM:CONSOLE /MACHINE:X64 "/OUT:$out\T103Native.exe" @objects windowsapp.lib ole32.lib shell32.lib comdlg32.lib advapi32.lib user32.lib bcrypt.lib winhttp.lib gdi32.lib ws2_32.lib mfplat.lib mfreadwrite.lib mfuuid.lib oleaut32.lib avrt.lib wintrust.lib crypt32.lib
  if ($LASTEXITCODE -ne 0) { throw 'LINK_FAILED' }
  foreach ($dll in @('Microsoft.Web.WebView2.Core.dll','WebView2Loader.dll','Microsoft.WindowsAppRuntime.Bootstrap.dll')) {
    Copy-Item -LiteralPath (Join-Path $RuntimeDllDirectory $dll) -Destination $out
  }
  $binaryHash = (Get-FileHash -LiteralPath "$out\T103Native.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
  Write-Output "T103_BINARY_SHA256=$binaryHash"
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
      $fixtureArguments = @("`"$caseRoot\profile`"","https://graf.test:$port",$scenario,"`"$out\Microsoft.WindowsAppRuntime.Bootstrap.dll`"")
      if ($CompletionFailureDiagnostic) { $fixtureArguments += '--fail-completion' }
      $fixture = Start-Process "$out\T103Native.exe" -ArgumentList $fixtureArguments -PassThru -WindowStyle Hidden -RedirectStandardOutput "$caseRoot\fixture.out" -RedirectStandardError "$caseRoot\fixture.err"
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
      if ((Get-FileHash -LiteralPath "$out\T103Native.exe" -Algorithm SHA256).Hash.ToLowerInvariant() -ne $binaryHash) { throw 'FIXTURE_BYTES_CHANGED' }
      if ($scenario -eq 'transport-reset') {
        Write-Output 'T103_COUNTS_BOUND=LOGIN_GET_1_TO_3_OTHER_FIVE_ZERO'
        $countsMatch = $row -cmatch '\A0 [1-3] 0 0 0 0\z'
      } elseif ($scenario -in @('history-get','history-get-repeated-url')) {
        # Browser caching may restore a safe GET without another network read.
        # Actual document order/authority is checked independently by the fixture.
        $countsMatch = $row -cmatch '\A[3-7] 0 0 0 0 0\z'
      } elseif ($scenario -in @('history-entry','history-entry-same-url')) {
        # GET-A/C + next fresh GET-A; at most one provisional GET before product denial.
        $countsMatch = $row -cmatch '\A[3-4] 0 0 0 0 1\z'
      } elseif ($scenario -eq 'cancel-history-host') {
        # All-GET A/B/C + next GET-A; at most one provisional GET-B before fixture Cancel.
        $countsMatch = $row -cmatch '\A[4-5] 0 0 0 0 0\z'
      } elseif ($scenario -in @('cancel-history-script','history-same-document')) {
        # Real A/POST-B/C, cancelled traversal or source-only changes, then a new GET-A.
        $countsMatch = $row -cmatch '\A[3-4] 0 0 0 0 1\z'
      } elseif ($scenario -in @('history-host-get','history-host-ordinary-back')) {
        # Three actual GETs, host Back/Forward; exact IDs/method/authority checked natively.
        $countsMatch = $row -cmatch '\A[3-5] 0 0 0 0 0\z'
      } elseif ($scenario -eq 'history-pending-read-fence') {
        # A/B/C + two useful BF reads; at most BF/GET provisional competitor reads. POST never reaches the server.
        $countsMatch = $row -cmatch '\A[3-7] 0 0 0 0 0\z'
      } elseif ($scenario -eq 'history-terminal-held') {
        # A/B/C + selected Back/Forward, with one real accepting result held before authority.
        $countsMatch = $row -cmatch '\A[3-5] 0 0 0 0 0\z'
      } elseif ($scenario -in @('history-host-quarantine','history-post','history-host-same-url')) {
        # A, POST-B, C, host fresh list/reset, fresh forward C, then useful host BF.
        $countsMatch = $row -cmatch '\A[4-6] 0 0 0 0 1\z'
      } elseif ($scenario -eq 'cancel-before-start') {
        # A provisional GET may reach the server before cancellation. It must
        # never replace the accepted page or revoke its native authority.
        $countsMatch = $row -cmatch '\A[2-3] 0 0 0 0 0\z'
      } else { $countsMatch = $row -ceq $expected[$scenario] }
      $pass = $fixtureExitCode -eq 0 -and $countsMatch -and (Get-Item -LiteralPath "$caseRoot\server.err").Length -eq 0 -and $watch.ElapsedMilliseconds -le 35000
      if ($scenario -in @('history-revalidation-no-anchor','history-revalidation-workspace-boundary','history-revalidation-token-boundary','history-revalidation-epoch-boundary','history-revalidation-post','history-revalidation-timeout-unknown','history-revalidation-timeout-reconfirmed','history-revalidation-close')) {
        $lines = @(Get-Content -LiteralPath "$caseRoot\fixture.out")
        $confirmed = [int]($scenario -ne 'history-revalidation-no-anchor')
        foreach ($marker in @("T097_NEGATIVE_INITIAL REAL_COOKIE=1 HTML_IDENTITY=1 CONFIRMED_A=$confirmed",
            "T097_NEGATIVE_SETUP kind=$scenario NATIVE_CORRELATION=1 AUTHORITY=0",
            'T097_NEGATIVE_BROWSER_TERMINAL MATCHING_NAVIGATION=1 OBSERVED=1',
            "T097_REVALIDATION_NEGATIVE_PASS kind=$scenario BAD_CASE_PROVED=1 NO_ADMISSION=1")) {
          $pass = $pass -and @($lines | Where-Object { $_ -ceq $marker }).Count -eq 1
        }
        $pass = $pass -and (Get-Item -LiteralPath "$caseRoot\fixture.err").Length -eq 0
        if ($scenario -notin @('history-revalidation-post','history-revalidation-timeout-unknown')) {
          $fresh = [int]($scenario -eq 'history-revalidation-timeout-reconfirmed')
          $marker = "T097_NEGATIVE_CALLBACKS ORIGINAL_DELIVERIES=1 FRESH_DELIVERIES=$fresh INERT=1"
          $pass = $pass -and @($lines | Where-Object { $_ -ceq $marker }).Count -eq 1
        }
        if ($scenario -eq 'history-revalidation-token-boundary') {
          $pass = $pass -and @($lines | Where-Object { $_ -ceq 'T097_NEGATIVE_COOKIE OWN_MANAGER_READ=1 DIFFERENT_TOKEN=1' }).Count -eq 1
        }
        if ($scenario -eq 'history-revalidation-post') {
          $pass = $pass -and @($lines | Where-Object { $_ -ceq 'T097_NEGATIVE_RESPONSE slot=1 METHOD=POST CORRELATED_HTML200=1' }).Count -eq 1
        }
        if ($scenario -in @('history-revalidation-timeout-unknown','history-revalidation-timeout-reconfirmed')) {
          $fresh = [int]($scenario -eq 'history-revalidation-timeout-reconfirmed')
          $pass = $pass -and @($lines | Where-Object { $_ -ceq 'T097_NEGATIVE_REPEAT_UNKNOWN SAME_ORIGINAL_DEADLINE=1' }).Count -eq 1 -and
            @($lines | Where-Object { $_ -cmatch ('^T097_NEGATIVE_DEADLINE ORIGINAL_5000MS=1 OBSERVED_TICK_LAG_MS=(100|[1-9]?[0-9]) FRESH_READ=' + $fresh + '$') }).Count -eq 1
          if ($fresh) {
            $pass = $pass -and @($lines | Where-Object { $_ -ceq 'T097_NEGATIVE_RECONFIRMED A=1 ORIGINAL_DEADLINE_REQUIRED=1' }).Count -eq 1 -and
              @($lines | Where-Object { $_ -ceq 'T097_NEGATIVE_FRESH_READ REAL_RESULT=1 ORIGINAL_CONTINUATION=1 HELD=1' }).Count -eq 1
          }
        }
      }
      if ($scenario -in @('history-revalidation-terminal','history-revalidation-preheaders','history-revalidation-before-start')) {
        $lines = @(Get-Content -LiteralPath "$caseRoot\fixture.out")
        $terminal = [int]($scenario -eq 'history-revalidation-terminal')
        $beforeStart = [int]($scenario -eq 'history-revalidation-before-start')
        foreach ($marker in @(
            'T097_REVALIDATION_INITIAL REAL_COOKIE=1 REAL_HTML_IDENTITY=1 REAL_READY=1',
            "T097_REVALIDATION_SETUP terminal=$terminal before_start=$beforeStart REAL_NATIVE_START=1 RESPONSE_GET=$terminal",
            'T097_REVALIDATION_UNKNOWN EFFECTIVE_NETWORK=0 NEW_NONCE=0 NEW_ACTIVATION=0',
            'T097_REVALIDATION_RESPONSE slot=0 EXACT_ROUTE=1 GET=1 HTML200=1 GENERATION_TAG=1',
            'T097_REVALIDATION_RESPONSE slot=1 EXACT_ROUTE=1 GET=1 HTML200=1 GENERATION_TAG=1',
            'T097_REVALIDATION_PASS GETS=2 NEW_ADMISSION=1 EFFECTS=0')) {
          $pass = $pass -and @($lines | Where-Object { $_ -ceq $marker }).Count -eq 1
        }
        $pass = $pass -and (Get-Item -LiteralPath "$caseRoot\fixture.err").Length -eq 0
        if ($terminal) {
          $pass = $pass -and @($lines | Where-Object { $_ -ceq 'T097_REVALIDATION_OLD_CALLBACK DELIVERED_ONCE=1 INERT=1 NEW_SNAPSHOT=1' }).Count -eq 1
        }
        if ($beforeStart) {
          foreach ($marker in @('T097_REVALIDATION_PRIOR_READY CONFIRMED_NETWORK_A=1 UNKNOWN=1',
              'T097_REVALIDATION_START ORDINARY=1 UNKNOWN=1')) {
            $pass = $pass -and @($lines | Where-Object { $_ -ceq $marker }).Count -eq 1
          }
        }
      }
      if ($scenario -eq 'shared-reader-session') {
        $sharedLines = @(Get-Content -LiteralPath "$caseRoot\fixture.out")
        foreach ($phase in 0..2) {
          $pattern = '^T121_SHARED_NATIVE phase=' + $phase + ' PASS=1 COOKIE_NATIVE=1 PUBLIC_BRIDGE=' + $(if ($phase -eq 1) { '0' } else { '1' }) + ' EFFECTS=0$'
          $pass = $pass -and @($sharedLines | Where-Object { $_ -cmatch $pattern }).Count -eq 1
        }
      }
      if ($CompletionFailureDiagnostic) {
        $lines = @(Get-Content -LiteralPath "$caseRoot\fixture.out")
        $control = @($lines | Where-Object { $_ -cmatch '^T103_NATIVE ' })
        $pass = $fixtureExitCode -eq 1 -and $countsMatch -and $control.Count -eq 1 -and
          $control[0] -cmatch '^T103_NATIVE case=initial200 result=FAIL reason=controlled-teardown-failure profile_verified=1 starts=1 completions=1 status=200 state=-?\d+$' -and
          (Get-Item -LiteralPath "$caseRoot\server.err").Length -eq 0 -and
          (Get-Item -LiteralPath "$caseRoot\fixture.err").Length -eq 0 -and $watch.ElapsedMilliseconds -le 35000
        foreach ($marker in @('T103_TEARDOWN stage=completion-enter errors=0','T103_TEARDOWN stage=completion-return errors=0',
          'T103_TEARDOWN stage=host-close-enter errors=0','T103_TEARDOWN stage=host-close-return errors=0',
          'T103_TEARDOWN stage=view-close-return errors=0','T103_TEARDOWN stage=terminal errors=0',
          'T103_BROWSER_EXITED=PASS','T103_TEARDOWN_APPLICATION_RETURN=1')) {
          $pass = $pass -and @($lines | Where-Object { $_ -ceq $marker }).Count -eq 1
        }
        Write-Output "T103_FIXTURE_TEARDOWN_CONTROL=$pass FINAL_COUNTS=$row"
      } else { Write-Output "T103_CASE=$scenario PASS=$pass FINAL_COUNTS=$row" }
      if ($pass) { $passed++ } else { $failed = $true }
    } catch { $caseFailure = $_ }
    finally {
      if ($scenario -eq 'history-account-boundary-redirect-held') {
        try {
          [IO.File]::WriteAllText("$caseRoot\response-release", 'release')
          [IO.File]::WriteAllText("$caseRoot\stop.request", 'stop')
          if ($server -and !$server.HasExited) {
            $remaining = [int][Math]::Max(0, [Math]::Min(3000, 35000 - $watch.ElapsedMilliseconds))
            if (!$server.WaitForExit($remaining)) { $processCleanupFailed = $true; Write-Output 'T103_HELD_RESPONSE_DRAIN=FAIL' }
          }
        } catch { $processCleanupFailed = $true; Write-Output 'T103_HELD_RESPONSE_RELEASE=FAIL' }
      }
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
$resultPrefix = if ($CompletionFailureDiagnostic) { 'T103_FIXTURE_TEARDOWN' } else { 'T103_CASES' }
Write-Output "${resultPrefix}_PASSED=$passed REQUESTED=$($Scenarios.Count)"
if ($runFailure) { throw $runFailure }
if ($failed) { exit 1 }
if (!$cleaned) { throw $cleanupFailure }
Write-Output "${resultPrefix}=PASS"
exit 0
