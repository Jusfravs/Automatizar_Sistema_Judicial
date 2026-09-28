---
goal: Preparar PostgreSQL y procesamiento concurrente para el Sistema Judicial
version: 1.0
date_created: 2026-09-22
last_updated: 2026-09-25
owner: Justin / Proyecto Sistema Judicial
status: In progress
tags: [postgresql, concurrencia, playwright, migracion, infraestructura]
---

# PostgreSQL y procesamiento concurrente

## Objetivo

Preparar el sistema para procesar casos en paralelo mediante PostgreSQL sin
alterar el motor determinista, las palabras clave ni el arbol procesal. SQLite
seguira siendo el motor predeterminado para ejecucion secuencial hasta que el
servidor PostgreSQL haya sido instalado, migrado y validado.

## Decisiones confirmadas

- PostgreSQL sera obligatorio solamente cuando `trabajadores > 1`.
- El piloto comenzara con dos trabajadores locales y navegadores visibles.
- El maximo configurable inicial sera cuatro trabajadores.
- Cada trabajador tendra su propio proceso, navegador y conexion PostgreSQL.
- Solo el coordinador escribira CSV y Excel, cada diez resultados y al cerrar.
- Una falla de PostgreSQL abortara el modo paralelo sin cambiar a SQLite.
- Se migraran General, Quito y Santo Domingo de forma idempotente.
- Se conservaran todas las versiones importadas y la fotografia vigente sera
  la de `actualizado_en` mas reciente.
- La IA permanecera desactivada durante el desarrollo y los pilotos.
- La inferencia actual y sus reglas no forman parte de este cambio.

## Fases

1. **Completada.** Desacoplar el procesamiento individual de la persistencia y la exportacion.
2. **Completada.** Definir una interfaz de cola con adaptadores SQLite y PostgreSQL.
3. **Completada.** Crear migraciones SQL versionadas, leases, heartbeat y auditoria.
4. **Completada en codigo.** Incorporar coordinador multiproceso para Windows y Playwright sincronico.
5. **Completada.** Migrar las bases existentes despues de instalar PostgreSQL.
6. **Pilotos funcionales completados y objetivo medido en corridas emparejadas.** Los lotes de 1, 10 y 50 causas terminaron; la comparacion de diez causas alcanzo una mejora de rendimiento de 64,4%. Falta la revision juridica de una clasificacion historica y la decision de activacion de los perfiles normales.

## Contratos principales

El repositorio de cola debe permitir crear una ejecucion, poblar trabajos,
reservar con exclusion mutua, renovar el lease, completar o fallar un trabajo,
recuperar leases vencidos, consultar estadisticas y recuperar resultados para
exportacion.

Estados de trabajo:

```text
PENDIENTE -> EN_PROCESO
EN_PROCESO -> PROCESADO | PARCIAL | SIN_RESULTADOS
EN_PROCESO -> EXCLUIDO_NO_CORRESPONDE | REVISION
EN_PROCESO -> ERROR_REINTENTABLE -> PENDIENTE
ERROR_REINTENTABLE -> ERROR_FINAL al agotar tres intentos
EN_PROCESO con lease vencido -> PENDIENTE
```

El lease durara 120 segundos y se renovara cada 30 segundos. Los reintentos
esperaran 1, 5 y 15 minutos.

## Migracion esperada

La inspeccion de solo lectura realizada el 22 de septiembre de 2026 encontro:

- 2.339 filas de cola entre las tres bases.
- 2.301 resultados historicos.
- 1.954 causas unicas.
- 122 causas compartidas entre General y Quito.
- 263 causas compartidas entre General y Santo Domingo.

La migracion preservara cada version y elegira el resultado mas reciente. En
empates se aplicara la prioridad General, Quito y Santo Domingo. Las bases
SQLite no se eliminaran ni modificaran.

### Resultado aplicado el 23 de septiembre de 2026

- 1.954 expedientes unicos conservados.
- 2.301 versiones historicas en `resultados_ejecucion`.
- 172.625 actuaciones en la fotografia vigente de los expedientes.
- 418 eventos de auditoria importados.
- 0 JSON invalidos.
- 0 causas duplicadas y 0 hashes duplicados.
- La segunda ejecucion completa inserto 0 registros en las tres fuentes.
- La prueba real de lease recupero el trabajo vencido y lo reservo de nuevo
  con intento 2; la ejecucion temporal se elimino de la base de pruebas.

## Criterios de aceptacion

- Las 291 pruebas actuales aprueban; cuatro pruebas PostgreSQL se omiten en la
  corrida ordinaria y las cuatro aprueban al activarlas contra
  `casos_judiciales_test`.
- Dos trabajadores nunca reservan la misma causa.
- Un trabajador interrumpido libera su trabajo al vencer el lease.
- Los reportes se regeneran por un unico escritor cada diez resultados y al
  finalizar.
- El modo paralelo no abre navegadores si PostgreSQL no responde.
- La migracion es idempotente y conserva los conteos indicados.
- El piloto paralelo mejora al menos 50% el rendimiento sin aumentar errores
  ni cambiar resultados de inferencia.

## Estado de activacion

PostgreSQL 18.6 esta instalado en `localhost:5432`, restringido a conexiones
locales y registrado en pgAdmin. Existen `casos_judiciales` y
`casos_judiciales_test`; la aplicacion usa el rol de privilegios minimos
`judicial_app` y la credencial se lee desde variables de entorno locales.

Los perfiles normales permanecen en SQLite y con la concurrencia desactivada.
Un perfil aislado en `outputs/excel_final_20260925/` ejecuto 50 causas reales
contra `casos_judiciales` y genero un Excel nuevo sin modificar `config.json`.

### Pilotos del 25 de septiembre de 2026

Los perfiles aislados en `outputs/postgres_pilotos_20260925/` usaron
`casos_judiciales_test`, navegadores visibles y la auditoria de IA desactivada:

| Perfil | Trabajadores | Resultado | Duracion |
| --- | ---: | --- | ---: |
| `solo` | 1 | 1/1 PROCESADO, sin errores | 42 s |
| `lote10` | 2 | 10/10 PROCESADO, 5 por trabajador, sin errores | 209 s |
| `lote50` | 2 | 50/50 PROCESADO, 25 por trabajador, sin errores | 644 s |
| `benchmark10_un_trabajador` | 1 | 10/10 PROCESADO, sin errores | 269 s |

Los 61 trabajos terminaron al primer intento y generaron CSV y Excel. La
comparacion con la fotografia historica encontro 57 clasificaciones iguales y
4 diferentes; estas diferencias requieren revision de evidencia y no prueban
por si solas una regresion de PostgreSQL.

El benchmark `benchmark10_un_trabajador` usa las mismas diez causas de
`lote10`. Su primera ejecucion (`e4a2c390-b6a8-4e63-b743-c1877f19882b`)
se cancelo tras errores `ARTEFACTOS_ERROR:[WinError 206]` al escribir rutas
largas y se excluye de la medicion. Se acorto el nombre de carpeta en disco,
conservando la clave completa en `result.json`. La nueva ejecucion
(`b3c46317-1196-48df-83ec-22042a3f723a`) termino con 10/10 resultados,
un intento por causa, CSV de 10 filas, Excel y cero fallidos. Los 13 campos de
fase, etapa y fechas comparados coincidieron en las diez causas entre uno y dos
trabajadores. Dos trabajadores redujeron el tiempo 22,3% y aumentaron el
rendimiento en causas por segundo 28,7%. El criterio de mejora de 50% no se
cumplio en esa primera comparacion.

Diagnostico de solo lectura: la suma de duraciones de las diez causas fue
264,9 s con un trabajador y 397,1 s con dos. Las diez soluciones de 2Captcha
sumaron 118,9 s y 245,3 s, respectivamente; la diferencia de espera del
proveedor (126,4 s) explica casi toda la diferencia de tiempo por causa
(132,2 s). Las corridas ocurrieron en horarios distintos, por lo que esta
observacion no prueba que la concurrencia cause la mayor latencia del CAPTCHA.
La siguiente medicion debe emparejar corridas cercanas en el tiempo y conservar
las mismas causas antes de atribuir el cuello de botella a PostgreSQL,
Playwright o 2Captcha.

### Comparacion emparejada posterior

El 25 de septiembre se repitieron las mismas diez causas en corridas
consecutivas: `7755f5be-1dc8-48cc-97ec-132782eb5ff2` con un trabajador
termino 10/10 en 291 s; `38b411f9-0728-4715-9414-6da33d60f572` con dos
termino 10/10 en 177 s, cinco por trabajador. Todas las causas terminaron al
primer intento, sin errores de cola ni CAPTCHA. Ambos CSV tienen diez filas,
los Excel las hojas `Reporte` y `PARA CARGA`, y la lista de fallidos esta vacia.
Coincidieron las diez causas y los 13 campos de fase, etapa y fechas comparados.

Dos trabajadores redujeron el tiempo 39,2% y aumentaron el rendimiento en
causas por segundo **64,4%**: el criterio de mejora de 50% se cumplio en esta
muestra emparejada. Las diez soluciones de 2Captcha sumaron 129,1 s en la
corrida individual y 156,7 s en la paralela. El resultado anterior de 28,7%
permanece como evidencia de variabilidad; una sola pareja de corridas no
garantiza esa mejora en todos los horarios o lotes.

Las cuatro diferencias frente a la fotografia historica se revisaron sin
escrituras: una causa historica no tenia actuaciones ni fase; dos incorporaron
5 y 13 actuaciones y avanzaron bajo las reglas actuales. En la cuarta, las
61 actuaciones antiguas mas una nueva se clasifican en sentencia con el motor
actual; al recalcular solo las 61 antiguas el resultado tambien es sentencia,
aunque la fotografia anterior guardaba embargo. Esto identifica una
clasificacion historica diferente, no una discrepancia entre uno y dos
trabajadores. La correccion juridica de esa fase queda pendiente de revision
de evidencia por una persona competente.
