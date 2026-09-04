# Automatización Sistema Judicial e-SATJE

Sistema en Python para consultar causas en el portal e-SATJE, obtener sus
actuaciones, inferir la fase procesal y consolidar los resultados en CSV, Excel
y SQLite. Se usa para lotes de El Oro, Quito y Santo Domingo.

## Flujo principal

```text
Excel de origen
    -> GestorCasos (CSV de trabajo)
    -> GestorCola (SQLite y estados)
    -> BotJudicial (Playwright/API e-SATJE)
    -> MotorInferenciaProcesal
    -> CSV, Excel y eventos durables
```

`main.py` es el punto de entrada operativo. Abre el navegador de forma visible;
si la API no resuelve un CAPTCHA, concede como máximo 30 segundos para
completarlo y, si no ocurre, deja la causa en revisión manual y sigue el lote.

## Componentes

| Módulo | Responsabilidad |
|---|---|
| `main.py` | Lotes, persistencia y exportación. |
| `src/motor_busqueda_web.py` | Navegación Playwright, API e-SATJE, CAPTCHA y retorno seguro al buscador. |
| `src/agente_extractor.py` | Extracción de actuaciones e inferencia de fases procesales. |
| `src/gestor_cola.py` | Cola SQLite transaccional. |
| `src/gestor_casos.py` | Lectura del Excel y consolidación CSV/Excel. |
| `src/servicio_captcha.py` | Cliente seguro para 2Captcha. |
| `scripts/` | Utilidades de diagnóstico, migración y reproceso. |

## Configuraciones

| Región | Configuración | Fuente |
|---|---|---|
| Lote general activo | `config.json` | `C:\Users\pasante.callcenter\Downloads\Reporte_jucios SIS 3 27082026 12.40.xlsx` (hoja `Reporte`) |
| Quito | `config_quito.json` | `data/quito/Reporte_juicios_QUITO_20260817.xlsx` |
| Santo Domingo | `config_santo_domingo.json` | `data/santo_domingo/Reporte_juicios_LSTODOMINGO_20260812.xlsx` |

Cada configuración define sus rutas, filtros, tiempos de navegación y política
de CAPTCHA. Actualmente `config.json` toma causas `ACTIVO` de todas las
sucursales; no comparta SQLite ni reportes entre regiones.

## Ejecución

Desde PowerShell, siga el [Manual de uso](MANUAL_DE_USO.md). El inicio seguro es:

```powershell
& .\.venv\Scripts\python.exe -u main.py --config config.json --lote 10
```

Después de validar el piloto, `main.py --config config.json` procesa los
pendientes del lote general. `src.orquestador` es *headless*: no permite la
ventana visible de 30 segundos para contingencias de CAPTCHA.

## Pruebas

La suite usa la biblioteca estándar `unittest`:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Referencia del 27 de agosto de 2026: 223 pruebas correctas y 3 omitidas por
integración PostgreSQL no configurada.

## Documentación relacionada

- [Manual de uso](MANUAL_DE_USO.md)
- [Contexto de reanudación](CONTEXTO_REANUDACION.md)
- [Configuración AutoCaptcha](../02_MODULOS_Y_CONFIGURACION/CONFIGURACION_AUTOCAPTCHA.md)
- [Índice completo](../INDICE.md)
