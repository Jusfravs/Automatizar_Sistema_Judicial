# Configuraci??n de AutoCaptcha (2Captcha)

La integraci??n usa la API JSON v2 de 2Captcha y resuelve el reCAPTCHA v2 del
formulario de b??squeda e-SATJE. La credencial nunca se guarda en `config.json`,
logs, evidencia HTML, SQLite ni control de versiones.

## Activaci??n segura

En la misma terminal de PowerShell desde la que se ejecutar?? el bot:

```powershell
$env:AUTOCAPTCHA_API_KEY = Read-Host "API key de 2Captcha"
& '.\.venv\Scripts\python.exe' -u 'main.py' --solo '12331-2014-0845'
```

`Read-Host` evita dejar la clave escrita dentro del comando. La variable vive solo
durante esa sesi??n de PowerShell. No se carga `.env` autom??ticamente.

## Comportamiento

1. Se identifica una ??nica sitekey y el callback p??blico usado por `ngx-recaptcha2`.
2. Se valida la disponibilidad del proveedor una vez por ejecuci??n.
3. Se crea una tarea `RecaptchaV2TaskProxyless`.
4. El resultado se sondea cada cinco segundos, con timeout total de dos minutos.
5. El token se entrega al callback Angular y se confirma que `BUSCAR` se habilite.
6. El bot espera diez segundos completos.
7. Se vuelven a validar causa, token y bot??n antes del ??nico clic.

La configuraci??n inicial es `api_con_fallback_manual`: los fallos recuperables
vuelven a la resoluci??n manual visible. Errores de credencial, saldo, circuito
abierto o presupuesto agotado no se ocultan como fallback.

## L??mites y rollback

- M??ximo dos tareas pagadas por causa, incluyendo reintentos.
- Tres fallos consecutivos abren el circuito y evitan seguir consumiendo saldo.
- F5/TSPD queda fuera de esta integraci??n.
- Un rechazo se reporta como incorrecto solo si el widget vaci?? su respuesta.
- Para desactivar todas las llamadas, cambie `captcha.modo` a `manual`.

## Evidencia

Los fallos de b??squeda se guardan bajo:

```text
data/temp_htmls/<causa>/<intento>/busqueda_XX/
```

El contenido de `g-recaptcha-response` se redacta antes de guardar el HTML.
