[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$StudioArgs)
$ErrorActionPreference = 'Stop'
$repo = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
& (Join-Path $repo 'studio.ps1') @StudioArgs

