# Manual de uso — Sistema de Casos Judiciales e-SATJE

Actualizado: 27 de agosto de 2026. Esta es la guía operativa vigente para este
equipo. Los documentos de planes y avances conservan su contexto histórico.

## 1. Preparar PowerShell

Abra una sola ventana de PowerShell y ejecute:

```powershell
Set-Location -LiteralPath 'C:\Users\pasante.callcenter\OneDrive - ESPOIR\Escritorio\Automatizar_Sistema_Judicial'
$python = '.\.venv\Scripts\python.exe'
Test-Path -LiteralPath $python
```

El último comando debe devolver `True`. Cierre Excel antes de ejecutar el bot;
no abra dos instancias de `main.py` al mismo tiempo.

## 2. Configuraciones regionales

| Región | Configuración | Base SQLite | Reportes |
|---|---|---|---|
| Lote general activo | `config.json` | `data/estado_casos_20260827.db` | `data/reporte_trabajo_20260827.csv` y `data/REPORTE_PROCESADO_FINAL_20260827.xlsx` |
| Quito | `config_quito.json` | `data/quito/estado_casos_quito.db` | `data/quito/` |
| Santo Domingo | `config_santo_domingo.json` | `data/santo_domingo/estado_casos_lstodomingo.db` | `data/santo_domingo/` |

No mezcle una configuración con archivos de otra región. Para el trabajo vigente
use:

```powershell
$config = 'config.json'
```

Desde el 27/08/2026, `config.json` apunta al reporte `Reporte_jucios SIS 3
27082026 12.40.xlsx` (hoja `Reporte`, 2.001 causas). Trabaja de forma aislada
en `data/reporte_trabajo_20260827.csv`,
`data/REPORTE_PROCESADO_FINAL_20260827.xlsx` y
`data/estado_casos_20260827.db`; no modifica el lote anterior.

Actualmente esta configuración usa `sucursal: "TODAS"` y
`estado_judicial: "ACTIVO"`: el lote toma causas activas de cualquier sucursal
según el orden del Excel.

## 3. AutoCaptcha

La configuración vigente usa `api_con_espera_humana_limitada`: primero solicita
la resolución a 2Captcha. No hay modo manual permanente. Si la API falla, el
navegador visible solo espera hasta 30 segundos para que una persona complete
el CAPTCHA; después deja la causa en `REVISION MANUAL` y continúa el lote. La
API key no se guarda en archivos.

En la misma PowerShell desde la que ejecutará el bot, cargue la clave sin
mostrarla:

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

El último comando debe devolver `True`. No pegue la clave en `config.json`,
`.env`, documentos, logs ni chats.

## 4. Ejecutar de forma visible

Use siempre `main.py` para una ejecución supervisada: abre Chromium visible y,
ante un fallo de la API, permite una única intervención de hasta 30 segundos.

Primero ejecute un piloto de diez causas:

```powershell
& $python -u main.py --config $config --lote 10
```

Para una causa puntual:

```powershell
& $python -u main.py --config $config --solo 07331-2024-00277
```

Solo después de revisar el piloto puede procesar todos los pendientes:

```powershell
& $python -u main.py --config $config
```

No use `python -m src.orquestador` cuando pueda necesitar esa ventana visible:
ese orquestador se ejecuta en modo *headless* y la causa pasará directamente a
revisión manual si la API no la resuelve.

## 5. Supervisar y reanudar

- La consola muestra la causa actual, la resolución del CAPTCHA y los estados
  `COMPLETADO`, `PARCIAL`, `ERROR` o `EXCLUIDO_NO_CORRESPONDE`.
- El estado durable se guarda en SQLite; el CSV y Excel se actualizan durante
  la ejecución y al finalizar.
- Si el proceso se interrumpe, no borre archivos: revise primero
  `data/estado_casos_20260827.db`, `data/reporte_trabajo_20260827.csv`,
  `data/REPORTE_PROCESADO_FINAL_20260827.xlsx` y
  `data/casos_fallidos_20260827.txt`.
- Para continuar un lote detenido, vuelva a ejecutar el mismo comando. La
  cola evita reprocesar causas con estado terminal.

## 6. Reiniciar una región desde cero

Un reinicio elimina el estado de ejecución de esa región, por lo que debe
autorizarse explícitamente. Antes de hacerlo, respalde coordinadamente la base,
CSV, Excel final y lista de fallidos. El Excel de origen nunca se elimina.

El reinicio de El Oro realizado el 26 de agosto de 2026 está preservado en:

```text
backups/reinicio_el_oro_20260826_095002/
```

## 7. Validación antes de cambios o ejecución masiva

```powershell
& $python -m unittest discover -s tests -q
```

La referencia actual es `223` pruebas correctas y `3` omitidas por requerir
PostgreSQL. `pytest` no forma parte de las dependencias instaladas en este
equipo; la suite usa `unittest`.

## 7.1 Reclasificar datos ya extraídos

Cuando se corrige una regla de clasificación, actualice lo ya recolectado sin
volver a navegar SATJE. Primero haga una vista previa:

```powershell
& $python scripts/reclasificar_desde_sqlite.py --config $config
```

Para aplicarla, generar respaldos y reconstruir CSV/Excel:

```powershell
& $python scripts/reclasificar_desde_sqlite.py --config $config --aplicar
```

El proceso actualiza la fase operativa que se envía y conserva `ULTIMA FASE`
como evidencia histórica. La limpieza integrada solo borra filas idénticas en
todas sus columnas; no borra dos registros del mismo juicio si representan
carteras, usuarios o créditos distintos.

## 8. Caso de regresión importante

La causa `07333-2023-02297` debe terminar en `2.1 CITACION
(PERSONA/BOLETA)`, con fecha `10/03/2026` y etapa/fase actual `CONTESTACION`.
Un despacho deprecatorio que ordena diligencias de embargo y citación no
demuestra un embargo ejecutado. La prueba de clasificación cubre esta regla.
