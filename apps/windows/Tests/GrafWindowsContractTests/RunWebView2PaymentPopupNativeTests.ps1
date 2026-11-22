# Standalone native fixture; does not build/install/launch the GRAF application.
# Run in an x64 VS developer PowerShell, with the existing generated WinRT headers
# and runtime DLL directory from a native build. Certificates must be synthetic.
param(
  [Parameter(Mandatory=$true)][string]$GeneratedHeaders,
  [Parameter(Mandatory=$true)][string]$RuntimeDllDirectory,
  [Parameter(Mandatory=$true)][string]$Python,
  [Parameter(Mandatory=$true)][string]$SyntheticCertificate,
  [Parameter(Mandatory=$true)][string]$SyntheticPrivateKey,
  [string[]]$Scenarios = @('form-targetblank','immediate','later','nested','iframe','same-url-iframe','cancel-after-assignment','first-navigation-failure','redirect-307','redirect-303','frame-chain','abort-only','same-tab-307')
)
$ErrorActionPreference = 'Stop'
$out = Join-Path ([IO.Path]::GetTempPath()) ('graf-t102-native-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $out | Out-Null
Write-Output ('T102_TEMP_DIRECTORY_NAME=' + [IO.Path]::GetFileName($out))
$failed = $false
$runFailure = $null
$cleanupFailure = $null
try {
  & (Join-Path $PSScriptRoot 'Build-WebView2NativeFixture.ps1') -GeneratedHeaders $GeneratedHeaders `
    -RuntimeDllDirectory $RuntimeDllDirectory -FixtureSource (Join-Path $PSScriptRoot 'WebView2PaymentPopupNativeTests.cpp') `
    -OutputDirectory $out -ExecutableName 'T102Native.exe'
  $binaryHash = (Get-FileHash -LiteralPath "$out\T102Native.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
  Write-Output "T102_BINARY_SHA256=$binaryHash"
  Write-Output 'T102_NATIVE_FIXTURE_BUILD=PASS'
  foreach ($scenario in $Scenarios) {
    if ($scenario -notin @('form-targetblank','immediate','later','nested','iframe','same-url-iframe','cancel-after-assignment','first-navigation-failure','redirect-307','redirect-303','frame-chain','abort-only','same-tab-307')) { throw 'UNKNOWN_SCENARIO' }
    $caseRoot = Join-Path $out ('case-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory $caseRoot | Out-Null
    Copy-Item $SyntheticCertificate "$caseRoot\cert.pem"
    Copy-Item $SyntheticPrivateKey "$caseRoot\key.pem"
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    $server = $null
    $fixture = $null
    $caseFailure = $null
    try {
      $server = Start-Process $Python -ArgumentList @("`"$PSScriptRoot\WebView2PaymentPopupLoopback.py`"","`"$caseRoot`"",$scenario,$port) -PassThru -WindowStyle Hidden -RedirectStandardOutput "$caseRoot\server.out" -RedirectStandardError "$caseRoot\server.err"
      [void]$server.Handle
      for ($i=0; $i -lt 30 -and !(Test-Path "$caseRoot\receipt.txt"); $i++) { Start-Sleep -Milliseconds 100 }
      if (!(Test-Path "$caseRoot\receipt.txt")) { throw 'SYNTHETIC_SERVER_NOT_READY' }
      $fixture = Start-Process "$out\T102Native.exe" -ArgumentList @("`"$caseRoot\profile`"","`"$caseRoot\receipt.txt`"","https://graf.test:$port",$scenario,"`"$out\Microsoft.WindowsAppRuntime.Bootstrap.dll`"") -PassThru -WindowStyle Hidden -RedirectStandardOutput "$caseRoot\fixture.out" -RedirectStandardError "$caseRoot\fixture.err"
      [void]$fixture.Handle
      $timeout = if ($scenario -eq 'same-tab-307') { 35000 } else { 25000 }
      if (!$fixture.WaitForExit($timeout)) { Stop-Process -Id $fixture.Id -Force; throw 'FIXTURE_TIMEOUT' }
      $fixture.Refresh()
      Get-Content "$caseRoot\fixture.out"
      Write-Output "FIXTURE_EXIT=$($fixture.ExitCode)"
      [IO.File]::WriteAllText("$caseRoot\stop.request", 'stop')
      if (!$server.WaitForExit(5000)) { throw 'SYNTHETIC_SERVER_DRAIN_TIMEOUT' }
      $server.Refresh()
      $serverExitCode = $server.ExitCode
      Write-Output "SYNTHETIC_SERVER_EXIT=$serverExitCode"
      if ($null -eq $serverExitCode) { throw 'SYNTHETIC_SERVER_EXIT_UNAVAILABLE' }
      if ($serverExitCode -ne 0) { throw 'SYNTHETIC_SERVER_DRAIN_FAILED' }
      $finalReceipt = Get-Content -LiteralPath "$caseRoot\receipt.txt" -Raw
      Write-Output ('SYNTHETIC_COUNTS=' + $finalReceipt)
      if ($fixture.ExitCode -eq 0) {
        if ($scenario -eq 'same-tab-307' -and
            @(Select-String -LiteralPath "$caseRoot\fixture.out" -Pattern '^T102_BROWSER_EXITED=PASS$').Count -ne 1) {
          Write-Output 'T102_BROWSER_EXIT_PROOF=FAIL'
          $failed = $true
        }
        $accepted = @(Select-String -LiteralPath "$caseRoot\fixture.out" -Pattern '^ACCEPTED_RECEIPT=(.*)$')
        if ($accepted.Count -ne 1 -or $accepted[0].Matches[0].Groups[1].Value -cne $finalReceipt) {
          Write-Output 'T102_FINAL_RECEIPT_CHANGED=FAIL'
          $failed = $true
        } else { Write-Output 'T102_FINAL_RECEIPT=PASS' }
      }
      if ($fixture.ExitCode -ne 0) { $failed = $true }
    } catch { $caseFailure = $_ }
    finally {
      $processCleanupFailed = $false
      foreach ($ownedProcess in @($fixture, $server)) {
        if (!$ownedProcess) { continue }
        try {
          if (!$ownedProcess.HasExited) { Stop-Process -Id $ownedProcess.Id -Force }
          if (!$ownedProcess.WaitForExit(5000)) { $processCleanupFailed = $true }
        } catch { $processCleanupFailed = $true }
        finally {
          try { $ownedProcess.Dispose() }
          catch { $processCleanupFailed = $true }
        }
      }
      try {
        if ((Test-Path -LiteralPath "$caseRoot\server.err") -and
            (Select-String -LiteralPath "$caseRoot\server.err" -SimpleMatch 'T102_RECEIPT_FAILURE' -Quiet)) {
          Write-Output 'T102_RECEIPT_FAILURE=FAIL'
          $failed = $true
        }
      } catch {
        Write-Output 'T102_SERVER_ERROR_CHECK=FAIL'
        $processCleanupFailed = $true
      }
      if ($processCleanupFailed) { Write-Output 'T102_OWNED_PROCESS_CLEANUP=FAIL' }
    }
    if ($caseFailure) { throw $caseFailure }
    if ($processCleanupFailed) { throw 'T102_OWNED_PROCESS_CLEANUP_FAILED' }
  }
} catch { $runFailure = $_ }
finally {
  # Exact fresh directory created above; never an application/user profile.
  $cleaned = $false
  $cleanupErrorType = ''
  $cleanupErrorCode = ''
  for ($attempt=0; $attempt -lt 20; $attempt++) {
    try { Remove-Item -LiteralPath $out -Recurse -Force; $cleaned = $true; break }
    catch {
      $cleanupFailure = $_
      $cleanupErrorType = $_.Exception.GetType().FullName
      $cleanupErrorCode = $_.Exception.HResult.ToString('X8')
      if ($attempt -eq 0) { Write-Output "T102_TEMP_CLEANUP_FIRST_ERROR=$cleanupErrorType/$cleanupErrorCode" }
      Start-Sleep -Milliseconds 250
    }
  }
  if (!$cleaned) {
    Write-Output "T102_TEMP_CLEANUP_ERROR_TYPE=$cleanupErrorType"
    Write-Output "T102_TEMP_CLEANUP_ERROR_HRESULT=$cleanupErrorCode"
    Write-Output 'T102_TEMP_CLEANUP=FAILED'
  } else { Write-Output 'T102_TEMP_CLEANUP=PASS' }
}
if ($runFailure) { throw $runFailure }
if (!$cleaned) { throw $cleanupFailure }
if ($failed) { exit 1 }
