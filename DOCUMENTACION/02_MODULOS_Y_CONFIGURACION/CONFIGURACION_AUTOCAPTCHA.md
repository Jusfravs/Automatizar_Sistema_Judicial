# Configuración de AutoCaptcha (2Captcha)

El proyecto usa la API JSON v2 de 2Captcha para resolver reCAPTCHA v2 del
portal e-SATJE. La credencial se obtiene solo desde la variable de entorno
`AUTOCAPTCHA_API_KEY`; no se carga automáticamente desde `.env` y nunca debe
guardarse en `config.json`, SQLite, reportes, logs o control de versiones.

## Modo vigente

La configuración principal (`config.json`) usa:

```json
"modo": "api_con_espera_humana_limitada"
```

El sistema comprueba saldo, crea una tarea proxyless, sondea su estado e inyecta
el token en el callback de Angular. No existe un modo de operación manual. Si
la API no puede resolver el reto, el navegador visible da como máximo 30
segundos para que una persona lo complete. Si no queda habilitado `BUSCAR`, la
causa se marca `REVISION MANUAL` y el lote continúa con la siguiente. Errores
de clave, saldo insuficiente o circuito abierto no consumen más tareas.

## Cargar la clave de forma segura

En la misma PowerShell de ejecución:

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

Para comprobar que está disponible sin revelar su contenido:

```powershell
[bool]$env:AUTOCAPTCHA_API_KEY
```

## Límites de seguridad

- Máximo dos tareas pagadas por causa.
- Máximo tres fallos consecutivos antes de abrir el circuito.
- Saldo mínimo configurable: USD 0,01.
- La política vigente es API primero; no cambie `captcha.modo` a `manual`, pues
  ese valor está bloqueado deliberadamente.
- `captcha.espera_humana_maxima_ms` queda fijado en `30000`; el programa no
  permite ampliarlo por encima de 30 segundos.

Ejecute `main.py` en modo visible: solo así alguien puede aprovechar esa breve
ventana de contingencia. El orquestador *headless* no es adecuado para ello.
