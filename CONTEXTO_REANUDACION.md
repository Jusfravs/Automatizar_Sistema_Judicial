# Contexto de reanudación

Última actualización: 9 de agosto de 2026, America/Guayaquil.

Leer este documento antes de modificar o reanudar el lote.

## 1. Estado general

El parche transaccional de navegación, extracción y regreso al buscador está
implementado. La suite completa quedó en **71 pruebas aprobadas**, `py_compile`
correcto y `git diff --check` limpio.

No hay un proceso de `main.py`/Playwright activo ni una ventana de Excel activa al
guardar este contexto.

No se realizó commit. El worktree contiene cambios deliberados y datos del usuario;
no usar `git reset`, `checkout` destructivo ni sobrescribir archivos sin inventario.

## 2. Decisiones vigentes

1. No eliminar el freno `REGRESO_AL_BUSCADOR_NO_CONFIRMADO`. Es una barrera de
   seguridad que impide iniciar otra causa desde una pantalla no confirmada.
2. AutoCaptcha está **PAUSADO**. Existe el plan
   `PLAN_IMPLEMENTACION_API_AUTOCAPTCHA.md`, pero no hay solucionador implementado
   ni llamadas externas activas.
3. La reanudación masiva requiere una decisión explícita después de revisar el punto
   de parada y reconciliar estados.
4. Los manifiestos y respaldos existentes no deben borrarse.

## 3. Correcciones implementadas

### 3.1. Varias carpetas internas

- Se permite `MOVIMIENTOS_LISTOS -> ABRIENDO_INFORMACION_PROCESO`.
- Los pilotos reales de 1, 2 y 3 carpetas terminaron completos.
- Extracción y navegación tienen estados separados.
- El retorno al buscador es acotado, auditable y confirmado por DOM visible.

### 3.2. Resultados múltiples después de BUSCAR

El portal puede mostrar varias filas para el mismo número base, por ejemplo:

```text
12331201700065G
12331201700065
```

La regla implementada es seleccionar solo la fila cuyo `.numero-proceso` sea
numérico y coincida exactamente con la causa. Se excluyen sufijos o prefijos
alfanuméricos, números más largos y coincidencias por subcadena.

La estructura Angular real está cubierta:

```text
section.causas .cuerpo .causa-individual
  -> .numero-proceso
  -> enlace de movimientos dentro de la misma fila
```

El flujo transaccional ya no busca iconos globales: abre exclusivamente el enlace
de la fila seleccionada. Si dos filas contienen el mismo número exacto, se detiene
como ambiguo en vez de escoger arbitrariamente.

### 3.3. Retorno desde `/causas`

`/causas` es un origen de recuperación válido. Desde allí se usa el control lateral
directo `routerlink="/busqueda-filtros"`. El respaldo `go_back()` permanece limitado
a `/movimientos`.

## 4. Evidencia operativa más reciente

La ejecución más reciente alcanzó la causa **51/355**:

```text
23331-2023-00119
```

A las 18:14:29 del 9 de agosto, la página/contexto del navegador fue cerrado durante
la espera del CAPTCHA. Playwright produjo `TargetClosedError`; el retorno no podía
confirmarse porque la página ya no existía, y el freno detuvo el lote. Esto no es el
defecto anterior de selección de fila.

Antes de ese cierre se registraron `CAPTCHA_TIMEOUT` en las causas
`23331-2022-04257`, `23331-2022-04262` y `23331-2022-04264`. Los intervalos largos
del log coinciden con una ejecución dejada en espera o un equipo suspendido; deben
auditarse antes de considerarlos fallos permanentes.

El log terminó en:

```text
Exportando informe final reestructurado a: data/REPORTE_PROCESADO_FINAL.xlsx
```

No aparece una confirmación posterior de cierre de esa exportación. Verificar el
archivo antes de asumir que la exportación final concluyó.

## 5. Estado SQLite al guardar este contexto

```text
ERROR:      307
PENDIENTE: 3406
PROCESADO:   30
```

Estados relevantes:

| Causa | SQLite |
|---|---|
| `12331-2017-00065` | `PROCESADO` |
| `12331-2014-0845` | `ERROR` |
| `12331-2016-1181` | `ERROR` |
| `12203-2015-00393` | `ERROR` |
| `12331-2017-00026` | `PROCESADO` |
| `23331-2023-00119` | `ERROR` |

Que `12331-2017-00065` esté `PROCESADO` confirma que la selección de la fila numérica
funcionó en una ejecución real.

## 6. Lista de fallidos actual

`data/casos_fallidos.txt` contiene:

```text
12331-2017-00065
12331-2014-0845
12331-2016-1181
12203-2015-00393
12331-2017-00026
```

Existe una discrepancia: `12331-2017-00065` y `12331-2017-00026` están como
`PROCESADO` en SQLite. No editar la lista a ciegas; reconciliarla contra SQLite y el
resultado durable más reciente antes de reanudar.

## 7. Respaldos y archivos que deben preservarse

Respaldo verificado anterior a los pilotos:

```text
data/backups/recuperacion_20260807_120637/
```

El archivo rastreado
`data/REPORTE JUICIOS PARA REVISIÓN JULIO_RESPALDO_EMERGENCIA.xlsx` aparece
modificado. Tratarlo como cambio propio del usuario/ejecución y no revertirlo.

Cambios de código/documentación pendientes sin commit:

- `config.json`
- `main.py`
- `src/motor_busqueda_web.py`
- `tests/test_navegacion_esatje.py`
- `tests/test_regreso_buscador.py`
- `PLAN_SOLUCION_REGRESO_BUSCADOR_NO_CONFIRMADO.md`
- `PLAN_IMPLEMENTACION_API_AUTOCAPTCHA.md`
- `data/backups/`

## 8. Orden seguro para retomar

1. Revisar este documento y `git status --short`.
2. Crear un nuevo respaldo con timestamp del CSV, Excel final, SQLite y fallidos.
3. Verificar si `REPORTE_PROCESADO_FINAL.xlsx` terminó de exportarse correctamente.
4. Reconciliar `casos_fallidos.txt` con SQLite y resultados durables.
5. Auditar las causas con `CAPTCHA_TIMEOUT` y `23331-2023-00119`.
6. Ejecutar `python -m pytest -q`; el punto de referencia es `71 passed`.
7. Usar `--solo <causa>` para cualquier recuperación o piloto.
8. Autorizar por separado cualquier reanudación masiva.
9. Mantener AutoCaptcha pausado hasta una decisión explícita.
