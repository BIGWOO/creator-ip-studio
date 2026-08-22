[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path (Split-Path -Parent (Resolve-Path (Join-Path $PSScriptRoot '..'))) 'comfyui-minimax-h3-provider'),
    [ValidateSet('creator', 'all')]
    [string]$Pack = 'creator',
    [switch]$DownloadModels,
    [switch]$Start,
    [switch]$SkipHashes
)

$ErrorActionPreference = 'Stop'
$repository = 'https://github.com/BIGWOO/comfyui-minimax-h3-provider.git'
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required but was not found in PATH.'
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required but was not found in PATH.'
}
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    throw 'An NVIDIA driver and GPU are required.'
}

if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot '.git'))) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $InstallRoot) | Out-Null
    & git clone --filter=blob:none $repository $InstallRoot
    if ($LASTEXITCODE -ne 0) { throw 'Provider repository clone failed.' }
} else {
    $origin = (& git -C $InstallRoot remote get-url origin).Trim()
    if ($origin -ne $repository -and $origin -ne $repository.Replace('.git', '')) {
        throw "Existing directory has an unexpected origin: $origin"
    }
    & git -C $InstallRoot pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Provider repository update failed.' }
}

& (Join-Path $InstallRoot 'scripts\setup.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Provider runtime setup failed.' }

if ($DownloadModels) {
    $downloadArgs = @{ Pack = $Pack }
    if ($SkipHashes) { $downloadArgs.SkipHash = $true }
    & (Join-Path $InstallRoot 'scripts\download-models.ps1') @downloadArgs
    if ($LASTEXITCODE -ne 0) { throw 'Provider model download failed.' }
}

if ($Start) {
    & (Join-Path $InstallRoot 'scripts\start.ps1') -Profile main -Background
    if ($LASTEXITCODE -ne 0) { throw 'Provider start failed.' }
}

[pscustomobject]@{
    ProviderRoot = $InstallRoot
    Pack = $Pack
    ModelsRequested = [bool]$DownloadModels
    Started = [bool]$Start
    Url = 'http://127.0.0.1:8188'
} | ConvertTo-Json
