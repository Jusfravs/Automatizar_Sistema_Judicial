# src/motor_busqueda_web.py
import os
import re
import json
import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from src.agente_extractor import AgenteExtractor, NavegadorArbolContenido
from src.logger_config import obtener_logger

# Intentar soporte opcional de YAML para keywords configurables
try:
    import yaml
    _YAML_AVAILABLE = True
except Exception:
    _YAML_AVAILABLE = False

logger = obtener_logger("BotJudicial")


def _load_extraction_keywords():
    """Carga una lista de keywords desde rutas conocidas o desde un archivo YAML/TSV simple.
    Busca en (en este orden): env(EXTRACTION_KEYWORDS_PATH), config/extraction_keywords.yml,
    data/extraction_keywords.yml, extraction_keywords.yml. Devuelve lista de strings en minúsculas.
    """
    candidates = [
        os.environ.get("EXTRACTION_KEYWORDS_PATH"),
        os.path.join("config", "extraction_keywords.yml"),
        os.path.join("data", "extraction_keywords.yml"),
        "extraction_keywords.yml",
    ]
    for p in candidates:
        if not p:
            continue
        try:
            if os.path.exists(p):
                if _YAML_AVAILABLE:
                    with open(p, "r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh)
                    if isinstance(data, dict):
                        kws = []
                        for v in data.values():
                            if isinstance(v, list):
                                kws.extend([str(x) for x in v])
                            elif isinstance(v, str):
                                kws.append(v)
                        return [k.lower() for k in kws if k]
                    elif isinstance(data, list):
                        return [str(x).lower() for x in data if x]
                else:
                    # fallback: leer líneas no comentadas
                    with open(p, "r", encoding="utf-8") as fh:
                        lines = [l.strip() for l in fh.readlines()]
                    lines = [l for l in lines if l and not l.startswith("#")]
                    return [l.lower() for l in lines]
        except Exception:
            continue

    # Default conservative set
    return [
        'mandam', 'mandamiento', 'mandamiento de ejecucion', 'auto de ejecucion', 'auto de ejecucion', 'auto de cumplimiento'
    ]


class BotJudicial:
    """
    Motor RPA Asistido con Arquitectura de Ejecución Dual para e-SATJE:
    1. Ruta Principal (API Fetching Nivel Dios 🚀): Intercepta respuestas JSON vía page.on('response'),
       bypass completo de BeautifulSoup4, tabulación vectorizada con Pandas y persistencia directa.
    2. Ruta de Respaldo (Sincronización DOM): Freno de ejecución con wait_for_selector('text="Actor/Ofendido:"')
       para asegurar inyección en Angular antes de enviar el HTML a BeautifulSoup4.
    """
    def __init__(self, url_portal):
        self.url_portal = url_portal
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.extractor = AgenteExtractor()
        self.nav_arbol = NavegadorArbolContenido()
        self.paquetes_api_interceptados = []
        self.datos_extraidos = None

    def iniciar_navegador(self, modo_visible=True):
        """Inicia el navegador Chromium con bypass anti-automatización para F5 WAF y listener API."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=not modo_visible,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--ignore-certificate-errors",
            ],
            ignore_default_args=["--enable-automation"]
        )
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            ignore_https_errors=True
        )
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-EC', 'es', 'en-US', 'en'] });
        """)
        self.page = self.context.new_page()
        
        # Ruta Principal: Listener de intercepción de red (API Fetching)
        self.page.on("response", self._interceptar_respuesta_api)
        
        logger.info("Navegador iniciado en %s", self.url_portal)
        self.page.goto(self.url_portal, timeout=60000, wait_until="domcontentloaded")
        
        # Aguardar la resolución pasiva del reto F5 WAF y renderizado de la UI Angular
        try:
            self.page.wait_for_selector(
                "input[placeholder*='códigoDependencia-Año-Secuencial'], input[formcontrolname='numeroJuicio'], button:has-text('BUSCAR')",
                state="visible",
                timeout=20000
            )
            logger.info("[OK] Portal del Consejo de la Judicatura cargado correctamente.")
        except Exception:
            logger.warning("[!] La UI de búsqueda tardó en aparecer; continuando observación.")

    def asegurar_navegador_vivo(self, modo_visible=True):
        """
        Verifica si la página y el contexto del navegador están activos.
        Si se cerró el navegador (Target page, context or browser has been closed),
        lo relanza automáticamente sin interrumpir la ejecución masiva.
        """
        try:
            if not self.page or self.page.is_closed() or not self.browser or not self.browser.is_connected():
                logger.warning("[!] El navegador o la pestaña fue cerrada. Relanzando automáticamente...")
                self.cerrar_navegador()
                self.iniciar_navegador(modo_visible=modo_visible)
                return True
        except Exception:
            logger.warning("[!] Error al verificar estado del navegador. Reiniciando instancia de Playwright...")
            self.cerrar_navegador()
            self.iniciar_navegador(modo_visible=modo_visible)
            return True
        return False

    def _verificar_sesion_activa(self):
        """
        Verifica si la sesión del portal sigue activa y el navegador está vivo.
        Si detecta expiración o cierre, relanza la navegación.
        """
        self.asegurar_navegador_vivo(modo_visible=True)
        try:
            contenido = self.page.inner_text("body", timeout=5000)
            indicadores_expiracion = [
                "sesión expirada", "session expired", "iniciar sesión",
                "vuelva a ingresar", "token expirado", "no autorizado",
            ]
            for indicador in indicadores_expiracion:
                if indicador.lower() in contenido.lower():
                    logger.warning("[!] Sesión expirada detectada. Reiniciando navegación...")
                    self.page.goto(self.url_portal, timeout=60000, wait_until="domcontentloaded")
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    return False
        except Exception as e_verif:
            if "closed" in str(e_verif).lower():
                logger.warning("[!] Detectado navegador cerrado durante verificación. Relanzando...")
                self.asegurar_navegador_vivo(modo_visible=True)
        return True

    def _interceptar_respuesta_api(self, response):
        """
        Ruta Principal: Captura JSON puros de la API Angular de la Judicatura.
        """
        try:
            url = response.url.lower()
            if any(kw in url for kw in ["/api/", "expel", "proceso", "causa", "actuaciones", "catalogo"]):
                if not any(ext in url for ext in [".js", ".css", ".png", ".ico", ".woff", ".svg"]):
                    if response.status in [200, 201]:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            data = response.json()
                            self.paquetes_api_interceptados.append({
                                "url": response.url,
                                "data": data
                            })
                            logger.debug("[RUTA PRINCIPAL API] Capturado JSON desde: %s", response.url)
        except Exception:
            pass

    def regresar_al_buscador(self):
        """
        Navegación jerárquica hacia arriba conservando sesión.
        """
        try:
            self.nav_arbol.subir_nivel("Retornando al nivel raíz de búsqueda")
            input_busqueda = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial']").first
            if input_busqueda.is_visible():
                return True

            btn_filtros = self.page.locator("button:has-text('Filtros de búsqueda'), a:has-text('Filtros de búsqueda')").first
            btn_regresar = self.page.locator("button:has-text('Regresar'), a:has-text('Regresar')").first

            for _ in range(3):
                if input_busqueda.is_visible():
                    break
                if btn_filtros.is_visible():
                    btn_filtros.click()
                    self.page.wait_for_selector("input[placeholder*='códigoDependencia-Año-Secuencial']", state="visible", timeout=3000)
                elif btn_regresar.is_visible():
                    btn_regresar.click()
                    self.page.wait_for_selector("input[placeholder*='códigoDependencia-Año-Secuencial']", state="visible", timeout=3000)
                else:
                    self.page.go_back()
                    self.page.wait_for_load_state("domcontentloaded")
            return True
        except Exception:
            self.page.goto(self.url_portal, wait_until="domcontentloaded")
            return False

    def procesar_flujo_judicatura(self, numero_juicio):
        """
        Modo Híbrido Asistido con Arquitectura de Ejecución Dual:
        1. Prepara búsqueda en Nivel 0.
        2. Aplica freno de ejecución estricto: wait_for_selector('text="Actor/Ofendido:"', state='visible').
        3. Procesa Ruta Principal (API + Pandas) o Ruta Respaldo (BeautifulSoup4 + DOM).
        """
        logger.info("Iniciando causa: %s", numero_juicio)
        self.paquetes_api_interceptados.clear()
        
        # Freno de ejecución estricto: debe coincidir ÚNICAMENTE con la vista de detalle del expediente (Image 2),
        # NO con la cabecera de la tabla de judicaturas "Actuaciones Judiciales" (Image 1).
        selector_freno_estricto = "text=/Información del proceso|Exportar PDF|Ampliar todo|Contraer todo/i"
        max_reintentos = 3
        intentos = 0

        while intentos < max_reintentos:
            try:
                # 0. Verificar sesión activa antes de cada intento
                self._verificar_sesion_activa()

                # 1. Preparar entrada en caja de búsqueda (Nivel 0)
                try:
                    input_causa = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial']").first
                    if not input_causa.is_visible():
                        self.regresar_al_buscador()

                    if input_causa.is_visible():
                        input_causa.fill("")
                        input_causa.fill(str(numero_juicio).strip())
                        logger.info("Causa '%s' lista en el buscador.", numero_juicio)
                        logger.info("Por favor, resuelve Captcha / busca y navega a la carpeta del expediente...")
                except Exception as e_fill:
                    logger.warning("Aviso al preparar la caja de búsqueda: %s", e_fill)

                # Intentar auto-click en el icono de carpeta 📁 si estamos en la tabla de resultados (Image 1)
                try:
                    self.page.wait_for_timeout(1000)
                    if not self.page.locator(selector_freno_estricto).first.is_visible():
                        for btn_sel in [
                            "tr td button:has(i)",
                            "tr td button",
                            "tr td a",
                            "i.fa-folder",
                            "i.fa-folder-open",
                            "button:has(.fa-folder)",
                        ]:
                            try:
                                folder_btn = self.page.locator(btn_sel).first
                                if folder_btn.is_visible():
                                    logger.info("Navegando automáticamente al expediente (click en carpeta 📁)...")
                                    folder_btn.click()
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass

                # 2. RUTA RESPALDO: Freno de Ejecución Estricto en la pantalla de detalle del expediente (Image 2)
                logger.info("FRENO DE EJECUCIÓN: Aguardando apertura del expediente (vista de detalle 'Información del proceso')...")
                self.page.wait_for_selector(selector_freno_estricto, state="visible", timeout=300000)
                self.nav_arbol.bajar_nivel("Expediente abierto -> Profundizando en contenido")

                # 3. Procesamiento Dual (API Fetching + Pandas // DOM + BS4)
                self.datos_extraidos = self._ejecutar_extraccion_detalles(numero_juicio)

                # 4. Esperar a que el usuario cierre el expediente (retorno en árbol)
                logger.info("Aguardando a que el operador cierre el expediente (state: hidden)...")
                self.page.wait_for_selector(selector_freno_estricto, state="hidden", timeout=300000)
                self.nav_arbol.subir_nivel("Expediente cerrado -> Retornando al nivel superior")

                return True

            except PlaywrightTimeoutError:
                intentos += 1
                logger.warning("Timeout alcanzado (intento %s/%s). El selector no apareció en 5 minutos.", intentos, max_reintentos)
                if intentos >= max_reintentos:
                    logger.error("Máximo de reintentos alcanzado para causa %s. Abortando.", numero_juicio)
                    return False
            except Exception as e:
                intentos += 1
                msg_err = str(e).lower()
                logger.warning("Excepción en bucle de observación pasiva (intento %s/%s): %s", intentos, max_reintentos, e)
                if "closed" in msg_err or "target page" in msg_err:
                    logger.warning("[!] Detectado cierre de navegador. Relanzando Chromium automáticamente...")
                    self.asegurar_navegador_vivo(modo_visible=True)
                if intentos >= max_reintentos:
                    logger.error("Máximo de reintentos alcanzado para causa %s. Abortando.", numero_juicio)
                    return False
                try:
                    if self.page and not self.page.is_closed():
                        self.page.wait_for_selector("body", state="visible", timeout=5000)
                except Exception:
                    pass

        return False

    def extraer_detalles_juicio(self):
        """Devuelve los datos procesados en la vista actual."""
        if self.datos_extraidos is not None:
            res = self.datos_extraidos
            self.datos_extraidos = None
            return res
        return self._ejecutar_extraccion_detalles()

    def _ejecutar_extraccion_detalles(self, numero_juicio=None):
        """
        Arquitectura Dual:
        - RUTA PRINCIPAL: Si la API interceptó JSON, procesar vectorialmente con Pandas (Bypass BeautifulSoup4).
        - RUTA RESPALDO: Si no hay API JSON, capturar HTML post-sincronización y procesar con BeautifulSoup4.
        Además, guarda artefactos (HTML + paquetes API) en data/temp_htmls para análisis cuando se pase numero_juicio.
        """
        datos = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None
        }

        # --- RUTA PRINCIPAL: INTERCEPCIÓN API (BYPASS BEAUTIFULSOUP4 + PANDAS) ---
        if self.paquetes_api_interceptados:
            # Cargar keywords configurables para detección de mandamiento (opcional)
            try:
                keywords = _load_extraction_keywords()
            except Exception:
                keywords = ['mandam','mandamiento','mandamiento de ejecucion','auto de ejecucion','auto de cumplimiento']

            logger.info("[RUTA PRINCIPAL API] Procesando %s respuesta(s) JSON con Pandas...", len(self.paquetes_api_interceptados))
            try:
                registros = []
                for p in self.paquetes_api_interceptados:
                    d = p.get("data")
                    if isinstance(d, dict):
                        registros.append(d)
                    elif isinstance(d, list):
                        registros.extend([item for item in d if isinstance(item, dict)])
                
                if registros:
                    df = pd.json_normalize(registros)
                    # Extracción vectorizada de fechas
                    cols_fechas = [c for c in df.columns if any(k in c.lower() for k in ["fechainicio", "fechaingreso", "fechaprovidencia", "fechapresentacion"]) ]
                    if cols_fechas:
                        primera_fecha = df[cols_fechas[0]].first_valid_index()
                        if primera_fecha is not None:
                            datos["FECHA INICIO JUICIO"] = str(df.at[primera_fecha, cols_fechas[0]])

                    # Recolectar actuaciones estructuradas desde la API JSON para inferencia jerárquica (Regla del Árbol)
                    actuaciones_api = []
                    for reg in registros:
                        acts = reg.get("actuaciones") or reg.get("listaActuaciones") or []
                        if isinstance(acts, list):
                            for act in acts:
                                if isinstance(act, dict):
                                    f_act = act.get("fecha") or act.get("fechaActuacion") or act.get("fechaProvidencia")
                                    d_act = act.get("actuacion") or act.get("detalle") or act.get("tipoActuacion") or act.get("actividad")
                                    if d_act:
                                        actuaciones_api.append({
                                            "fecha": str(f_act) if f_act else None,
                                            "detalle": str(d_act).upper()
                                        })

                    if actuaciones_api:
                        from src.agente_extractor import MotorInferenciaProcesal
                        res_api = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones_api)
                        if res_api and res_api.get("ULTIMA_ETAPA"):
                            etapa_api = res_api.get("ULTIMA_ETAPA")
                            fase_api = res_api.get("ULTIMA_FASE")
                            fecha_api = res_api.get("FECHA_FIN_ULTIMA_FASE") or datos.get("FECHA INICIO JUICIO")
                            
                            datos["ETAPA_PROCESAL"] = etapa_api
                            datos["FASE_PROCESAL"] = fase_api
                            datos["FECHA INICIAL FASE ACTUAL"] = fecha_api
                            datos["ULTIMA ETAPA"] = etapa_api
                            datos["ULTIMA FASE"] = fase_api
                            datos["FECHA FIN ULTIMA FASE"] = fecha_api
                            datos["ETAPA ACTUAL"] = res_api.get("ETAPA_ACTUAL") or etapa_api
                            datos["FASE ACTUAL"] = res_api.get("FASE_ACTUAL") or fase_api
                            datos["FECHA INICIO FASE ACTUAL"] = fecha_api
                            if res_api.get("MENSAJE_ESPECIAL"):
                                datos["COMENTARIO_ULTIMO"] = res_api.get("MENSAJE_ESPECIAL")

                            logger.info("[RUTA PRINCIPAL API] Clasificación por Regla del Árbol: '%s' / '%s' en fecha %s", etapa_api, fase_api, datos["FECHA INICIAL FASE ACTUAL"])
                            return datos
            except Exception as e_pandas:
                logger.warning("Conmutando a Ruta de Respaldo por aviso en Pandas: %s", e_pandas)

        # --- RUTA RESPALDO: SINCRONIZACIÓN DOM (AGENTE EXTRACTOR) ---
        logger.info("[RUTA RESPALDO DOM] Procesando HTML renderizado post-sincronización con AgenteExtractor...")
        try:
            # Intentar asegurar que el listado de actuaciones se cargue (esperar XHR o forzar click en la pestaña)
            try:
                # Esperar por una respuesta JSON o una URL con 'actuacion' en el path (más tolerante)
                resp = self.page.wait_for_response(
                    lambda r: (r.headers and 'content-type' in r.headers and 'json' in r.headers.get('content-type','').lower() and r.status in [200,201])
                              or 'actuacion' in r.url.lower() or 'actuaciones' in r.url.lower(),
                    timeout=5000
                )
                try:
                    logger.info("[RUTA RESPALDO DOM] Interceptada respuesta de actuaciones/JSON: %s", resp.url)
                except Exception:
                    logger.info("[RUTA RESPALDO DOM] Interceptada respuesta de actuaciones/JSON (URL no disponible)")
            except Exception:
                # Intentar clickar en pestañas comunes que cargan actuaciones (varias alternativas)
                clicked = False
                for sel in ["text='Actuaciones Judiciales'", "text='Actuaciones'", "a:has-text('Actuaciones')", "button:has-text('Actuaciones Judiciales')", "button:has-text('Actuaciones')"]:
                    try:
                        loc = self.page.locator(sel).first
                        if loc.is_visible():
                            loc.scroll_into_view_if_needed()
                            loc.click()
                            self.page.wait_for_load_state("networkidle", timeout=5000)
                            logger.info("[RUTA RESPALDO DOM] Click en selector para cargar actuaciones: %s", sel)
                            clicked = True
                            break
                    except Exception:
                        continue

                # Si no se pudo clickar con selectores estándar, intentar clickar por texto via JS (más robusto para Angular/custom tags)
                if not clicked:
                    try:
                        js_click = (
                            "(function(){var els = Array.from(document.querySelectorAll('button, a, span, div'));"
                            "var r=els.find(e=>/actuaciones?/i.test(e.innerText)); if(r){r.scrollIntoView(); r.click(); return true;} return false;})()"
                        )
                        rv = self.page.evaluate(js_click)
                        if rv:
                            logger.info("[RUTA RESPALDO DOM] Click por texto realizado vía evaluate()")
                            try:
                                self.page.wait_for_load_state("networkidle", timeout=4000)
                            except Exception:
                                pass
                    except Exception:
                        pass

            # Esperar explícitamente a que Angular inyecte las filas de la tabla de actuaciones en el DOM
            try:
                self.page.wait_for_selector(
                    "table tr td, tr.mat-row, mat-row, .actuacion-item, tr:has(td)",
                    state="visible",
                    timeout=8000
                )
                logger.info("[RUTA RESPALDO DOM] Tabla de actuaciones detectada y visible en el DOM.")
            except Exception:
                logger.warning("[!] No se detectaron filas de tabla explícitas en 8s; procediendo con la lectura del DOM actual.")

            # Esperar estabilización de red
            try:
                self.page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass

            # Capturar contenido principal y el contenido de frames/iframes para analizarlos todos juntos
            contenido_html = self.page.content()
            try:
                frames_html = []
                for f in self.page.frames:
                    try:
                        # proteger contra frames None en entornos de test
                        if f is None:
                            continue
                        fc = f.content()
                        if fc:
                            frames_html.append(fc)
                    except Exception:
                        # algunos frames pueden fallar al leer si son cross-origin — ignorar
                        continue
            except Exception:
                frames_html = []

            # Concatenar contenido principal + frames para pasar al extractor como respaldo más completo
            contenido_total = contenido_html + "\n" + "\n\n".join(frames_html)

            # Guardar artefactos para análisis offline si se proporcionó numero_juicio
            try:
                import json as _json
                dir_temp = os.path.join("data", "temp_htmls")
                os.makedirs(dir_temp, exist_ok=True)
                if numero_juicio:
                    # Guardar HTML combinado (principal + frames)
                    ruta_html = os.path.join(dir_temp, f"{numero_juicio}.html")
                    with open(ruta_html, "w", encoding="utf-8") as fh:
                        fh.write(contenido_total)
                    logger.info("[ARTIFACT] HTML (principal+frames) guardado en: %s", ruta_html)

                    # Guardar frames por separado para diagnóstico
                    try:
                        for idx, fhtml in enumerate(frames_html):
                            ruta_f = os.path.join(dir_temp, f"{numero_juicio}_frame_{idx+1}.html")
                            with open(ruta_f, "w", encoding="utf-8") as ff:
                                ff.write(fhtml)
                        if frames_html:
                            logger.info("[ARTIFACT] %s frame(s) guardado(s) para: %s", len(frames_html), numero_juicio)
                    except Exception:
                        pass

                    if self.paquetes_api_interceptados:
                        ruta_api = os.path.join(dir_temp, f"{numero_juicio}_api.json")
                        with open(ruta_api, "w", encoding="utf-8") as fa:
                            _json.dump(self.paquetes_api_interceptados, fa, ensure_ascii=False, indent=2)
                        logger.info("[ARTIFACT] Paquetes API guardados en: %s", ruta_api)
            except Exception as e_save:
                logger.warning("No se pudo guardar artefactos para %s: %s", numero_juicio, e_save)

            # Pasar el HTML combinado al extractor para mayor cobertura (incluye iframes cuando fue posible leerlos)
            datos_dom = self.extractor.procesar_html_string(contenido_total)

            # Conservar fecha de inicio si fue extraída previamente
            if datos["FECHA INICIO JUICIO"] and not datos_dom.get("FECHA INICIO JUICIO"):
                datos_dom["FECHA INICIO JUICIO"] = datos["FECHA INICIO JUICIO"]
            return datos_dom
        except Exception as e:
            logger.error("Inconveniente al leer actuaciones en Ruta Respaldo: %s", e)
            return datos

    def cerrar_navegador(self):
        """Cierra la sesión del navegador."""
        if hasattr(self, 'context') and self.context:
            try:
                self.context.close()
            except Exception:
                pass
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Navegador cerrado.")
