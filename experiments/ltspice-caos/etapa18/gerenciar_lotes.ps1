param([int]$MaxParallel=6)
$ErrorActionPreference='Stop'
$ensaioPython='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1007-641-0_26.1007.641.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe'
$ensaioExe='C:/Users/joaqu/AppData/Local/Programs/ADI/LTspice/LTspice.exe'
$ensaioTodos=@()
foreach($ensaioManifesto in Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'lotes_*.json') {
    $ensaioTodos+=Get-Content -LiteralPath $ensaioManifesto.FullName -Raw | ConvertFrom-Json
}
$ensaioTodos=@($ensaioTodos | Select-Object -Unique)
# Piloto e os dois controles L2 continuam nos seus runners ja ativos.
$ensaioOrdem=@('L2_5_10_v2','R_C','R_L2_5_10','C_replay_on','C_queda_on','C_duplo_on','C_tolerancia_mais','C_tolerancia_menos','C_vies12_on','C_dupla_falha','L2_replay_v2','L2_vies_v2')
$ensaioLancados=@{}
function Test-EnsaioCompleto([string]$Nome) {
    $ensaioArquivo=Join-Path $PSScriptRoot "$Nome.log"
    return ((Test-Path -LiteralPath $ensaioArquivo) -and ((Get-Content -LiteralPath $ensaioArquivo -Raw) -match 'Measurement: pico_orcamento'))
}
while($true) {
    foreach($ensaioNome in @($ensaioLancados.Keys)) {
        $ensaioProc=$ensaioLancados[$ensaioNome]
        if($ensaioProc.HasExited) {
            if(-not (Test-EnsaioCompleto $ensaioNome)) { throw "Ensaio incompleto: $ensaioNome" }
            Write-Output "Concluido: $ensaioNome"
            $ensaioLancados.Remove($ensaioNome)
        }
    }
    $ensaioCompletos=@($ensaioTodos | Where-Object { Test-EnsaioCompleto $_ })
    if($ensaioCompletos.Count -eq $ensaioTodos.Count) { break }
    $ensaioAtivos=@()
    foreach($ensaioProc in Get-CimInstance Win32_Process -Filter "Name = 'LTspice.exe'") {
        if($ensaioProc.CommandLine -match '-b\s+"?([^"\s]+)\.cir') {
            $ensaioNome=[IO.Path]::GetFileName($Matches[1])
            if($ensaioNome -in $ensaioTodos) { $ensaioAtivos+=$ensaioNome }
        }
    }
    $ensaioLimite=$MaxParallel
    # Reserva uma vaga para a transicao automatica do runner de controles.
    if(('L2_5_10_off' -notin $ensaioAtivos) -and ('L2_5_10_off' -notin $ensaioCompletos)) { $ensaioLimite-- }
    foreach($ensaioNome in $ensaioOrdem) {
        if($ensaioAtivos.Count -ge $ensaioLimite) { break }
        if(($ensaioNome -in $ensaioAtivos) -or ($ensaioNome -in $ensaioCompletos) -or $ensaioLancados.ContainsKey($ensaioNome)) { continue }
        $ensaioMemoria=Get-CimInstance Win32_OperatingSystem
        if($ensaioMemoria.FreeVirtualMemory -lt 2500000) { break }
        if((Get-PSDrive -Name C).Free -lt 4GB) { throw 'Menos de 4 GB livres: revisar armazenamento antes de novo ensaio.' }
        if(Test-Path -LiteralPath (Join-Path $PSScriptRoot "$ensaioNome.raw")) { throw "RAW parcial preexistente preservado: $ensaioNome" }
        $ensaioProc=Start-Process -FilePath $ensaioExe -ArgumentList '-b',"$ensaioNome.cir" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
        $ensaioLancados[$ensaioNome]=$ensaioProc
        $ensaioAtivos+=$ensaioNome
        Write-Output "Iniciado: $ensaioNome (PID $($ensaioProc.Id))"
    }
    Start-Sleep -Seconds 10
}
Write-Output 'Todos os lotes terminaram; iniciando auditoria dos RAWs.'
& $ensaioPython -u (Join-Path $PSScriptRoot 'analisar_etapa18.py')
if($LASTEXITCODE -ne 0) { throw 'Analise completa falhou.' }
& $ensaioPython -u (Join-Path $PSScriptRoot 'verificar_entrega.py')
if($LASTEXITCODE -ne 0) { throw 'Verificacao da entrega falhou.' }
Write-Output 'Analise e verificacao completas.'
