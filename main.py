# main.py
import json
from src.gestor_casos import GestorCasos
from src.motor_busqueda_web import BotJudicial

def main():
    print("=" * 60)
    print("🤖 RPA JUDICATURA - SISTEMA ASISTIDO DE CONSULTA MASIVA")
    print("=" * 60)

    # 1. Cargar Repositorio CRUD y Criterios de Filtrado
    repo = GestorCasos("config.json")
    casos = repo.obtener_casos_pendientes()
    total = len(casos)

    if total == 0:
        print("[-] No existen juicios pendientes para procesar.")
        return

    print(f"[*] Total de causas a procesar: {total}")

    # 2. Iniciar Motor Web de Playwright
    bot = BotJudicial(repo.config['navegacion']['url_portal'])
    bot.iniciar_navegador(modo_visible=True)

    # 3. Bucle Principal RPA
    exitosos = 0
    try:
        for i, numero_juicio in enumerate(casos, 1):
            print(f"\n--- CAUSA {i}/{total}: {numero_juicio} ---")
            
            if bot.procesar_flujo_judicatura(numero_juicio):
                datos = bot.extraer_detalles_juicio()
                if repo.actualizar_caso(numero_juicio, datos):
                    exitosos += 1
                    print(f"[+] Juicio {numero_juicio} guardado exitosamente.")
            
            # Autoguardado preventivo en CSV cada 20 causas
            if i % 20 == 0:
                print(f"\n[!] Autoguardado preventivo de seguridad ({i}/{total})...")
                repo.guardar()

        # Guardado final de la base CSV y exportación consolidada a Excel
        print("\n[!] Bucle finalizado. Guardando y exportando informe...")
        repo.guardar()
        repo.exportar_excel()

    finally:
        bot.cerrar_navegador()

    print("=" * 60)
    print(f"✅ PROCESO COMPLETADO. {exitosos} de {total} causas procesadas con éxito.")
    print("=" * 60)

if __name__ == "__main__":
    main()