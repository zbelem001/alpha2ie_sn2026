param(
    [switch]$XRoad,
    [switch]$Extended,
    [switch]$Build
)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $composeArguments = @('compose')
    if ($XRoad) { $composeArguments += @('--profile', 'xroad') }
    if ($Extended) { $composeArguments += @('--profile', 'extended') }
    $composeArguments += @('up', '-d')
    if ($Build) { $composeArguments += '--build' }
    & docker @composeArguments
    if ($LASTEXITCODE -ne 0) { throw 'Le démarrage Docker a échoué.' }

    # Delete only successful, stopped initialization containers, never volumes.
    foreach ($service in @('keycloak-profile-init', 'keycloak-admin-client-init', 'registry-db-init', 'xroad-setup')) {
        $containerIds = & docker compose --profile xroad --profile admin-setup ps -a -q $service
        foreach ($containerId in $containerIds) {
            if (-not $containerId) { continue }
            $state = & docker inspect --format '{{.State.Status}} {{.State.ExitCode}}' $containerId
            if ($LASTEXITCODE -ne 0) { throw "Inspection impossible : $service" }
            if ($state -eq 'exited 0') { & docker rm $containerId | Out-Null }
        }
    }
    Write-Host 'Citoyen : http://localhost:3000 | Agent : http://localhost:3001 | Administration : http://localhost:3002'
} finally {
    Pop-Location
}
