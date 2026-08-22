[CmdletBinding()]
param([switch]$PurgeContainers)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Push-Location $root
try {
    docker compose down
    if ($PurgeContainers) {
        $answer = Read-Host 'Remove Creator IP Studio database volume too? Type REMOVE'
        if ($answer -eq 'REMOVE') {
            docker compose down --volumes
        }
    }
} finally {
    Pop-Location
}
Write-Output 'Source, workspaces, models, assets, and deliveries were preserved.'

