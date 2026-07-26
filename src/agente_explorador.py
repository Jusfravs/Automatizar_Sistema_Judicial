# src/agente_explorador.py
import os
from playwright.sync_api import sync_playwright
from src.logger_config import obtener_logger

logger = obtener_logger("AgenteExplorador")


class AgenteExplorador:
    """
    Agente Explorador RPA aislante de Playwright.
    Navega por el portal e-SATJE, alcanza la vista de actuaciones y guarda el HTML crudo en disco.
    """
    def __init__(self, url_portal="https://procesosjudiciales.funcionjudicial.gob.ec/busqueda-filtros", dir_temp="temp_htmls", modo_visible=False):
        self.url_portal = url_portal
        self.dir_temp = dir_temp
        os.makedirs(self.dir_temp, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=not modo_visible)
        self.page = self.browser.new_page()
        logger.info(f"Agente Explorador iniciado en {self.url_portal} (Headless: {not modo_visible}, Dir HTML: {self.dir_temp})")
        self.page.goto(self.url_portal, timeout=60000)

    def regresar_al_buscador(self):
        """Navega de retorno al buscador conservando la sesión."""
        try:
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
                    self.page.wait_for_timeout(600)
                elif btn_regresar.is_visible():
                    btn_regresar.click()
                    self.page.wait_for_timeout(600)
                else:
                    self.page.go_back()
                    self.page.wait_for_timeout(600)
            return True
        except Exception as e:
            logger.warning(f"Error al regresar al buscador: {e}")
            self.page.goto(self.url_portal, wait_until="domcontentloaded")
            return False

    def descargar_html_juicio(self, numero_causa):
        """
        Navega hasta la vista de actuaciones para una causa y guarda el HTML crudo en temp_htmls/{numero_causa}.html.
        Retorna la ruta del archivo generado o None en caso de falla.
        """
        causa_str = str(numero_causa).strip()
        ruta_archivo = os.path.join(self.dir_temp, f"{causa_str}.html")
        logger.info(f"Iniciando descarga HTML para causa: {causa_str}")

        try:
            # 1. Asegurar presencia en el buscador e inyectar el número de causa
            input_causa = self.page.locator("input[placeholder*='códigoDependencia-Año-Secuencial']").first
            if not input_causa.is_visible():
                if "busqueda" not in self.page.url.lower():
                    self.page.goto(self.url_portal, wait_until="domcontentloaded")
                else:
                    self.regresar_al_buscador()

            input_causa.wait_for(state="visible", timeout=10000)
            input_causa.click()
            input_causa.fill("")
            input_causa.press_sequentially(causa_str, delay=15)
            input_causa.dispatch_event("input")
            input_causa.dispatch_event("change")
            logger.info(f"Causa '{causa_str}' ingresada en el buscador.")

            # 2. Clic en el botón BUSCAR o presionar Enter
            try:
                btn_buscar = self.page.locator("button:has-text('BUSCAR'), button:has-text('Buscar'), button[type='submit'], .mat-mdc-button:has-text('BUSCAR')").first
                if btn_buscar.is_visible(timeout=2000) and btn_buscar.is_enabled(timeout=2000):
                    btn_buscar.click()
                    logger.info("Clic en botón BUSCAR realizado.")
                else:
                    input_causa.press("Enter")
                    logger.info("Envío por tecla Enter realizado.")
            except Exception as e_buscar:
                logger.warning(f"Aviso en botón BUSCAR, enviando Enter: {e_buscar}")
                input_causa.press("Enter")

            # 3. Esperar tabla de resultados o carpeta
            try:
                self.page.locator("table, mat-table, .fa-folder, .fa-folder-open, .mat-mdc-table, button:has(.fa-folder)").first.wait_for(state="visible", timeout=8000)
                selector_carpeta = (
                    "table tr td i.fa-folder, table tr td i.fa-folder-open, "
                    "table tr td a, table tr td button, .fa-folder, .fa-folder-open, "
                    "i[title*='Detalle'], a[title*='Detalle'], button:has(.fa-folder)"
                )
                carpeta_paso1 = self.page.locator(selector_carpeta).first
                if carpeta_paso1.is_visible(timeout=4000):
                    carpeta_paso1.click(force=True)
                    logger.info("Clic en carpeta de la tabla de resultados.")
            except Exception as e_p1:
                logger.warning(f"Aviso al buscar carpeta de resultados: {e_p1}")

            # 4. Esperar pantalla de 'Datos generales' e ingresar a la carpeta de la dependencia
            try:
                self.page.locator(".fa-folder, .fa-folder-open, button:has(.fa-folder), a:has(.fa-folder), td:last-child button, td:last-child a, td:last-child i").first.wait_for(state="visible", timeout=8000)
                carpetas_dep = self.page.locator("i.fa-folder, i.fa-folder-open, .fa-folder, button:has(.fa-folder), a:has(.fa-folder), td:last-child button, td:last-child a, td:last-child i")
                if carpetas_dep.count() > 0:
                    carpetas_dep.first.click(force=True)
                    logger.info("Clic en carpeta de la dependencia jurisdiccional.")
            except Exception as e_p2:
                logger.warning(f"Aviso al buscar carpeta de dependencia: {e_p2}")

            # 5. Esperar confirmación de la pantalla final 'Información del proceso'
            logger.info("Aguardando confirmación de la vista de actuaciones...")
            self.page.locator("table, mat-table, .mat-mdc-table, tr").first.wait_for(state="visible", timeout=20000)
            self.page.wait_for_timeout(1500)

            # 6. Extraer HTML crudo completo y guardar en temp_htmls/{numero_causa}.html
            contenido_html = self.page.content()
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(contenido_html)

            logger.info(f"HTML extraído exitosamente en: {ruta_archivo} (Tamaño: {len(contenido_html)} caracteres)")
            return ruta_archivo

        except Exception as e:
            logger.error(f"Fallo al extraer HTML de la causa {causa_str}: {e}")
            return None

    def cerrar(self):
        """Cierra el navegador y Playwright."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Agente Explorador cerrado.")
