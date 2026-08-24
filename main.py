import os
import re
import sys

from src.logger_config import configurar_logging, obtener_logger

from src.gestor_casos import GestorCasos
from src.gestor_cola import GestorCola
from src.motor_busqueda_web import BotJudicial


logger = obtener_logger("Main")
RUTA_CASOS_FALLIDOS = os.path.join("data", "casos_fallidos.txt")
TAMANO_BLOQUE_NAVEGADOR = 10
MAXIMO_LOTE = 100

def extraer_ruta_config(argumentos):
    """Extrae --config <ruta> sin alterar los modos de seleccion existentes."""
    argumentos = list(argumentos or [])
    ruta_config = "config.json"
    if "--config" not in argumentos:
        return ruta_config, argumentos

    indice = argumentos.index("--config")
    if indice + 1 >= len(argumentos) or not argumentos[indice + 1].strip():
        raise ValueError("USO_INVALIDO: --config <ruta>")
    ruta_config = argumentos[indice + 1]
    restantes = argumentos[:indice] + argumentos[indice + 2:]
    if "--config" in restantes:
        raise ValueError("USO_INVALIDO: --config solo puede indicarse una vez")
    return ruta_config, restantes


def guardar_casos_fallidos(casos_fallidos, ruta_salida=RUTA_CASOS_FALLIDOS):
    """Persiste una causa fallida por línea para facilitar su reanudación."""
    directorio_salida = os.path.dirname(ruta_salida)
    if directorio_salida:
        os.makedirs(directorio_salida, exist_ok=True)

    with open(ruta_salida, "w", encoding="utf-8") as archivo_fallidos:
        for numero_juicio in casos_fallidos:
            archivo_fallidos.write(f"{numero_juicio}\n")


def actualizar_casos_fallidos_piloto(
    casos_procesados, casos_fallidos, ruta_salida=RUTA_CASOS_FALLIDOS
):
    """Actualiza solo las causas del piloto y conserva los fallos ajenos."""
    existentes = []
    if os.path.isfile(ruta_salida):
        with open(ruta_salida, "r", encoding="utf-8") as archivo:
            existentes = [linea.strip() for linea in archivo if linea.strip()]
    objetivos = {_causa_comparable(causa) for causa in casos_procesados}
    resultado = [
        causa for causa in existentes if _causa_comparable(causa) not in objetivos
    ]
    vistos = {_causa_comparable(causa) for causa in resultado}
    for causa in casos_fallidos:
        comparable = _causa_comparable(causa)
        if comparable and comparable not in vistos:
            resultado.append(causa)
            vistos.add(comparable)
    guardar_casos_fallidos(resultado, ruta_salida)
    return resultado


def _causa_comparable(valor):
    return str(valor or "").replace("-", "").strip()


def motivo_revision_manual_por_formato(causa):
    """Devuelve el motivo cuando una causa no tiene un formato SATJE reconocible."""
    texto = str(causa or "").strip()
    if re.fullmatch(r"\d{5}-\d{4}-\d{4,5}", texto):
        return None
    if re.fullmatch(r"\d{13,14}", texto):
        return None
    return "FORMATO_CAUSA_INVALIDO"


def dividir_en_bloques(casos, tamano_bloque=TAMANO_BLOQUE_NAVEGADOR):
    """Divide un lote largo en sesiones acotadas de navegador."""
    if tamano_bloque < 1:
        raise ValueError("TAMANO_BLOQUE_INVALIDO")
    return [
        list(casos[indice:indice + tamano_bloque])
        for indice in range(0, len(casos), tamano_bloque)
    ]


def seleccionar_casos(casos, argumentos):
    """Aplica modos acotados o el inicio legado sin ampliar silenciosamente el lote."""
    argumentos = list(argumentos or [])
    if not argumentos:
        return list(casos)
    if argumentos[0] == "--solo":
        if len(argumentos) != 2 or not argumentos[1].strip():
            raise ValueError("USO_INVALIDO: --solo <causa>")
        objetivo = _causa_comparable(argumentos[1])
        coincidencia = next(
            (causa for causa in casos if _causa_comparable(causa) == objetivo), None
        )
        if coincidencia is None:
            raise ValueError(f"CAUSA_SOLO_NO_ENCONTRADA:{argumentos[1]}")
        return [coincidencia]
    if argumentos[0] == "--pendientes":
        if len(argumentos) != 1:
            raise ValueError("USO_INVALIDO: --pendientes")
        return list(casos)
    if argumentos[0] == "--reprocesar-filtro":
        if len(argumentos) != 1:
            raise ValueError("USO_INVALIDO: --reprocesar-filtro")
        resultado = []
        vistos = set()
        for causa in casos:
            comparable = _causa_comparable(causa)
            if comparable and comparable not in vistos:
                vistos.add(comparable)
                resultado.append(causa)
        return resultado
    if argumentos[0] == "--lote":
        if len(argumentos) != 2:
            raise ValueError("USO_INVALIDO: --lote <cantidad 2..100>")
        try:
            cantidad = int(argumentos[1])
        except (TypeError, ValueError) as exc:
            raise ValueError("USO_INVALIDO: --lote <cantidad 2..100>") from exc
        if cantidad < 2 or cantidad > MAXIMO_LOTE:
            raise ValueError("LOTE_FUERA_DE_RANGO:2..100")
        return list(casos)[:cantidad]
    if argumentos[0].startswith("--") or len(argumentos) != 1:
        raise ValueError("ARGUMENTOS_INVALIDOS")
    objetivo = _causa_comparable(argumentos[0])
    indice = next(
        (i for i, causa in enumerate(casos) if _causa_comparable(causa) == objetivo),
        None,
    )
    return list(casos) if indice is None else list(casos[indice:])


def guardar_csv_o_fallar(repo):
    if not repo.guardar():
        raise RuntimeError("PERSISTENCIA_ERROR:CSV")


def main(argv=None):
    configurar_logging()
    argumentos = list(sys.argv[1:] if argv is None else argv)
    ruta_config, argumentos = extraer_ruta_config(argumentos)
    logger.info("=" * 60)
    logger.info("[RPA JUDICATURA] - SISTEMA ASISTIDO DE CONSULTA MASIVA")
    logger.info("=" * 60)

    repo = GestorCasos(ruta_config)
    rutas_config = repo.config.get("rutas", {})
    ruta_db = rutas_config.get("archivo_db", "estado_casos.db")
    ruta_casos_fallidos = rutas_config.get(
        "archivo_casos_fallidos", RUTA_CASOS_FALLIDOS
    )
    modo_limitado = argumentos[:1] in (
        ["--solo"], ["--lote"], ["--pendientes"],
        ["--reprocesar-filtro"],
    )
    if modo_limitado:
        repo.filtros["inicio_desde_juicio"] = None
    casos = repo.obtener_casos_pendientes()

    # --- Integración con SQLite (GestorCola) ---
    cola = GestorCola(ruta_db=ruta_db)

    # --- Integración con PostgreSQL (si está configurado) ---
    gestor_pg = None
    config_db = repo.config.get("base_de_datos", {})
    if config_db.get("motor") == "postgres":
        try:
            from src.db_postgres import GestorPostgres
            gestor_pg = GestorPostgres(
                host=config_db.get("host"),
                port=config_db.get("puerto"),
                user=config_db.get("usuario"),
                password=os.getenv(config_db.get("password_env", "POSTGRES_PASSWORD"), ""),
                dbname=config_db.get("nombre_db")
            )
            logger.info("[POSTGRES] Sincronización activa con base de datos '%s'.", config_db.get("nombre_db"))
        except Exception as e:
            logger.warning("[POSTGRES] No se pudo inicializar sincronización PostgreSQL: %s", e)

    # Verificar esquema de la base de datos
    if not cola.verificar_esquema():
        logger.critical(
            "El esquema de la base de datos no es válido. "
            "Ejecute 'python migracion_db.py' para reparar."
        )
        sys.exit(1)

    # Recuperar registros huérfanos (EN_PROCESO → PENDIENTE)
    huerfanos_recuperados = cola.recuperar_huerfanos()
    if huerfanos_recuperados > 0:
        logger.info("Se recuperaron %s registros huérfanos.", huerfanos_recuperados)

    if argumentos[:1] in (["--lote"], ["--pendientes"]):
        total_candidatos = len(casos)
        casos = cola.filtrar_causas_pendientes(casos)
        logger.info(
            "[LOTE LIMITADO] Se omitieron %s causas no pendientes según SQLite.",
            total_candidatos - len(casos),
        )

    casos_antes_seleccion = list(casos)
    casos = seleccionar_casos(casos, argumentos)
    if argumentos[:1] == ["--solo"]:
        logger.info("[MODO PILOTO] Se procesará únicamente la causa: %s", casos[0])
    elif argumentos[:1] == ["--lote"]:
        logger.info(
            "[LOTE LIMITADO] Se procesarán %s causas consecutivas: %s",
            len(casos), casos,
        )
    elif argumentos[:1] == ["--pendientes"]:
        logger.info(
            "[PENDIENTES] Se procesaran %s causas unicas pendientes.",
            len(casos),
        )
    elif argumentos[:1] == ["--reprocesar-filtro"]:
        logger.info(
            "[REPROCESO FILTRO] %s filas representan %s causas unicas.",
            len(casos_antes_seleccion),
            len(casos),
        )
    elif argumentos and casos == casos_antes_seleccion:
        logger.warning(
            "[!] Causa inicial '%s' no encontrada; se conserva el lote completo.",
            argumentos[0],
        )
    elif argumentos:
        logger.info("[+] Iniciando procesamiento desde la causa: %s", casos[0])

    # Poblar SQLite solo con el conjunto que este proceso puede recorrer.
    cola.poblar_cola(casos)

    total = len(casos)
    if total == 0:
        logger.info("[-] No existen juicios pendientes para procesar.")
        guardar_casos_fallidos([], ruta_casos_fallidos)
        return

    logger.info("[*] Total de causas a procesar: %s", total)
    bloques = dividir_en_bloques(casos)
    logger.info(
        "[LOTES] Se ejecutar\u00e1n %s bloque(s) de hasta %s causas; cada bloque usa una sesi\u00f3n nueva.",
        len(bloques), TAMANO_BLOQUE_NAVEGADOR,
    )

    bot = BotJudicial(
        repo.config["navegacion"]["url_portal"],
        repo.config.get("navegacion", {}),
        captcha=repo.config.get("captcha", {}),
    )
    intervalo_guardado = repo.config.get("sistema", {}).get("intervalo_autoguardado", 5)
    exitosos = 0
    casos_fallidos = []
    sesion_abierta = False

    try:
        for i, numero_juicio in enumerate(casos, 1):
            indice_bloque = (i - 1) // TAMANO_BLOQUE_NAVEGADOR
            inicio_bloque = indice_bloque * TAMANO_BLOQUE_NAVEGADOR
            fin_bloque = min(inicio_bloque + TAMANO_BLOQUE_NAVEGADOR, total)
            motivo_formato = motivo_revision_manual_por_formato(numero_juicio)
            if not motivo_formato and (
                i == inicio_bloque + 1 or not sesion_abierta
            ):
                if i == inicio_bloque + 1:
                    logger.info(
                        "[BLOQUE %s/%s] Iniciando sesi\u00f3n para causas %s a %s.",
                        indice_bloque + 1, len(bloques), inicio_bloque + 1, fin_bloque,
                    )
                else:
                    logger.info(
                        "[BLOQUE %s/%s] Reiniciando sesi\u00f3n para continuar desde la causa %s.",
                        indice_bloque + 1, len(bloques), i,
                    )
                bot.iniciar_navegador(modo_visible=True)
                sesion_abierta = True

            logger.info("--- CAUSA %s/%s: %s ---", i, total, numero_juicio)

            try:
                if motivo_formato:
                    resultado = {
                        "estado": "ERROR_VERIFICACION_MANUAL",
                        "error": motivo_formato,
                        "regreso_confirmado": True,
                    }
                else:
                    resultado = bot.procesar_flujo_judicatura(numero_juicio)
                if not isinstance(resultado, dict) or not resultado.get("estado"):
                    raise RuntimeError("CONTRATO_RESULTADO_INVALIDO")

                estado = resultado["estado"]
                if estado in {"COMPLETADO", "PARCIAL", "EXCLUIDO_NO_CORRESPONDE"}:
                    datos = resultado.get("datos") or {}
                    if not repo.actualizar_caso(numero_juicio, datos):
                        raise RuntimeError("PERSISTENCIA_CSV_RECHAZADA")
                    guardar_csv_o_fallar(repo)
                    estado_sqlite = {
                        "COMPLETADO": "PROCESADO",
                        "PARCIAL": "PARCIAL",
                        "EXCLUIDO_NO_CORRESPONDE": "EXCLUIDO_NO_CORRESPONDE",
                    }[estado]
                    cola.registrar_resultado_transaccional(
                        numero_juicio,
                        resultado,
                        origen="ESATJE_TRANSACCIONAL",
                        ruta_html=None,
                        estado_final=estado_sqlite,
                    )
                    if gestor_pg:
                        try:
                            ciudad_pg = repo.filtros.get("sucursal") or "QUITO"
                            gestor_pg.registrar_resultado(numero_juicio, resultado, ciudad=ciudad_pg)
                        except Exception as e:
                            logger.warning("[POSTGRES] Error al persistir expediente %s: %s", numero_juicio, e)
                    if estado == "COMPLETADO":
                        exitosos += 1
                        logger.info("[+] Juicio %s completado y persistido.", numero_juicio)
                    elif estado == "PARCIAL":
                        logger.warning("[!] Juicio %s persistido como PARCIAL.", numero_juicio)
                    else:
                        logger.info(
                            "[-] Juicio %s excluido por no corresponder a la cartera.",
                            numero_juicio,
                        )
                elif estado == "SIN_RESULTADOS":
                    cola.registrar_resultado_transaccional(
                        numero_juicio,
                        resultado,
                        origen="ESATJE_TRANSACCIONAL",
                        estado_final="SIN_RESULTADOS",
                    )
                    if gestor_pg:
                        try:
                            gestor_pg.registrar_error(numero_juicio, origen="ESATJE_TRANSACCIONAL", error_detalle="SIN_RESULTADOS")
                        except Exception as e:
                            logger.warning("[POSTGRES] Error al registrar sin resultados de %s: %s", numero_juicio, e)
                    logger.info("[-] Juicio %s sin resultados, estado persistido.", numero_juicio)
                elif estado in {
                    "EXTRACCION_ERROR",
                    "ERROR_NAVEGACION",
                    "ERROR_VERIFICACION_MANUAL",
                }:
                    detalle = resultado.get("error") or "ERROR_SIN_DETALLE"
                    if estado in {
                        "ERROR_VERIFICACION_MANUAL", "ERROR_NAVEGACION"
                    }:
                        comentario = f"REVISION MANUAL: {detalle}"
                        if not repo.actualizar_caso(
                            numero_juicio,
                            {
                                "COMENTARIO_ULTIMO": comentario,
                                "ETAPA ACTUAL": "REVISION MANUAL",
                                "FASE ACTUAL": "REVISION MANUAL",
                            },
                        ):
                            raise RuntimeError("PERSISTENCIA_CSV_RECHAZADA")
                        guardar_csv_o_fallar(repo)
                    cola.registrar_error_extraccion(
                        numero_juicio, "ESATJE_TRANSACCIONAL", detalle
                    )
                    cola.registrar_resultado_transaccional(
                        numero_juicio,
                        resultado,
                        origen="ESATJE_TRANSACCIONAL",
                        estado_final="ERROR",
                    )
                    if gestor_pg:
                        try:
                            gestor_pg.registrar_error(numero_juicio, origen="ESATJE_TRANSACCIONAL", error_detalle=detalle)
                        except Exception as e:
                            logger.warning("[POSTGRES] Error al registrar error de %s: %s", numero_juicio, e)
                    casos_fallidos.append(numero_juicio)
                    logger.error(
                        "[-] Juicio %s terminó como %s: %s", numero_juicio, estado, detalle
                    )
                else:
                    raise RuntimeError("ESTADO_RESULTADO_DESCONOCIDO:%s" % estado)

                if not resultado.get("regreso_confirmado"):
                    if estado == "ERROR_NAVEGACION":
                        logger.warning(
                            "[REVISION MANUAL] %s sin retorno confirmado; "
                            "se reiniciar\u00e1 la sesi\u00f3n antes de continuar.",
                            numero_juicio,
                        )
                        bot.cerrar_navegador()
                        sesion_abierta = False
                    else:
                        raise RuntimeError("REGRESO_AL_BUSCADOR_NO_CONFIRMADO")

            except Exception as exc:
                logger.exception(
                    "[!] Fallo no recuperable en causa %s; el lote se detiene.",
                    numero_juicio,
                )
                if numero_juicio not in casos_fallidos:
                    casos_fallidos.append(numero_juicio)
                try:
                    cola.registrar_error_extraccion(
                        numero_juicio, "LOTE_DETENIDO", str(exc)
                    )
                except Exception:
                    logger.exception("No se pudo registrar el motivo de detención en SQLite.")
                raise

            # Autoguardado preventivo.
            if i % intervalo_guardado == 0:
                logger.info("[!] Autoguardado preventivo de seguridad (%s/%s)...", i, total)
                guardar_csv_o_fallar(repo)

            if i == fin_bloque:
                casos_bloque = casos[inicio_bloque:fin_bloque]
                logger.info(
                    "[BLOQUE %s/%s] Persistiendo resultados y cerrando navegador.",
                    indice_bloque + 1, len(bloques),
                )
                guardar_csv_o_fallar(repo)
                repo.exportar_excel()
                if modo_limitado:
                    actualizar_casos_fallidos_piloto(
                        casos_bloque, casos_fallidos, ruta_casos_fallidos
                    )
                bot.cerrar_navegador()
                sesion_abierta = False

    finally:
        # Estas persistencias deben ejecutarse incluso ante una interrupción o excepción.
        logger.info("[!] Finalizando: guardando y exportando informe...")
        try:
            if not repo.guardar():
                logger.error("No se pudo guardar el CSV final.")
        except Exception:
            logger.exception("No se pudo guardar el CSV final.")

        try:
            repo.exportar_excel()
        except Exception:
            logger.exception("No se pudo exportar el informe final a Excel.")

        try:
            if modo_limitado:
                fallidos_persistidos = actualizar_casos_fallidos_piloto(
                    casos, casos_fallidos, ruta_casos_fallidos
                )
            else:
                guardar_casos_fallidos(casos_fallidos, ruta_casos_fallidos)
                fallidos_persistidos = casos_fallidos
            logger.info(
                "Listado de causas fallidas guardado en: %s", ruta_casos_fallidos
            )
            logger.info(
                "Causas fallidas persistidas: %s", fallidos_persistidos
            )
        except Exception:
            logger.exception("No se pudo persistir el listado de causas fallidas.")

        try:
            bot.cerrar_navegador()
        except Exception:
            logger.exception("No se pudo cerrar correctamente el navegador.")

    # Estadísticas finales de SQLite
    try:
        stats = cola.obtener_estadisticas()
        logger.info("[SQLite] Estadísticas finales: %s", stats)
    except Exception:
        pass

    logger.info("[OK] PROCESO COMPLETADO. %s de %s causas procesadas con éxito.", exitosos, total)

    if casos_fallidos:
        logger.warning("[!] Hubo %s causas con errores: %s", len(casos_fallidos), casos_fallidos)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
