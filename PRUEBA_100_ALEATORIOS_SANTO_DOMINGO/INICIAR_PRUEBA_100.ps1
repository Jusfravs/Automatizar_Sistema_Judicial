$ErrorActionPreference = "Stop"
$proyecto = "C:\Users\HP\OneDrive\Desktop\Casos Judiciales"
$config = "PRUEBA_100_ALEATORIOS_SANTO_DOMINGO\config_prueba_100_santo_domingo.json"
$python = Join-Path $proyecto ".venv\Scripts\python.exe"
$main = Join-Path $proyecto "main.py"
$skill = "C:\Users\HP\.codex\skills\rpa-esatje-operacion\scripts\rpa_esatje_operacion.py"

Set-Location -LiteralPath $proyecto

if (-not [bool]$env:AUTOCAPTCHA_API_KEY) {
    throw "AUTOCAPTCHA_API_KEY no esta cargada en esta terminal. No se inicia la prueba."
}

& $python $skill --proyecto $proyecto --config $config doctor
if ($LASTEXITCODE -ne 0) { throw "El doctor RPA fallo. No se inicia la prueba." }

for ($bloque = 1; $bloque -le 10; $bloque++) {
    Write-Host ""
    Write-Host "===== BLOQUE $bloque DE 10 (10 CAUSAS) =====" -ForegroundColor Cyan
    & $python -u $main --config $config --lote 10
    if ($LASTEXITCODE -ne 0) {
        throw "El bloque $bloque termino con codigo $LASTEXITCODE. Se detiene la secuencia."
    }
}

& $python $skill --proyecto $proyecto --config $config estado
Write-Host "Prueba finalizada. Revise PRUEBA_100_ALEATORIOS_SANTO_DOMINGO\REPORTE_RESULTADO_PRUEBA_100.xlsx" -ForegroundColor Green
