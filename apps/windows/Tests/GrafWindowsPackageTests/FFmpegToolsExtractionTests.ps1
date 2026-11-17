param([string]$BuilderSource = (Get-Content -LiteralPath "$PSScriptRoot\..\..\scripts\build-graf-ffmpeg.ps1" -Raw))
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($BuilderSource,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'SOURCE_PARSE'}
foreach($name in @('Hash','Write-Utf8','Json','Run')){
 $fn=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name},$true)
 if($null -eq $fn){throw 'FUNCTION_ABSENT'}
 . ([scriptblock]::Create($fn.Extent.Text))
}
$begin=$BuilderSource.IndexOf('    $tar = ',[StringComparison]::Ordinal)
$end=$BuilderSource.IndexOf('    $msys = ',$begin,[StringComparison]::Ordinal)
if($begin -lt 0 -or $end -le $begin){throw 'BOOTSTRAP_ABSENT'}
$bootstrap=[scriptblock]::Create($BuilderSource.Substring($begin,$end-$begin))
$utf8=[Text.UTF8Encoding]::new($false)
$fixture=Join-Path $env:TEMP ('Graf Tools Check '+[guid]::NewGuid().ToString('N'))
$work=Join-Path $fixture 'work space'
$prefix=Join-Path $fixture 'install'
$inputRoot=Join-Path $fixture 'input'
$shadow=Join-Path $fixture 'path'
$nativeTar=Join-Path $env:SystemRoot 'System32\tar.exe'
$originalPath=$env:PATH
try{
 $null=New-Item -ItemType Directory -Path $work,"$prefix\share\graf","$inputRoot\msys64\usr\bin",$shadow
 [IO.File]::WriteAllText("$inputRoot\msys64\usr\bin\synthetic.txt",'synthetic-tools',$utf8)
 & $nativeTar -cJf "$work\msys2-base.tar.xz" -C $inputRoot msys64
 if($LASTEXITCODE -ne 0){throw 'ARCHIVE_CREATE'}
 $before=Hash "$work\msys2-base.tar.xz"
 # A real harmless executable shadows tar; bootstrap must ignore it.
 Copy-Item -LiteralPath "$env:SystemRoot\System32\where.exe" -Destination "$shadow\tar.exe"
 $env:PATH="$shadow;$originalPath"
 if((Get-Command tar.exe -CommandType Application|Select-Object -First 1).Source -ine "$shadow\tar.exe"){throw 'PATH_SHADOW_MISSING'}
 $items=@(. $bootstrap *>&1)
 if($tar -ine $nativeTar -or [IO.File]::ReadAllText("$work\msys64\usr\bin\synthetic.txt") -cne 'synthetic-tools'){throw 'NATIVE_EXTRACTION'}
 if((Hash "$work\msys2-base.tar.xz") -cne $before){throw 'ARCHIVE_CHANGED'}
 $terminal=Get-Content -LiteralPath "$prefix\share\graf\tools-extract.terminal.json" -Raw|ConvertFrom-Json
 if($terminal.exit -ne 0){throw 'EXTRACTION_EXIT'}
 $messages=($items|ForEach-Object ToString)-join "`n"
 if($messages -notmatch 'FFmpeg stage started name=tools-extract pid=[0-9]+' -or $messages -notmatch 'FFmpeg stage terminal name=tools-extract exit=0 elapsed_ms=[0-9]+'){throw 'PROCESS_EVIDENCE'}
}finally{
 $env:PATH=$originalPath
 if(Test-Path -LiteralPath $fixture){Remove-Item -LiteralPath $fixture -Recurse -Force}
}
@{ok=$true;native_extraction=$true;path_shadow_ignored=$true;archive_unchanged=$true;own_temp_removed=!(Test-Path -LiteralPath $fixture);network_requests=0;full_builder_executed=$false}|ConvertTo-Json -Compress
