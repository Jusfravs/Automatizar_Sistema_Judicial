# src/agente_explorador.py
import json
import os
import pandas as pd
from playwright.sync_api import sync_playwright
from src.logger_config import obtener_logger

logger = obtener_logger("AgenteExplorador")


class AgenteExplorador:
    """
    Agente Explorador RPA desacoplado con 3 Fases de Sincronización Angular:
    1. Fase de Interacción Inicial: Espera simple de input, inyección de causa y clic en BUSCAR.
    2. Fase de Resultados: Espera de la grilla/tabla de resultados y clic en la carpeta del expediente.
    3. Fase de Extracción (El Freno Real): Espera estricta wait_for_selector('text="Actor/Ofendido:"')
       únicamente POST-CLIC de carpeta cuando la vista de detalle está abierta e hidratada al 100%.
    """
    def __init__(self, url_portal="https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros", dir_temp="temp_htmls", modo_visible=False):
        self.url_portal = url_portal
        self.dir_temp = dir_temp
        os.makedirs(self.dir_temp, exist_ok=True)
        self.paquetes_json_api = []
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not modo_visible)
        self.page = self.browser.new_page()
        
        # Listener de Intercepción de Red (API Fetching)
        self.page.on("response", self._interceptar_respuesta_api)
        
        logger.info(f"Agente Explorador iniciado en {self.url_portal} (Headless: {not modo_visible}, Dir HTML: {self.dir_temp})")
        self.page.goto(self.url_portal, timeout=60000, wait_until="domcontentloaded")

    def _interceptar_respuesta_api(self, response):
        """Captura respuestas JSON puros de la API de la Judicatura."""
        try:
            url = response.url.lower()
            if any(kw in url for kw in ["/api/", "expel", "proceso", "causa", "actuaciones", "catalogo"]):
                if not any(ext in url for ext in [".js", ".css", ".png", ".ico", ".woff", ".svg"]):
                    if response.status in [200, 201]:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            data = response.json()
                            self.paquetes_json_api.append({
                                "url": response.url,
                                "data": data
                            })
                            logger.info(f"[API FETCH] Capturado JSON desde: {response.url}")
        except Exception as e:
            logger.warning(f"Respuesta no-JSON ignorada: {e}")

    def procesar_datos_api_con_pandas(self):
        """Limpia vectorialmente los paquetes JSON interceptados usando Pandas."""
        if not self.paquetes_json_api:
            return None
        
        try:
            registros = []
            for paquete in self.paquetes_json_api:
                data = paquete.get("data")
                if isinstance(data, dict):
                    registros.append(data)
                elif isinstance(data, list):
                    registros.extend([d for d in data if isinstance(d, dict)])
            
            if not registros:
                return None

            df = pd.json_normalize(registros)
            logger.info(f"[PANDAS CLEANUP] DataFrame compilado con {len(df)} registros desde API JSON.")
            return df
        except Exception as e:
            logger.warning(f"Aviso al procesar JSON API con Pandas: {e}")
            return None

    def regresar_al_buscador(self):
        """Regresa al buscador utilizando esperas explícitas condicionales."""
        try:
            input_busqueda = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial'], input[formcontrolname='numeroJuicio']").first
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
        except Exception as e:
            logger.warning(f"Error al regresar al buscador: {e}")
            self.page.goto(self.url_portal, wait_until="domcontentloaded")
            return False

    def descargar_html_juicio(self, numero_causa):
        """
        Navega y extrae la causa siguiendo las 3 Fases de Sincronización Angular:
        - FASE 1: Interacción Inicial (Sin frenos profundos) -> Inyección + Clic BUSCAR.
        - FASE 2: Resultados -> Esperar grilla de resultados + Clic en la carpeta.
        - FASE 3: Extracción (El Freno Real) -> wait_for_selector('text="Actor/Ofendido:"') POST-CLIC.
        """
        causa_str = str(numero_causa).strip()
        ruta_html = os.path.join(self.dir_temp, f"{causa_str}.html")
        ruta_json = os.path.join(self.dir_temp, f"{causa_str}.json")
        self.paquetes_json_api.clear()
        
        logger.info(f"Iniciando flujo de 3 fases Angular para causa: {causa_str}")

        try:
            # --- FASE 1: INTERACCIÓN INICIAL (SIN FRENOS PROFUNDOS) ---
            selector_input_busqueda = "input[placeholder*='códigoDependencia-Año-Secuencial'], input[formcontrolname='numeroJuicio']"
            input_causa = self.page.locator(selector_input_busqueda).first
            
            if not input_causa.is_visible():
                if "busqueda" not in self.page.url.lower():
                    self.page.goto(self.url_portal, wait_until="domcontentloaded")
                else:
                    self.regresar_al_buscador()

            # Espera simple para visibilidad de la caja de texto
            self.page.wait_for_selector(selector_input_busqueda, state="visible", timeout=10000)
            input_causa.click()
            input_causa.fill("")
            input_causa.press_sequentially(causa_str, delay=15)
            input_causa.dispatch_event("input")
            input_causa.dispatch_event("change")
            logger.info(f"[FASE 1] Causa '{causa_str}' ingresada. Enviando búsqueda...")

            # Clic en el botón BUSCAR o tecla Enter (sin frenos de detalle todavía)
            btn_buscar = self.page.locator("button:has-text('BUSCAR'), button:has-text('Buscar'), button[type='submit']").first
            try:
                btn_buscar.wait_for(state="visible", timeout=2000)
                if btn_buscar.is_enabled():
                    btn_buscar.click()
                else:
                    input_causa.press("Enter")
            except Exception:
                input_causa.press("Enter")

            # --- FASE 2: RESULTADOS (ESPERA DE LA GRILLA Y CLIC EN CARPETA) ---
            logger.info("[FASE 2] Aguardando renderizado de la grilla de resultados/tabla...")
            selector_grilla_resultados = "table, [role='grid'], i.fa-folder, i.fa-folder-open, button:has(.fa-folder)"
            self.page.wait_for_selector(selector_grilla_resultados, state="visible", timeout=10000)

            # Localizar y hacer clic en la carpeta del expediente
            selector_carpeta_relativo = "xpath=//table//tr//td//a | //table//tr//td//button | //i[contains(@class, 'fa-folder')] | //button[contains(@class, 'mat-mdc-button')]"
            carpeta = self.page.locator(selector_carpeta_relativo).first
            if carpeta.is_visible(timeout=5000):
                carpeta.click(force=True)
                logger.info("[FASE 2] Clic en la carpeta del expediente realizado.")

            # --- FASE 3: EXTRACCIÓN (EL FRENO REAL POST-CLIC DE CARPETA) ---
            logger.info("[FASE 3 - EL FRENO REAL] Aguardando hidratación completa del expediente en Angular...")
            selector_freno_estricto = "text=/Actor\\/Ofendido:|Información del proceso|Actuaciones Judiciales|Exportar PDF/i"
            
            # BLOQUEO EXPLÍCITO OBLIGATORIO POST-CLIC DE CARPETA
            self.page.wait_for_selector(selector_freno_estricto, state="visible", timeout=15000)
            logger.info("[FRENO REAL SUPERADO] DOM 100% hidratado con los datos de la Judicatura.")

            # Guardar JSON interceptado de API si existió
            if self.paquetes_json_api:
                with open(ruta_json, "w", encoding="utf-8") as f:
                    json.dump(self.paquetes_json_api, f, ensure_ascii=False, indent=2)
                logger.info(f"[API JSON] Guardados {len(self.paquetes_json_api)} paquetes en: {ruta_json}")

            # Captura de HTML seguro para BeautifulSoup4
            contenido_html = self.page.content()
            with open(ruta_html, "w", encoding="utf-8") as f:
                f.write(contenido_html)

            logger.info(f"[EXTRACCIÓN COMPLETADA] HTML capturado en: {ruta_html} ({len(contenido_html)} bytes)")
            return ruta_html

        except Exception as e:
            logger.error(f"Fallo en secuencia de 3 fases para causa {causa_str}: {e}")
            return None

    def cerrar(self):
        """Cierra el navegador y Playwright."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Agente Explorador cerrado.")
