"""Monitorea las interacciones manuales en e-SATJE sin automatizar los clics."""
import json
import os
import sys
from time import monotonic

RAIZ_PROYECTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ_PROYECTO not in sys.path:
    sys.path.insert(0, RAIZ_PROYECTO)

from src.logger_config import configurar_logging
from src.motor_busqueda_web import BotJudicial


def cargar_navegacion():
    ruta = os.path.join(RAIZ_PROYECTO, "config.json")
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)["navegacion"]


def estado_visible(page):
    return page.evaluate("""() => {
        const campo = document.querySelector("input[formcontrolname='numeroCausa']");
        const boton = [...document.querySelectorAll("button")].find(
            e => e.textContent.trim().toUpperCase() === "BUSCAR"
        );
        return {
            url: location.href,
            causa: campo?.value ?? null,
            captcha: Boolean(document.querySelector(
                "ngx-recaptcha2, textarea[name='g-recaptcha-response'], iframe[title*='recaptcha' i]"
            )),
            buscar: boton ? {
                disabled: boton.disabled,
                aria: boton.getAttribute("aria-label"),
                clase: boton.className,
            } : null,
        };
    }""")


def instalar_monitor(page):
    page.evaluate("""() => {
        window.__monitorEsatjeEventos = [];
        document.addEventListener("click", evento => {
            const objetivo = evento.target;
            const accionable = objetivo.closest(
                "button, a, [role='link'], [role='button'], [mattooltip]"
            );
            const fila = objetivo.closest("tr, mat-row, [role='row'], .fila");
            const describir = nodo => nodo ? {
                etiqueta: nodo.tagName,
                texto: (nodo.innerText || nodo.textContent || "").trim().slice(0, 1000),
                rol: nodo.getAttribute("role"),
                aria: nodo.getAttribute("aria-label"),
                titulo: nodo.getAttribute("title"),
                tooltip: nodo.getAttribute("mattooltip"),
                clase: typeof nodo.className === "string" ? nodo.className : "",
            } : null;
            window.__monitorEsatjeEventos.push({
                instante: new Date().toISOString(),
                objetivo: describir(objetivo),
                accionable: describir(accionable),
                fila: describir(fila),
            });
        }, true);
    }""")


def extraer_eventos(page):
    return page.evaluate("""() => {
        const eventos = window.__monitorEsatjeEventos || [];
        window.__monitorEsatjeEventos = [];
        return eventos;
    }""")


def guardar_evidencia(page, directorio, causa, indice, evento, estado):
    base = os.path.join(directorio, f"monitoreo_{causa}_{indice:03d}")
    with open(f"{base}.json", "w", encoding="utf-8") as archivo:
        json.dump({"evento": evento, "estado": estado}, archivo, ensure_ascii=False, indent=2)
    with open(f"{base}.html", "w", encoding="utf-8") as archivo:
        archivo.write(page.content())
    page.screenshot(path=f"{base}.png", full_page=True)


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/monitorear_esatje.py 23331-2022-02089")
        return 2

    causa_original = sys.argv[1].strip()
    navegacion = cargar_navegacion()
    configurar_logging(
        os.path.join(RAIZ_PROYECTO, "diagnostico_esatje.log"),
        reemplazar=True,
    )
    bot = BotJudicial(navegacion["url_portal"], navegacion)
    directorio = os.path.join(RAIZ_PROYECTO, "data", "temp_htmls")
    os.makedirs(directorio, exist_ok=True)
    causa = BotJudicial._causa_canonica(causa_original)
    indice = 0
    ultimo_estado = None

    try:
        bot.iniciar_navegador(modo_visible=True)
        bot._preparar_busqueda(causa_original)
        bot.page.bring_to_front()
        instalar_monitor(bot.page)
        print("MONITOREO_LISTO: complete CAPTCHA y haga manualmente BUSCAR, detalle y carpetas.")
        limite = monotonic() + 300
        while monotonic() < limite:
            estado = estado_visible(bot.page)
            if estado != ultimo_estado:
                print("ESTADO", json.dumps(estado, ensure_ascii=False))
                ultimo_estado = estado
            for evento in extraer_eventos(bot.page):
                indice += 1
                guardar_evidencia(bot.page, directorio, causa, indice, evento, estado)
                print("EVENTO", indice, json.dumps(evento, ensure_ascii=False))
            bot.page.wait_for_timeout(250)
        return 0
    finally:
        bot.cerrar_navegador()


if __name__ == "__main__":
    raise SystemExit(main())

