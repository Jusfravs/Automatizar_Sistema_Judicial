# src/motor_busqueda_web.py
import re
from playwright.sync_api import sync_playwright
from src.agente_extractor import AgenteExtractor, NavegadorArbolContenido

class BotJudicial:
    """
    Motor RPA simplificado para la interacción con el portal e-SATJE.
    Incorpora búsqueda por similitud semántica y navegación jerárquica en el árbol de información.
    """
    def __init__(self, url_portal):
        self.url_portal = url_portal
        self.playwright = None
        self.browser = None
        self.page = None
        self.extractor = AgenteExtractor()
        self.nav_arbol = NavegadorArbolContenido()

    def iniciar_navegador(self, modo_visible=True):
        """Inicia el navegador Chromium de Playwright."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not modo_visible)
        self.page = self.browser.new_page()
        print(f"[*] Navegador iniciado en {self.url_portal}")
        self.page.goto(self.url_portal, timeout=60000)

    def regresar_al_buscador(self):
        """
        Navegación jerárquica hacia arriba (subir un nivel) para conservar la sesión.
        """
        try:
            self.nav_arbol.subir_nivel("Retornando al nivel raíz de búsqueda")
            input_busqueda = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial']").first
            if input_busqueda.is_visible():
                return True

            btn_filtros = self.page.locator("button:has-text('Filtros de búsqueda'), a:has-text('Filtros de búsqueda'), text=/Filtros de búsqueda/i").first
            btn_regresar = self.page.locator("button:has-text('Regresar'), a:has-text('Regresar'), text=/Regresar/i").first

            for _ in range(3):
                if input_busqueda.is_visible():
                    break
                if btn_filtros.is_visible():
                    btn_filtros.click()
                    self.page.wait_for_timeout(600)
                elif btn_regresar.is_visible():
                    btn_regresar.click()
                    self.page.wait_for_timeout(600)
                else:
                    self.page.go_back()
                    self.page.wait_for_timeout(600)
            return True
        except Exception:
            self.page.goto(self.url_portal, wait_until="domcontentloaded")
            return False

    def procesar_flujo_judicatura(self, numero_juicio):
        """
        Modo Híbrido Asistido con navegación jerárquica en el árbol:
        1. Prepara búsqueda en Nivel 0 (Raíz).
        2. Al detectar llegada a la vista de expediente -> Avanza / baja un nivel a Nivel 1.
        3. Realiza la lectura automática por similitud semántica.
        4. Al cerrar expediente -> Retrocede / sube un nivel a Nivel 0.
        """
        print(f"\n[-] Iniciando causa: {numero_juicio}")
        selector_vista_final = "text=/Información del proceso|Actuaciones Judiciales|Exportar PDF/i"

        while True:
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

                # 2. Espera Pasiva Indefinida a que el operador ingrese al expediente
                print("[*] Navegando en árbol: Aguardando llegada a carpeta de expediente (timeout=0)...")
                self.page.wait_for_selector(selector_vista_final, state="visible", timeout=0)
                self.nav_arbol.bajar_nivel("Expediente abierto -> Profundizando en contenido")

                # 3. Lectura automática con escaneo por similitud semántica
                self.datos_extraidos = self._ejecutar_extraccion_detalles()

                # 4. Esperar a que el usuario cierre el expediente (retorno en árbol)
                print("[*] Aguardando a que el operador cierre el expediente (state: hidden, timeout=0)...")
                self.page.wait_for_selector(selector_vista_final, state="hidden", timeout=0)
                self.nav_arbol.subir_nivel("Expediente cerrado -> Retornando al nivel superior")

                return True

            except Exception as e:
                print(f"[!] Excepción en bucle de observación pasiva: {e}. Reintentando ciclo...")
                self.page.wait_for_timeout(1000)
                continue

    def extraer_detalles_juicio(self):
        """
        Devuelve los datos procesados en la vista actual.
        """
        if getattr(self, 'datos_extraidos', None) is not None:
            res = self.datos_extraidos
            self.datos_extraidos = None
            return res
        return self._ejecutar_extraccion_detalles()

    def _ejecutar_extraccion_detalles(self):
        """
        Extrae y clasifica actuaciones usando similitud semántica.
        """
        datos = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None
        }

        try:
            print("[*] Aguardando renderizado de actuaciones...")
            try:
                self.page.wait_for_selector("text=/\\d{2}\\/\\d{2}\\/\\d{4}/", timeout=10000)
            except Exception:
                self.page.wait_for_timeout(2000)

            # 1. Extraer Fecha de Inicio General de etiquetas superiores
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

            # 2. Extracción de actuaciones en DOM
            filas = self.page.locator("table tbody tr, table tr, tr, [role='row'], .mat-row").all()
            for fila in filas:
                try:
                    cols = fila.locator("td, th, div").all()
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
                    print(f"[+] Match por similitud semántica (score {score}): '{fase}' en fecha {fecha_act}")
                    break

            if not estado_encontrado and actuaciones_validas:
                datos["FECHA INICIAL FASE ACTUAL"] = actuaciones_validas[0][0]
                datos["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                datos["FASE_PROCESAL"] = actuaciones_validas[0][1][:100]

            return datos
        except Exception as e:
            print(f"[ERROR] Inconveniente al leer actuaciones: {e}")
            return datos

    def cerrar_navegador(self):
        """Cierra la sesión del navegador."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("[*] Navegador cerrado.")