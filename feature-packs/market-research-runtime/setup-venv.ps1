<#
.SYNOPSIS
  CQR market-research runtime: ensure Python, create <root>/runtime/pipeline-venv, pip install requirements.
.DESCRIPTION
  Installed by Core at <root>/data/organization-features/org.cqr.market-research-runtime/.
  Last stdout line is a JSON result: {"ok":..,"status":..,"python":..,"venv":..}.
  status: ready | removed | not_installed | no_python | python_install_failed | venv_failed | pip_failed | import_failed
#>
param(
  [string]$Root = '',
  [switch]$Force,
  [switch]$Remove,
  [switch]$NoPythonInstall
)

# Continue (not Stop): in Windows PowerShell 5.1, native stderr (pip warnings) under
# 2>&1 becomes ErrorRecords and Stop would abort the run. Exit codes are checked explicitly.
$ErrorActionPreference = 'Continue'
$FeatureId = 'org.cqr.market-research-runtime'
$PythonVersion = '3.12.10'
$InstallerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"

if (-not $Root) {
  # <root>/data/organization-features/<id>/setup-venv.ps1
  $Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
}
$Venv = Join-Path $Root 'runtime\pipeline-venv'
$VenvPy = Join-Path $Venv 'Scripts\python.exe'
$Marker = Join-Path $Venv '.cqr-runtime.json'
$Requirements = Join-Path $PSScriptRoot 'requirements.txt'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir 'market-research-runtime-setup.log'

function Write-Log([string]$Text) {
  $line = '[{0}] {1}' -f (Get-Date -Format 's'), $Text
  Add-Content -Path $LogFile -Value $line -Encoding UTF8
  Write-Host $Text
}

function Finish([bool]$Ok, [string]$Status, [string]$Python = '', [string]$Message = '') {
  $result = [ordered]@{ ok = $Ok; status = $Status; feature = $FeatureId; python = $Python; venv = $Venv; message = $Message }
  Write-Log "result: $Status $Message"
  Write-Output ($result | ConvertTo-Json -Compress)
  if ($Ok) { exit 0 } else { exit 1 }
}

# Returns "3.12" style version or $null. Store aliases (WindowsApps) are skipped: they open the Store instead of running.
function Get-PyVersion([string]$Exe, [string[]]$Prefix = @()) {
  if (-not $Exe) { return $null }
  if ($Exe -match '\\WindowsApps\\') { return $null }
  try {
    $out = & $Exe @Prefix -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    $v = ([string]$out).Trim()
    if ($v -match '^3\.(11|12|13)$') { return $v }
  } catch { }
  return $null
}

function Resolve-PyExe([string]$Exe, [string[]]$Prefix = @()) {
  try {
    $p = & $Exe @Prefix -c "import sys;print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $p) { return ([string]$p).Trim() }
  } catch { }
  return $null
}

function Find-Python {
  if ($env:CQR_BOOTSTRAP_PYTHON -and (Get-PyVersion $env:CQR_BOOTSTRAP_PYTHON)) { return $env:CQR_BOOTSTRAP_PYTHON }
  $local = Join-Path $env:LOCALAPPDATA 'Programs\Python'
  foreach ($dir in @('Python312', 'Python313', 'Python311')) {
    $exe = Join-Path $local "$dir\python.exe"
    if ((Test-Path $exe) -and (Get-PyVersion $exe)) { return $exe }
  }
  $py = Get-Command py.exe -ErrorAction SilentlyContinue
  if ($py) {
    foreach ($tag in @('-3.12', '-3.13', '-3.11')) {
      if (Get-PyVersion $py.Source @($tag)) { return (Resolve-PyExe $py.Source @($tag)) }
    }
  }
  foreach ($cmd in @(Get-Command python.exe -All -ErrorAction SilentlyContinue)) {
    if (Get-PyVersion $cmd.Source) { return $cmd.Source }
  }
  return $null
}

function Install-Python {
  $installer = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"
  Write-Log "Python 3.11~3.13 없음 → $InstallerUrl 다운로드"
  [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
  $ProgressPreference = 'SilentlyContinue'
  Invoke-WebRequest -Uri $InstallerUrl -OutFile $installer -UseBasicParsing -ErrorAction Stop
  $sig = Get-AuthenticodeSignature -FilePath $installer
  if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    throw "Python 설치 파일 서명 확인 실패: $($sig.Status) $($sig.SignerCertificate.Subject)"
  }
  Write-Log 'Python 사용자 범위 조용히 설치 중…'
  $proc = Start-Process -FilePath $installer -Wait -PassThru -ArgumentList @(
    '/quiet', 'InstallAllUsers=0', 'PrependPath=0', 'Include_launcher=0', 'Include_test=0',
    'Include_doc=0', 'Include_tcltk=0', 'Shortcuts=0', 'AssociateFiles=0'
  )
  Remove-Item $installer -Force -ErrorAction SilentlyContinue
  if ($proc.ExitCode -ne 0) { throw "Python 설치 실패 (exit $($proc.ExitCode))" }
  $exe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
  if (-not (Get-PyVersion $exe)) { throw "Python 설치 후 실행 파일을 찾지 못함: $exe" }
  return $exe
}

Write-Log "=== $FeatureId setup (root=$Root remove=$Remove force=$Force) ==="

if ($Remove) {
  if (-not (Test-Path $Venv)) { Finish $true 'not_installed' }
  if (-not (Test-Path $Marker)) {
    Finish $false 'not_installed' '' '이 스크립트가 만든 venv가 아니어서 지우지 않았습니다 (.cqr-runtime.json 없음).'
  }
  Remove-Item -Recurse -Force $Venv
  Finish $true 'removed'
}

$created = $false
if ((Test-Path $VenvPy) -and -not $Force) {
  Write-Log '기존 venv 재사용 → 패키지만 맞춥니다.'
} else {
  $created = $true
  $basePy = Find-Python
  if (-not $basePy) {
    if ($NoPythonInstall) { Finish $false 'no_python' '' 'Python 3.11~3.13이 없습니다.' }
    try { $basePy = Install-Python } catch { Finish $false 'python_install_failed' '' $_.Exception.Message }
  }
  Write-Log "기준 Python: $basePy"
  if (Test-Path $Venv) { Remove-Item -Recurse -Force $Venv }
  New-Item -ItemType Directory -Force -Path (Split-Path $Venv) | Out-Null
  & $basePy -m venv $Venv 2>&1 | ForEach-Object { Write-Log "$_" }
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPy)) { Finish $false 'venv_failed' $basePy 'venv 생성 실패' }
}

$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
Write-Log 'pip install (PyPI) 시작 — 수 분 걸릴 수 있습니다.'
& $VenvPy -m pip install --upgrade pip 2>&1 | ForEach-Object { Write-Log "$_" }
& $VenvPy -m pip install -r $Requirements 2>&1 | ForEach-Object { Write-Log "$_" }
if ($LASTEXITCODE -ne 0) { Finish $false 'pip_failed' $VenvPy 'pip install 실패 (인터넷/PyPI 접속 확인). 로그를 확인하세요.' }

& $VenvPy -c "import langgraph, langgraph.checkpoint.sqlite, langchain_openai, langchain_ollama, chromadb, ddgs, pydantic_settings" 2>&1 | ForEach-Object { Write-Log "$_" }
if ($LASTEXITCODE -ne 0) { Finish $false 'import_failed' $VenvPy '설치 후 import 확인 실패' }

$pyVer = (& $VenvPy -c "import platform;print(platform.python_version())").Trim()
if ($created -or (Test-Path $Marker)) {
  # Marker = "this script owns the venv"; -Remove only deletes owned venvs.
  $markerDoc = [ordered]@{ feature = $FeatureId; python = $pyVer; installed_at = (Get-Date).ToString('o') }
  [IO.File]::WriteAllText($Marker, ($markerDoc | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
}
Finish $true 'ready' $VenvPy "Python $pyVer"
