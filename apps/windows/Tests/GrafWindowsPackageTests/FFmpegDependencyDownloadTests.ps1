param([string]$BuilderSource = (Get-Content -LiteralPath "$PSScriptRoot\..\..\scripts\build-graf-ffmpeg.ps1" -Raw))
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($BuilderSource,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'SOURCE_PARSE'}
$fn=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Download'},$true)
if($null -eq $fn){throw 'FUNCTION_ABSENT'}
. ([scriptblock]::Create($fn.Extent.Text))
function Hash($path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Invoke-WebRequest {
 [CmdletBinding()]param([switch]$UseBasicParsing,[string]$Uri,[string]$OutFile,[int]$TimeoutSec)
 $script:calls++
 if(!$UseBasicParsing -or $TimeoutSec -ne 120 -or $Uri -cne $script:input.url){throw 'REQUEST_ARGUMENT_CHANGED'}
 if($script:mode -eq 'html'){
  $ex=[Net.WebException]::new('SECRET_MESSAGE', $null,[Net.WebExceptionStatus]::ProtocolError,$null)
  $er=[Management.Automation.ErrorRecord]::new($ex,'synthetic',[Management.Automation.ErrorCategory]::ConnectionError,$null)
  $er.ErrorDetails=[Management.Automation.ErrorDetails]::new('<html>SECRET_HTML https://redirect.invalid/SECRET_REDIRECT?secret=SECRET_QUERY</html>')
  $PSCmdlet.ThrowTerminatingError($er)
 }
 if($script:mode -eq 'socket'){
  $ex=[Net.WebException]::new('SECRET_SOCKET',[Net.Sockets.SocketException]::new(10061),[Net.WebExceptionStatus]::ConnectFailure,$null)
  throw $ex
 }
 if($script:mode -eq 'chain'){
  $ex=[InvalidOperationException]::new('SECRET_CHAIN')
  for($i=0;$i -lt 8;$i++){$ex=[InvalidOperationException]::new('SECRET_CHAIN',$ex)}
  throw $ex
 }
 [IO.File]::WriteAllBytes($OutFile,[Text.Encoding]::UTF8.GetBytes('abc'))
}
$work=Join-Path $env:TEMP ('Graf-DownloadCheck-'+[guid]::NewGuid().ToString('N'))
$null=New-Item -ItemType Directory -Path $work
$results=@()
try{
 foreach($case in @('success','html','socket','chain','badbytes','badhash')){
  $script:mode=$case;$script:calls=0
  $script:input=[pscustomobject]@{name='synthetic.bin';url='https://SECRET_USER:SECRET_PASSWORD@example.invalid/public?secret=SECRET_QUERY#SECRET_FRAGMENT';bytes=3;sha256='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'}
  if($case -eq 'badbytes'){$script:input.bytes=4}
  if($case -eq 'badhash'){$script:input.sha256='0'*64}
  $script:failure=$null
  $items=@(& {try{Download $script:input}catch{$script:failure=$_.Exception.Message}} *>&1)
  $text=($items|ForEach-Object ToString)-join "`n"
  if($text -match 'SECRET_|<html>|redirect.invalid'){throw 'PRIVATE_DIAGNOSTIC_LEAK'}
  if($script:calls -ne 1){throw 'REQUEST_COUNT'}
  if($text -notmatch 'url=https://example.invalid/public'){throw 'PUBLIC_URL'}
  $paths=@($items|Where-Object {$_ -is [string] -and $_ -ceq (Join-Path $work 'synthetic.bin')})
  if($case -eq 'success'){
   if($null -ne $script:failure -or $paths.Count -ne 1 -or $text -notmatch 'download verified'){throw 'SUCCESS_STREAM_OR_PIN'}
  }else{
   if(!$script:failure -or $paths.Count -ne 0 -or $text -match 'download verified'){throw 'REFUSAL_PIN_OR_STREAM'}
   if($case -in @('html','socket','chain') -and $script:failure -cne 'Pinned dependency download failed; see safe diagnostic above.'){throw 'UNSAFE_FAILURE'}
   if($case -eq 'html' -and $text -notmatch 'web_status=ProtocolError'){throw 'PROTOCOL_DIAGNOSTIC'}
   if($case -eq 'socket' -and $text -notmatch 'native_error=10061'){throw 'SOCKET_DIAGNOSTIC'}
   if($case -eq 'chain' -and ([regex]::Matches($text,'cause depth=')).Count -ne 4){throw 'EXCEPTION_BOUND'}
   if($case -in @('badbytes','badhash') -and $script:failure -cne 'Dependency download pin mismatch.'){throw 'PIN_FAILURE_CHANGED'}
  }
  $results+=@{case=$case;pass=$true;calls=$script:calls}
 }
}finally{
 $f=Join-Path $work 'synthetic.bin';if(Test-Path -LiteralPath $f){[IO.File]::Delete($f)}
 [IO.Directory]::Delete($work)
}
@{ok=$true;source_parse_errors=0;cases=$results;own_temp_removed=!(Test-Path -LiteralPath $work);network_requests=0;builder_executed=$false}|ConvertTo-Json -Depth 5 -Compress
