param([int]$Slot=0,[int]$Slots=2,[string]$Manifest='lotes.json')
$ErrorActionPreference='Stop'
$ensaioDir=$PSScriptRoot
$ensaioLista=Get-Content -LiteralPath (Join-Path $ensaioDir $Manifest) -Raw | ConvertFrom-Json
$ensaioIndice=0
foreach($ensaioNome in $ensaioLista) {
    if(($ensaioIndice % $Slots) -eq $Slot) {
        $ensaioProc=Start-Process -FilePath 'C:\Users\joaqu\AppData\Local\Programs\ADI\LTspice\LTspice.exe' -ArgumentList '-b',"$ensaioNome.cir" -WorkingDirectory $ensaioDir -WindowStyle Hidden -PassThru
        $ensaioProc.WaitForExit()
        $ensaioLog=Get-Content -LiteralPath (Join-Path $ensaioDir "$ensaioNome.log") -Raw
        if($ensaioLog -notmatch 'Measurement: pico_orcamento') { throw "Simulacao incompleta: $ensaioNome" }
        Write-Output "Concluido: $ensaioNome"
    }
    $ensaioIndice++
}
Write-Output "Lote $Slot concluido."
