# Plan de implementación: API de AutoCaptcha para e-SATJE

## 0. Estado, decisión y alcance

- Fecha: 7 de agosto de 2026.
- Estado: **PAUSADO por decisión operativa del 8 de agosto de 2026**; diseño listo,
  sin código del solucionador implementado ni llamadas externas activadas.
- CAPTCHA confirmado en evidencia local: Google reCAPTCHA v2, renderizado de forma
  explícita por Angular mediante `ngx-captcha`.
- Decisión de referencia: implementar primero el contrato REST v2 de 2Captcha con
  `RecaptchaV2TaskProxyless`, detrás de una interfaz desacoplada denominada
  `ProveedorCaptcha`.
- Si “AutoCaptcha” corresponde a otro proveedor, se sustituirá únicamente el
  adaptador. Antes de escribir ese adaptador deben entregarse el nombre y la
  documentación oficial del proveedor; nunca se inferirán endpoints ni formatos.
- La activación queda condicionada a que el uso esté autorizado y sea compatible
  con las condiciones aplicables al portal y al proveedor.

El alcance comprende exclusivamente el reCAPTCHA v2 del formulario de búsqueda.
No comprende eludir ni automatizar páginas F5/TSPD, bloqueos WAF, controles de
sesión, límites del portal ni desafíos distintos. Si aparece F5/TSPD, el bot debe
detener o derivar a intervención manual sin enviar esa página al proveedor.

## 1. Objetivo

Eliminar la intervención manual ordinaria en el reCAPTCHA sin debilitar los frenos
ya implementados:

1. detectar un único widget válido;
2. crear como máximo las tareas autorizadas por causa;
3. recibir un token sin exponer secretos;
4. entregar el token al callback real de Angular;
5. confirmar que el botón `BUSCAR` quedó habilitado de forma estable;
6. hacer un único clic mediante el mecanismo existente;
7. conservar fallback manual, auditoría, límites de costo y parada segura.

Obtener un token no se considerará éxito. El éxito será observable únicamente
cuando Angular acepte el token, la causa continúe intacta y `BUSCAR` quede habilitado.

## 2. Estado actual que debe preservarse

`BotJudicial` ya dispone de:

- detección del montaje del widget y de `g-recaptcha-response`;
- estado `ESPERAR_FIN_CAPTCHA`;
- espera pasiva de hasta `captcha_timeout_ms`;
- comprobación estable de causa y botón habilitado;
- bloqueo de doble clic por `(causa, intento_id)`;
- clasificación de timeout y evidencia de navegación;
- modo `--solo` para pilotos;
- retorno fiable al buscador después de cada causa.

La nueva integración se insertará entre `CAUSA_ESCRITA` y
`BUSQUEDA_HABILITADA`. No reemplazará `_enviar_busqueda_una_vez()` ni sus
invariantes.

## 3. Riesgos técnicos que gobiernan el diseño

### 3.1. Callback de Angular

Escribir el token solamente en `textarea[name="g-recaptcha-response"]` puede no
actualizar el `FormControl` de Angular. El widget se renderiza explícitamente y su
callback es el que normalmente comunica la respuesta a `ngx-captcha`.

Antes de activar llamadas pagadas se ejecutará una inspección controlada para
determinar cuál de estas rutas expone el portal:

1. callback público en `data-callback`;
2. callback entregado a `grecaptcha.render`, capturado sin cambiar su semántica;
3. callback accesible desde la instancia del componente.

No se dependerá de recorrer estructuras privadas y no documentadas de Google como
mecanismo silencioso de producción. Si no se puede identificar y ejecutar un
callback inequívoco, la integración se mantendrá en modo manual.

### 3.2. Duplicación y costo

El flujo de navegación puede reintentar una causa. Sin un presupuesto compartido,
un timeout podría crear varias tareas pagadas para el mismo widget. Cada desafío
tendrá una huella y un registro idempotente asociado a:

```text
(causa_canonica, intento_id, url, sitekey, widget_id)
```

Una huella no podrá tener dos tareas activas. El límite total por causa se aplicará
también entre reintentos externos del navegador.

### 3.3. Token efímero

El token no se reutilizará entre causas, recargas, widgets ni sesiones. Después de
recibirlo se inyectará y enviará la búsqueda inmediatamente. Si el widget se reinicia
o el token expira antes del clic, se descartará y consumirá, como máximo, otro intento
dentro del presupuesto.

### 3.4. Fallos del proveedor

Se distinguirán errores de credencial, saldo, red, rate limit, tarea insoluble,
timeout, respuesta inválida y token rechazado. Ninguno se convertirá en un clic
forzado ni en una búsqueda sin CAPTCHA confirmado.

### 3.5. Datos y secretos

Al proveedor se enviarán solo los datos mínimos del desafío: URL pública, sitekey,
tipo de tarea y, si resulta estrictamente necesario, user-agent. No se enviarán:

- número de causa;
- HTML, capturas o resultados judiciales;
- cookies de sesión;
- credenciales del portal;
- archivos locales;
- proxy, salvo una fase futura con autorización separada.

La API key y los tokens nunca aparecerán en logs, JSON de evidencia, excepciones,
SQLite ni control de versiones.

## 4. Arquitectura propuesta

### 4.1. Modelo de dominio

Crear `src/servicio_captcha.py` con objetos pequeños y comprobables:

```python
CaptchaDesafio(
    tipo="recaptcha_v2",
    website_url="...",
    sitekey="...",
    widget_id="...",
    invisible=False,
)

CaptchaSolucion(
    token="...",          # solo en memoria
    task_id="...",
    proveedor="2captcha",
    latencia_ms=0,
    costo_usd=None,
)
```

Definir el protocolo:

```python
class ProveedorCaptcha(Protocol):
    def comprobar_disponibilidad(self) -> dict: ...
    def resolver(self, desafio: CaptchaDesafio, contexto: dict) -> CaptchaSolucion: ...
    def reportar_incorrecta(self, task_id: str) -> None: ...
```

El motor recibirá el proveedor por inyección opcional en el constructor. Las pruebas
usarán un proveedor falso y no realizarán tráfico externo.

### 4.2. Adaptador inicial

Implementar `Proveedor2Captcha` con la API JSON v2:

1. `POST https://api.2captcha.com/createTask`;
2. tarea `RecaptchaV2TaskProxyless` con `websiteURL` y `websiteKey`;
3. conservar `taskId` únicamente en memoria y auditoría saneada;
4. sondear `POST https://api.2captcha.com/getTaskResult`;
5. aceptar solo `status="ready"`, `errorId=0` y un token no vacío;
6. mapear cualquier otra respuesta a una excepción tipada;
7. usar `reportIncorrect` solo cuando el portal demuestre rechazo del token.

Se usará la biblioteca estándar de Python para HTTP y JSON, con transporte
inyectable, evitando una dependencia nueva para dos operaciones POST. El cliente
tendrá timeout por petición y no repetirá automáticamente `createTask` ante una
respuesta incierta: primero deberá determinar si recibió o no un `taskId`.

### 4.3. Configuración

Añadir una sección sin secretos a `config.json`:

```json
"captcha": {
  "modo": "manual",
  "proveedor": "2captcha",
  "api_key_env": "AUTOCAPTCHA_API_KEY",
  "tipo_tarea": "recaptcha_v2_proxyless",
  "http_timeout_ms": 10000,
  "resolucion_timeout_ms": 120000,
  "sondeo_ms": 5000,
  "confirmacion_inyeccion_timeout_ms": 10000,
  "max_tareas_por_causa": 2,
  "max_errores_consecutivos": 3,
  "saldo_minimo_usd": 1.0,
  "fallback_manual": true,
  "reportar_incorrecta": true
}
```

Valores válidos de `modo`:

- `manual`: comportamiento actual, cero llamadas externas;
- `api_supervisada`: usa API y mantiene el navegador visible;
- `api_con_fallback_manual`: ante un fallo recuperable, vuelve a la espera manual;
- `api_estricta`: ante un fallo, persiste el error y detiene el lote.

El repositorio conservará `manual` como valor inicial. La API key se leerá
exclusivamente desde `AUTOCAPTCHA_API_KEY`. Se añadirán `.env` y `.env.*` a
`.gitignore`, dejando solo `.env.example` con un nombre de variable vacío. El código
no cargará `.env` automáticamente ni escribirá la clave en disco.

### 4.4. Detector del desafío

Implementar `_diagnosticar_captcha()` como operación de lectura. Debe devolver:

```python
{
    "tipo": "recaptcha_v2",
    "renderizado": True,
    "sitekeys_encontradas": 1,
    "sitekey": "<redactada en logs>",
    "widget_id": "...",
    "invisible": False,
    "callback_disponible": True,
    "token_presente": False,
    "f5_tspd_detectado": False,
}
```

La sitekey se buscará, en orden, en `data-sitekey`, parámetros públicos del widget
y el parámetro `k` del iframe `api2/anchor`. Debe existir exactamente una sitekey
coherente. Cero o varias producirán `CAPTCHA_DESCRIPTOR_INVALIDO` y no crearán tarea.
La sitekey completa podrá vivir en memoria, pero en auditoría solo se guardará una
huella SHA-256 corta.

### 4.5. Entrega del token a Angular

Implementar `_aplicar_solucion_captcha(desafio, solucion)`:

1. revalidar URL, sitekey, widget y causa antes de tocar el DOM;
2. escribir el token en todos los campos de respuesta pertenecientes al único widget;
3. despachar `input` y `change` con burbujeo;
4. invocar una sola vez el callback explícitamente capturado para ese widget;
5. no habilitar el botón alterando `disabled`, clases o atributos;
6. confirmar que `grecaptcha.getResponse(widget_id)` o la respuesta del widget no
   esté vacía cuando la API pública lo permita;
7. esperar que el botón quede visible y habilitado durante dos sondeos consecutivos;
8. confirmar que la causa escrita no cambió.

Si el callback no es inequívoco o el botón no se habilita, producir
`CAPTCHA_INYECCION_NO_CONFIRMADA`. El bot no hará clic.

### 4.6. Orquestación

Sustituir la espera directa por `_resolver_o_esperar_captcha(causa, intento_id)`:

```text
CAUSA_ESCRITA
  -> CAPTCHA_DIAGNOSTICADO
  -> CAPTCHA_TAREA_CREADA
  -> CAPTCHA_RESOLVIENDO
  -> CAPTCHA_TOKEN_RECIBIDO
  -> CAPTCHA_INYECTADO
  -> BUSQUEDA_HABILITADA
  -> BUSQUEDA_ENVIADA
```

Ramas terminales o de fallback:

```text
CAPTCHA_CONFIG_ERROR
CAPTCHA_PROVEEDOR_ERROR
CAPTCHA_SIN_SALDO
CAPTCHA_RESOLUCION_TIMEOUT
CAPTCHA_DESCRIPTOR_INVALIDO
CAPTCHA_INYECCION_NO_CONFIRMADA
CAPTCHA_TOKEN_RECHAZADO
CAPTCHA_CIRCUITO_ABIERTO
CAPTCHA_MANUAL_REQUERIDO
```

El modo manual seguirá usando `_esperar_busqueda_habilitada()`. El modo con fallback
manual entrará en esa espera solo si el navegador es visible y el fallo es
recuperable. En ejecución no supervisada, un fallback manual imposible debe detener
la causa inmediatamente.

### 4.7. Presupuesto y cortacircuito

Mantener un contexto por ejecución con:

```python
{
    "tareas_por_causa": {},
    "tareas_activas": {},
    "errores_consecutivos": 0,
    "costo_acumulado_usd": 0,
    "circuito_abierto": False,
}
```

Reglas:

- máximo dos tareas por causa, incluyendo reintentos de navegación;
- una sola tarea activa por huella;
- no reintentar `createTask` por HTTP ambiguo;
- abrir circuito después de tres errores consecutivos del proveedor;
- un éxito reinicia el contador de errores consecutivos;
- saldo insuficiente, clave inválida o circuito abierto detienen el modo estricto;
- no crear tareas anticipadas para causas futuras;
- comprobar saldo una vez al inicio, nunca exponerlo como requisito por cada causa.

### 4.8. Rechazo del token

Después del clic, distinguir el rechazo de un timeout general. Se considerará evidencia
de rechazo cuando el portal permanezca en el formulario y el widget se reinicie,
muestre error o vacíe la respuesta sin presentar resultados.

En ese caso:

1. registrar `CAPTCHA_TOKEN_RECHAZADO` sin guardar el token;
2. reportar la tarea incorrecta si está habilitado y el proveedor lo admite;
3. crear una segunda tarea solo si queda presupuesto;
4. si vuelve a fallar, fallback manual o parada según el modo.

No se reportará una solución como incorrecta ante errores de red, F5/TSPD, cambio de
sesión, fallo del botón o indisponibilidad del portal.

## 5. Auditoría y persistencia

Registrar eventos estructurados, sin secretos:

```python
{
    "causa": "<canonica>",
    "intento_id": "...",
    "modo": "api_supervisada",
    "proveedor": "2captcha",
    "task_id": "...",
    "widget_hash": "...",
    "estado": "CAPTCHA_INYECTADO",
    "latencia_ms": 18340,
    "costo_usd": 0.0,
    "tarea_numero": 1,
    "fallback_manual": False
}
```

Aplicar una función central de saneamiento que elimine campos llamados `clientKey`,
`api_key`, `token`, `gRecaptchaResponse`, cookies y cabeceras de autorización antes
de registrar respuestas o excepciones.

Ante fallo terminal, la evidencia podrá incluir diagnóstico DOM, URL y captura, pero
nunca el token, la clave ni la respuesta JSON cruda del proveedor.

## 6. Archivos previstos

- `src/servicio_captcha.py`: protocolo, modelos, cliente HTTP, adaptador 2Captcha,
  errores tipados, presupuesto y saneamiento.
- `src/motor_busqueda_web.py`: detector, callback, inyección, estados y orquestación.
- `main.py`: validación de configuración al inicio, modo visible/fallback y política
  de parada.
- `config.json`: política no secreta, inicialmente `modo="manual"`.
- `.gitignore`: exclusión de `.env` y variantes.
- `.env.example`: únicamente `AUTOCAPTCHA_API_KEY=`.
- `tests/test_servicio_captcha.py`: contrato del proveedor y fallos HTTP.
- `tests/test_navegacion_esatje.py`: integración DOM/Angular y regresión manual.
- [`README.md`](../01_GENERAL/README.md): configuración, activación, costos, rollback y diagnóstico.

No se modificará `src/agente_extractor.py`, la inferencia procesal ni la extracción
de expedientes.

## 7. Plan de pruebas

### 7.1. Cliente del proveedor

1. `createTask` exitoso conserva un único `taskId`.
2. `processing -> ready` devuelve una solución válida.
3. credencial inválida, saldo insuficiente y rate limit tienen errores distintos.
4. timeout HTTP antes y después de recibir `taskId` no duplica tareas.
5. JSON inválido o token vacío se rechaza.
6. el timeout total detiene el sondeo.
7. `reportIncorrect` solo se emite con rechazo probado.
8. ninguna traza contiene clave ni token.

### 7.2. DOM y Angular

1. extrae una sitekey única de `data-sitekey`.
2. usa `k` del iframe como respaldo y exige coherencia.
3. cero o dos sitekeys impiden crear tarea.
4. captura un callback por widget sin alterar el render normal.
5. inyecta el token e invoca el callback una vez.
6. token presente pero botón deshabilitado no se considera éxito.
7. botón habilitado con causa alterada no permite clic.
8. el token expirado o widget reiniciado se descarta.
9. una pantalla F5/TSPD nunca se envía al proveedor.

### 7.3. Flujo e idempotencia

1. modo manual conserva exactamente el comportamiento actual.
2. modo API resuelve, confirma y hace un solo clic.
3. un reintento de navegación respeta el presupuesto global de la causa.
4. dos llamadas sobre la misma huella reutilizan la tarea activa.
5. proveedor caído activa fallback manual solo cuando corresponde.
6. modo estricto detiene el lote después de persistir el error.
7. tres errores consecutivos abren el circuito.
8. una solución exitosa reinicia el contador del circuito.
9. no existe reutilización de token entre causas consecutivas.
10. `regreso_confirmado=False` conserva el freno existente.

### 7.4. Seguridad y regresión

- suite completa verde;
- `py_compile` y `git diff --check`;
- búsqueda automática de patrones de API key/token en logs y evidencias;
- ninguna prueba unitaria accede a Internet;
- el modo inicial después del merge continúa siendo manual.

## 8. Pilotos y despliegue gradual

### Fase 0. Precondiciones

1. Confirmar proveedor y documentación oficial.
2. Confirmar autorización de uso en el portal.
3. Crear credencial de saldo limitado exclusiva para este bot.
4. Definir presupuesto monetario y responsable operativo.
5. Mantener copia verificada de configuración, SQLite, CSV y Excel.

### Fase 1. Diagnóstico sin costo

Ejecutar una causa en modo visible sin llamar al proveedor. Capturar únicamente:
tipo, sitekey hash, widget id, mecanismo de callback, URL y estados del botón. La
fase termina cuando el callback de Angular sea inequívoco.

### Fase 2. Contrato del proveedor

Probar credencial, saldo y sandbox/demo oficial. Verificar creación, sondeo, timeout,
saneamiento y reporte incorrecto con transporte controlado.

### Fase 3. Piloto e-SATJE 1/1

Activar `api_supervisada` para una sola causa mediante `--solo`. Confirmar una tarea,
un token, un callback, un clic, resultado durable y retorno al buscador.

### Fase 4. Piloto secuencial

Ejecutar tres causas consecutivas y confirmar que existen tres tareas independientes,
cero reutilización de token, cero clics dobles y costo dentro del presupuesto.

### Fase 5. Lote supervisado

Ejecutar diez causas con navegador visible. Auditar tasa de solución, latencia,
rechazos, fallbacks, costo por causa y aparición de F5/TSPD.

### Fase 6. Activación

Solo después de aceptar todas las fases se podrá cambiar a
`api_con_fallback_manual` o `api_estricta`. La ejecución masiva requerirá una
autorización independiente; implementar el código no la concede.

## 9. Criterios de aceptación

1. El modo manual sigue funcionando sin API key.
2. La clave solo se obtiene de `AUTOCAPTCHA_API_KEY` y nunca se registra.
3. El portal se identifica como un único reCAPTCHA v2 antes de crear una tarea.
4. El callback real de Angular se invoca una sola vez.
5. El token por sí solo no habilita artificialmente el botón.
6. Solo se pulsa `BUSCAR` cuando causa, token y botón están confirmados.
7. Existe como máximo una tarea activa por desafío y dos por causa.
8. Los reintentos externos no evaden el presupuesto.
9. F5/TSPD queda fuera del solucionador y provoca parada o fallback explícito.
10. Los errores del proveedor quedan clasificados y persistidos sin secretos.
11. El cortacircuito detiene consumo repetitivo ante fallos sistémicos.
12. Los pilotos de 1 y 3 causas terminan durables y regresan al buscador.
13. La suite completa queda verde y el diff no contiene credenciales.
14. Volver a `modo="manual"` desactiva toda llamada externa sin revertir código.

## 10. Rollback operativo

El rollback primario será cambiar `captcha.modo` a `manual` y retirar
`AUTOCAPTCHA_API_KEY` del entorno. El cliente no debe construirse ni comprobar saldo
en modo manual. Esta reversión no afecta extracción, persistencia, retorno al buscador
ni datos ya procesados.

Si una activación produce rechazos o bloqueos del portal:

1. detener el lote;
2. abrir el circuito;
3. volver a modo manual;
4. conservar logs saneados y tareas/costos agregados;
5. no reintentar masivamente las causas afectadas hasta auditar el origen.

## 11. Orden de implementación

1. Validar proveedor, autorización, presupuesto y credencial limitada.
2. Añadir primero las pruebas del cliente y del saneamiento.
3. Implementar modelos, errores, transporte y adaptador.
4. Implementar el diagnóstico del widget sin llamadas pagadas.
5. identificar y probar el callback real de Angular.
6. implementar inyección y confirmación observable.
7. extender la máquina de estados y la auditoría.
8. integrar presupuesto, idempotencia y cortacircuito.
9. integrar fallback manual y política de parada en `main.py`.
10. documentar configuración y rollback.
11. ejecutar suite y controles de secretos.
12. realizar las fases de piloto en orden.
13. solicitar autorización separada para activar el lote.

## 12. Referencias técnicas contrastadas

- API v2 y flujo `createTask`/`getTaskResult`:
  <https://2captcha.com/api-docs/quick-start>
- Contrato de `RecaptchaV2TaskProxyless`, sitekey y token:
  <https://2captcha.com/api-docs/recaptcha-v2>
- API oficial de Google reCAPTCHA v2, callback y expiración:
  <https://developers.google.com/recaptcha/docs/display>
