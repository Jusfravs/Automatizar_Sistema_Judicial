# src/motor_busqueda_web.py
import os
import re
import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from src.agente_extractor import AgenteExtractor, NavegadorArbolContenido
from src.logger_config import obtener_logger

logger = obtener_logger("BotJudicial")


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
        self.page = None
        self.extractor = AgenteExtractor()
        self.nav_arbol = NavegadorArbolContenido()
        self.paquetes_api_interceptados = []
        self.datos_extraidos = None

    def iniciar_navegador(self, modo_visible=True):
        """Inicia el navegador Chromium con listener de intercepción de red API."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not modo_visible)
        self.page = self.browser.new_page()
        
        # Ruta Principal: Listener de intercepción de red (API Fetching)
        self.page.on("response", self._interceptar_respuesta_api)
        
        logger.info("Navegador iniciado en %s", self.url_portal)
        self.page.goto(self.url_portal, timeout=60000, wait_until="domcontentloaded")
        self.page.wait_for_load_state("networkidle", timeout=30000)

    def _verificar_sesion_activa(self):
        """
        Verifica si la sesión del portal sigue activa.
        Si detecta expiración, vuelve a navegar al portal.
        """
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
                    self.page.wait_for_load_state("networkidle", timeout=30000)
                    return False
        except Exception:
            pass
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
        
        selector_freno_estricto = "text=/Actor\\/Ofendido:|Información del proceso|Actuaciones Judiciales|Exportar PDF/i"
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

                # 2. RUTA RESPALDO: Freno de Ejecución Estricto (wait_for_selector)
                logger.info("FRENO DE EJECUCIÓN: Aguardando inyección completa en Angular...")
                self.page.wait_for_selector(selector_freno_estricto, state="visible", timeout=300000)
                self.nav_arbol.bajar_nivel("Expediente abierto -> Profundizando en contenido")

                # 3. Procesamiento Dual (API Fetching + Pandas // DOM + BS4)
                self.datos_extraidos = self._ejecutar_extraccion_detalles()

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
                logger.warning("Excepción en bucle de observación pasiva (intento %s/%s): %s", intentos, max_reintentos, e)
                if intentos >= max_reintentos:
                    logger.error("Máximo de reintentos alcanzado para causa %s. Abortando.", numero_juicio)
                    return False
                try:
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

    def _ejecutar_extraccion_detalles(self):
        """
        Arquitectura Dual:
        - RUTA PRINCIPAL: Si la API interceptó JSON, procesar vectorialmente con Pandas (Bypass BeautifulSoup4).
        - RUTA RESPALDO: Si no hay API JSON, capturar HTML post-sincronización y procesar con BeautifulSoup4.
        """
        datos = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None
        }

        # --- RUTA PRINCIPAL: INTERCEPCIÓN API (BYPASS BEAUTIFULSOUP4 + PANDAS) ---
        if self.paquetes_api_interceptados:
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
                    cols_fechas = [c for c in df.columns if any(k in c.lower() for k in ["fechainicio", "fechaingreso", "fechapresentacion"])]
                    if cols_fechas:
                        primera_fecha = df[cols_fechas[0]].first_valid_index()
                        if primera_fecha is not None:
                            datos["FECHA INICIO JUICIO"] = str(df.at[primera_fecha, cols_fechas[0]])

                    # Extracción y clasificación de actuaciones desde API JSON
                    for reg in registros:
                        actuaciones = reg.get("actuaciones") or reg.get("listaActuaciones") or []
                        if isinstance(actuaciones, list):
                            for act in actuaciones:
                                if isinstance(act, dict):
                                    f_act = act.get("fecha") or act.get("fechaActuacion")
                                    d_act = act.get("actuacion") or act.get("detalle") or act.get("tipoActuacion")
                                    if f_act and d_act:
                                        etapa, fase, score = self.extractor.evaluar_similitud_semantica(str(d_act))
                                        if etapa and score >= 0.7:
                                            datos["FECHA INICIAL FASE ACTUAL"] = str(f_act)
                                            datos["ETAPA_PROCESAL"] = etapa
                                            datos["FASE_PROCESAL"] = fase
                                            logger.info("Match en Ruta Principal API (Score %s): '%s' en fecha %s", score, fase, f_act)
                                            return datos
            except Exception as e_pandas:
                logger.warning("Conmutando a Ruta de Respaldo por aviso en Pandas: %s", e_pandas)

        # --- RUTA RESPALDO: SINCRONIZACIÓN DOM (AGENTE EXTRACTOR) ---
        logger.info("[RUTA RESPALDO DOM] Procesando HTML renderizado post-sincronización con AgenteExtractor...")
        try:
            contenido_html = self.page.content()
            datos_dom = self.extractor.procesar_html_string(contenido_html)
            # Conservar fecha de inicio si fue extraída previamente
            if datos["FECHA INICIO JUICIO"] and not datos_dom.get("FECHA INICIO JUICIO"):
                datos_dom["FECHA INICIO JUICIO"] = datos["FECHA INICIO JUICIO"]
            return datos_dom
        except Exception as e:
            logger.error("Inconveniente al leer actuaciones en Ruta Respaldo: %s", e)
            return datos

    def cerrar_navegador(self):
        """Cierra la sesión del navegador."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Navegador cerrado.")
