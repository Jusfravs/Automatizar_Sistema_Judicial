# Configuración de AutoCaptcha (2Captcha)

Actualizado: 25 de septiembre de 2026.

El bot usa la API JSON v2 de 2Captcha para reCAPTCHA v2 del portal e-SATJE.
La clave se lee de AUTOCAPTCHA_API_KEY en el proceso que inicia el bot. No se
carga desde .env ni se guarda en config.json, SQLite, reportes o logs.

## Modo vigente

config.json usa api_con_espera_humana_limitada. El bot comprueba saldo, crea
una tarea proxyless, sondea el resultado e inyecta el token. Si la API falla,
Chromium visible concede hasta 30 segundos para completar el reto. Después
la causa pasa a revisión manual. No hay modo manual permanente.

## Cargar la clave

Use la misma PowerShell que ejecutará main.py o el lanzador .cmd:

~~~powershell
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
~~~

La comprobación debe devolver True. Si empezó en CMD, escriba
powershell -NoExit, cargue la clave allí y permanezca en esa PowerShell.
Un .cmd llamado desde ella hereda la variable; una consola nueva o un
doble clic no la heredarán. No pegue la clave en chats ni comandos visibles.

## Límites

- Máximo dos tareas pagadas por causa.
- Máximo tres fallos consecutivos antes de abrir el circuito.
- Saldo mínimo configurable de USD 0,01.
- El valor de espera_humana_maxima_ms es 30000; no se permite ampliarlo.
- No cambie captcha.modo a manual: ese modo está bloqueado.

Para los comandos actuales de SQLite y PostgreSQL consulte el
[Manual de uso](../01_GENERAL/MANUAL_DE_USO.md).
