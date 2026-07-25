# src/motor_busqueda_web.py
import re
from playwright.sync_api import sync_playwright

class BotJudicial:
    """
    Motor RPA simplificado para la interacción con el portal e-SATJE.
    """
    ARBOL_PROCESAL = {
        "CONGELAMIENTO": ("6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS"),
        "RETENCION": ("6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS"),
        "REMATE": ("6 LIQUIDACION Y EMBARGO", "6.4 REMATE"),
        "EMBARGO": ("6 LIQUIDACION Y EMBARGO", "6.3 EMBARGO"),
        "MANDAMIENTO": ("6 LIQUIDACION Y EMBARGO", "6.2 MANDAMIENTO DE EJECUCION"),
        "LIQUIDADOR": ("6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR"),
        "LIQUIDACION": ("6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR"),
        "EJECUTORIADA": ("5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA"),
        "APELACION": ("5 SENTENCIA", "5.2 APELACION"),
        "SENTENCIA": ("5 SENTENCIA", "5.1 SENTENCIA EMITIDA POR EL JUEZ"),
        "FIJACION": ("4 AUDIENCIA", "4.1 FIJACION FECHA AUDIENCIA"),
        "AUDIENCIA": ("4 AUDIENCIA", "4.2 AUDIENCIA"),
        "CONTESTACION": ("3 CONTESTACION", "3.1 CONTESTACION"),
        "PRENSA": ("2 CITACION", "2.2 CITACION POR PRENSA"),
        "CITACION": ("2 CITACION", "2.1 CITACION"),
        "CALIFICACION": ("1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION"),
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
            print("[+] ¡Documentos detectados! Retomando lectura automática...")
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

        try:
            # 1. Fecha de Inicio General
            try:
                elem_fecha = self.page.locator("text=/Fecha ingreso|Fecha de ingreso/i").first
                texto_fecha = elem_fecha.locator("xpath=following-sibling::* | xpath=..").first.inner_text().strip()
                m_fecha = re.search(r'\d{2}/\d{2}/\d{4}', texto_fecha)
                datos["FECHA INICIO JUICIO"] = m_fecha.group(0) if m_fecha else texto_fecha[:10]
            except Exception:
                pass

            # 2. Escaneo de actuaciones
            self.page.wait_for_timeout(800)
            filas = self.page.locator("table tbody tr, tbody tr, tr").all()
            estado_encontrado = False

            for fila in filas:
                try:
                    cols = fila.locator("td").all()
                    if len(cols) < 2:
                        continue
                        
                    f_text = cols[0].inner_text().strip()
                    m_f = re.search(r'\d{2}/\d{2}/\d{4}', f_text)
                    fecha_actuacion = m_f.group(0) if m_f else f_text[:10]
                    detalle_actuacion = cols[1].inner_text().strip().upper()

                    for palabra_clave, (etapa, fase) in self.ARBOL_PROCESAL.items():
                        if palabra_clave in detalle_actuacion:
                            datos["FECHA INICIAL FASE ACTUAL"] = fecha_actuacion
                            datos["ETAPA_PROCESAL"] = etapa
                            datos["FASE_PROCESAL"] = fase
                            estado_encontrado = True
                            print(f"[+] Match: '{palabra_clave}' -> Etapa: {etapa} | Fase: {fase} ({fecha_actuacion})")
                            break
                    if estado_encontrado:
                        break
                except Exception:
                    continue

            if not estado_encontrado and filas:
                first_cols = filas[0].locator("td").all()
                if len(first_cols) >= 2:
                    f_raw = first_cols[0].inner_text().strip()
                    m_f = re.search(r'\d{2}/\d{2}/\d{4}', f_raw)
                    datos["FECHA INICIAL FASE ACTUAL"] = m_f.group(0) if m_f else f_raw[:10]
                    datos["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                    datos["FASE_PROCESAL"] = first_cols[1].inner_text().strip()[:100]

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