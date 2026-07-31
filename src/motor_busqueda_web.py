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

                    # Heurística adicional: si la API no provee actuaciones, intentar inferir desde campos de alto nivel
                    for reg in registros:
                        # Construir un texto compuesto con campos relevantes
                        posibles = []
                        for key in ("nombreTipoAccion", "nombreProvidencia", "nombreTipoResolucion", "nombreDelito", "nombreMateria", "nombreEstadoJuicio", "nombreProvidencia"):
                            v = reg.get(key) if isinstance(reg, dict) else None
                            if v:
                                posibles.append(str(v))
                        texto_compuesto = " ".join(posibles)

                        # Heurística explícita para tipo de acción 'EJECUTIVO' -> MANDAMIENTO DE EJECUCIÓN
                        if isinstance(reg, dict) and reg.get('nombreTipoAccion') and 'EJECUT' in str(reg.get('nombreTipoAccion')).upper():
                            # Recolectar candidatos explícitos de 'MANDAMIENTO' y luego elegir el más representativo (aquí: el más temprano)
                            candidatos = []
                            try:
                                for rsearch in registros:
                                    if not isinstance(rsearch, dict):
                                        continue
                                    # 1) Priorizar 'tipo' que contenga 'MANDAMIENTO'
                                    tfield = rsearch.get('tipo') or ''
                                    if isinstance(tfield, str) and 'mandamiento' in tfield.lower():
                                        fecha_c = rsearch.get('fecha') or rsearch.get('fechaActuacion') or rsearch.get('fechaProvidencia')
                                        if fecha_c:
                                            candidatos.append(fecha_c)
                                        continue
                                    # 2) búsqueda directa en campos de texto
                                    for txt_field in ('actividad', 'nombreProvidencia', 'nombreTipoResolucion', 'nombreTipoAccion'):
                                        tv = rsearch.get(txt_field)
                                        if isinstance(tv, str) and 'mandam' in tv.lower():
                                            fecha_c = rsearch.get('fecha') or rsearch.get('fechaActuacion') or rsearch.get('fechaProvidencia')
                                            if fecha_c:
                                                candidatos.append(fecha_c)
                                            break
                                    # 3) buscar dentro de sub-listas de actuaciones
                                    actos = rsearch.get('actuaciones') or rsearch.get('listaActuaciones') or []
                                    if isinstance(actos, list):
                                        for a in actos:
                                            if isinstance(a, dict):
                                                text_a = (a.get('actuacion') or a.get('detalle') or a.get('actividad') or a.get('tipo') or '')
                                                if isinstance(text_a, str) and 'mandam' in text_a.lower():
                                                    fecha_c = a.get('fecha') or a.get('fechaActuacion') or a.get('fechaProvidencia')
                                                    if fecha_c:
                                                        candidatos.append(fecha_c)
                                                    break
                            except Exception:
                                candidatos = []

                            # Elegir candidato: preferir el más temprano (min) si existen varios. Si no, fallback al fechaIngreso
                            fecha_n = None
                            try:
                                if candidatos:
                                    # ISO-strings compare lexicographically for timestamp order when in same format
                                    fecha_n = sorted(candidatos)[0]
                            except Exception:
                                fecha_n = None

                            if not fecha_n:
                                fecha_n = reg.get("fechaIngreso") or reg.get("fecha_ingreso") or reg.get("fechaProvidencia")

                            datos["FECHA INICIAL FASE ACTUAL"] = fecha_n if fecha_n else datos.get("FECHA INICIO JUICIO")
                            datos["ETAPA_PROCESAL"] = "6 LIQUIDACION Y EMBARGO"
                            datos["FASE_PROCESAL"] = "6.2 MANDAMIENTO DE EJECUCION"
                            logger.info("Heurística API dedujo MANDAMIENTO DE EJECUCION desde nombreTipoAccion: %s -- fecha seleccionada: %s", reg.get('nombreTipoAccion'), fecha_n)
                            return datos

                        if texto_compuesto:
                            etapa_api, fase_api, score_api = self.extractor.evaluar_similitud_semantica(texto_compuesto)
                            if etapa_api and score_api >= 0.6:
                                # Usar la fecha de ingreso si existe
                                fecha_n = reg.get("fechaIngreso") or reg.get("fecha_ingreso") or reg.get("fechaProvidencia")
                                datos["FECHA INICIAL FASE ACTUAL"] = fecha_n if fecha_n else datos.get("FECHA INICIO JUICIO")
                                datos["ETAPA_PROCESAL"] = etapa_api
                                datos["FASE_PROCESAL"] = fase_api
                                logger.info("Heurística API match (Score %s): '%s' desde campos de registro", score_api, fase_api)
                                return datos

                    # Extracción y clasificación de actuaciones desde API JSON (cuando existan)
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

            # Pequeña espera para que Angular injete contenido dinámico adicional
            try:
                self.page.wait_for_load_state("networkidle", timeout=2000)
            except Exception:
                pass

            # Capturar contenido principal y el contenido de frames/iframes para analizarlos todos juntos
            contenido_html = self.page.content()
            try:
                frames_html = []
                for f in self.page.frames:
                    try:
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

            # Fallback heurístico: si el HTML combinado contiene 'MANDAMIENTO DE EJECUCION' y extractor no lo detectó, sobreescribir
            try:
                lower_total = contenido_total.lower()
                if 'mandamiento de ejecucion' in lower_total or 'mandamiento de ejecución' in lower_total:
                    if not datos_dom.get('FASE_PROCESAL') or 'mandamiento' not in str(datos_dom.get('FASE_PROCESAL','')).lower():
                        datos_dom['ETAPA_PROCESAL'] = '6 LIQUIDACION Y EMBARGO'
                        datos_dom['FASE_PROCESAL'] = '6.2 MANDAMIENTO DE EJECUCION'
                        logger.info("Fallback DOM: detectado 'MANDAMIENTO DE EJECUCION' en HTML combinado; sobrescribiendo clasificación")
            except Exception:
                pass

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
