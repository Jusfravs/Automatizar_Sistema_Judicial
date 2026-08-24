# Manual de uso — Sistema de Casos Judiciales e-SATJE

Última actualización operativa: 17 de agosto de 2026.

Este manual explica cómo preparar, verificar, iniciar, supervisar y recuperar el sistema desde Windows PowerShell. Está pensado para el operador que ejecuta consultas individuales, lotes controlados o procesamiento masivo con AutoCaptcha mediante 2Captcha.

## 1. Qué hace el sistema

El sistema:

- Lee las causas desde el archivo regional seleccionado: `config.json`, `config_santo_domingo.json` o `config_quito.json`.
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

3. No abra en Excel el archivo CSV ni el Excel final definidos por la configuración regional mientras el bot esté trabajando. Excel puede bloquear el guardado.

4. No ejecute dos instancias de `main.py` al mismo tiempo. Ambas usarían la misma base, los mismos reportes y el mismo saldo de CAPTCHA.

5. Nunca escriba la API key dentro de `config.json`, archivos `.md`, capturas, mensajes o comandos visibles.

6. No elimine ni reemplace `estado_casos.db` para intentar resolver un error. Esa base contiene el estado durable de la cola.

7. Para una validación nueva, empiece con una causa individual; después avance a lotes de 2, 5 y 10. Use el modo masivo solamente cuando esos pilotos terminen correctamente.

## 3. Inicio rápido para uso diario

Abra Windows PowerShell y prepare las variables de operación:

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
$python = '.\.venv\Scripts\python.exe'
$operador = 'C:\Users\HP\.codex\skills\rpa-esatje-operacion\scripts\rpa_esatje_operacion.py'
$proyecto = (Get-Location).Path
$config = 'config_quito.json'
Test-Path -LiteralPath $python
Test-Path -LiteralPath $operador
```

Los dos últimos comandos deben mostrar:

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

Antes de abrir el navegador, compruebe el entorno y consulte la cola regional:

```powershell
& $python $operador --proyecto $proyecto --config $config doctor
& $python $operador --proyecto $proyecto --config $config estado --limite 10
```

Para planificar y después procesar las siguientes tres causas pendientes:

```powershell
& $python $operador --proyecto $proyecto --config $config lote 3
& $python $operador --proyecto $proyecto --config $config lote 3 --ejecutar
```

El primer comando solo muestra el plan. El segundo abre el navegador, puede consumir CAPTCHA y modifica SQLite, CSV y Excel.

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

En el primer uso de la configuración principal o después de una actualización de su esquema:

```powershell
& '.\.venv\Scripts\python.exe' -u 'migracion_db.py'
```

Este comando trabaja exclusivamente con `estado_casos.db`, la base principal. No lo use para Quito o Santo Domingo: en esas regiones consulte primero `estado` y permita que el siguiente inicio controlado de `main.py` recupere los registros huérfanos.

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

### 5.2 Verificar que la configuración regional sea válida

```powershell
Get-Content -Raw -Encoding UTF8 -LiteralPath $config | ConvertFrom-Json | Out-Null
if ($?) { 'CONFIG_OK' }
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

La referencia al 17 de agosto de 2026 es 159 pruebas. El número puede aumentar cuando se agreguen nuevas pruebas. Algunas pruebas simulan fallos y pueden imprimir advertencias o trazas intencionales; la validación definitiva es que el proceso termine con `OK` y sin `FAILED` ni `ERRORS`.

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

## 6. Comandos de operación, lotes y revisión masiva

La forma recomendada de operar el RPA es mediante `rpa_esatje_operacion.py`. Esta interfaz valida rutas, configuración, credencial y concurrencia antes de invocar `main.py`.

### 6.1 Seleccionar la región

Defina estas variables una vez por cada ventana de PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\HP\OneDrive\Desktop\Casos Judiciales'
$python = '.\.venv\Scripts\python.exe'
$operador = 'C:\Users\HP\.codex\skills\rpa-esatje-operacion\scripts\rpa_esatje_operacion.py'
$proyecto = (Get-Location).Path
```

Ejecute solamente una de estas líneas para seleccionar la configuración:

```powershell
$config = 'config_quito.json'           # Quito
$config = 'config_santo_domingo.json'   # Santo Domingo
$config = 'config.json'                 # Configuración principal/general
```

Cada configuración utiliza su propio Excel, CSV, SQLite y archivo de fallidos. No cambie de `$config` a mitad de una ejecución.

### 6.2 Diagnóstico y estado antes de ejecutar

```powershell
& $python $operador --proyecto $proyecto --config $config doctor
& $python $operador --proyecto $proyecto --config $config estado --limite 10
```

`doctor` debe confirmar las rutas, el portal, la credencial y que no existe otra instancia de `main.py`. `estado` muestra los totales `PENDIENTE`, `PROCESADO`, `PARCIAL`, `SIN_RESULTADOS`, `ERROR`, posibles `EN_PROCESO` y los últimos eventos.

Para ver hasta 100 eventos recientes:

```powershell
& $python $operador --proyecto $proyecto --config $config estado --limite 100
```

### 6.3 Planificar sin abrir el navegador

Los comandos `solo`, `lote` y `pendientes` no ejecutan nada si se omite `--ejecutar`. Utilice primero ese modo para revisar el comando que se lanzará:

```powershell
& $python $operador --proyecto $proyecto --config $config solo '17230-2016-17734'
& $python $operador --proyecto $proyecto --config $config lote 5
& $python $operador --proyecto $proyecto --config $config pendientes
```

El resultado debe comenzar con `PLAN_SEGURO (no ejecutado)`.

### 6.4 Procesar una causa exacta

```powershell
& $python $operador --proyecto $proyecto --config $config solo '17230-2016-17734' --ejecutar
```

Use `solo` para:

- Realizar el primer piloto de una región.
- Reintentar una causa marcada como `ERROR`.
- Verificar una corrección sin avanzar la cola.
- Revisar un caso especial ya identificado.

Una causa en `ERROR` no será elegida por `lote` ni por `pendientes`; debe reintentarse expresamente con `solo`.

### 6.5 Ejecutar lotes de distintas magnitudes

`lote` admite cualquier entero entre 2 y 100, incluidos ambos límites. Toma únicamente las siguientes causas con estado `PENDIENTE` en el SQLite de la configuración seleccionada. Los lotes mayores a 10 se ejecutan internamente en bloques de 10: al finalizar cada bloque se guarda CSV, SQLite y Excel, se cierra el navegador y se abre una sesión nueva para el siguiente bloque.

Lote mínimo de 2:

```powershell
& $python $operador --proyecto $proyecto --config $config lote 2 --ejecutar
```

Lote pequeño de 3:

```powershell
& $python $operador --proyecto $proyecto --config $config lote 3 --ejecutar
```

Lote de validación de 5:

```powershell
& $python $operador --proyecto $proyecto --config $config lote 5 --ejecutar
```

Lote máximo controlado de 10:

```powershell
& $python $operador --proyecto $proyecto --config $config lote 10 --ejecutar
```

Para revisar 20, 50 o 100 causas en bloques controlados, use un único `--lote <cantidad>`; el sistema separa internamente la ejecución en bloques de 10. No inicie varias ventanas en paralelo.

Secuencia recomendada:

```text
1 causa individual → lote 2 o 3 → lote 5 → lote 10 → todos los pendientes
```

Si aparece `REGRESO_AL_BUSCADOR_NO_CONFIRMADO`, considere detenido el lote y no lance el siguiente bloque hasta revisar el evento.

### 6.6 Revisión masiva de todos los pendientes

Este modo procesa todas las causas que el SQLite regional conserve como `PENDIENTE`. Primero muestre el plan:

```powershell
& $python $operador --proyecto $proyecto --config $config pendientes
```

La ejecución masiva requiere dos confirmaciones explícitas:

```powershell
& $python $operador --proyecto $proyecto --config $config pendientes --ejecutar --confirmar-masivo
```

Antes de usarla:

- Complete correctamente una causa individual y lotes de 5 y 10.
- Ejecute `doctor` y `estado` con el JSON regional correcto.
- Confirme el número de pendientes que se procesará.
- Cierre el CSV y el Excel regionales.
- Compruebe saldo suficiente para los CAPTCHA pendientes.
- Verifique conexión estable, energía y espacio en disco.
- Mantenga una sola instancia del RPA.
- Abra una segunda ventana únicamente para seguir el log.

`pendientes` no reprocesa estados `PROCESADO`, `PARCIAL`, `SIN_RESULTADOS` o `ERROR`. Tampoco vacía la región ni reinicia resultados anteriores.

### 6.7 Revisión total desde cero

“Procesar todos los pendientes” y “volver a procesar toda una región desde cero” son operaciones distintas. Para empezar de cero se deben respaldar y regenerar coordinadamente SQLite, CSV y Excel de esa región. No elimine la base ni use `scripts/reset_db.py` manualmente.

La preparación total debe realizarse con el script regional revisado —por ejemplo, `scripts/preparar_quito.py` para Quito— y solo después de confirmar que sus rutas apuntan exclusivamente a la región deseada. Luego se valida con `doctor`, `estado`, una causa individual y lotes crecientes antes del modo masivo.

### 6.8 Ejecutar las pruebas antes de una revisión amplia

```powershell
& $python $operador --proyecto $proyecto --config $config pruebas
```

Las pruebas no abren el portal ni consumen CAPTCHA. Deben terminar en `OK`.

### 6.9 Comandos directos de `main.py`

La interfaz operativa anterior es la opción recomendada. Para mantenimiento técnico, los equivalentes directos son:

```powershell
& $python -u 'main.py' --config $config --solo '17230-2016-17734'
& $python -u 'main.py' --config $config --lote 5
& $python -u 'main.py' --config $config --pendientes
```

No use `main.py` sin modo ni utilice una causa como argumento de inicio para una operación diaria: esas formas pueden ampliar el conjunto a procesar y omiten las confirmaciones protectoras de la interfaz operativa.

## 7. Cómo funciona el AutoCaptcha

La configuración se encuentra en la sección `captcha` del JSON regional seleccionado.

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
& $python $operador --proyecto $proyecto --config $config estado --limite 10
```

Este comando obtiene automáticamente el SQLite correcto desde `$config`; así se evita consultar por accidente la base de otra región.

Estados habituales:

- `PENDIENTE`: todavía no procesado.
- `EN_PROCESO`: reservado por una ejecución activa.
- `PROCESADO`: extracción completa y persistida.
- `PARCIAL`: se guardó información útil, pero no quedó completa.
- `SIN_RESULTADOS`: el portal no devolvió una causa coincidente.
- `ERROR`: requiere revisión o reintento explícito.

### 10.2 Casos fallidos registrados

```powershell
$rutasFallidos = @{
    'config.json' = '.\data\casos_fallidos.txt'
    'config_santo_domingo.json' = '.\data\santo_domingo\casos_fallidos_lstodomingo.txt'
    'config_quito.json' = '.\data\quito\casos_fallidos_quito.txt'
}
$archivoFallidos = $rutasFallidos[$config]
if (Test-Path -LiteralPath $archivoFallidos) { Get-Content -LiteralPath $archivoFallidos }
```

### 10.3 Últimas líneas del log

```powershell
Get-Content -LiteralPath '.\ejecucion_produccion.log' -Tail 100
```

## 11. Archivos importantes

| Archivo o carpeta | Función |
|---|---|
| `config.json` | Rutas, filtros, tiempos y configuración del CAPTCHA. |
| `config_santo_domingo.json` | Configuración y rutas aisladas de Santo Domingo. |
| `config_quito.json` | Configuración y rutas aisladas de Quito. |
| `estado_casos.db` | Estado durable de la cola y resultados transaccionales. |
| `data/santo_domingo/estado_casos_lstodomingo.db` | Estado durable de Santo Domingo. |
| `data/quito/estado_casos_quito.db` | Estado durable de Quito. |
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

Si Windows o el equipo se apagó abruptamente, no elimine ni edite SQLite. Compruebe primero la configuración regional y el estado:

```powershell
& $python $operador --proyecto $proyecto --config $config doctor
& $python $operador --proyecto $proyecto --config $config estado --limite 20
```

Si no existe otra instancia de `main.py`, el siguiente `solo`, `lote` o `pendientes` recuperará de forma controlada los registros huérfanos. `migracion_db.py` se reserva para mantenimiento de la base principal `estado_casos.db`.

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
& $python $operador --proyecto $proyecto --config $config solo '<NUMERO-DE-CAUSA>' --ejecutar
```

No use `lote` ni `pendientes` para reintentar errores, porque esos modos seleccionan únicamente estados pendientes.

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
- [ ] Seleccioné el `$config` de la región correcta.
- [ ] Excel está cerrado.
- [ ] No hay otra instancia del bot.
- [ ] Las pruebas terminan en `OK`.
- [ ] La conectividad con 2Captcha responde 200.
- [ ] La API key está cargada y la comprobación booleana devuelve `True`.
- [ ] Hay saldo suficiente.
- [ ] Ejecuté `doctor` y revisé `estado`.
- [ ] Comenzaré con `solo` o un lote pequeño.
- [ ] Si usaré `pendientes`, confirmé expresamente el alcance masivo.

Después de terminar:

- [ ] La línea final indica cuántas causas tuvieron éxito.
- [ ] Revisé las estadísticas SQLite.
- [ ] Revisé `data/casos_fallidos.txt`.
- [ ] El CSV y el Excel se guardaron.
- [ ] No quedó una segunda instancia activa.
- [ ] Eliminé la API key si finalizó la jornada.
