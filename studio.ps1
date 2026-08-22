[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$StudioArgs
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run --project $root studio @StudioArgs
} elseif (Test-Path (Join-Path $root '.venv\Scripts\studio.exe')) {
    & (Join-Path $root '.venv\Scripts\studio.exe') @StudioArgs
} else {
    throw 'uv or a local .venv is required. Run scripts\bootstrap.ps1 first.'
}

