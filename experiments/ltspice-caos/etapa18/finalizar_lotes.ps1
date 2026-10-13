$ErrorActionPreference='Stop'
$ensaioPython='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1007-641-0_26.1007.641.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe'
$ensaioNomes=@()
foreach($ensaioManifesto in Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'lotes_*.json') {
    $ensaioNomes+=Get-Content -LiteralPath $ensaioManifesto.FullName -Raw | ConvertFrom-Json
}
$ensaioNomes=$ensaioNomes | Select-Object -Unique
while($true) {
    $ensaioCompletos=0
    foreach($ensaioNome in $ensaioNomes) {
        $ensaioLog=Join-Path $PSScriptRoot "$ensaioNome.log"
        if((Test-Path -LiteralPath $ensaioLog) -and ((Get-Content -LiteralPath $ensaioLog -Raw) -match 'Measurement: pico_orcamento')) { $ensaioCompletos++ }
    }
    if($ensaioCompletos -eq $ensaioNomes.Count) { break }
    Start-Sleep -Seconds 20
}
Write-Output 'Todos os lotes terminaram; iniciando auditoria dos RAWs.'
& $ensaioPython (Join-Path $PSScriptRoot 'analisar_etapa18.py')
if($LASTEXITCODE -ne 0) { throw 'Analise completa falhou.' }
& $ensaioPython (Join-Path $PSScriptRoot 'verificar_entrega.py')
if($LASTEXITCODE -ne 0) { throw 'Verificacao da entrega falhou.' }
Write-Output 'Analise e verificacao completas.'
