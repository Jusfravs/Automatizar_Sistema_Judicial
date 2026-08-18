# **Análisis de Ejecución: RPA Judicatura**

## **1\. Resumen del Sistema**

Según el archivo config.json y los logs, el sistema es un bot (RPA) construido presumiblemente en Python (usando Playwright o Puppeteer, Pandas, SQLite y BeautifulSoup) diseñado para extraer expedientes judiciales del portal de la Función Judicial de Ecuador.

Cuenta con una arquitectura avanzada:

* Intercepta respuestas de la API (RUTA PRIMARIA XHR).  
* Tiene un motor de respaldo para leer el HTML (RUTA RESPALDO DOM).  
* Usa un sistema de colas y autoguardado para reanudar el trabajo (GestorCola, GestorCasos).

## **2\. Diagnóstico de los Problemas Críticos**

Al analizar ejecucion\_produccion.log, el bot comienza ejecutándose bien, pero luego sufre una **falla en cascada masiva**. Todos los juicios fallan progresivamente (ej. 23331-2022-04261, 23331-2023-00120, etc.).

Aquí están las causas exactas identificadas en los logs:

### **A. Muerte del Navegador (Browser Context Closed)**

El error más letal que aparece repetidamente a partir del 29 de julio a las 12:05 es:

> Page.wait\_for\_selector: Target page, context or browser has been closed

**¿Qué significa?** El bot está intentando buscar elementos (como la caja de búsqueda o el texto del actor/ofendido) en una pestaña o navegador que **ya no existe**. El navegador se cerró abruptamente (por un crasheo, falta de memoria, o se cerró manualmente), pero el script de Python siguió intentando procesar los 213 casos en la cola, disparando el mismo error en cada uno a la velocidad de la luz.

### **B. Bloqueo por Captcha o Carga de Angular (Timeouts)**

Antes de que el navegador muriera, vemos este patrón:

> \[BotJudicial\] Por favor, resuelve Captcha / busca y navega a la carpeta del expediente...

> \[BotJudicial\] FRENO DE EJECUCIÓN: Aguardando inyección completa en Angular...

> \[WARNING\] \[BotJudicial\] Timeout alcanzado (intento 3/3). El selector no apareció en 5 minutos.

**¿Qué significa?** El bot se queda esperando hasta 5 minutos a que aparezca el selector text=/Actor\\/Ofendido:|Información del proceso.../. Al no aparecer, aborta el caso. Esto suele pasar por dos motivos en esa página específica:

1. Apareció el reCAPTCHA de Google de la Función Judicial y el script se quedó congelado esperándolo.  
2. La arquitectura de Angular de la página falló al cargar los datos tras enviar la petición, dejando la página en blanco o cargando infinitamente.

### **C. Corrupción del Estado (CSV vacío)**

> \[CRITICAL\] \[GestorCasos\] El archivo CSV está vacío o corrupto. Intentando autoreparar desde el Excel original...

Afortunadamente programaste un mecanismo de autorecuperación, pero el hecho de que el CSV se vacíe indica que el proceso de Python se está cerrando forzosamente o matando en medio de una operación de escritura (I/O).

## **3\. Recomendaciones Técnicas Inmediatas**

Para estabilizar el robot, te sugiero aplicar estas correcciones en el código de tu BotJudicial:

1. **Recrear el contexto del navegador (Try/Catch):**  
   Debes envolver la iteración de tus casos en un bloque try/except. Si capturas un error de tipo TargetClosedError o Target page... closed, **no debes pasar al siguiente caso inmediatamente**. Debes reiniciar el navegador (browser.close(), playwright.chromium.launch()) y volver a iniciar sesión antes de continuar.  
2. **Manejo de Captchas:**  
   El log muestra que pides "resolución de captcha". Si esto es manual, asegúrate de que el bot no haga un timeout silencioso si el usuario se demora. Podrías integrar pausas implícitas (page.pause() en Playwright) que detengan la ejecución hasta que el humano resuelva el captcha.  
3. **Optimizar los tiempos de espera (Angular):**  
   En lugar de esperar 5 minutos por un texto específico (Actor/Ofendido), usa page.wait\_for\_load\_state('networkidle'). Angular dispara múltiples peticiones XHR. Al esperar a que la red esté inactiva, te aseguras de que la tabla ya cargó completamente antes de buscar los selectores.