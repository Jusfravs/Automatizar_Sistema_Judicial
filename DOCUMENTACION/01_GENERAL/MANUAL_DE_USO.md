# Manual de uso — Sistema de Casos Judiciales e-SATJE

Actualizado: 25 de septiembre de 2026 (America/Guayaquil).

Esta es la referencia para ejecutar main.py en este equipo. Los planes y el manual
anterior registran decisiones históricas; sus comandos no sustituyen esta guía.

## 1. Consola y Python

Abra PowerShell y mantenga esa misma ventana durante la ejecución. Si abrió CMD,
escriba powershell -NoExit para entrar a PowerShell antes de cargar las claves.
Una variable cargada en una ventana no aparece en otra. Un archivo .cmd iniciado
desde esa PowerShell sí hereda sus variables. No abra el lanzador con doble clic.

~~~powershell
$proyecto = 'C:\Users\pasante.callcenter\OneDrive - ESPOIR\Escritorio\Automatizar_Sistema_Judicial'
Set-Location -LiteralPath $proyecto
$python = (Get-Command python).Source
& $python --version
~~~

El Python verificado en este equipo es Python 3.12. Cierre el Excel de salida
antes de ejecutar y no inicie dos lotes sobre los mismos archivos.

## 2. Configuraciones operativas

| Perfil | Configuración | Persistencia y salida |
|---|---|---|
| General | config.json | SQLite: data/estado_casos_20260827.db; CSV: data/reporte_trabajo_20260827.csv; Excel: data/REPORTE_PROCESADO_FINAL_IMPRESION_CORREGIDO_20260902.xlsx |
| Quito | config_quito.json | SQLite y reportes en data/quito/ |
| Santo Domingo | config_santo_domingo.json | SQLite y reportes en data/santo_domingo/ |

Los tres perfiles normales siguen con base_de_datos.motor = sqlite. El perfil
general toma causas con ESTADO = ACTIVO de todas las sucursales. Consulte las
rutas de la configuración antes de procesar; no combine archivos regionales.

## 3. Credenciales de la sesión

La clave de 2Captcha se lee de AUTOCAPTCHA_API_KEY. PostgreSQL lee la contraseña
de POSTGRES_PASSWORD. No se cargan desde .env. Cárguelas en la PowerShell que
iniciará el bot, sin escribir sus valores en comandos, documentos ni chats:

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
[bool]$env:POSTGRES_PASSWORD
~~~

Ambas comprobaciones deben devolver True para los pilotos PostgreSQL. Si la
segunda devuelve False, cargue POSTGRES_PASSWORD mediante el mismo método
seguro, sustituyendo el nombre de la variable. No muestre su contenido.

La política vigente intenta 2Captcha primero. Si falla, Chromium visible
permite hasta 30 segundos de intervención humana por causa. No existe un modo
manual permanente. La guía de AutoCaptcha detalla sus límites.

## 4. Ejecución secuencial con SQLite

Use estos comandos solo cuando quiera trabajar sobre el perfil normal y sus
archivos operativos. Para una causa:

~~~powershell
& $python -u main.py --config config.json --solo 07331-2024-00277 --workers 1
~~~

Para un lote acotado:

~~~powershell
& $python -u main.py --config config.json --lote 10 --workers 1
~~~

Revise primero los resultados antes de ampliar el lote. El modo --solo busca
la causa en el reporte filtrado; --lote N toma las primeras N causas de ese
reporte. No use --workers 2 con SQLite: main.py lo rechaza.

## 5. Pilotos reales de PostgreSQL del 25 de septiembre

Los pilotos usan casos_judiciales_test y reportes aislados en
outputs/postgres_pilotos_20260925/. Son tres grupos distintos: 1, 10 y 50
causas. Sus configuraciones no activan la auditoría de IA. Terminaron con
1/1, 10/10 y 50/50 causas PROCESADO, respectivamente, sin errores y con CSV
y Excel generados. Los tiempos observados fueron 42, 209 y 644 segundos.

Para repetir un piloto, confirme ambas variables de la sección 3 y ejecute
su lanzador desde la misma PowerShell. Los comandos son:

~~~powershell
Set-Location -LiteralPath 'C:\Users\pasante.callcenter\OneDrive - ESPOIR\Escritorio\Automatizar_Sistema_Judicial'
& '.\outputs\postgres_pilotos_20260925\solo\ejecutar_piloto.cmd'
& '.\outputs\postgres_pilotos_20260925\lote10\ejecutar_piloto.cmd'
& '.\outputs\postgres_pilotos_20260925\lote50\ejecutar_piloto.cmd'
~~~

Cada .cmd comprueba las claves, cambia a su propia carpeta y ejecuta main.py
con --config y --workers. Los valores son, respectivamente, --solo con un
trabajador, --lote 10 con dos y --lote 50 con dos. El archivo
ejecucion_produccion.log, el CSV, el Excel y casos_fallidos.txt quedan en la
carpeta de cada etapa. Si los archivos locales de outputs no están presentes,
prepare antes una configuración PostgreSQL aislada; no cambie config.json solo
para copiar estos ejemplos.

No repita a ciegas un piloto PostgreSQL: una nueva invocación crea otra
ejecución. Verifique primero la ejecución, los trabajos y los reportes.

La primera comparación de las mismas diez causas con un trabajador se canceló
por `ARTEFACTOS_ERROR:[WinError 206]`: la ruta de la evidencia superaba el
límite de Windows y causó reintentos de la misma causa. El código ya utiliza
un nombre corto para esa carpeta y trata ese error como no recuperable.
La repetición terminó con 10/10 PROCESADO al primer intento, CSV de 10 filas,
Excel y cero fallidos en 269 segundos. Los 13 campos de fase, etapa y fechas
comparados coincidieron con el lote de dos trabajadores. Este bajó el tiempo
de 269 a 209 segundos (22,3 %) y aumentó el rendimiento en 28,7 %; el
objetivo de 50 % del plan no se alcanzó en esa primera comparación.

Una comparación emparejada posterior procesó las mismas diez causas en
291 segundos con un trabajador y 177 segundos con dos. Las diez causas
coincidieron, todas terminaron al primer intento y los 13 campos procesales
comparados fueron iguales. Dos trabajadores aumentaron el rendimiento
64,4 % en esa muestra, superando el objetivo de 50 %. Ambos reportes tienen
diez filas, Excel completo y cero fallidos.

Las esperas de 2Captcha sumaron 118,9 s en la primera comparación individual
y 245,3 s en la paralela, realizadas a horas distintas. En la comparación
emparejada sumaron 129,1 s y 156,7 s. La variación del proveedor influye en
el tiempo total. Cada repetición crea una ejecución nueva y consume tareas
reales de CAPTCHA.

Para una medición emparejada, con las claves en la misma PowerShell y Chromium
visible, ejecute las mismas diez causas primero con uno y luego con dos
trabajadores:

~~~powershell
Set-Location -LiteralPath 'C:\Users\pasante.callcenter\OneDrive - ESPOIR\Escritorio\Automatizar_Sistema_Judicial'
& '.\outputs\postgres_pilotos_20260925\benchmark10_un_trabajador\ejecutar_piloto.cmd'
if ($LASTEXITCODE -ne 0) { throw 'Falló el benchmark de un trabajador' }
& '.\outputs\postgres_pilotos_20260925\lote10\ejecutar_piloto.cmd'
~~~

Revise el estado final de ambas ejecuciones, las diez causas, los CSV y Excel
y sus tiempos antes de comparar rendimiento. La comparación histórica dio 57
coincidencias y 4 diferencias en las 61 causas: una no tenía actuaciones
antiguas, dos incorporaron actuaciones nuevas y la cuarta ya produce la nueva
fase al recalcular su historial antiguo con el motor actual. Esa última
requiere revisión jurídica de evidencia antes de corregir una fase oficial.

### Lote real de 50 para un Excel final nuevo

El 25 de septiembre se procesaron las primeras 50 causas únicas del Excel
fuente `C:\Users\pasante.callcenter\Downloads\REPORTE PROCESADO FINAL FASES Y ETAPAS ENVÍO A SISTEMAS.xlsx`.
El perfil aislado `outputs/excel_final_20260925/config_produccion_50.json`
usa PostgreSQL `casos_judiciales`, dos trabajadores y un CSV nuevo generado
desde las 2001 filas de la hoja `Reporte`. No modifica el Excel fuente ni los
archivos operativos anteriores del perfil general.

La ejecución `1d359713-8da2-4597-a1f9-2a7b54ffba5c` terminó `COMPLETADA`:
50/50 `PROCESADO` al primer intento, 25 por trabajador, cero fallidos y 766 s.
El Excel nuevo está en
`outputs/excel_final_20260925/REPORTE_PROCESADO_FINAL_20260925.xlsx`.
Conserva 2001 filas en `Reporte` y la hoja `PARA CARGA`; solo las 50 causas
seleccionadas se actualizaron en esta corrida. Sus campos `ULTIMA FASE`,
`FASE ACTUAL` y `ETAPA ACTUAL` coinciden entre PostgreSQL, CSV y Excel.
`seleccion_50.json` guarda las 50 causas y la huella del Excel fuente. El
lanzador de este lote impide repetirlo cuando el Excel de salida ya existe.

### Continuar el Excel final con comandos directos

Se reutilizan `main.py` y el perfil
`outputs/excel_final_20260925/config_excel_final_postgres.json` para todos los
lotes de este reporte. No se necesita generar un `.cmd` ni un `.py` por lote.
Desde la carpeta del proyecto, en la PowerShell con las claves cargadas:

~~~powershell
& $python -u main.py --config outputs/excel_final_20260925/config_excel_final_postgres.json --lote 100 --omitir-procesados --workers 2
~~~

`--omitir-procesados` consulta la cola de la base PostgreSQL configurada y
omite las causas `PROCESADO` de ejecuciones `COMPLETADA`. Selecciona causas
unicas en el orden del reporte; no utiliza los historiales migrados para
marcarlas como realizadas. Esta opcion sirve para continuar el mismo CSV y
Excel que ya contienen los resultados anteriores; no debe usarse para iniciar
un reporte vacio con resultados de otras ejecuciones.

`--excluir` aparta una causa, se puede repetir y no reduce el numero de
trabajadores. La causa `07331-2025-00296` queda pendiente de revision por la
diferencia de fase historica documentada. `--workers 2` mantiene ambos
trabajadores. Para otro tamano de lote cambie `100` por una cantidad entre
2 y 100; `--solo <causa> --workers 1` sigue disponible para una causa.

La opcion `--lote N` sin `--omitir-procesados` conserva su comportamiento
anterior: toma las primeras N filas candidatas y puede repetir causas.
Antes del siguiente lote de 100 se guardaron copias del CSV y del Excel en
`outputs/excel_final_20260925/respaldo_antes_100/`.

### Corrida completa del mismo reporte

El lote de 100 del 25 de septiembre termino con 99 causas procesadas y una
en revision, en 1523 segundos, usando dos trabajadores. La causa sin resultados
es `07333-2015-00239`. El perfil reutilizable registra las exclusiones en
`filtros_activos.causas_revision_manual`: esa causa, `07331-2025-00296`
(diferencia de fase pendiente) y `13334-2023-002182` (numero pendiente de
verificacion, por indicacion del usuario). Se conservan sus filas del reporte.

Para todas las causas restantes, desde la carpeta del proyecto:

~~~powershell
& $python -u main.py --config outputs/excel_final_20260925/config_excel_final_postgres.json --pendientes --omitir-procesados --workers 2
~~~

Este modo no tiene el limite de 100 de `--lote`. Omite los procesados de
ejecuciones completas de la misma base y las revisiones configuradas; conserva
una sola consulta por causa. Reutiliza el CSV y el Excel final acumulados.
Ejecute un solo coordinador a la vez sobre estos archivos. Para consultar de
nuevo una causa apartada, revise primero su motivo y retire su entrada de
`causas_revision_manual`.

### Excel final corregido (28 de septiembre de 2026)

Después de la corrida general se regeneró el libro desde el CSV acumulado, sin
consultar otra vez el portal. El archivo vigente es
`outputs/excel_final_20260925/REPORTE_PROCESADO_FINAL_20260925_CORREGIDO.xlsx`;
el perfil `config_excel_final_postgres.json` apunta a esta ruta. Conserva 2001
filas en `Reporte` y 1951 en `PARA CARGA`. Hay 34 causas marcadas para revisión
del título de su última gestión; 33 se apartaron de `PARA CARGA` porque antes
figuraban como cargables. La causa `07331-2026-00445` muestra el título
`DEVOLUCIÓN DEPRECATORIO POR CUMPLIMIENTO DE DILIGENCIA (RAZON DE NOTIFICACION)`
y la fecha `24/09/2026`. El libro abre en Excel con ambas tablas y filtros.
Los historiales completos permanecen en el CSV; Excel limita cada celda a
32767 caracteres.

## 6. Comprobar y recuperar

Para PostgreSQL, inspeccione en pgAdmin la base casos_judiciales_test:

~~~sql
SELECT * FROM v_estado_ejecuciones ORDER BY creado_en DESC;
SELECT * FROM v_trabajadores_activos;
SELECT * FROM v_cola_trabajo WHERE estado IN ('ERROR_FINAL', 'REVISION');
~~~

Confirme cuántas causas terminaron, si queda un lease activo y si el Excel y
el CSV aislados corresponden al lote. El coordinador es el único escritor de
reportes y exporta cada diez resultados y al cerrar. Ante una interrupción,
consulte la guía de PostgreSQL antes de iniciar otra ejecución.

Para SQLite, revise el archivo de base, el CSV, el Excel y la lista de fallidos
del perfil correspondiente. La cola SQLite conserva estados terminales. No
borre bases ni sustituya reportes para intentar reanudar.

## 7. Auditoría NVIDIA NIM (separada del RPA)

config.json ya contiene este bloque de inferencia_ia:

~~~json
{
  "modo": "sombra",
  "proveedor": "nvidia",
  "modelo": "nvidia/nemotron-3-super-120b-a12b",
  "api_key_env": "NVIDIA_API_KEY"
}
~~~

El nombre de variable admitido por el cliente actual es NVIDIA_API_KEY. La clave se lee exclusivamente de
NVIDIA_API_KEY. La auditoría usa resultados judiciales ya persistidos: no abre
el portal, no resuelve CAPTCHA y no cambia la fase oficial. Los pilotos
PostgreSQL de la sección 5 no incluyen esta configuración de IA.

Cargue la clave sin mostrarla en la misma PowerShell donde ejecutará el
auditor. No la pegue en config.json, .env, logs ni chats:

~~~powershell
$secureNvidia = Read-Host 'API key de NVIDIA NIM' -AsSecureString
$ptrNvidia = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureNvidia)
try {
    $env:NVIDIA_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptrNvidia)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptrNvidia)
}
Remove-Variable secureNvidia, ptrNvidia -ErrorAction SilentlyContinue
[bool]$env:NVIDIA_API_KEY
~~~

La comprobación debe devolver True. Una clave cargada en otra ventana no
aparece en esta. Desde la raíz del proyecto, con el Python de la sección 1,
ejecute primero una muestra pequeña en SQLite:

~~~powershell
& $python -m scripts.auditar_inferencia_nvidia --config config.json --limite 2
~~~

El comando imprime un resumen JSON con vistos, auditados, revisión, omitidos,
errores y circuito_abierto. Revise las propuestas y evidencias antes de
ampliar la muestra. Las auditorías de versiones anteriores del prompt no
deben aprobarse sin la validación descrita en el
[Contrato de inferencia NVIDIA](../02_MODULOS_Y_CONFIGURACION/CONTRATO_INFERENCIA_HIBRIDA_IA.md).

Cuando exista un perfil PostgreSQL con inferencia_ia en modo sombra, el mismo
comando usa esa base si base_de_datos.motor = postgres. Los perfiles aislados
del piloto de navegación no tienen ese bloque; no son un atajo para auditar
NVIDIA. Para revisar continuamente nuevos resultados, el ejecutor admite
--seguir --limite 10 --intervalo 60 y se detiene con Ctrl+C. Use ese modo
solo después de comprobar el primer lote. El contrato enlazado explica la
revisión humana y la importación simulada de decisiones.

## 8. Verificación y mantenimiento

~~~powershell
& $python -m unittest discover -s tests -q
~~~

La corrida del 24 de septiembre terminó con 290 pruebas y 4 omitidas; las
4 pruebas de integración PostgreSQL pasaron por separado contra
casos_judiciales_test. Estos números son evidencia fechada, no un resultado
garantizado de futuras corridas. La guía de PostgreSQL incluye el comando de
integración.

Para reclasificar resultados SQLite existentes sin navegar SATJE:

~~~powershell
& $python scripts/reclasificar_desde_sqlite.py --config config.json
~~~

El modo de vista previa no aplica cambios. El argumento --aplicar sí actualiza
estado y reportes tras crear respaldos; revíselo antes de usarlo. La inferencia
procesal y las palabras clave no se cambian al activar PostgreSQL.

Caso de regresión documentado: 07333-2023-02297 debe conservar la citación
acreditada del 10/03/2026; un despacho deprecatorio que ordena diligencias no
prueba por sí mismo un embargo ejecutado.
