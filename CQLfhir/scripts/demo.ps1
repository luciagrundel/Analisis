param(
    [string]$BaseUrl = 'http://localhost:8080/fhir',
    [switch]$SoloCargar,
    [int]$EsperaSegundos = 240
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$BaseUrl = $BaseUrl.TrimEnd('/')
$headers = @{ Accept = 'application/fhir+json' }
function Send-Fhir($Method, $Path, $Resource) {
    $json = $Resource | ConvertTo-Json -Depth 50
    Invoke-RestMethod -Method $Method -Uri "$BaseUrl/$Path" -Headers $headers `
        -ContentType 'application/fhir+json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json)) -TimeoutSec 120
}
$deadline = (Get-Date).AddSeconds($EsperaSegundos)
do {
    try {
        $metadata = Invoke-RestMethod "$BaseUrl/metadata" -Headers $headers -TimeoutSec 10
        if ($metadata.resourceType -eq 'CapabilityStatement') { break }
    } catch { }
    if ((Get-Date) -ge $deadline) { throw "HAPI no esta listo en $BaseUrl. Revisa: docker compose logs --tail 100" }
    Start-Sleep -Seconds 3
} while ($true)

$bundle = Get-Content "$root/data/pacientes.json" -Raw | ConvertFrom-Json
$loaded = Send-Fhir POST '' $bundle
if ($loaded.resourceType -ne 'Bundle' -or $loaded.type -ne 'transaction-response') { throw 'Respuesta de carga inesperada.' }
foreach ($entry in $loaded.entry) {
    if ($entry.response.status -notmatch '^2\d\d') { throw "Error de carga: $($entry.response.status)" }
}
$source = [IO.File]::ReadAllText("$root/cql/ReglasBasicas.cql")
$library = @{
    resourceType = 'Library'; id = 'reglas-basicas'
    url = 'http://example.org/fhir/Library/ReglasBasicas'
    name = 'ReglasBasicas'; version = '1.0.0'; status = 'active'
    type = @{ coding = @(@{ system = 'http://terminology.hl7.org/CodeSystem/library-type'; code = 'logic-library' }) }
    content = @(@{ contentType = 'text/cql'; data = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($source)) })
}
$null = Send-Fhir PUT 'Library/reglas-basicas' $library
$planSource = [IO.File]::ReadAllText("$root/cql/PlanSeguimiento.cql")
$planLibrary = @{
    resourceType = 'Library'; id = 'plan-seguimiento'
    url = 'http://example.org/fhir/Library/PlanSeguimiento'
    name = 'PlanSeguimiento'; version = '1.0.0'; status = 'active'
    type = @{ coding = @(@{ system = 'http://terminology.hl7.org/CodeSystem/library-type'; code = 'logic-library' }) }
    relatedArtifact = @(@{ type = 'depends-on'; resource = 'http://example.org/fhir/Library/ReglasBasicas|1.0.0' })
    content = @(@{ contentType = 'text/cql'; data = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($planSource)) })
}
$null = Send-Fhir PUT 'Library/plan-seguimiento' $planLibrary
$plan = Get-Content "$root/data/plan-seguimiento.json" -Raw | ConvertFrom-Json
$null = Send-Fhir PUT 'PlanDefinition/plan-seguimiento' $plan
Write-Host 'Pacientes, observaciones, dos Library y PlanDefinition cargados.'
if ($SoloCargar) { return }

$output = Join-Path $root 'output'
$null = New-Item -ItemType Directory -Force -Path $output
$cases = @(
    @{ id = 'ana'; edad = 36; adulto = $true; cantidad = 1; combinado = $true },
    @{ id = 'bruno'; edad = 15; adulto = $false; cantidad = 1; combinado = $false },
    @{ id = 'carla'; edad = 40; adulto = $true; cantidad = 0; combinado = $false }
)
foreach ($case in $cases) {
    $request = @{ resourceType = 'Parameters'; parameter = @(@{ name = 'subject'; valueString = "Patient/$($case.id)" }) }
    $result = Send-Fhir POST 'Library/reglas-basicas/$evaluate' $request
    $result | ConvertTo-Json -Depth 50 | Set-Content "$output/$($case.id).json" -Encoding UTF8
    if ($result.resourceType -ne 'Parameters') { throw "Resultado inesperado para $($case.id)" }
    $expected = @{ Edad = $case.edad; EsAdulto = $case.adulto; CantidadObservacionesFinales = $case.cantidad; TieneObservacionesFinales = ($case.cantidad -gt 0); AdultoConObservaciones = $case.combinado }
    foreach ($name in $expected.Keys) {
        $parameter = @($result.parameter | Where-Object name -eq $name)
        if ($parameter.Count -ne 1) { throw "Falta el resultado $name en $($case.id). Revisa output." }
        $value = @($parameter[0].PSObject.Properties | Where-Object Name -like 'value*')
        if ($value.Count -ne 1 -or $null -eq $value[0].Value -or $value[0].Value -ne $expected[$name]) {
            throw "Resultado incorrecto: $($case.id) / $name. Esperado: $($expected[$name]). Revisa output."
        }
    }
    Write-Host "OK $($case.id): edad=$($case.edad), adulto=$($case.adulto), observaciones finales=$($case.cantidad), combinado=$($case.combinado)"
}
Write-Host 'Las 15 comprobaciones de resultados pasaron. Respuestas completas en output/.'

foreach ($case in $cases) {
    $request = @{ resourceType = 'Parameters'; parameter = @(@{ name = 'subject'; valueString = "Patient/$($case.id)" }) }
    $evaluation = Send-Fhir POST 'Library/plan-seguimiento/$evaluate' $request
    $evaluation | ConvertTo-Json -Depth 50 | Set-Content "$output/$($case.id)-plan-evaluacion.json" -Encoding UTF8
    $condition = @($evaluation.parameter | Where-Object name -eq 'RequiereSeguimiento')
    if ($condition.Count -ne 1 -or $null -eq $condition[0].valueBoolean -or $condition[0].valueBoolean -ne $case.combinado) {
        throw "Condicion de seguimiento incorrecta para $($case.id)."
    }
    $carePlan = Send-Fhir POST 'PlanDefinition/plan-seguimiento/$apply' $request
    $carePlan | ConvertTo-Json -Depth 50 | Set-Content "$output/$($case.id)-careplan.json" -Encoding UTF8
    if ($carePlan.resourceType -ne 'CarePlan' -or $carePlan.subject.reference -ne "Patient/$($case.id)") {
        throw "Se esperaba un CarePlan para Patient/$($case.id). Revisa output."
    }
    if (-not $carePlan.status -or -not $carePlan.intent) { throw 'CarePlan sin status o intent.' }
    $groups = @($carePlan.contained | Where-Object resourceType -eq 'RequestGroup')
    $actions = @($groups | ForEach-Object { $_.action } | Where-Object { $null -ne $_ })
    $expectedActions = if ($case.combinado) { 1 } else { 0 }
    if ($actions.Count -ne $expectedActions) {
        throw "Acciones incorrectas para $($case.id): esperadas $expectedActions, recibidas $($actions.Count)."
    }
    if ($expectedActions -eq 1 -and $actions[0].title -ne $plan.action[0].title) { throw 'Accion de seguimiento inesperada.' }
    Write-Host "OK CarePlan $($case.id): requiere seguimiento=$($case.combinado), acciones=$($actions.Count)"
}
Write-Host 'CQL de seguimiento y CarePlan verificados para los tres pacientes. Archivos *-careplan.json en output/.'
