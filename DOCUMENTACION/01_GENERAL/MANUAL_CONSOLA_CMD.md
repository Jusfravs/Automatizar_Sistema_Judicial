# Manual de uso de la consola CMD

Este manual explica el uso diario del menú interactivo del Sistema Judicial en Windows. Para trabajar con un Excel nuevo, abre la consola, elige el archivo, revisa el lote preparado y decide cuándo iniciar el procesamiento. Preparar el lote **no abre e-SATJE ni procesa causas**.

## 1. Abrir y recorrer el menú

1. Abre `INICIAR_CONSOLA_JUDICIAL.cmd` con doble clic desde la carpeta del proyecto.
2. Usa **↑** y **↓** para moverte, **Enter** para abrir una opción y **Esc** o **0** para volver. En una terminal sin lectura interactiva de teclas, escribe el número de la opción y pulsa **Enter**.
3. El encabezado del menú muestra el lote activo y el servidor PostgreSQL configurado. Elige **Salir** cuando termines.

La ventana que abre el archivo `.cmd` queda en pausa al salir para que puedas leer cualquier mensaje final. Si Windows indica que no encuentra `python` o falta un módulo, la instalación de Python o de las dependencias del proyecto todavía no está lista; consulta el [manual general](MANUAL_DE_USO.md).

## 2. Preparar un Excel nuevo

1. Entra en **Elegir Excel y preparar lote**.
2. Navega por las carpetas de la consola. Empieza en `Descargas`; puedes entrar en una carpeta, subir con **.. Carpeta anterior** o elegir **Pegar ruta de un Excel**.
3. Selecciona un archivo `.xlsx`. La pantalla mostrará las filas, las causas únicas, las filas activas y la carpeta de destino.
4. Elige **Crear lote y seleccionarlo**. Cuando aparezca **Lote preparado**, ese lote queda activo en el menú.

Si primero quieres comprobar el archivo sin crear un lote, usa **Validar Excel**. Acepta las mismas formas de selección y solo muestra el resultado de la validación.

### Formato mínimo del Excel

La hoja debe contener `CODIGO_JUICIO`, `NUMERO_JUICIO`, `SUCURSAL` y `ESTADO`. La consola reconoce variantes como «Número de juicio», «Número de causa» y «Código de juicio»; también admite `ESTADO.1` cuando Excel duplicó ese encabezado. Busca la hoja `Reporte` o `migrado` y, si no existen, examina las demás hojas. Reconoce encabezados en las filas 1, 2 o 6.

Los campos obligatorios no pueden estar vacíos y `CODIGO_JUICIO` no puede repetirse. Solo se aceptan archivos `.xlsx`. Si la validación falla, corrige una **copia del Excel original** y vuelve a seleccionarla. El mensaje de error indica la causa detectada.

### Archivos creados

Cada lote queda en `outputs/lotes/<nombre_del_excel>_<huella>/`. La consola crea:

| Archivo | Para qué sirve |
| --- | --- |
| `origen.xlsx` | Copia del Excel elegido; permite reconocer su contenido. |
| `reporte_trabajo.csv` | Datos normalizados que usa el sistema. |
| `reporte_trabajo.csv.bak` | Respaldo inicial del CSV. |
| `casos.txt` | Causas pendientes únicas según las reglas vigentes. |
| `casos_fallidos.txt` | Registro de causas fallidas; comienza vacío. |
| `manifiesto.json` | Identifica el Excel, la hoja y el lote. |

Las reglas generales están en `config_consola.json`; la consola no crea un `config.json` distinto para cada Excel nuevo. Si eliges otra vez **el mismo contenido**, se abre el lote existente sin borrar sus avances. Si modificas el Excel, se crea un lote nuevo. `reporte_final.xlsx` puede aparecer después del procesamiento.

## 3. Recuperar un lote

Usa **Seleccionar lote preparado** para volver a una carpeta de `outputs/lotes/` o pegar su ruta. La consola selecciona el lote y actualiza `casos.txt` con las reglas comunes actuales. Después puedes consultar su estado, revisar errores o continuar pendientes.

No borres ni edites `origen.xlsx`, `manifiesto.json`, el CSV o su respaldo mientras el lote esté en uso. Si cambias las reglas de `config_consola.json`, revísalas antes de reanudar un lote antiguo: las reglas comunes también se aplican al volver a abrirlo.

## 4. Configurar PostgreSQL

Entra en **Configurar conexión PostgreSQL** y elige:

- **Servidor en este equipo**: usa `localhost` y solicita puerto, base y usuario.
- **Servidor remoto**: solicita host, puerto, base, usuario y ruta del certificado CA para TLS `verify-full`.
- **Solo cargar contraseña**: conserva los datos de conexión guardados y solicita únicamente la contraseña para esta sesión.

Pulsa **Enter** en un campo para conservar el valor mostrado entre corchetes. Host, puerto, base, usuario y TLS se guardan en `config_consola.json`. La contraseña se pide sin mostrarla y queda solo en la sesión de la consola; al cerrar la ventana tendrás que ingresarla de nuevo. No escribas contraseñas en el JSON, el Excel ni un mensaje de chat.

Luego usa **Comprobar conexión y esquema**. Debe mostrar conexión, esquema y auditoría de configuración listos antes de procesar. Si falta la migración `003`, usa **Aplicar migraciones pendientes** con una cuenta administradora; esa opción aplica únicamente `003_config_comun_auditoria.sql`. Las migraciones `001` y `002` deben estar instaladas previamente por quien administra la base. La credencial administrativa se pide para esa operación y no se guarda en el archivo común.

Para un servidor remoto, reúne sus datos de conexión y el certificado CA antes de configurar esta opción.

## 5. Procesar causas

Con un lote seleccionado, entra en **Procesar causas**. Puedes elegir:

| Modo | Uso recomendado |
| --- | --- |
| **Piloto: una causa** | Comprueba el flujo completo con una causa elegida. |
| **Lote pequeño: 10 causas** | Amplía la prueba después del piloto. |
| **Lote: 50 causas** | Procesa un bloque mayor. |
| **Todas las causas activas** | Ejecuta las causas que correspondan según las reglas. |
| **Continuar pendientes de este lote** | Reanuda trabajo pendiente del lote seleccionado. |

En el piloto, selecciona una causa de la lista o escribe su número. En los otros modos, elige entre **1 y 4 trabajadores**. La consola pedirá la contraseña de PostgreSQL y la clave de 2Captcha si no están cargadas en esta sesión. Antes de empezar, mostrará el modo, los trabajadores y el servidor; selecciona **Iniciar ahora** para confirmar.

Conviene empezar por un piloto y revisar el resultado antes de procesar más causas. Mantén la consola abierta durante la ejecución. Si interrumpes el proceso, revisa el estado y los errores antes de usar **Continuar pendientes**. No ejecutes a la vez lotes diferentes que compartan causas.

## 6. Consultar avance y errores

- **Ver estado de ejecuciones** muestra las corridas recientes del lote, su progreso, pendientes, causas en proceso, atendidas y errores finales.
- **Revisar errores y causas pendientes** muestra las causas que requieren atención, sus intentos y el último error registrado, cuando existe.
- `casos_fallidos.txt` y los reportes del lote permanecen en su carpeta para revisión posterior.

Estas consultas necesitan la conexión PostgreSQL y la contraseña de la sesión. Si aparece «No hay registros para este lote», todavía no hay ejecuciones registradas para él.

## 7. Problemas frecuentes

| Mensaje o situación | Qué revisar |
| --- | --- |
| No se encuentra el Excel | Confirma que el archivo exista, termine en `.xlsx` y no sea un archivo temporal de Excel (`~$`). |
| `CABECERA_NO_RECONOCIDA` | Comprueba los cuatro encabezados obligatorios y que estén en una de las filas admitidas. |
| `CODIGO_JUICIO_DUPLICADO` o un campo vacío | Corrige el Excel y vuelve a prepararlo; el archivo corregido será un lote nuevo. |
| No conecta a PostgreSQL | Revisa host, puerto, base, usuario, contraseña y disponibilidad del servidor. |
| Esquema o auditoría pendiente | Pide al administrador instalar las migraciones faltantes; el menú solo aplica la `003` sobre una base ya inicializada. |
| Falló una causa | Consulta **Revisar errores y causas pendientes** antes de reanudar. |

Para detalles técnicos y el uso por comandos, consulta [Consola para nuevos Excel](CONSOLA_EXCEL.md) y la [guía PostgreSQL](../03_BASE_DE_DATOS/GUIA_PGADMIN_POSTGRES.md).
