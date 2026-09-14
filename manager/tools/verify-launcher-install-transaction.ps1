#requires -Version 5.1
$ErrorActionPreference = 'Stop'

$installerPath = Join-Path $PSScriptRoot 'install\install-launcher.ps1'
$installerUiPath = Join-Path $PSScriptRoot 'install\install-launcher-ui.ps1'
$tokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($installerPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {
  throw "Installer syntax error: $($parseErrors[0].Message)"
}

$uiTokens = $null
$uiParseErrors = $null
$uiAst = [Management.Automation.Language.Parser]::ParseFile($installerUiPath, [ref]$uiTokens, [ref]$uiParseErrors)
if ($uiParseErrors.Count -gt 0) {
  throw "Installer UI syntax error: $($uiParseErrors[0].Message)"
}
$uiSource = $uiAst.Extent.Text
if ($uiSource -match 'treating as success because WorkKitLauncher\.exe exists') {
  throw 'Installer UI must not replace a failed installer exit code based on a restored executable.'
}

$requiredFunctions = @(
  'Remove-InstallPath',
  'Start-LauncherInstallTransaction',
  'Undo-LauncherInstallTransaction',
  'Complete-LauncherInstallTransaction'
)
foreach ($name in $requiredFunctions) {
  $definition = $ast.Find({
    param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
  }, $true)
  if ($null -eq $definition) { throw "Missing installer function: $name" }
  Invoke-Expression $definition.Extent.Text
}

function New-TestTree([string]$root, [string]$marker) {
  New-Item -ItemType Directory -Force -Path (Join-Path $root 'bin\work-kit-launcher') | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $root 'ui\work-kit-launcher') | Out-Null
  Set-Content -LiteralPath (Join-Path $root 'WorkKitLauncher.exe') -Value "$marker-exe"
  Set-Content -LiteralPath (Join-Path $root 'launcher-manifest.json') -Value "{`"marker`":`"$marker`"}"
  Set-Content -LiteralPath (Join-Path $root 'bin\work-kit-launcher\payload.txt') -Value "$marker-bin"
  Set-Content -LiteralPath (Join-Path $root 'ui\work-kit-launcher\payload.txt') -Value "$marker-ui"
}

$testRoot = Join-Path ([IO.Path]::GetTempPath()) ("launcher-install-transaction-test-{0}" -f [Guid]::NewGuid().ToString('N'))
try {
  New-TestTree $testRoot 'old'
  Start-LauncherInstallTransaction $testRoot | Out-Null
  New-TestTree $testRoot 'partial'
  Undo-LauncherInstallTransaction

  if ((Get-Content -LiteralPath (Join-Path $testRoot 'WorkKitLauncher.exe') -Raw).Trim() -ne 'old-exe') {
    throw 'Rollback did not restore the previous executable.'
  }
  if ((Get-Content -LiteralPath (Join-Path $testRoot 'bin\work-kit-launcher\payload.txt') -Raw).Trim() -ne 'old-bin') {
    throw 'Rollback did not restore the previous launcher payload.'
  }
  if (Test-Path -LiteralPath $script:installTransaction.BackupRoot) {
    throw 'Rollback backup directory was not removed.'
  }

  Remove-Item -LiteralPath $testRoot -Recurse -Force
  New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
  Start-LauncherInstallTransaction $testRoot | Out-Null
  New-TestTree $testRoot 'partial-only'
  Undo-LauncherInstallTransaction
  foreach ($relativePath in $script:installTransaction.ManagedPaths) {
    if (Test-Path -LiteralPath (Join-Path $testRoot $relativePath)) {
      throw "Fresh-install rollback left a partial path: $relativePath"
    }
  }

  New-TestTree $testRoot 'old'
  Start-LauncherInstallTransaction $testRoot | Out-Null
  New-TestTree $testRoot 'new'
  Complete-LauncherInstallTransaction
  if ((Get-Content -LiteralPath (Join-Path $testRoot 'WorkKitLauncher.exe') -Raw).Trim() -ne 'new-exe') {
    throw 'Commit did not retain the new executable.'
  }
  if (Test-Path -LiteralPath $script:installTransaction.BackupRoot) {
    throw 'Commit backup directory was not removed.'
  }
} finally {
  Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host 'verify-launcher-install-transaction: OK'
