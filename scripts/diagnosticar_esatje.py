"""Ejecuta una sola causa en e-SATJE para diagnosticar la navegaci?n visible."""
import json
import os
import sys

RAIZ_PROYECTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, RAIZ_PROYECTO)

from src.motor_busqueda_web import BotJudicial


def cargar_navegacion():
    ruta_config = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        return json.load(archivo)["navegacion"]


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/diagnosticar_esatje.py 23331-2022-02089")
        return 2

    numero_causa = sys.argv[1].strip()
    navegacion = cargar_navegacion()
    bot = BotJudicial(navegacion["url_portal"], navegacion)

    try:
        bot.iniciar_navegador(modo_visible=True)
        completado = bot.procesar_flujo_judicatura(numero_causa)
        estado = (bot.datos_extraidos or {}).get("ESTADO_NAVEGACION", "SIN_ESTADO")
        print(f"RESULTADO_DIAGNOSTICO causa={numero_causa} completado={completado} estado={estado}")
        return 0 if completado else 1
    finally:
        bot.cerrar_navegador()


if __name__ == "__main__":
    raise SystemExit(main())

