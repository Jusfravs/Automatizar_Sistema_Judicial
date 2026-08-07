import os
import sys

from src.logger_config import configurar_logging, obtener_logger

from src.gestor_casos import GestorCasos
from src.gestor_cola import GestorCola
from src.motor_busqueda_web import BotJudicial


logger = obtener_logger("Main")
RUTA_CASOS_FALLIDOS = os.path.join("data", "casos_fallidos.txt")


def guardar_casos_fallidos(casos_fallidos, ruta_salida=RUTA_CASOS_FALLIDOS):
    """Persiste una causa fallida por línea para facilitar su reanudación."""
    directorio_salida = os.path.dirname(ruta_salida)
    if directorio_salida:
        os.makedirs(directorio_salida, exist_ok=True)

    with open(ruta_salida, "w", encoding="utf-8") as archivo_fallidos:
        for numero_juicio in casos_fallidos:
            archivo_fallidos.write(f"{numero_juicio}\n")


def main():
    configurar_logging()
    logger.info("=" * 60)
    logger.info("[RPA JUDICATURA] - SISTEMA ASISTIDO DE CONSULTA MASIVA")
    logger.info("=" * 60)

    repo = GestorCasos("config.json")
    casos = repo.obtener_casos_pendientes()

    # --- Integración con SQLite (GestorCola) ---
    cola = GestorCola(ruta_db="estado_casos.db")

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

    # Poblar la cola SQLite con los casos del CSV (INSERT OR IGNORE)
    cola.poblar_cola(casos)

    # Permitir iniciar procesamiento desde un número de juicio específico pasado como argumento.
    if len(sys.argv) > 1:
        start_num = sys.argv[1]
        if start_num in casos:
            start_idx = casos.index(start_num)
            logger.info("[+] Iniciando procesamiento desde el número de juicio especificado: %s", start_num)
            casos = casos[start_idx:]
        else:
            logger.warning(
                "[!] Número de juicio '%s' no encontrado en la lista de casos pendientes. "
                "Se procesarán todos los casos.",
                start_num,
            )

    total = len(casos)
    if total == 0:
        logger.info("[-] No existen juicios pendientes para procesar.")
        guardar_casos_fallidos([])
        return

    logger.info("[*] Total de causas a procesar: %s", total)

    bot = BotJudicial(
        repo.config["navegacion"]["url_portal"],
        repo.config.get("navegacion", {}),
    )
    intervalo_guardado = repo.config.get("sistema", {}).get("intervalo_autoguardado", 5)
    exitosos = 0
    casos_fallidos = []

    try:
        bot.iniciar_navegador(modo_visible=True)

        for i, numero_juicio in enumerate(casos, 1):
            logger.info("--- CAUSA %s/%s: %s ---", i, total, numero_juicio)

            try:
                resultado = bot.procesar_flujo_judicatura(numero_juicio)
                if not isinstance(resultado, dict) or not resultado.get("estado"):
                    raise RuntimeError("CONTRATO_RESULTADO_INVALIDO")

                estado = resultado["estado"]
                if estado in {"COMPLETADO", "PARCIAL"}:
                    datos = resultado.get("datos") or {}
                    if not repo.actualizar_caso(numero_juicio, datos):
                        raise RuntimeError("PERSISTENCIA_CSV_RECHAZADA")
                    repo.guardar()
                    estado_sqlite = "PROCESADO" if estado == "COMPLETADO" else "PARCIAL"
                    cola.registrar_resultado_transaccional(
                        numero_juicio,
                        resultado,
                        origen="ESATJE_TRANSACCIONAL",
                        ruta_html=None,
                        estado_final=estado_sqlite,
                    )
                    if estado == "COMPLETADO":
                        exitosos += 1
                        logger.info("[+] Juicio %s completado y persistido.", numero_juicio)
                    else:
                        logger.warning("[!] Juicio %s persistido como PARCIAL.", numero_juicio)
                elif estado == "SIN_RESULTADOS":
                    cola.registrar_resultado_transaccional(
                        numero_juicio,
                        resultado,
                        origen="ESATJE_TRANSACCIONAL",
                        estado_final="SIN_RESULTADOS",
                    )
                    logger.info("[-] Juicio %s sin resultados, estado persistido.", numero_juicio)
                elif estado in {"EXTRACCION_ERROR", "ERROR_NAVEGACION"}:
                    detalle = resultado.get("error") or "ERROR_SIN_DETALLE"
                    cola.registrar_error_extraccion(
                        numero_juicio, "ESATJE_TRANSACCIONAL", detalle
                    )
                    cola.registrar_resultado_transaccional(
                        numero_juicio,
                        resultado,
                        origen="ESATJE_TRANSACCIONAL",
                        estado_final="ERROR",
                    )
                    casos_fallidos.append(numero_juicio)
                    logger.error(
                        "[-] Juicio %s terminó como %s: %s", numero_juicio, estado, detalle
                    )
                else:
                    raise RuntimeError("ESTADO_RESULTADO_DESCONOCIDO:%s" % estado)

                if not resultado.get("regreso_confirmado"):
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
                repo.guardar()

    finally:
        # Estas persistencias deben ejecutarse incluso ante una interrupción o excepción.
        logger.info("[!] Finalizando: guardando y exportando informe...")
        try:
            repo.guardar()
        except Exception:
            logger.exception("No se pudo guardar el CSV final.")

        try:
            repo.exportar_excel()
        except Exception:
            logger.exception("No se pudo exportar el informe final a Excel.")

        try:
            guardar_casos_fallidos(casos_fallidos)
            logger.info("Listado de causas fallidas guardado en: %s", RUTA_CASOS_FALLIDOS)
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
