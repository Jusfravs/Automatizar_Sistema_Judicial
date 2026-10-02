# Migración de la base judicial a Supabase Free

## Estado y alcance

La migración conserva una copia íntegra de las 560.664 filas originales. Los
campos voluminosos de `expedientes`, `resultados_ejecucion`, `actuaciones` y
`actuaciones_procesales` se guardan en archivos gzip dentro del bucket privado
`judicial-historico`. PostgreSQL conserva las columnas operativas, las relaciones,
los índices y una referencia verificable al archivo original.

El archivo local se encuentra en
`%LOCALAPPDATA%\SistemaJudicial\supabase_historico_20261002`. Su manifiesto
registra SHA-256, tamaño y filas de cada uno de los 65 objetos. Una copia de
seguridad PostgreSQL anterior a la migración está en
`%LOCALAPPDATA%\SistemaJudicial\backups`.

## Ejecutar

1. Instalar dependencias: `python -m pip install -r requirements.txt`.
2. En el panel de Supabase del proyecto `kwofqyuyzqooepjiuiae`, obtener la
   contraseña de Database y una **Secret API key** de API Keys. También se
   admite la clave heredada `service_role`. No pegarlas
   en el chat, en `config_consola.json` ni en Git.
3. Abrir PowerShell en la raíz del proyecto y ejecutar:

   ```powershell
   python scripts/migrar_supabase_gratis.py
   ```

   El programa pedirá ambas credenciales sin mostrarlas. Primero sube y
   verifica los 65 objetos; después crea las tablas e importa las filas.
   También acepta `--solo-subir` y `--solo-importar` para reanudar por etapas.
4. Al terminar, comprobar el mensaje `Migración confirmada y filas verificadas`.
   El programa cambia únicamente `base_de_datos` en el `config_consola.json`
   común y guarda las claves en el Administrador de credenciales de Windows
   del usuario actual. La configuración previa se copia a
   `%LOCALAPPDATA%\SistemaJudicial\backups\config_consola_pre_supabase.json`.
5. Abrir el sistema normalmente con `python consola.py`.

La conexión usa el pooler de sesión de Supabase con TLS `verify-full` y el
certificado CA local en `%LOCALAPPDATA%\SistemaJudicial\supabase-prod-ca-2021.crt`.
Si ese archivo falta, se debe descargar desde **Database > SSL Configuration**
en el panel de Supabase antes de importar.

## Límites operativos

La lectura de resultados históricos y la auditoría de IA reconstruyen sus
datos originales desde Storage y verifican SHA-256. Para ello el proceso debe
correr bajo el mismo usuario de Windows que ejecutó la migración, o recibir
`SUPABASE_DB_PASSWORD` y `SUPABASE_SECRET_KEY` como variables de entorno.
Las consultas SQL directas sobre los cuatro campos compactados muestran sus
valores compactos; el historial íntegro permanece en el bucket privado.

El plan gratuito tiene límites de capacidad. Vigilar el crecimiento de
PostgreSQL y Storage antes de ejecutar nuevos lotes grandes. La migración
inicial se aborta antes de confirmar si la base se aproxima a 500 MB.
