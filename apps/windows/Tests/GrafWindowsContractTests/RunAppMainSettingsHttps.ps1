# Only generated synthetic resources, an isolated AppMain derivative and a disposable localhost leaf.
param(
 [Parameter(Mandatory=$true)][string]$Stage,
 [Parameter(Mandatory=$true)][string]$Executable,
 [Parameter(Mandatory=$true)][string]$ExpectedExeSha256,
 [Parameter(Mandatory=$true)][string]$ExpectedCertificateSha256,
 [Parameter(Mandatory=$true)][string]$Python,
 [Parameter(Mandatory=$true)][string]$ServerScript,
 [Parameter(Mandatory=$true)][string]$ExpectedServerSha256,
 [switch]$Trust
)
$ErrorActionPreference='Stop'
$name=if($Trust){'trusted'}else{'untrusted'}
$receipt=[ordered]@{terminal=$false;mode=$name;full_chain_pass=$false;installed=$false;audio_started=$false}
$server=$null;$app=$null;$owned=$false;$thumb=$null;$before=$null
try {
 if((Get-FileHash -LiteralPath $Executable).Hash -ine $ExpectedExeSha256){throw 'EXE_MISMATCH'}
 if((Get-FileHash -LiteralPath (Join-Path $Stage 'cert.cer')).Hash -ine $ExpectedCertificateSha256){throw 'CERTIFICATE_MISMATCH'}
 if((Get-FileHash -LiteralPath $ServerScript).Hash -ine $ExpectedServerSha256){throw 'SERVER_SOURCE_MISMATCH'}
 if(@(Get-Process GrafWindowsApp -ErrorAction SilentlyContinue).Count){throw 'APP_ALREADY_RUNNING'}
 $cert=[Security.Cryptography.X509Certificates.X509Certificate2]::new((Join-Path $Stage 'cert.cer'))
 $pem=[IO.File]::ReadAllText((Join-Path $Stage 'cert.pem')).Replace('-----BEGIN CERTIFICATE-----','').Replace('-----END CERTIFICATE-----','')
 if([Convert]::ToBase64String([Convert]::FromBase64String($pem)) -cne [Convert]::ToBase64String($cert.RawData)){throw 'SERVER_CERTIFICATE_MISMATCH'}
 $thumb=$cert.Thumbprint
 $constraints=@($cert.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.19'})
 $san=@($cert.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.17'})
 $eku=@($cert.Extensions | Where-Object {$_.Oid.Value -eq '2.5.29.37'})
 if($cert.Subject -cne 'CN=localhost' -or $cert.Issuer -cne $cert.Subject -or $cert.HasPrivateKey -or
    $cert.NotAfter -le [DateTime]::Now -or $cert.NotAfter -gt [DateTime]::Now.AddDays(2) -or
    $constraints.Count -ne 1 -or $constraints[0].CertificateAuthority -or !$constraints[0].Critical -or
    $san.Count -ne 1 -or [BitConverter]::ToString($san[0].RawData) -cne '30-0B-82-09-6C-6F-63-61-6C-68-6F-73-74' -or
    $eku.Count -ne 1 -or $eku[0].EnhancedKeyUsages.Count -ne 1 -or $eku[0].EnhancedKeyUsages[0].Value -ne '1.3.6.1.5.5.7.3.1'){throw 'NOT_DISPOSABLE_LOCALHOST_LEAF'}
 $before=@(Get-ChildItem Cert:\CurrentUser\Root | ForEach-Object {$_.Thumbprint} | Sort-Object)
 if($before -contains $thumb){throw 'TEST_CERTIFICATE_ALREADY_TRUSTED'}
 $receipt.certificate_thumbprint=$thumb
 if($Trust){
  # Set ownership before import so finally also handles a partial import failure.
  $owned=$true
  Import-Certificate -FilePath (Join-Path $Stage 'cert.cer') -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
  if(!(Test-Path ('Cert:\CurrentUser\Root\'+$thumb))){throw 'TRUST_IMPORT_FAILED'}
 }
 foreach($file in @('ready','stop.request','close.request','server-counts.json')){
  $path=Join-Path $Stage $file
  if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}
 }
 $server=Start-Process $Python -ArgumentList @(('"'+$serverScript+'"'),('"'+$Stage+'"')) -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Stage ($name+'-server.out')) -RedirectStandardError (Join-Path $Stage ($name+'-server.err'))
 [void]$server.Handle
 for($i=0;$i -lt 100 -and !(Test-Path (Join-Path $Stage 'ready'));$i++){if($server.HasExited){throw 'SERVER_EARLY_EXIT'};Start-Sleep -Milliseconds 50}
 if(!(Test-Path (Join-Path $Stage 'ready'))){throw 'SERVER_NOT_READY'}
 $app=Start-Process $Executable -ArgumentList ('"'+$Stage+'"') -PassThru -RedirectStandardOutput (Join-Path $Stage ($name+'-ui.out')) -RedirectStandardError (Join-Path $Stage ($name+'-ui.err'))
 [void]$app.Handle
 if(!$app.WaitForExit(620000)){throw 'APP_DEADLINE'}
 $app.Refresh();$receipt.app_exit=$app.ExitCode
 $log=Get-Content -LiteralPath (Join-Path $Stage ($name+'-ui.err')) -Raw
 $receipt.cleanup_reported=$log -match 'terminal=1 .*browser_stopped=1 registry_cleaned=1 profile_cleaned=1'
 if(!$receipt.cleanup_reported){throw 'NATIVE_CLEANUP_NOT_CONFIRMED'}
 $receipt.native_scenario_pass=$Trust -and $app.ExitCode -eq 73
 $receipt.untrusted_refused=!$Trust -and $app.ExitCode -eq 3 -and $log -match 'SETTINGS_UI tls_rejected=1' -and
  $log -notmatch 'SETTINGS_UI response=1 get=1 status=200' -and $log -notmatch 'SETTINGS_UI native_read present=1'
 if(!$Trust -and !$receipt.untrusted_refused){throw 'UNTRUSTED_TLS_ACCEPTANCE_UNPROVEN'}
 if((Get-FileHash -LiteralPath $Executable).Hash -ine $ExpectedExeSha256){throw 'EXE_CHANGED'}
 if((Get-FileHash -LiteralPath $ServerScript).Hash -ine $ExpectedServerSha256){throw 'SERVER_SOURCE_CHANGED'}
}catch{$receipt.failure=$_.Exception.Message}
finally {
 if($app){try {
  if(!$app.HasExited){
   [IO.File]::WriteAllText((Join-Path $Stage 'close.request'),'close')
   if(!$app.WaitForExit(15000)){
    & taskkill.exe /PID $app.Id /T /F | Out-Null
    [void]$app.WaitForExit(5000)
    throw 'APP_FORCED_CLEANUP_NOT_ACCEPTED'
   }
  }
  $receipt.app_stopped=$app.HasExited
 }catch{$receipt.app_drain_failure=$_.Exception.Message}}
 # Exact owned public leaf only. Never alter LocalMachine trust or another certificate.
 try {
  if($owned -and (Test-Path ('Cert:\CurrentUser\Root\'+$thumb))){Remove-Item -LiteralPath ('Cert:\CurrentUser\Root\'+$thumb)}
  if($before -ne $null){
   $after=@(Get-ChildItem Cert:\CurrentUser\Root | ForEach-Object {$_.Thumbprint} | Sort-Object)
   $receipt.trust_restored=($before -join ',') -ceq ($after -join ',')
   if(!$receipt.trust_restored){throw 'TRUST_SNAPSHOT_CHANGED'}
  }
 }catch{$receipt.trust_failure=$_.Exception.Message}
 if($Trust -and $receipt.trust_restored -and $server -and !$server.HasExited){
  $tcp=$null;$tls=$null
  try {
   $origin=[Uri]([IO.File]::ReadAllText((Join-Path $Stage 'fixture-origin.txt')).Trim())
   if($origin.Scheme -cne 'https' -or $origin.Host -cne 'localhost' -or $origin.Port -lt 1024){throw 'NOT_LOOPBACK_PROBE'}
   $tcp=[Net.Sockets.TcpClient]::new()
   if(!$tcp.ConnectAsync('127.0.0.1',$origin.Port).Wait(3000)){throw 'TLS_PROBE_CONNECT_DEADLINE'}
   $tls=[Net.Security.SslStream]::new($tcp.GetStream(),$false)
   $tls.ReadTimeout=3000;$tls.WriteTimeout=3000
   try {$tls.AuthenticateAsClient('localhost');throw 'REMOVED_CERTIFICATE_STILL_TRUSTED'}
   catch {
    if($_.Exception -is [Security.Authentication.AuthenticationException] -or $_.Exception.InnerException -is [Security.Authentication.AuthenticationException]){
     $receipt.fresh_tls_refused=$true
    }else{throw}
   }
  }catch{$receipt.trust_failure=$_.Exception.Message}
  finally{if($tls){$tls.Dispose()};if($tcp){$tcp.Dispose()}}
 }
 if($server){try {
  if(!$server.HasExited){
   [IO.File]::WriteAllText((Join-Path $Stage 'stop.request'),'stop')
   if(!$server.WaitForExit(5000)){
    Stop-Process -InputObject $server -Force
    [void]$server.WaitForExit(5000)
    throw 'SERVER_FORCED_CLEANUP_NOT_ACCEPTED'
   }
  }
  $receipt.server_stopped=$server.HasExited
 }catch{$receipt.server_drain_failure=$_.Exception.Message}}
 $receipt.https_slice_pass=$receipt.native_scenario_pass -and $receipt.cleanup_reported -and
  $receipt.app_stopped -and $receipt.server_stopped -and $receipt.trust_restored -and $receipt.fresh_tls_refused -and
  !$receipt.failure -and !$receipt.app_drain_failure -and !$receipt.server_drain_failure -and !$receipt.trust_failure
 if($app){$app.Dispose()};if($server){$server.Dispose()};if($cert){$cert.Dispose()}
 $receipt.terminal=$true
 $receipt | ConvertTo-Json | Set-Content (Join-Path $Stage ($name+'-result.json')) -Encoding UTF8
 $receipt | ConvertTo-Json
}
if($receipt.failure -or $receipt.app_drain_failure -or $receipt.server_drain_failure -or $receipt.trust_failure){exit 1}
if($Trust -and !$receipt.https_slice_pass){exit 3}
