# Consola para nuevos Excel

Abre `INICIAR_CONSOLA_JUDICIAL.cmd` con doble clic o ejecuta `python consola.py`.
El menú usa flechas y Enter. Elige **Elegir Excel y preparar lote** y selecciona
un `.xlsx` en el explorador de la consola. La preparación no consulta e-SATJE:
después podrás revisar conexión y escoger el tamaño de la ejecución.

## Un config para los Excel nuevos

`config_consola.json` es el único archivo editable de reglas y conexión para
los lotes nuevos. El menú guarda allí host, puerto, base, usuario y TLS; la
contraseña PostgreSQL y la clave de 2Captcha permanecen solo en la sesión.
Los perfiles regionales antiguos (`config_quito.json` y
`config_santo_domingo.json`) conservan sus reglas actuales.

Cada Excel válido produce una carpeta en `outputs/lotes/` con:

- `origen.xlsx`: copia verificada por SHA-256 del archivo seleccionado.
- `reporte_trabajo.csv` y `reporte_trabajo.csv.bak`: datos normalizados y respaldo inicial.
- `casos.txt`: causas activas únicas, en el orden de entrada.
- `casos_fallidos.txt`: vacío hasta que haya resultados fallidos.
- `manifiesto.json`: identidad, hoja, cantidades y huella del Excel; no contiene reglas ni claves.

El reporte `reporte_final.xlsx` aparece tras procesar. Si seleccionas otra vez
el mismo contenido, la consola reabre su carpeta y conserva CSV, respaldo,
fallidos y resultados. Un Excel modificado crea un lote nuevo. Los lotes de la
consola anterior se completan al reabrirlos; su `config.json` antiguo se
conserva como archivo histórico, pero las ejecuciones nuevas leen el config
común. Cambios posteriores al config común también afectan lotes existentes;
cada ejecución registra la huella de las reglas efectivas en PostgreSQL.

## PostgreSQL

La consola requiere las migraciones 001, 002 y 003. La opción **Comprobar
conexión y esquema** indica si falta la columna de auditoría de la migración
003. Para preparar una base nueva use `scripts/inicializar_postgres.py` según
la [guía PostgreSQL](../03_BASE_DE_DATOS/GUIA_PGADMIN_POSTGRES.md). No aplique
migraciones en una base operativa durante una ejecución.
También puedes elegir **Aplicar migraciones pendientes** en el menú: solicita
la contraseña administrativa solo para esa operación y no la guarda.

Para automatización siguen disponibles los subcomandos:

```powershell
python consola.py validar 'C:\ruta\nuevo.xlsx'
python consola.py preparar 'C:\ruta\nuevo.xlsx' --salida 'outputs\lotes\octubre_01'
python consola.py diagnostico 'outputs\lotes\octubre_01'
python consola.py ejecutar 'outputs\lotes\octubre_01' --lote 10 --workers 2
python consola.py errores 'outputs\lotes\octubre_01'
```

La cola PostgreSQL coordina los trabajadores de una ejecución. La consola
bloquea dos ejecuciones simultáneas del mismo lote, pero perfiles distintos
todavía pueden contener la misma causa; no los ejecutes simultáneamente sobre
causas compartidas. Los reportes de cada lote permanecen en su carpeta.
