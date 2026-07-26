# src/motor_busqueda_web.py
import re
from playwright.sync_api import sync_playwright

class BotJudicial:
    """
    Motor RPA simplificado para la interacción con el portal e-SATJE.
    """
    ARBOL_PROCESAL = {
        # Etapa 6: Liquidez y embargo
        "CONGELAMIENTO": ("6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS"),
        "RETENCION": ("6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS"),
        "REMATE": ("6 LIQUIDACION Y EMBARGO", "6.4 REMATE"),
        "EMBARGO": ("6 LIQUIDACION Y EMBARGO", "6.3 EMBARGO"),
        "MANDAMIENTO": ("6 LIQUIDACION Y EMBARGO", "6.2 MANDAMIENTO DE EJECUCION"),
        "LIQUIDADOR": ("6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR"),
        "LIQUIDACION": ("6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR"),
        
        # Etapa 5: Sentencia
        "EJECUTORIA": ("5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA"),
        "EJECUTORIADA": ("5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA"),
        "APELACION": ("5 SENTENCIA", "5.2 APELACION"),
        "SENTENCIA": ("5 SENTENCIA", "5.1 SENTENCIA EMITIDA POR EL JUEZ"),
        
        # Etapa 4: Audiencia
        "FIJACION": ("4 AUDIENCIA", "4.1 FIJACION FECHA AUDIENCIA"),
        "AUDIENCIA": ("4 AUDIENCIA", "4.2 AUDIENCIA"),
        
        # Etapa 3: Contestación
        "CONTESTACION": ("3 CONTESTACION", "3.1 CONTESTACION"),
        
        # Etapa 2: Citación
        "PRENSA": ("2 CITACION", "2.2 CITACION POR PRENSA"),
        "CITACION": ("2 CITACION", "2.1 CITACION"),
        "CITAR": ("2 CITACION", "2.1 CITACION"),
        
        # Etapa 1: Presentación y calificación
        "CALIFICACION": ("1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION"),
        "CALIFICA": ("1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION"),
        "DEMANDA": ("1 PRESENTACION Y CALIFICACION", "1.1 PRESENTAR DEMANDA")
    }

    def __init__(self, url_portal):
        self.url_portal = url_portal
        self.playwright = None
        self.browser = None
        self.page = None

    def iniciar_navegador(self, modo_visible=True):
        """Inicia el navegador Chromium de Playwright."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not modo_visible)
        self.page = self.browser.new_page()
        print(f"[*] Navegador iniciado en {self.url_portal}")
        self.page.goto(self.url_portal, timeout=60000)

    def regresar_al_buscador(self):
        """Navegación interna para conservar la sesión y evitar Captchas excesivos."""
        try:
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
        Modo Asistido: Llenado de número de causa y espera dinámica de vista de documentos.
        """
        print(f"\n[-] Iniciando causa: {numero_juicio}")
        try:
            input_causa = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial']").first
            
            if not input_causa.is_visible():
                if "busqueda" not in self.page.url.lower():
                    self.page.goto(self.url_portal, wait_until="domcontentloaded")
                else:
                    self.regresar_al_buscador()

            input_causa.wait_for(state="visible", timeout=10000)
            input_causa.fill("")
            input_causa.fill(str(numero_juicio).strip())
            
            print(f"[!] Causa '{numero_juicio}' lista en el buscador.")
            print("[!] Por favor, resuelve Captcha / dale a BUSCAR y entra al expediente...")
            print("[*] Aguardando llegada a la pantalla 'Información del proceso'...")
            
            self.page.wait_for_selector(
                "text=/Información del proceso|Actuaciones Judiciales/i", 
                timeout=300000
            )
            print("[+] ¡Llegada a 'Información del proceso' detectada! Retomando lectura automática...")
            return True

        except Exception as e:
            print(f"[ERROR] Timeout o fallo al esperar la vista del juicio {numero_juicio}: {e}")
            return False

    def extraer_detalles_juicio(self):
        """
        Extrae la fecha de inicio y la actuación procesal correspondiente.
        """
        datos = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None
        }
        estado_encontrado = False

        try:
            # 1. Esperar dinámicamente la carga de las actuaciones (AJAX)
            print("[*] Aguardando renderizado de actuaciones...")
            try:
                self.page.wait_for_selector("text=/\\d{2}\\/\\d{2}\\/\\d{4}/", timeout=10000)
                print("[+] Actuaciones cargadas dinámicamente.")
            except Exception:
                self.page.wait_for_timeout(2000)

            # 2. Intentar extraer Fecha de Inicio General de etiquetas superiores
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

            # ESTRATEGIA A: Selectores de filas en DOM
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
                        if "DETALLE" not in detalle_act or "RAZON" in detalle_act or "ABANDONO" in detalle_act:
                            actuaciones_validas.append((fecha_act, detalle_act))
                except Exception:
                    continue

            # ESTRATEGIA B: Si no se hallaron filas con DOM, analizar el texto completo de la página
            if len(actuaciones_validas) == 0:
                print("[!] Extracción DOM vacía. Usando scanner de texto plano...")
                texto_pagina = self.page.inner_text("body")
                lineas = [l.strip() for l in texto_pagina.split("\n") if l.strip()]
                
                for idx, line in enumerate(lineas):
                    m_f = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                    if m_f:
                        fecha_act = m_f.group(1)
                        # Extraer texto adicional de la línea o tomar la siguiente línea
                        linea_limpia = re.sub(r'\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2})?', '', line).strip()
                        if len(linea_limpia) > 3:
                            detalle_act = linea_limpia.upper()
                        elif (idx + 1) < len(lineas):
                            detalle_act = lineas[idx + 1].upper()
                        else:
                            detalle_act = ""

                        if "FECHA DE INGRESO" not in detalle_act and "BUSQUEDA" not in detalle_act:
                            actuaciones_validas.append((fecha_act, detalle_act))

            print(f"[+] Total de actuaciones procesables extraídas: {len(actuaciones_validas)}")

            # Si no se encontró FECHA INICIO JUICIO arriba, usar la fecha de la última actuación (más antigua)
            if not datos["FECHA INICIO JUICIO"] and actuaciones_validas:
                datos["FECHA INICIO JUICIO"] = actuaciones_validas[-1][0]

            # Buscar coincidencias con el árbol procesal (desde la actuación más reciente)
            for fecha_act, detalle_act in actuaciones_validas:
                for palabra_clave, (etapa, fase) in self.ARBOL_PROCESAL.items():
                    if palabra_clave in detalle_act:
                        datos["FECHA INICIAL FASE ACTUAL"] = fecha_act
                        datos["ETAPA_PROCESAL"] = etapa
                        datos["FASE_PROCESAL"] = fase
                        estado_encontrado = True
                        print(f"[+] Coincidencia encontrada: '{palabra_clave}' -> Etapa: {etapa} | Fase: {fase} (Fecha: {fecha_act})")
                        break
                if estado_encontrado:
                    break

            # Fallback si ninguna palabra clave coincidió pero hay actuaciones
            if not estado_encontrado and actuaciones_validas:
                datos["FECHA INICIAL FASE ACTUAL"] = actuaciones_validas[0][0]
                datos["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                datos["FASE_PROCESAL"] = actuaciones_validas[0][1][:100]
                print(f"[!] Sin match exacto en Árbol Procesal. Asignado por defecto: {actuaciones_validas[0][1][:50]}")

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