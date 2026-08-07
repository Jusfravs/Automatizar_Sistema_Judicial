# src/motor_busqueda_web.py
import os
import re
import json
from time import monotonic
from traceback import format_exc
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
    def __init__(self, url_portal, navegacion=None):
        self.url_portal = url_portal
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.extractor = AgenteExtractor()
        self.nav_arbol = NavegadorArbolContenido()
        self.paquetes_api_interceptados = []
        self.datos_extraidos = None
        self.navegacion = {
            "captcha_timeout_ms": 300000,
            "captcha_render_timeout_ms": 15000,
            "resultados_timeout_ms": 30000,
            "datos_generales_timeout_ms": 30000,
            "actuaciones_timeout_ms": 30000,
            "pantalla_final_timeout_ms": 30000,
            "pantalla_final_estabilizacion_ms": 1500,
            "max_reintentos_transicion": 2,
        }
        self.navegacion.update(navegacion or {})
        self.ultimo_estado_navegacion = None
        self._busquedas_enviadas = set()

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

    @staticmethod
    def _causa_canonica(numero_juicio):
        """Normaliza el numero de causa para comparar portal y archivo de origen."""
        return re.sub(r"\D", "", str(numero_juicio or ""))

    @staticmethod
    def _causa_para_formulario(numero_juicio):
        """Conserva el formato que exige la m?scara de e-SATJE al escribir la causa."""
        valor = str(numero_juicio or "").strip()
        if re.fullmatch(r"\d{5}-\d{4}-\d{5,}", valor):
            return valor
        causa = BotJudicial._causa_canonica(valor)
        if len(causa) >= 14:
            return f"{causa[:5]}-{causa[5:9]}-{causa[9:]}"
        return valor

    def _cambiar_estado_navegacion(self, causa, anterior, siguiente, accion, **extra):
        self.ultimo_estado_navegacion = siguiente
        evento = {
            "causa": self._causa_canonica(causa),
            "estado_anterior": anterior,
            "estado_siguiente": siguiente,
            "accion": accion,
            **extra,
        }
        logger.info("[NAVEGACION_ESATJE] %s", json.dumps(evento, ensure_ascii=False, default=str))

    def _input_causa_unico(self):
        selector = "input[formcontrolname='numeroCausa'], input[formcontrolname='numeroJuicio'], input[placeholder*='Dependencia' i], input[placeholder*='causa' i]"
        locator = self.page.locator(selector)
        if locator.count() != 1:
            raise RuntimeError("INPUT_CAUSA_AMBIGUO_O_AUSENTE")
        return locator.nth(0)

    def _boton_buscar_unico(self):
        boton = self.page.get_by_role("button", name=re.compile(r"^\s*BUSCAR\s*$", re.IGNORECASE))
        if boton.count() == 1:
            return boton.nth(0)

        respaldo = self.page.locator("button[type='submit']:has-text('BUSCAR'), button:has-text('BUSCAR')")
        if respaldo.count() != 1:
            raise RuntimeError("BOTON_BUSCAR_AMBIGUO_O_AUSENTE")
        return respaldo.nth(0)

    def _captcha_renderizado(self):
        """Confirma que Angular ya mont? el control CAPTCHA en el formulario."""
        respuestas = self.page.locator("textarea[name='g-recaptcha-response']")
        widgets = self.page.locator(
            "ngx-recaptcha2, .g-recaptcha, .h-captcha, "
            "iframe[title*='recaptcha' i], iframe[src*='recaptcha' i]"
        )
        return respuestas.count() > 0 or widgets.count() > 0

    def _captcha_visible(self):
        """Indica si el CAPTCHA visible a?n no tiene un token v?lido del operador."""
        respuestas = self.page.locator("textarea[name='g-recaptcha-response']")
        widgets = self.page.locator(
            "ngx-recaptcha2, .g-recaptcha, .h-captcha, "
            "iframe[title*='recaptcha' i], iframe[src*='recaptcha' i]"
        )
        if widgets.count() == 0 and respuestas.count() == 0:
            return False

        for indice in range(respuestas.count()):
            try:
                if respuestas.nth(indice).input_value().strip():
                    return False
            except Exception:
                continue
        return True

    @staticmethod
    def _boton_habilitado(boton):
        clases = boton.get_attribute("class") or ""
        etiqueta = boton.get_attribute("aria-label") or ""
        return (
            boton.is_visible()
            and boton.is_enabled()
            and boton.get_attribute("disabled") is None
            and boton.get_attribute("aria-disabled") != "true"
            and "button-disabled" not in clases.lower()
            and "deshabilitado" not in etiqueta.lower()
        )

    def _preparar_busqueda(self, numero_juicio):
        causa = self._causa_canonica(numero_juicio)
        if not causa:
            raise ValueError("CAUSA_VACIA")

        if not self.regresar_al_buscador():
            raise RuntimeError("NO_SE_PUDO_VOLVER_AL_BUSCADOR")

        campo = self._input_causa_unico()
        campo.fill("")
        campo.press_sequentially(self._causa_para_formulario(numero_juicio), delay=15)
        campo.dispatch_event("input")
        campo.dispatch_event("change")

        if self._causa_canonica(campo.input_value()) != causa:
            raise RuntimeError("CAUSA_NO_CONFIRMADA_EN_CAMPO")

        self._cambiar_estado_navegacion(causa, "PREPARAR_BUSCADOR", "CAUSA_ESCRITA", "escribir_causa")
        return causa

    def _esperar_busqueda_habilitada(self, causa):
        limite = monotonic() + (self.navegacion["captcha_timeout_ms"] / 1000)
        limite_renderizado = min(
            limite,
            monotonic() + (self.navegacion.get("captcha_render_timeout_ms", 15000) / 1000),
        )
        estable = 0
        captcha_renderizado = False
        causa_reescrita = False
        while monotonic() < limite:
            campo = self._input_causa_unico()
            boton = self._boton_buscar_unico()
            causa_correcta = self._causa_canonica(campo.input_value()) == causa
            habilitado = self._boton_habilitado(boton)
            captcha_renderizado = captcha_renderizado or self._captcha_renderizado()
            esperando_renderizado = not captcha_renderizado and monotonic() < limite_renderizado

            if captcha_renderizado and habilitado and not causa_correcta and not causa_reescrita:
                campo.fill("")
                campo.press_sequentially(self._causa_para_formulario(causa), delay=15)
                campo.dispatch_event("input")
                campo.dispatch_event("change")
                causa_reescrita = True
                self.page.wait_for_timeout(250)
                continue

            if not esperando_renderizado and causa_correcta and habilitado:
                estable += 1
                if estable >= 2:
                    self._cambiar_estado_navegacion(causa, "ESPERAR_FIN_CAPTCHA", "BUSQUEDA_HABILITADA", "captcha_finalizado")
                    return boton
            else:
                estable = 0
            self.page.wait_for_timeout(250)

        self._cambiar_estado_navegacion(causa, "ESPERAR_FIN_CAPTCHA", "CAPTCHA_TIMEOUT", "espera_pasiva_timeout")
        raise PlaywrightTimeoutError("CAPTCHA_TIMEOUT: BUSCAR no quedo habilitado")

    def _enviar_busqueda_una_vez(self, causa, intento_id):
        clave = (causa, intento_id)
        if clave in self._busquedas_enviadas:
            raise RuntimeError("DOBLE_CLICK_BUSCAR_BLOQUEADO")

        campo = self._input_causa_unico()
        boton = self._boton_buscar_unico()
        if self._causa_canonica(campo.input_value()) != causa:
            raise RuntimeError("CAUSA_CAMBIO_ANTES_DE_BUSCAR")
        if not self._boton_habilitado(boton):
            raise RuntimeError("BUSCAR_NO_HABILITADO")

        self._busquedas_enviadas.add(clave)
        boton.click()
        self._cambiar_estado_navegacion(
            causa,
            "BUSQUEDA_HABILITADA",
            "BUSQUEDA_ENVIADA",
            "click_buscar",
            intento_id=intento_id,
            click_numero=1,
        )

    def _filas_resultado_coincidentes(self, causa):
        causa = self._causa_canonica(causa)
        filas = self.page.locator("table tbody tr, table tr, mat-row, [role='grid'] [role='row'], [role='row']")
        coincidencias = []
        for indice in range(filas.count()):
            fila = filas.nth(indice)
            try:
                if fila.is_visible() and causa in self._causa_canonica(fila.inner_text()):
                    coincidencias.append(fila)
            except Exception:
                continue
        return coincidencias

    def _esperar_resultados(self, causa):
        limite = monotonic() + (self.navegacion["resultados_timeout_ms"] / 1000)
        while monotonic() < limite:
            if "/causas" in self.page.url.lower():
                enlaces_movimientos = self.page.locator(
                    "a[aria-label*='movimientos' i], a:has(mat-icon:has-text('folder_open'))"
                )
                if enlaces_movimientos.count() == 1 and enlaces_movimientos.first.is_visible():
                    self._cambiar_estado_navegacion(
                        causa, "BUSQUEDA_ENVIADA", "RESULTADOS_LISTOS", "validar_vista_causas"
                    )
                    return enlaces_movimientos.first
            texto = self.page.inner_text("body").upper()
            if "REGISTROS ENCONTRADOS: 0" in texto or "NO SE ENCONTRARON RESULTADOS" in texto:
                self._cambiar_estado_navegacion(causa, "BUSQUEDA_ENVIADA", "SIN_RESULTADOS", "validar_resultados")
                return "SIN_RESULTADOS"

            coincidencias = self._filas_resultado_coincidentes(causa)
            if len(coincidencias) == 1:
                self._cambiar_estado_navegacion(causa, "BUSQUEDA_ENVIADA", "RESULTADOS_LISTOS", "validar_resultados")
                return coincidencias[0]
            if len(coincidencias) > 1:
                self._cambiar_estado_navegacion(causa, "BUSQUEDA_ENVIADA", "RESULTADO_AMBIGUO", "validar_resultados")
                raise RuntimeError("RESULTADO_AMBIGUO")
            self.page.wait_for_timeout(250)

        raise PlaywrightTimeoutError("RESULTADOS_TIMEOUT")

    def _boton_carpeta_en_fila(self, fila, contexto):
        selectores = (
            "button:has(i.fa-folder), a:has(i.fa-folder), button:has(i.fa-folder-open), a:has(i.fa-folder-open)",
            "[role='link']:has(i.material-icons:has-text('folder')), [role='link']:has(i:has-text('folder'))",
            "button[aria-label*='detalle' i], a[aria-label*='detalle' i], [role='link'][aria-label*='detalle' i]",
            "[mattooltip='Ver archivos'], [role='link'][aria-label*='archivo' i]",
        )
        for selector in selectores:
            botones = fila.locator(selector)
            if botones.count() == 1:
                return botones.nth(0)

        accionables = fila.locator("button, a, [role='link'], [role='button'], [mattooltip='Ver archivos']")
        candidatos = []
        for indice in range(accionables.count()):
            accionable = accionables.nth(indice)
            try:
                etiqueta = " ".join(
                    filtro for filtro in (
                        accionable.get_attribute("aria-label"),
                        accionable.get_attribute("title"),
                        accionable.inner_text(),
                    ) if filtro
                ).upper()
                tiene_icono = accionable.locator(
                    "i.fa-folder, i.fa-folder-open, i.material-icons:has-text('folder'), i:has-text('folder')"
                ).count() > 0
                if "CARPETA" in etiqueta or "ARCHIVO" in etiqueta or tiene_icono:
                    candidatos.append(accionable)
            except Exception:
                continue
        if len(candidatos) != 1:
            raise RuntimeError(f"CARPETA_AMBIGUA_O_AUSENTE:{contexto}")
        return candidatos[0]

    def _abrir_detalle_causa(self, causa, fila):
        if "/causas" in self.page.url.lower():
            enlace_movimientos = self.page.locator(
                "a[aria-label*='movimientos' i], a:has(mat-icon:has-text('folder_open'))"
            )
            if enlace_movimientos.count() != 1:
                raise RuntimeError("ENLACE_MOVIMIENTOS_AUSENTE_O_AMBIGUO")
            etiqueta = enlace_movimientos.first.get_attribute("aria-label") or ""
            if causa not in self._causa_canonica(etiqueta):
                raise RuntimeError("ENLACE_MOVIMIENTOS_NO_CORRESPONDE_A_CAUSA")
            enlace_movimientos.first.click()
            self.page.wait_for_url(
                re.compile(r"/movimientos(?:[/?#]|$)"),
                timeout=self.navegacion["datos_generales_timeout_ms"],
            )
            enlace_detalle = self.page.locator(
                "[mattooltip='Ver detalle del proceso judicial'], "
                "[aria-label*='detalle del proceso judicial' i]"
            )
            if enlace_detalle.count() != 1:
                raise RuntimeError("ENLACE_DETALLE_PROCESO_AUSENTE_O_AMBIGUO")
            enlace_detalle.first.click()
            self.page.wait_for_url(
                re.compile(r"/actuaciones(?:[/?#]|$)"),
                timeout=self.navegacion["datos_generales_timeout_ms"],
            )
            self._cambiar_estado_navegacion(
                causa, "RESULTADOS_LISTOS", "DETALLE_CAUSA_ABIERTO", "click_movimientos_y_detalle"
            )
            return
        if causa not in self._causa_canonica(fila.inner_text()):
            raise RuntimeError("FILA_NO_CORRESPONDE_A_CAUSA")
        carpeta = self._boton_carpeta_en_fila(fila, "detalle")
        carpeta.scroll_into_view_if_needed()
        if not carpeta.is_visible() or not carpeta.is_enabled():
            raise RuntimeError("CARPETA_DETALLE_NO_ACCIONABLE")
        carpeta.click()
        self._cambiar_estado_navegacion(causa, "RESULTADOS_LISTOS", "DETALLE_CAUSA_ABIERTO", "click_carpeta_detalle")

    def _esperar_datos_generales(self, causa):
        limite = monotonic() + (self.navegacion["datos_generales_timeout_ms"] / 1000)
        while monotonic() < limite:
            texto = self.page.inner_text("body")
            texto_normalizado = texto.upper()
            if (
                "DATOS GENERALES" in texto_normalizado
                and "NUMERO DE PROCESO" in texto_normalizado
                and causa in self._causa_canonica(texto)
            ):
                self._cambiar_estado_navegacion(causa, "DETALLE_CAUSA_ABIERTO", "DATOS_GENERALES_LISTOS", "validar_datos_generales")
                return True
            self.page.wait_for_timeout(250)
        raise PlaywrightTimeoutError("DATOS_GENERALES_TIMEOUT")

    def _esperar_pantalla_final_estable(self, causa):
        """Espera a que terminen de renderizar actuaciones y controles de archivos."""
        limite = monotonic() + (self.navegacion["pantalla_final_timeout_ms"] / 1000)
        firma_anterior = None
        estable = 0
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        while monotonic() < limite:
            texto = self.page.inner_text("body")
            carpetas = self.page.locator(
                "[mattooltip='Ver archivos'], [role='link'][aria-label*='archivos' i]"
            )
            firma = (len(texto), carpetas.count(), self.page.locator(".fila").count())
            if "INFORMACION DEL PROCESO" in texto.upper() and carpetas.count() > 0 and firma == firma_anterior:
                estable += 1
                if estable >= 3:
                    self.page.wait_for_timeout(self.navegacion["pantalla_final_estabilizacion_ms"])
                    self._cambiar_estado_navegacion(
                        causa, "DATOS_GENERALES_LISTOS", "PANTALLA_FINAL_ESTABLE", "estabilizar_actuaciones"
                    )
                    return True
            else:
                estable = 0
            firma_anterior = firma
            self.page.wait_for_timeout(250)
        raise PlaywrightTimeoutError("PANTALLA_FINAL_NO_ESTABLE")

    def _descriptores_carpetas_actuaciones(self):
        filas = self.page.locator("table tbody tr, table tr, [role='row'], mat-row, .fila")
        descriptores = []
        vistos = set()
        for indice in range(filas.count()):
            fila = filas.nth(indice)
            try:
                if not fila.is_visible():
                    continue
                texto = " ".join(fila.inner_text().split())
                if not texto:
                    continue
                carpeta = self._boton_carpeta_en_fila(fila, "actuaciones")
                if not carpeta.is_visible():
                    continue
                clave = re.sub(r"\s+", " ", texto.upper())[:300]
                if clave not in vistos:
                    vistos.add(clave)
                    descriptores.append({"clave": clave, "indice_visual": indice, "texto": texto})
            except RuntimeError:
                continue
        return descriptores

    def _localizar_fila_carpeta(self, descriptor):
        filas = self.page.locator("table tbody tr, table tr, [role='row'], mat-row, .fila")
        candidatos = []
        for indice in range(filas.count()):
            fila = filas.nth(indice)
            try:
                texto = re.sub(r"\s+", " ", fila.inner_text().upper())[:300]
                if fila.is_visible() and texto == descriptor["clave"]:
                    candidatos.append(fila)
            except Exception:
                continue
        if len(candidatos) != 1:
            raise RuntimeError("CARPETA_NO_RELOCALIZABLE")
        return candidatos[0]

    def _esperar_actuaciones(self, causa):
        limite = monotonic() + (self.navegacion["actuaciones_timeout_ms"] / 1000)
        senales = ("INFORMACION DEL PROCESO", "EXPORTAR PDF", "AMPLIAR TODO", "CONTRAER TODO")
        while monotonic() < limite:
            texto = self.page.inner_text("body").upper()
            if any(senal in texto for senal in senales):
                self._cambiar_estado_navegacion(causa, "ABRIR_CARPETA", "ACTUACIONES_LISTAS", "validar_actuaciones")
                return True
            self.page.wait_for_timeout(250)
        raise PlaywrightTimeoutError("ACTUACIONES_TIMEOUT")

    def _volver_a_datos_generales(self, causa):
        for nombre in ("Cerrar", "Regresar"):
            boton = self.page.get_by_role("button", name=re.compile(rf"^\s*{nombre}\s*$", re.IGNORECASE))
            if boton.count() == 1:
                boton.nth(0).click()
                try:
                    self._esperar_datos_generales(causa)
                    return True
                except PlaywrightTimeoutError:
                    continue
        try:
            self.page.go_back()
            self._esperar_datos_generales(causa)
            return True
        except Exception:
            return False

    def _volver_al_buscador(self, causa):
        """Regresa al formulario y verifica que el ?nico campo de causa est? disponible."""
        for _ in range(3):
            try:
                campo = self._input_causa_unico()
                if campo.is_visible():
                    self._cambiar_estado_navegacion(
                        causa, "VOLVER_AL_BUSCADOR", "BUSCADOR_LISTO", "validar_formulario"
                    )
                    return True
            except RuntimeError:
                pass

            boton = self.page.get_by_role(
                "button", name=re.compile(r"^\s*Regresar\s*$", re.IGNORECASE)
            )
            if boton.count() == 1 and boton.nth(0).is_visible():
                boton.nth(0).click()
            else:
                try:
                    self.page.go_back()
                except Exception:
                    break
            self.page.wait_for_timeout(250)

        raise RuntimeError("NO_SE_PUDO_VOLVER_AL_BUSCADOR")

    @staticmethod
    def _clave_archivo(valor):
        return re.sub(r"[^A-Za-z0-9_-]+", "_", str(valor or "")).strip("_")[:80] or "sin_clave"

    def _guardar_evidencia_fallo(self, causa, estado, error, carpeta=None):
        """Guarda evidencia diagn?stica sin interrumpir el tratamiento del error."""
        try:
            directorio = os.path.join("data", "temp_htmls")
            os.makedirs(directorio, exist_ok=True)
            sufijo = "_".join(
                self._clave_archivo(valor)
                for valor in (self._causa_canonica(causa), estado, carpeta)
                if valor
            )
            base = os.path.join(directorio, sufijo)
            if self.page and not self.page.is_closed():
                try:
                    self.page.screenshot(path=f"{base}.png", full_page=True)
                except Exception:
                    pass
                try:
                    with open(f"{base}.html", "w", encoding="utf-8") as archivo:
                        archivo.write(self.page.content())
                except Exception:
                    pass
                url = self.page.url
            else:
                url = None

            evidencia = {
                "causa": self._causa_canonica(causa),
                "estado": estado,
                "carpeta": carpeta,
                "url": url,
                "error": str(error),
                "traza": format_exc(),
                "ultimo_paquete_api": self.paquetes_api_interceptados[-1] if self.paquetes_api_interceptados else None,
            }
            with open(f"{base}.json", "w", encoding="utf-8") as archivo:
                json.dump(evidencia, archivo, ensure_ascii=False, indent=2, default=str)
        except Exception as exc:
            logger.warning("[NAVEGACION_ESATJE] No se pudo guardar evidencia: %s", exc)

    def _paquetes_api_de_carpeta(self, paquetes, causa):
        """A?sla paquetes posteriores al clic de carpeta y descarta respuestas no relacionadas."""
        causa = self._causa_canonica(causa)
        seleccionados = []
        for paquete in paquetes:
            url = str(paquete.get("url", "")).lower()
            contenido = json.dumps(paquete.get("data", ""), ensure_ascii=False, default=str)
            contenido_canonico = self._causa_canonica(contenido)
            es_actuacion = "actuacion" in url
            contiene_causa = causa and causa in contenido_canonico
            contiene_otro_identificador = bool(re.search(r"\d{10,}", contenido))
            if es_actuacion and (contiene_causa or not contiene_otro_identificador):
                seleccionados.append(paquete)
        return seleccionados

    def _metadatos_carpeta(self, causa, descriptor):
        texto = re.sub(r"\s+", " ", descriptor.get("texto", "")).strip()
        dependencia = re.search(
            r"DEPENDENCIA JURISDICCIONAL\s*:\s*(.*?)(?=\s+CIUDAD\s*:|$)",
            texto,
            re.IGNORECASE,
        )
        ciudad = re.search(r"CIUDAD\s*:\s*(.*?)(?=\s+\d{1,3}\s+\d{2}/\d{2}/\d{4}|$)", texto, re.IGNORECASE)
        return {
            "CAUSA": self._causa_canonica(causa),
            "CLAVE_CARPETA": descriptor["clave"],
            "INSTANCIA_CARPETA": descriptor.get("indice_visual"),
            "DEPENDENCIA_JURISDICCIONAL": dependencia.group(1).strip() if dependencia else None,
            "CIUDAD_CARPETA": ciudad.group(1).strip() if ciudad else None,
        }

    def _aplicar_inferencia_consolidada(self, datos):
        actuaciones = datos.get("HISTORIAL_ACTUACIONES", [])
        if not actuaciones:
            return datos

        from src.agente_extractor import MotorInferenciaProcesal
        inferencia = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones)
        if not inferencia or not inferencia.get("ULTIMA_ETAPA"):
            return datos

        datos["ETAPA_PROCESAL"] = inferencia.get("ULTIMA_ETAPA")
        datos["FASE_PROCESAL"] = inferencia.get("ULTIMA_FASE")
        datos["FECHA INICIAL FASE ACTUAL"] = inferencia.get("FECHA_FIN_ULTIMA_FASE")
        datos["ULTIMA ETAPA"] = inferencia.get("ULTIMA_ETAPA")
        datos["ULTIMA FASE"] = inferencia.get("ULTIMA_FASE")
        datos["FECHA FIN ULTIMA FASE"] = inferencia.get("FECHA_FIN_ULTIMA_FASE")
        datos["ETAPA ACTUAL"] = inferencia.get("ETAPA_ACTUAL") or inferencia.get("ULTIMA_ETAPA")
        datos["FASE ACTUAL"] = inferencia.get("FASE_ACTUAL") or inferencia.get("ULTIMA_FASE")
        datos["FECHA INICIO FASE ACTUAL"] = inferencia.get("FECHA_FIN_ULTIMA_FASE")
        if inferencia.get("MENSAJE_ESPECIAL"):
            datos["COMENTARIO_ULTIMO"] = inferencia.get("MENSAJE_ESPECIAL")
        return datos

    def _procesar_todas_las_carpetas(self, causa):
        descriptores = self._descriptores_carpetas_actuaciones()
        if not descriptores:
            raise RuntimeError("SIN_CARPETAS_ACTUACIONES")

        resultados = []
        errores = []
        for descriptor in descriptores:
            try:
                fila = self._localizar_fila_carpeta(descriptor)
                carpeta = self._boton_carpeta_en_fila(fila, "actuaciones")
                cursor_api = len(self.paquetes_api_interceptados)
                carpeta.scroll_into_view_if_needed()
                carpeta.click()
                self._cambiar_estado_navegacion(causa, "DATOS_GENERALES_LISTOS", "ABRIR_CARPETA", "click_carpeta_actuaciones", carpeta=descriptor["clave"])
                self._esperar_actuaciones(causa)
                paquetes_carpeta = self._paquetes_api_de_carpeta(
                    self.paquetes_api_interceptados[cursor_api:], causa
                )
                datos = self._ejecutar_extraccion_detalles(
                    causa, paquetes_api=paquetes_carpeta, carpeta=descriptor["clave"]
                )
                if isinstance(datos, dict):
                    datos["ORIGEN_CARPETA"] = descriptor
                    datos["ORIGEN_DATA"] = "API" if paquetes_carpeta else "DOM"
                    datos.setdefault("HISTORIAL_ACTUACIONES", [])
                    resultados.append(datos)
                if not self._volver_a_datos_generales(causa):
                    raise RuntimeError("NO_SE_PUDO_VOLVER_A_DATOS_GENERALES")
            except Exception as exc:
                errores.append({"carpeta": descriptor, "error": str(exc)})
                logger.warning("[NAVEGACION_ESATJE] Carpeta parcial %s: %s", descriptor["clave"], exc)
                self._guardar_evidencia_fallo(causa, "ERROR_CARPETA", exc, descriptor["clave"])
                self._volver_a_datos_generales(causa)

        if not resultados:
            raise RuntimeError("CARPETAS_SIN_EXTRACCION")

        consolidado = dict(resultados[0])
        actuaciones = []
        vistas = set()
        for datos in resultados:
            for actuacion in datos.get("HISTORIAL_ACTUACIONES", []):
                enriquecida = dict(actuacion)
                enriquecida.update(self._metadatos_carpeta(causa, datos["ORIGEN_CARPETA"]))
                enriquecida["ORIGEN_CARPETA"] = datos["ORIGEN_CARPETA"]["clave"]
                enriquecida["ORIGEN_DATA"] = datos.get("ORIGEN_DATA")
                clave = (
                    enriquecida.get("fecha"),
                    enriquecida.get("detalle"),
                    enriquecida["ORIGEN_CARPETA"],
                )
                if clave not in vistas:
                    vistas.add(clave)
                    actuaciones.append(enriquecida)
        consolidado["HISTORIAL_ACTUACIONES"] = actuaciones
        consolidado["CARPETAS_PROCESADAS"] = [d["ORIGEN_CARPETA"] for d in resultados]
        consolidado["ERRORES_CARPETAS"] = errores
        consolidado["ESTADO_NAVEGACION"] = "PARCIAL" if errores else "COMPLETADO"
        self._aplicar_inferencia_consolidada(consolidado)
        return consolidado

    def _procesar_flujo_autonomo(self, numero_juicio):
        causa_original = str(numero_juicio or "").strip()
        causa = self._causa_canonica(causa_original)
        self.paquetes_api_interceptados.clear()
        self._busquedas_enviadas.clear()
        max_intentos = int(self.navegacion["max_reintentos_transicion"])

        for intento in range(1, max_intentos + 1):
            intento_id = f"{causa}:{intento}"
            try:
                if not self._verificar_sesion_activa():
                    raise RuntimeError("SESION_EXPIRADA")
                causa = self._preparar_busqueda(causa_original)
                self._cambiar_estado_navegacion(causa, "CAUSA_ESCRITA", "ESPERAR_FIN_CAPTCHA", "esperar_buscar_habilitado")
                self._esperar_busqueda_habilitada(causa)
                self._enviar_busqueda_una_vez(causa, intento_id)
                resultado = self._esperar_resultados(causa)
                if resultado == "SIN_RESULTADOS":
                    self.datos_extraidos = {"ESTADO_NAVEGACION": "SIN_RESULTADOS", "HISTORIAL_ACTUACIONES": []}
                    return False

                self._abrir_detalle_causa(causa, resultado)
                self._esperar_datos_generales(causa)
                self._esperar_pantalla_final_estable(causa)
                self.datos_extraidos = self._procesar_todas_las_carpetas(causa)
                self._volver_a_datos_generales(causa)
                self._volver_al_buscador(causa)
                self._cambiar_estado_navegacion(causa, "CONSOLIDAR_EVIDENCIA", "CAUSA_COMPLETADA", "volver_al_buscador")
                return True
            except PlaywrightTimeoutError as exc:
                estado = self.ultimo_estado_navegacion or "CAPTCHA_TIMEOUT"
                self._cambiar_estado_navegacion(causa, estado, "ERROR_NAVEGACION", "timeout", error=str(exc), intento=intento)
                self._guardar_evidencia_fallo(causa, estado, exc)
            except Exception as exc:
                estado = self.ultimo_estado_navegacion or "ERROR_NAVEGACION"
                self._cambiar_estado_navegacion(causa, estado, "ERROR_NAVEGACION", "error", error=str(exc), intento=intento)
                self._guardar_evidencia_fallo(causa, estado, exc)

            if intento < max_intentos:
                try:
                    self._volver_al_buscador(causa)
                except Exception as retorno_error:
                    logger.warning("[NAVEGACION_ESATJE] No se pudo reiniciar el formulario: %s", retorno_error)

        self.datos_extraidos = {
            "ESTADO_NAVEGACION": "ERROR_NAVEGACION",
            "HISTORIAL_ACTUACIONES": [],
        }
        return False

    def procesar_flujo_judicatura(self, numero_juicio):
        """
        Modo Híbrido Asistido con Arquitectura de Ejecución Dual:
        1. Prepara búsqueda en Nivel 0.
        2. Aplica freno de ejecución estricto: wait_for_selector('text="Actor/Ofendido:"', state='visible').
        3. Procesa Ruta Principal (API + Pandas) o Ruta Respaldo (BeautifulSoup4 + DOM).
        """
        logger.info("Iniciando causa: %s", numero_juicio)
        return self._procesar_flujo_autonomo(numero_juicio)
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

    def _ejecutar_extraccion_detalles(self, numero_juicio=None, paquetes_api=None, carpeta=None):
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
        paquetes = self.paquetes_api_interceptados if paquetes_api is None else paquetes_api

        if paquetes:
            # Cargar keywords configurables para detección de mandamiento (opcional)
            try:
                keywords = _load_extraction_keywords()
            except Exception:
                keywords = ['mandam','mandamiento','mandamiento de ejecucion','auto de ejecucion','auto de cumplimiento']

            logger.info("[RUTA PRINCIPAL API] Procesando %s respuesta(s) JSON con Pandas...", len(paquetes))
            try:
                registros = []
                for p in paquetes:
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
                                    f_act = next(
                                        (act.get(campo) for campo in (
                                            "fecha", "fechaActuacion", "fechaProvidencia",
                                            "fechaCrea", "fechaCreacion", "fechaRegistro", "fechaIngreso"
                                        ) if act.get(campo)),
                                        None
                                    )
                                    d_act = act.get("actuacion") or act.get("detalle") or act.get("tipoActuacion") or act.get("actividad")
                                    if d_act:
                                        actuaciones_api.append({
                                            "fecha": str(f_act) if f_act else None,
                                            "detalle": str(d_act).upper()
                                        })

                    if actuaciones_api:
                        datos["HISTORIAL_ACTUACIONES"] = actuaciones_api
                        from src.agente_extractor import MotorInferenciaProcesal
                        res_api = MotorInferenciaProcesal.inferir_estado_procesal(actuaciones_api)
                        if res_api and res_api.get("ULTIMA_ETAPA"):
                            etapa_api = res_api.get("ULTIMA_ETAPA")
                            fase_api = res_api.get("ULTIMA_FASE")
                            fecha_api = res_api.get("FECHA_FIN_ULTIMA_FASE")
                            
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

                    if paquetes:
                        sufijo = f"_{self._clave_archivo(carpeta)}" if carpeta else ""
                        ruta_api = os.path.join(dir_temp, f"{numero_juicio}{sufijo}_api.json")
                        with open(ruta_api, "w", encoding="utf-8") as fa:
                            _json.dump(paquetes, fa, ensure_ascii=False, indent=2)
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
