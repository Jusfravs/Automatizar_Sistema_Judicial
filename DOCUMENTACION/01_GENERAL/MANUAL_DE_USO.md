# Manual de uso — Sistema de Casos Judiciales e-SATJE

Última actualización: 24 de agosto de 2026.

Este manual contiene únicamente los comandos que se usan para operar el proyecto desde Windows PowerShell. Todos se ejecutan directamente con `main.py`; no requieren herramientas internas de Codex.

## 1. Preparación de PowerShell

Abra PowerShell y sitúese en el proyecto:

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
$python = '.\.venv\Scripts\python.exe'
Test-Path -LiteralPath $python
```

El último comando debe mostrar `True`.

Si la ventana de PowerShell no tiene cargada la clave de AutoCaptcha, cárguela sin mostrarla:

```powershell
$secureKey = Read-Host 'API key de 2Captcha' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:AUTOCAPTCHA_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
Remove-Variable secureKey, ptr -ErrorAction SilentlyContinue
[bool]$env:AUTOCAPTCHA_API_KEY
```

La última línea debe mostrar `True`. No imprima nunca el contenido de la variable.

Antes de ejecutar, cierre Excel si tiene abierto el CSV o el reporte final de la región. No ejecute dos ventanas de `main.py` a la vez.

## 2. Elegir la configuración correcta

Defina una sola configuración por sesión:

| Región | Configuración | Archivo de entrada | Reporte final |
|---|---|---|---|
| El Oro (configuración principal) | `config.json` | `data/REPORTE_JUICIOS_LISTO_PARA_REVISION.xlsx` | `data/REPORTE_PROCESADO_FINAL.xlsx` |
| Quito | `config_quito.json` | `data/quito/Reporte_juicios_QUITO_20260817.xlsx` | `data/quito/REPORTE_PROCESADO_QUITO.xlsx` |
| Santo Domingo | `config_santo_domingo.json` | `data/santo_domingo/Reporte_juicios_LSTODOMINGO_20260812.xlsx` | `data/santo_domingo/REPORTE_PROCESADO_LSTODOMINGO.xlsx` |

Ejemplo para El Oro:

```powershell
$config = 'config.json'
```

El Excel universal de El Oro contiene todas las sucursales, pero `config.json` aplica el filtro vigente de El Oro. No cambie filtros, Excel ni configuración mientras un lote esté ejecutándose.

## 3. Comandos de ejecución

### Procesar los siguientes 10 pendientes

Este es el comando habitual y recomendado:

```powershell
& $python -u main.py --config $config --lote 10
```

Solo procesa causas pendientes. Omite las que SQLite ya tenga como `PROCESADO`, `ERROR`, `PARCIAL`, `SIN_RESULTADOS` o `EXCLUIDO_NO_CORRESPONDE`.

### Procesar otro tamaño de lote

`--lote` acepta de 2 a 100 causas:

```powershell
& $python -u main.py --config $config --lote 2
& $python -u main.py --config $config --lote 20
& $python -u main.py --config $config --lote 50
```

Aunque se soliciten 20, 50 o 100 causas, el sistema trabaja internamente en bloques de 10: guarda SQLite, CSV y Excel, cierra el navegador y abre una sesión nueva entre bloques.

### Procesar todos los pendientes

Este comando inicia el navegador de inmediato y procesa todos los pendientes de la región configurada. Úselo solo después de revisar pilotos y lotes de 10:

```powershell
& $python -u main.py --config $config --pendientes
```

No reinicia ni reprocesa causas ya terminales.

### Ejecutar una causa concreta

Para probar, revisar o reintentar una sola causa:

```powershell
& $python -u main.py --config $config --solo '17233-2025-09168'
```

Sustituya el número por la causa requerida. Use `--solo` para un piloto o para una causa que necesite revisión puntual; no use este modo como forma de procesar una región completa.

## 4. Qué no usar en la operación diaria

No use estos comandos sin una revisión técnica previa:

```text
python main.py
python main.py --reprocesar-filtro
python scripts/reset_db.py
python migracion_db.py
```

- Sin modo, `main.py` puede recorrer un alcance mayor al esperado.
- `--reprocesar-filtro` ignora el flujo normal de pendientes.
- `reset_db.py` borra la cola SQLite.
- `migracion_db.py` es mantenimiento de esquema, no un comando para retomar un lote.

Tampoco edite SQLite, CSV, estados o resultados mientras el bot esté abierto.

## 5. Verificación antes de un lote amplio

Compruebe que el código y sus pruebas estén correctos:

```powershell
& $python -m unittest discover -v
```

El resultado final debe contener `OK` y no `FAILED` ni `ERRORS`.

Para una prueba nueva o después de cambiar la inferencia, siga este orden:

```text
una causa con --solo → lote 2 o 5 → lote 10 → lote 20 o más → --pendientes
```

## 6. Supervisar la ejecución

En una segunda ventana de PowerShell puede seguir el log sin detener el bot:

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
Get-Content -LiteralPath '.\ejecucion_produccion.log' -Tail 80 -Wait
```

Presione `Ctrl+C` solamente en la ventana que sigue el log para detener la visualización. Para detener el bot, vaya a su ventana y presione `Ctrl+C` una vez; espere a que termine de guardar y exportar.

Al finalizar correctamente, busque una línea similar a:

```text
[OK] PROCESO COMPLETADO. 10 de 10 causas procesadas con éxito.
```

El resumen SQLite puede incluir errores históricos. Para evaluar el lote actual, use la línea final del proceso, los fallos listados y el Excel recién exportado.

## 7. Resultados y estados

Los resultados se conservan en conjunto: SQLite controla la cola, el CSV conserva continuidad y el Excel es el informe para revisión.

Estados más habituales:

- `PENDIENTE`: aún no se ha procesado.
- `PROCESADO`: extracción e inferencia guardadas.
- `PARCIAL`: se obtuvo información útil, pero incompleta.
- `ERROR`: requiere revisión o un reintento puntual con `--solo`.
- `SIN_RESULTADOS`: el portal no devolvió una causa válida.
- `EXCLUIDO_NO_CORRESPONDE`: la carátula no pertenece a Fundación Parea / Espoir o no corresponde a cobro de pagaré a la orden.

Los casos no recuperables por navegación, datos insuficientes o validación se identifican en el reporte para revisión manual; no deben hacer colapsar el resto del lote.

Archivos principales de El Oro:

| Archivo | Uso |
|---|---|
| `estado_casos.db` | Estados y resultados durables de la cola. |
| `data/reporte_trabajo.csv` | Continuidad de los datos de trabajo. |
| `data/REPORTE_PROCESADO_FINAL.xlsx` | Informe final de El Oro. |
| `data/casos_fallidos.txt` | Causas fallidas del último alcance ejecutado. |
| `data/temp_htmls/<causa>/` | Evidencia HTML, JSON y capturas de cada causa. |

Quito y Santo Domingo usan sus rutas regionales indicadas en su configuración.

## 8. PostgreSQL

`config.json` y `config_quito.json` tienen sincronización PostgreSQL configurada. Si la contraseña no está disponible en la ventana de PowerShell, el sistema seguirá con SQLite y mostrará una advertencia.

Para habilitar la sincronización en esa ventana sin revelar la contraseña en pantalla:

```powershell
$securePg = Read-Host 'Contraseña de PostgreSQL' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePg)
try {
    $env:POSTGRES_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
Remove-Variable securePg, ptr -ErrorAction SilentlyContinue
```

No imprima `$env:POSTGRES_PASSWORD`.

## 9. Errores frecuentes

### Excel o CSV bloqueado

Cierre el archivo indicado en el log y vuelva a lanzar únicamente el lote o causa pendiente. No borre SQLite.

### `REGRESO_AL_BUSCADOR_NO_CONFIRMADO`

El lote se detuvo por seguridad. Comparta el log desde el inicio de esa causa y la carpeta de evidencia; no inicie el siguiente bloque hasta revisarlo.

### `CAPTCHA_TIMEOUT` o error de AutoCaptcha

Revise conexión, saldo y que la clave esté cargada en la misma ventana de PowerShell. Cuando el sistema se estabilice, reintente solo la causa afectada:

```powershell
& $python -u main.py --config $config --solo '<NUMERO-DE-CAUSA>'
```

### Datos, fase o fecha incorrectos

No consuma otro CAPTCHA de inmediato. Comparta la causa, el resultado que aparece en Excel, el resultado correcto esperado y capturas/evidencia del portal. La corrección debe ser un parche universal, no una edición manual aislada del Excel.

## 10. Cierre de la sesión

Cuando termine y no haya ejecuciones activas:

```powershell
Remove-Item Env:AUTOCAPTCHA_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:POSTGRES_PASSWORD -ErrorAction SilentlyContinue
```

Conserve el log, SQLite, CSV y Excel de la región como una misma unidad. Si necesita reiniciar una región desde cero, solicite primero una preparación con respaldo de los cuatro elementos.
