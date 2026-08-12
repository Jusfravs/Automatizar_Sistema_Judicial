# Manual de uso — Sistema de Casos Judiciales e-SATJE

Última actualización operativa: 11 de agosto de 2026.

Este manual explica cómo preparar, verificar, iniciar, supervisar y recuperar el sistema desde Windows PowerShell. Está pensado para el operador que ejecuta consultas individuales, lotes controlados o procesamiento masivo con AutoCaptcha mediante 2Captcha.

## 1. Qué hace el sistema

El sistema:

- Lee las causas desde el archivo configurado en `config.json`.
- Abre un navegador Chromium visible mediante Playwright.
- Consulta el portal e-SATJE.
- Resuelve reCAPTCHA v2 mediante 2Captcha o permite resolución manual según la configuración.
- Extrae y clasifica las actuaciones procesales.
- Guarda estados y resultados en SQLite, CSV y Excel.
- Conserva evidencias HTML, JSON y capturas para diagnóstico.
- Puede continuar después de errores sin volver a procesar los casos terminales cuando se usa `--lote`.

## 2. Reglas importantes antes de comenzar

1. Ejecute siempre los comandos desde:

   ```text
   C:\Users\HP\OneDrive\Desktop\Casos Judiciales
   ```

2. Use siempre el Python del entorno virtual:

   ```text
   .\.venv\Scripts\python.exe
   ```

   No es necesario activar el entorno virtual.

3. No abra `data/REPORTE_PROCESADO_FINAL.xlsx` ni `data/reporte_trabajo.csv` en Excel mientras el bot esté trabajando. Excel puede bloquear el guardado.

4. No ejecute dos instancias de `main.py` al mismo tiempo. Ambas usarían la misma base, los mismos reportes y el mismo saldo de CAPTCHA.

5. Nunca escriba la API key dentro de `config.json`, archivos `.md`, capturas, mensajes o comandos visibles.

6. No elimine ni reemplace `estado_casos.db` para intentar resolver un error. Esa base contiene el estado durable de la cola.

7. Para una validación nueva, empiece con `--solo`; después use `--lote 2` o `--lote 3`.

## 3. Inicio rápido para uso diario

Abra Windows PowerShell y ejecute:

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
Test-Path -LiteralPath '.\.venv\Scripts\python.exe'
```

El segundo comando debe mostrar:

```text
True
```

Cargue la clave de 2Captcha de forma oculta:

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
```

Compruebe únicamente que la variable existe, sin mostrar su contenido:

```powershell
[bool]$env:AUTOCAPTCHA_API_KEY
```

Debe responder `True`.

Para procesar las siguientes tres causas pendientes:

```powershell
& '.\.venv\Scripts\python.exe' -u 'main.py' --lote 3
```

La API key permanece disponible solamente en esa ventana de PowerShell. Si abre otra ventana o cierra la actual, deberá cargarla nuevamente.

## 4. Instalación inicial o reconstrucción del entorno

Esta sección se utiliza en un equipo nuevo o si la carpeta `.venv` no existe.

### 4.1 Verificar Python

```powershell
py --version
```

Se requiere Python 3.10 o superior.

### 4.2 Crear el entorno virtual

Desde la raíz del proyecto:

```powershell
py -3 -m venv .venv
```

### 4.3 Instalar las dependencias

```powershell
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r 'requirements.txt'
```

### 4.4 Instalar Chromium para Playwright

```powershell
& '.\.venv\Scripts\python.exe' -m playwright install chromium
```

La integración actual usa directamente la API JSON v2 de 2Captcha. No necesita ejecutar `pip install 2captcha-python`.

### 4.5 Inicializar o verificar SQLite

En el primer uso o después de una actualización del esquema:

```powershell
& '.\.venv\Scripts\python.exe' -u 'migracion_db.py'
```

Este comando crea un respaldo de `estado_casos.db`, verifica las tablas e índices y devuelve registros huérfanos de `EN_PROCESO` a `PENDIENTE`.

## 5. Verificaciones antes de una ejecución

### 5.1 Verificar Python y dependencias principales

```powershell
& '.\.venv\Scripts\python.exe' --version
& '.\.venv\Scripts\python.exe' -c "import playwright, pandas, openpyxl, bs4, lxml; print('DEPENDENCIAS_OK')"
```

Resultado esperado:

```text
DEPENDENCIAS_OK
```

### 5.2 Verificar que `config.json` sea válido

```powershell
& '.\.venv\Scripts\python.exe' -c "import json; json.load(open('config.json', encoding='utf-8')); print('CONFIG_OK')"
```

### 5.3 Compilar el código sin ejecutar el portal

```powershell
& '.\.venv\Scripts\python.exe' -m compileall -q 'main.py' 'src'
if ($LASTEXITCODE -eq 0) { 'COMPILACION_OK' }
```

### 5.4 Ejecutar todas las pruebas automáticas

```powershell
& '.\.venv\Scripts\python.exe' -m unittest discover -v
```

La línea final debe ser:

```text
OK
```

La referencia actual es 88 pruebas. El número puede aumentar cuando se agreguen nuevas pruebas. Algunas pruebas simulan fallos y pueden imprimir advertencias o trazas intencionales; la validación definitiva es que el proceso termine con `OK` y sin `FAILED` ni `ERRORS`.

### 5.5 Pruebas específicas

AutoCaptcha y red:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest -v tests.test_servicio_captcha
```

Navegación e-SATJE:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest -v tests.test_navegacion_esatje
```

Freno y persistencia transaccional:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest -v tests.test_freno_transaccional
```

Retorno al buscador y modos `--solo` / `--lote`:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest -v tests.test_regreso_buscador
```

Base SQLite:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest -v tests.test_migracion
```

### 5.6 Verificar conectividad HTTPS con 2Captcha

Esta prueba no usa la API key y no consume saldo:

```powershell
(Invoke-WebRequest -Uri 'https://api.2captcha.com' -Method Get -UseBasicParsing -TimeoutSec 15).StatusCode
```

Resultado esperado:

```text
200
```

### 5.7 Verificar la cuenta de 2Captcha sin crear una tarea

Primero cargue la API key. Después ejecute:

```powershell
@'
import os
from src.servicio_captcha import Proveedor2Captcha

proveedor = Proveedor2Captcha(
    os.environ.get("AUTOCAPTCHA_API_KEY"),
    {
        "http_timeout_ms": 10000,
        "max_intentos_red": 3,
        "reintento_red_ms": 1000,
        "saldo_minimo_usd": 0.01,
    },
)
print(proveedor.comprobar_disponibilidad())
'@ | & '.\.venv\Scripts\python.exe' -
```

Esta consulta solo valida la credencial y muestra el saldo. No crea ni cobra una tarea CAPTCHA.

## 6. Modos de ejecución

| Objetivo | Comando | Comportamiento |
|---|---|---|
| Una causa exacta | `main.py --solo <causa>` | Procesa únicamente esa causa. También sirve para reintentar un estado `ERROR`. |
| Lote controlado | `main.py --lote <2..5>` | Toma las siguientes causas con estado `PENDIENTE` en SQLite. |
| Producción completa | `main.py` | Procesa el conjunto devuelto por los filtros y el reporte de trabajo. Úselo solo después de validar lotes pequeños. |
| Continuar desde una causa | `main.py <causa>` | Procesa desde esa causa hacia adelante; no significa “solo una causa”. |

### 6.1 Procesar una causa

```powershell
& '.\.venv\Scripts\python.exe' -u 'main.py' --solo '12331-2025-00604'
```

Use este modo para:

- Hacer una prueba real controlada.
- Reintentar una causa marcada como `ERROR`.
- Verificar una corrección sin avanzar toda la cola.

### 6.2 Procesar un lote de 2 a 5

```powershell
& '.\.venv\Scripts\python.exe' -u 'main.py' --lote 3
```

Valores permitidos: 2, 3, 4 o 5.

El modo `--lote` excluye causas que SQLite ya registra como `PROCESADO`, `PARCIAL`, `SIN_RESULTADOS`, `ERROR` u otro estado terminal. Solo elige pendientes. Para reintentar un `ERROR`, use `--solo`.

### 6.3 Producción completa

```powershell
& '.\.venv\Scripts\python.exe' -u 'main.py'
```

Antes de usar este modo:

- Ejecute toda la suite de pruebas.
- Complete al menos un `--solo` correctamente.
- Complete un lote de 2 o 3 correctamente.
- Compruebe saldo suficiente en 2Captcha.
- Cierre Excel.
- Verifique espacio libre en disco.
- Confirme que no exista otra instancia del bot.

### 6.4 Continuar desde una causa hacia adelante

```powershell
& '.\.venv\Scripts\python.exe' -u 'main.py' '23331-2022-04261'
```

Advertencia: este modo no se limita a una causa. La causa indicada funciona como punto de inicio del conjunto restante.

## 7. Cómo funciona el AutoCaptcha

La configuración se encuentra en la sección `captcha` de `config.json`.

Flujo normal:

1. El bot detecta el widget reCAPTCHA v2 y su sitekey.
2. Consulta el saldo y valida la API key una vez por ejecución.
3. Crea una tarea `RecaptchaV2TaskProxyless`.
4. Consulta el resultado cada cinco segundos durante un máximo de cinco minutos.
5. Informa cada treinta segundos cuando la tarea todavía sigue `processing`.
6. Entrega el token al callback de Angular.
7. Confirma que el botón `BUSCAR` quede habilitado.
8. Espera diez segundos y vuelve a validar antes de hacer un único clic.

Protecciones activas:

- Máximo de dos tareas pagadas por causa.
- Tres fallos consecutivos abren el circuito.
- Los tokens y la API key se redactan en logs y evidencias.
- `getBalance` y `getTaskResult` reintentan errores transitorios de red.
- `createTask` no se repite automáticamente después de una respuesta ambigua, evitando posibles cobros duplicados.
- La configuración activa es `api_supervisada`: no detiene un lote esperando intervención manual.

Modos de CAPTCHA:

- `manual`: no llama al proveedor; el operador resuelve el CAPTCHA visible.
- `api_con_fallback_manual`: usa 2Captcha y, si un error recuperable persiste, espera resolución manual.
- `api_supervisada`: usa la API y registra el error si no puede resolver; no espera fallback manual.

Para desactivar temporalmente las llamadas pagadas, cambie `captcha.modo` a `manual`. Haga cambios en `config.json` solamente con el bot detenido.

## 8. Qué observar durante la ejecución

Mensajes normales de AutoCaptcha:

```text
[CAPTCHA] Proveedor 2Captcha disponible; credencial validada.
[CAPTCHA] Tarea <id> creada; espera maxima del proveedor: 300s.
[CAPTCHA] Tarea <id> sigue processing...
[CAPTCHA] Token entregado a Angular...
[CAPTCHA] Solución confirmada...
```

Ante una interrupción transitoria puede aparecer:

```text
[CAPTCHA] Fallo transitorio en getBalance; reintento 2/3...
```

Eso no es un fallo final si después aparece la confirmación del proveedor.

Resultado satisfactorio de una causa:

```text
[+] Juicio <número> completado y persistido.
```

Resultado final satisfactorio de un piloto:

```text
[OK] PROCESO COMPLETADO. 1 de 1 causas procesadas con éxito.
```

El resumen de SQLite puede contener errores históricos:

```text
{'ERROR': 332, 'PENDIENTE': 3395, 'PROCESADO': 16}
```

Ese total no significa que la última ejecución haya fallado. Para el resultado de la ejecución actual, revise la línea `PROCESO COMPLETADO` y las causas listadas al final.

## 9. Monitoreo en otra ventana de PowerShell

Abra una segunda ventana y ejecute:

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
Get-Content -LiteralPath '.\ejecucion_produccion.log' -Tail 80 -Wait
```

Presione `Ctrl+C` en esa segunda ventana para dejar de seguir el log. Esto no detiene el bot que se ejecuta en la primera ventana.

## 10. Consultar el estado del sistema

### 10.1 Estadísticas de SQLite

```powershell
& '.\.venv\Scripts\python.exe' -c "from src.gestor_cola import GestorCola; print(GestorCola(ruta_db='estado_casos.db').obtener_estadisticas())"
```

Estados habituales:

- `PENDIENTE`: todavía no procesado.
- `EN_PROCESO`: reservado por una ejecución activa.
- `PROCESADO`: extracción completa y persistida.
- `PARCIAL`: se guardó información útil, pero no quedó completa.
- `SIN_RESULTADOS`: el portal no devolvió una causa coincidente.
- `ERROR`: requiere revisión o reintento explícito.

### 10.2 Casos fallidos registrados

```powershell
if (Test-Path -LiteralPath '.\data\casos_fallidos.txt') {
    Get-Content -LiteralPath '.\data\casos_fallidos.txt'
}
```

### 10.3 Últimas líneas del log

```powershell
Get-Content -LiteralPath '.\ejecucion_produccion.log' -Tail 100
```

## 11. Archivos importantes

| Archivo o carpeta | Función |
|---|---|
| `config.json` | Rutas, filtros, tiempos y configuración del CAPTCHA. |
| `estado_casos.db` | Estado durable de la cola y resultados transaccionales. |
| `ejecucion_produccion.log` | Registro detallado de todas las ejecuciones. |
| `data/reporte_trabajo.csv` | Reporte de trabajo y continuidad. |
| `data/REPORTE_PROCESADO_FINAL.xlsx` | Informe Excel exportado. |
| `data/casos_fallidos.txt` | Lista operativa de fallos de la ejecución. |
| `data/temp_htmls/<causa>/` | HTML, API JSON, capturas, diagnósticos y manifiestos por intento. |
| `requirements.txt` | Dependencias Python. |
| `tests/` | Suite de pruebas. |

No modifique manualmente archivos dentro de `data/temp_htmls` durante una ejecución.

## 12. Detener y reanudar de forma segura

Para detener el proceso:

1. Vaya a la ventana donde está ejecutándose el bot.
2. Presione `Ctrl+C` una sola vez.
3. Espere a que aparezcan los mensajes de guardado y exportación.
4. No cierre la ventana durante `Finalizando: guardando y exportando informe`.

En el siguiente inicio, el sistema recupera registros que hayan quedado en `EN_PROCESO` y los devuelve a `PENDIENTE`.

Si Windows o el equipo se apagó abruptamente, ejecute antes de continuar:

```powershell
& '.\.venv\Scripts\python.exe' -u 'migracion_db.py'
```

## 13. Copias de seguridad

Antes de una actualización importante, con el bot detenido:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
Copy-Item -LiteralPath '.\estado_casos.db' -Destination ".\estado_casos.db.manual_$stamp"
Copy-Item -LiteralPath '.\data\reporte_trabajo.csv' -Destination ".\data\reporte_trabajo.csv.manual_$stamp"
```

`migracion_db.py` también genera automáticamente un respaldo fechado de SQLite antes de verificar el esquema.

No use `scripts/reset_db.py` como una operación normal. Puede cambiar estados masivamente y debe reservarse para mantenimiento técnico previamente revisado.

## 14. Solución de problemas frecuentes

### PowerShell no reconoce `.\.venv\Scripts\python.exe`

Causa probable: la terminal no está situada en el proyecto o no existe el entorno virtual.

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
Test-Path -LiteralPath '.\.venv\Scripts\python.exe'
```

Si responde `False`, reconstruya el entorno siguiendo la sección 4.

### La variable de AutoCaptcha responde `False`

La clave no está cargada en esa ventana. Repita el bloque seguro de la sección 3.

No muestre la clave con:

```powershell
$env:AUTOCAPTCHA_API_KEY
```

### `CAPTCHA_RED_ERROR` o `WinError 10054`

Es una interrupción de comunicación, no necesariamente una clave inválida. El cliente reintenta automáticamente las consultas seguras hasta tres veces.

Compruebe:

```powershell
(Invoke-WebRequest -Uri 'https://api.2captcha.com' -Method Get -UseBasicParsing -TimeoutSec 15).StatusCode
```

Si no responde 200:

- Revise la conexión a Internet.
- Desactive temporalmente VPN o proxy solo si las políticas del equipo lo permiten.
- Revise antivirus o firewall.
- Espere unos minutos y reintente con `--solo`.

### `ERROR_KEY_DOES_NOT_EXIST`

La API key es incorrecta, fue revocada o contiene espacios. Genere una nueva clave en el proveedor y cárguela de nuevo. No la guarde en el proyecto.

### `ERROR_ZERO_BALANCE` o saldo insuficiente

Recargue saldo en 2Captcha. El sistema exige como mínimo el valor configurado en `saldo_minimo_usd`.

### `CAPTCHA_TIMEOUT: BUSCAR no quedó habilitado`

La configuración activa no entra en fallback manual. Si 2Captcha no entrega una solución en cinco minutos, la causa se registra como error y el lote puede continuar.

Si 2Captcha confirmó una solución antes del timeout, conserve el bloque del log desde `Inicio de resolución` hasta el error.

Si el operador cambia el modo a `api_con_fallback_manual`, después del timeout del proveedor comenzará una espera manual adicional.

Para reintentar la causa, use `--solo` después de que termine el lote.

### Timeout esperando `/actuaciones`

La versión actual ya no depende del evento global `load`; valida la ruta, la causa, los controles de la pantalla y la ausencia de cargadores. Si el error vuelve a aparecer, comparta el log completo y la carpeta de evidencia de ese intento.

### Página vacía en `/busqueda-filtros`

El sistema detecta cuando Angular no monta el formulario y realiza una sola recarga controlada. Si la recuperación falla, cierre el navegador, confirme Internet y reintente con `--solo`.

### Chromium no inicia

Ejecute:

```powershell
& '.\.venv\Scripts\python.exe' -m playwright install chromium
```

También confirme que ningún antivirus esté bloqueando el Chromium administrado por Playwright.

### Error al guardar Excel o CSV

Cierre Excel y cualquier programa que tenga abiertos:

- `data/REPORTE_PROCESADO_FINAL.xlsx`
- `data/reporte_trabajo.csv`

Después reintente la causa. No elimine SQLite.

### Advertencia de límite de 32.767 caracteres en Excel

Excel limita el tamaño de una celda. El informe Excel puede truncar textos excepcionalmente extensos; las evidencias JSON/HTML y el resultado durable conservan la información usada por el sistema.

### Una causa permanece en `ERROR`

Reinténtela explícitamente:

```powershell
& '.\.venv\Scripts\python.exe' -u 'main.py' --solo '<NUMERO-DE-CAUSA>'
```

No use `--lote` para reintentar errores, porque ese modo selecciona únicamente estados pendientes.

## 15. Información que debe conservarse al reportar un error

Comparta:

- Número de causa.
- Comando exacto utilizado, sin la API key.
- Bloque del log desde el inicio de la causa hasta el traceback.
- Línea final `PROCESO COMPLETADO` o lista de fallidos.
- Ruta de la evidencia dentro de `data/temp_htmls/<causa>/`.
- Captura del navegador si ayuda a identificar la pantalla.

Nunca comparta:

- API key de 2Captcha.
- Tokens `g-recaptcha-response`.
- Cookies o encabezados de autorización.
- Datos judiciales completos fuera de los canales autorizados.

## 16. Cerrar la sesión de trabajo

Cuando termine y el bot ya no esté ejecutándose, elimine la API key de la sesión:

```powershell
Remove-Item Env:AUTOCAPTCHA_API_KEY -ErrorAction SilentlyContinue
[bool]$env:AUTOCAPTCHA_API_KEY
```

El último comando debe mostrar `False`.

Cierre PowerShell únicamente después de confirmar que el reporte final terminó de guardarse.

## 17. Lista de verificación operativa

Antes de iniciar:

- [ ] Estoy en la carpeta correcta.
- [ ] `.venv\Scripts\python.exe` existe.
- [ ] Excel está cerrado.
- [ ] No hay otra instancia del bot.
- [ ] Las pruebas terminan en `OK`.
- [ ] La conectividad con 2Captcha responde 200.
- [ ] La API key está cargada y la comprobación booleana devuelve `True`.
- [ ] Hay saldo suficiente.
- [ ] Comenzaré con `--solo` o un lote pequeño.

Después de terminar:

- [ ] La línea final indica cuántas causas tuvieron éxito.
- [ ] Revisé las estadísticas SQLite.
- [ ] Revisé `data/casos_fallidos.txt`.
- [ ] El CSV y el Excel se guardaron.
- [ ] No quedó una segunda instancia activa.
- [ ] Eliminé la API key si finalizó la jornada.
