[CmdletBinding()]
param(
    [ValidateSet('cpu','nvidia','cloud')]
    [string]$Mode = 'cpu'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required. Install it from https://docs.astral.sh/uv/ and rerun.'
}
uv python install 3.11
uv sync --project $root --extra dev --extra tts
uv run --project $root studio doctor --mode $Mode

