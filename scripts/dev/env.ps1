<#
.SYNOPSIS
    Configures session-level environment variables for Agentic RAG local development.
.DESCRIPTION
    Sets project-local cache directories on the E: drive (Hugging Face, Pip, NPM, Torch, Temp)
    and ensures the project virtual environment is active in the current PowerShell session.
    Does NOT modify machine-wide or user-wide registry settings permanently.
.EXAMPLE
    . .\scripts\dev\env.ps1
#>

[CmdletBinding()]
param()

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Write-Host "Configuring session environment for: $ProjectRoot" -ForegroundColor Cyan

# 1. Project-local cache root on E: drive
$CacheRoot = Join-Path $ProjectRoot ".cache"
$TmpRoot = Join-Path $ProjectRoot ".tmp"

$HfHome = Join-Path $CacheRoot "huggingface"
$PipCache = Join-Path $CacheRoot "pip"
$NpmCache = Join-Path $ProjectRoot ".npm-cache"
$TorchHome = Join-Path $CacheRoot "torch"

# Ensure directories exist
@( $CacheRoot, $TmpRoot, $HfHome, $PipCache, $NpmCache, $TorchHome ) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# 2. Session-only environment variables
$env:HF_HOME = $HfHome
$env:PIP_CACHE_DIR = $PipCache
$env:npm_config_cache = $NpmCache
$env:TORCH_HOME = $TorchHome
$env:TEMP = $TmpRoot
$env:TMP = $TmpRoot

Write-Host "  [Cache] HF_HOME        = $env:HF_HOME"
Write-Host "  [Cache] PIP_CACHE_DIR  = $env:PIP_CACHE_DIR"
Write-Host "  [Cache] NPM cache      = $env:npm_config_cache"
Write-Host "  [Cache] TORCH_HOME     = $env:TORCH_HOME"
Write-Host "  [Cache] Session TEMP   = $env:TEMP"

# 3. Virtual Environment Activation (Preserving root .venv)
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "  [Python] Activating root .venv..." -ForegroundColor Green
    & $VenvActivate
    $PyVersion = & python --version 2>&1
    Write-Host "  [Python] Active version: $PyVersion"
} else {
    Write-Warning "Root virtual environment not found at $VenvActivate"
}

Write-Host "Development environment configuration complete." -ForegroundColor Cyan
