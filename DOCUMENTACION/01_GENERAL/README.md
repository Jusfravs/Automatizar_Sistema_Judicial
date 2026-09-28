# Automatización del Sistema Judicial e-SATJE

Proyecto Python para consultar causas en e-SATJE, extraer actuaciones, calcular
la fase procesal y producir CSV y Excel. El punto de entrada operativo es
main.py. La referencia de comandos vigente es el Manual de uso; esta página
solo describe la estructura.

## Flujo

~~~text
Reporte de origen -> GestorCasos -> causas filtradas
                                -> SQLite (secuencial) o PostgreSQL (trabajadores)
                                -> BotJudicial y motor procesal
                                -> CSV y Excel por un único escritor
~~~

SQLite sigue siendo el motor de config.json, config_quito.json y
config_santo_domingo.json. PostgreSQL 18.6 está instalado y migrado, pero los
pilotos reales de navegador y concurrencia siguen pendientes. Las
configuraciones aisladas de los pilotos locales están en
outputs/postgres_pilotos_20260925/ y apuntan a casos_judiciales_test.

## Componentes

| Archivo | Función |
|---|---|
| main.py | Selección de causas y entrada a la ruta SQLite o PostgreSQL. |
| src/gestor_casos.py | Lectura del reporte y exportación CSV/Excel. |
| src/gestor_cola.py | Cola secuencial SQLite. |
| src/repositorio_postgres.py | Cola y resultados PostgreSQL. |
| src/coordinador_concurrente.py | Trabajadores y exportador único. |
| src/procesador_caso.py | Una causa por trabajador y sesión Playwright. |
| src/motor_busqueda_web.py | Navegación y extracción e-SATJE. |
| src/agente_extractor.py | Inferencia procesal determinista. |
| src/servicio_captcha.py | Cliente 2Captcha. |

## Empezar y verificar

Siga el [Manual de uso](MANUAL_DE_USO.md) para cargar claves en la consola
correcta, elegir perfil y ejecutar un piloto visible. Para PostgreSQL consulte
también la [Guía de PostgreSQL y pgAdmin](../03_BASE_DE_DATOS/GUIA_PGADMIN_POSTGRES.md).
No copie comandos de planes o avances antiguos sin contrastarlos con el manual.

La suite usa unittest. Desde la raíz del proyecto:

~~~powershell
python -m unittest discover -s tests -q
~~~

La corrida del 24 de septiembre de 2026 terminó con 290 pruebas y 4
omitidas. Las 4 pruebas de integración PostgreSQL se ejecutaron aparte sobre
casos_judiciales_test. Son resultados fechados, no una garantía de la próxima
corrida.

## Documentación relacionada

- [Contexto de reanudación](CONTEXTO_REANUDACION.md)
- [Configuración de AutoCaptcha](../02_MODULOS_Y_CONFIGURACION/CONFIGURACION_AUTOCAPTCHA.md)
- [Índice completo](../INDICE.md)
