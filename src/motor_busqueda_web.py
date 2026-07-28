# src/motor_busqueda_web.py
import re
import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from src.agente_extractor import AgenteExtractor, NavegadorArbolContenido

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
        
        print(f"[*] Navegador iniciado en {self.url_portal}")
        self.page.goto(self.url_portal, timeout=60000, wait_until="domcontentloaded")

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
                            print(f"[RUTA PRINCIPAL API] Capturado JSON desde: {response.url}")
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
        print(f"\n[-] Iniciando causa: {numero_juicio}")
        self.paquetes_api_interceptados.clear()
        
        selector_freno_estricto = "text=/Actor\\/Ofendido:|Información del proceso|Actuaciones Judiciales|Exportar PDF/i"
        max_reintentos = 3
        intentos = 0

        while intentos < max_reintentos:
            try:
                # 1. Preparar entrada en caja de búsqueda (Nivel 0)
                try:
                    input_causa = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial']").first
                    if not input_causa.is_visible():
                        self.regresar_al_buscador()

                    if input_causa.is_visible():
                        input_causa.fill("")
                        input_causa.fill(str(numero_juicio).strip())
                        print(f"[!] Causa '{numero_juicio}' lista en el buscador.")
                        print("[!] Por favor, resuelve Captcha / busca y navega a la carpeta del expediente...")
                except Exception as e_fill:
                    print(f"[!] Aviso al preparar la caja de búsqueda: {e_fill}")

                # 2. RUTA RESPALDO: Freno de Ejecución Estricto (wait_for_selector)
                print("[*] FRENO DE EJECUCIÓN: Aguardando inyección completa en Angular (text='Actor/Ofendido:')...")
                self.page.wait_for_selector(selector_freno_estricto, state="visible", timeout=300000)
                self.nav_arbol.bajar_nivel("Expediente abierto -> Profundizando en contenido")

                # 3. Procesamiento Dual (API Fetching + Pandas // DOM + BS4)
                self.datos_extraidos = self._ejecutar_extraccion_detalles()

                # 4. Esperar a que el usuario cierre el expediente (retorno en árbol)
                print("[*] Aguardando a que el operador cierre el expediente (state: hidden)...")
                self.page.wait_for_selector(selector_freno_estricto, state="hidden", timeout=300000)
                self.nav_arbol.subir_nivel("Expediente cerrado -> Retornando al nivel superior")

                return True

            except PlaywrightTimeoutError:
                intentos += 1
                print(f"[!] Timeout alcanzado (intento {intentos}/{max_reintentos}). El selector no apareció en 5 minutos.")
                if intentos >= max_reintentos:
                    print(f"[ERROR] Máximo de reintentos alcanzado para causa {numero_juicio}. Abortando.")
                    return False
            except Exception as e:
                intentos += 1
                print(f"[!] Excepción en bucle de observación pasiva (intento {intentos}/{max_reintentos}): {e}")
                if intentos >= max_reintentos:
                    print(f"[ERROR] Máximo de reintentos alcanzado para causa {numero_juicio}. Abortando.")
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
            print(f"[🚀 RUTA PRINCIPAL API] Procesando {len(self.paquetes_api_interceptados)} respuesta(s) JSON con Pandas...")
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
                                            print(f"[+] Match en Ruta Principal API (Score {score}): '{fase}' en fecha {f_act}")
                                            return datos
            except Exception as e_pandas:
                print(f"[!] Conmutando a Ruta de Respaldo por aviso en Pandas: {e_pandas}")

        # --- RUTA RESPALDO: SINCRONIZACIÓN DOM (BEAUTIFULSOUP4 + LXML) ---
        print("[* RUTA RESPALDO DOM] Procesando HTML renderizado post-sincronización con BeautifulSoup4...")
        try:
            # 1. Extraer Fecha de Inicio General
            try:
                elems_fecha = self.page.locator("text=/Fecha de ingreso|Fecha ingreso|Fecha presentación|Fecha inicio/i").all()
                for ef in elems_fecha:
                    txt = ef.inner_text().strip()
                    m = re.search(r'\d{2}/\d{2}/\d{4}', txt)
                    if m:
                        datos["FECHA INICIO JUICIO"] = m.group(0)
                        break
                    try:
                        parent_txt = ef.locator("xpath=..").inner_text().strip()
                        m_p = re.search(r'\d{2}/\d{2}/\d{4}', parent_txt)
                        if m_p:
                            datos["FECHA INICIO JUICIO"] = m_p.group(0)
                            break
                    except Exception:
                        pass
            except Exception:
                pass

            actuaciones_validas = []

            # 2. Extracción de actuaciones en DOM (Selectores relativos XPath)
            filas = self.page.locator("xpath=//table//tr | //div[@role='row']").all()
            for fila in filas:
                try:
                    cols = fila.locator("xpath=.//td | .//th | .//div").all()
                    if len(cols) >= 2:
                        txt_col0 = cols[0].inner_text().strip()
                        txt_col1 = cols[1].inner_text().strip()
                    else:
                        txt_row = fila.inner_text().strip()
                        parts = [p.strip() for p in txt_row.split("\n") if p.strip()]
                        if len(parts) >= 2:
                            txt_col0, txt_col1 = parts[0], parts[1]
                        else:
                            continue

                    m_f = re.search(r'\d{2}/\d{2}/\d{4}', txt_col0)
                    if not m_f:
                        m_f = re.search(r'\d{2}/\d{2}/\d{4}', txt_col0 + " " + txt_col1)

                    if m_f:
                        fecha_act = m_f.group(0)
                        detalle_act = txt_col1.upper()
                        if "BUSQUEDA" not in detalle_act:
                            actuaciones_validas.append((fecha_act, detalle_act))
                except Exception:
                    continue

            # Fallback en texto plano
            if not actuaciones_validas:
                texto_pagina = self.page.inner_text("body")
                lineas = [l.strip() for l in texto_pagina.split("\n") if l.strip()]
                for idx, line in enumerate(lineas):
                    m_f = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                    if m_f:
                        fecha_act = m_f.group(1)
                        linea_limpia = re.sub(r'\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2})?', '', line).strip()
                        if len(linea_limpia) > 3:
                            detalle_act = linea_limpia.upper()
                        elif (idx + 1) < len(lineas):
                            detalle_act = lineas[idx + 1].upper()
                        else:
                            detalle_act = ""
                        actuaciones_validas.append((fecha_act, detalle_act))

            if not datos["FECHA INICIO JUICIO"] and actuaciones_validas:
                datos["FECHA INICIO JUICIO"] = actuaciones_validas[-1][0]

            # 3. Clasificación con Similitud Semántica
            estado_encontrado = False
            for fecha_act, detalle_act in actuaciones_validas:
                etapa, fase, score = self.extractor.evaluar_similitud_semantica(detalle_act)
                if etapa and score >= 0.7:
                    datos["FECHA INICIAL FASE ACTUAL"] = fecha_act
                    datos["ETAPA_PROCESAL"] = etapa
                    datos["FASE_PROCESAL"] = fase
                    estado_encontrado = True
                    print(f"[+] Match en Ruta Respaldo DOM (Score {score}): '{fase}' en fecha {fecha_act}")
                    break

            if not estado_encontrado and actuaciones_validas:
                datos["FECHA INICIAL FASE ACTUAL"] = actuaciones_validas[0][0]
                datos["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                datos["FASE_PROCESAL"] = actuaciones_validas[0][1][:100]

            return datos
        except Exception as e:
            print(f"[ERROR] Inconveniente al leer actuaciones en Ruta Respaldo: {e}")
            return datos

    def cerrar_navegador(self):
        """Cierra la sesión del navegador."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("[*] Navegador cerrado.")
