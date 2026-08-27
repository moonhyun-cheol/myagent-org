# CQR Market Research — PowerShell wrapper for Codex agent / local use
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path $PSScriptRoot -Parent
$managerRoot = Split-Path $scriptDir -Parent
$pipelineRoot = Join-Path $scriptDir "cqr_product_pipeline"
$sessionFile = Join-Path $scriptDir ".session.json"

function Test-PythonWorks($exe) {
    if (-not $exe) { return $false }
    try {
        & $exe -c "pass" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

$pythonCandidates = @()
if ($env:CQR_PIPELINE_PYTHON) { $pythonCandidates += $env:CQR_PIPELINE_PYTHON }
if ($env:CQR_PIPELINE_VENV) {
    $pythonCandidates += (Join-Path $env:CQR_PIPELINE_VENV "Scripts\python.exe")
}
if ($env:CQR_ROOT) {
    $pythonCandidates += (Join-Path $env:CQR_ROOT "runtime\pipeline-venv\Scripts\python.exe")
}
$pythonCandidates += (Join-Path $pipelineRoot ".venv\Scripts\python.exe")
$pythonCandidates += "C:\Users\Temp\cqr-pipeline-venv\Scripts\python.exe"
$onPath = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $onPath) { $onPath = Get-Command python -ErrorAction SilentlyContinue }
if ($onPath) { $pythonCandidates += $onPath.Source }

# A venv can exist but be unusable (e.g. non-ASCII path .pth decoded with cp949),
# so probe each candidate instead of taking the first that exists.
$venvPython = $null
foreach ($candidate in $pythonCandidates) {
    if (-not $candidate) { continue }
    $isPath = $candidate -match '[\\/]'
    if ($isPath -and -not (Test-Path $candidate)) { continue }
    if (Test-PythonWorks $candidate) { $venvPython = $candidate; break }
    Write-Host "python candidate unusable: $candidate"
}

if (-not $venvPython) {
    throw "No working python found. Create runtime/pipeline-venv, repair cqr_product_pipeline/.venv, or set CQR_PIPELINE_PYTHON."
}

Write-Host "python: $venvPython"

$env:CQR_MANAGER_ROOT = $managerRoot

function Get-SessionMeta {
    if (-not (Test-Path $sessionFile)) { return $null }
    return Get-Content $sessionFile -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Set-SessionMeta($meta) {
    $meta | ConvertTo-Json -Depth 5 | Set-Content $sessionFile -Encoding UTF8
}

function Test-DryRunFlag($argList) {
    return ($argList -contains "-DryRun") -or ($argList -contains "--dry-run")
}

function Get-DryRunArg($argList) {
    if (Test-DryRunFlag $argList) { return @("--dry-run") }
    return @()
}

$cmd = $args[0]
if ($cmd) {
    $cmdNorm = $cmd.TrimStart('/').ToLowerInvariant()
    if ($cmdNorm -in @('deep-research', 'deepresearch')) {
        $cmd = 'research'
    }
    elseif ($cmdNorm -notin @('research', 'pipeline', 'status') -and $args.Count -ge 2) {
        # /심층리서치 "brief" — non-ASCII alias; brief is args[1]
        $args = @('research', $args[1]) + @($args | Select-Object -Skip 2)
        $cmd = 'research'
    }
}

if (-not $cmd) {
    Write-Host @"
CQR Market Research runner

  .\run.ps1 deep-research "Liberator summer cargo Amazon review pain" [-DryRun]
  .\run.ps1 research "<same>" [-DryRun]
  .\run.ps1 pipeline start "<brief>" [-DryRun]
  .\run.ps1 pipeline approve "<approval text>"
  .\run.ps1 status

  Korean alias: .\run.ps1 /심층리서치 "brief"  (same as research)
"@
    exit 0
}

switch ($cmd) {
    "research" {
        $brief = $args[1]
        if (-not $brief) { throw "Usage: run.ps1 research `"<brief>`" [-DryRun]" }
        $extraArgs = @($args | Select-Object -Skip 2)
        $sessionId = $null
        foreach ($a in $extraArgs) {
            if ($a -match '^-') { continue }
            $sessionId = $a
            break
        }
        if (-not $sessionId) { $sessionId = [guid]::NewGuid().ToString("N").Substring(0, 8) }
        $outDir = Join-Path $scriptDir "output\$sessionId"
        $dryArgs = Get-DryRunArg $args
        Push-Location $pipelineRoot
        try {
            if ($dryArgs.Count -gt 0) {
                & $venvPython -m cqr_product_pipeline.cli.run_research `
                    --brief $brief `
                    --session-id $sessionId `
                    --output-dir $outDir `
                    --dry-run
            } else {
                & $venvPython -m cqr_product_pipeline.cli.run_research `
                    --brief $brief `
                    --session-id $sessionId `
                    --output-dir $outDir
            }
        } finally { Pop-Location }
        Set-SessionMeta @{
            session_id = $sessionId
            brief = $brief
            mode = "research"
            output_dir = $outDir
            thread_id = $sessionId
        }
    }
    "pipeline" {
        $sub = $args[1]
        switch ($sub) {
            "start" {
                $brief = $args[2]
                if (-not $brief) { throw "Usage: run.ps1 pipeline start `"<brief>`" [-DryRun]" }
                $extraArgs = @($args | Select-Object -Skip 3)
                $sessionId = $null
                foreach ($a in $extraArgs) {
                    if ($a -match '^-') { continue }
                    $sessionId = $a
                    break
                }
                if (-not $sessionId) { $sessionId = [guid]::NewGuid().ToString("N").Substring(0, 8) }
                $outDir = Join-Path $scriptDir "output\$sessionId"
                $dryArgs = Get-DryRunArg $args
                Push-Location $pipelineRoot
                try {
                    if ($dryArgs.Count -gt 0) {
                        & $venvPython -m cqr_product_pipeline.cli.run_pipeline `
                            --brief $brief `
                            --thread-id $sessionId `
                            --output-dir $outDir `
                            --dry-run
                    } else {
                        & $venvPython -m cqr_product_pipeline.cli.run_pipeline `
                            --brief $brief `
                            --thread-id $sessionId `
                            --output-dir $outDir
                    }
                } finally { Pop-Location }
                Set-SessionMeta @{
                    session_id = $sessionId
                    brief = $brief
                    mode = "pipeline"
                    output_dir = $outDir
                    thread_id = $sessionId
                }
            }
            "approve" {
                $text = $args[2]
                if (-not $text) { throw "Usage: run.ps1 pipeline approve `"A 승인, B 거절`"" }
                $meta = Get-SessionMeta
                if (-not $meta) { throw "No session — run pipeline start first" }
                $sessionId = $meta.thread_id
                $outDir = $meta.output_dir
                $dryArgs = Get-DryRunArg $args
                Push-Location $pipelineRoot
                try {
                    if ($dryArgs.Count -gt 0) {
                        & $venvPython -m cqr_product_pipeline.cli.run_pipeline `
                            --resume `
                            --approve-text $text `
                            --thread-id $sessionId `
                            --output-dir $outDir `
                            --dry-run
                    } else {
                        & $venvPython -m cqr_product_pipeline.cli.run_pipeline `
                            --resume `
                            --approve-text $text `
                            --thread-id $sessionId `
                            --output-dir $outDir
                    }
                } finally { Pop-Location }
            }
            default { throw "Unknown pipeline subcommand: $sub" }
        }
    }
    "status" {
        $meta = Get-SessionMeta
        if (-not $meta) {
            Write-Host "No active session (.session.json missing)"
            exit 0
        }
        Write-Host "Session: $($meta.session_id)"
        Write-Host "Mode:    $($meta.mode)"
        Write-Host "Brief:   $($meta.brief)"
        Write-Host "Output:  $($meta.output_dir)"
        Write-Host "Thread:  $($meta.thread_id)"
    }
    default { throw "Unknown command: $cmd" }
}
