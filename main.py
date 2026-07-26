import json
import logging  # Útil para trackear errores sin ensuciar la consola principal
import sys
from src.gestor_casos import GestorCasos
from src.motor_busqueda_web import BotJudicial

def main():
    print("============================================================")
    print("[RPA JUDICATURA] - SISTEMA ASISTIDO DE CONSULTA MASIVA")
    print("============================================================")

    repo = GestorCasos("config.json")
    casos = repo.obtener_casos_pendientes()
    # Permitir iniciar procesamiento desde un número de juicio específico pasado como argumento
    start_num = None
    if len(sys.argv) > 1:
        start_num = sys.argv[1]
        if start_num in casos:
            start_idx = casos.index(start_num)
            print(f"[+] Iniciando procesamiento desde el número de juicio especificado: {start_num}")
            casos = casos[start_idx:]
        else:
            print(f"[!] Número de juicio '{start_num}' no encontrado en la lista de casos pendientes. Se procesarán todos los casos.")
    total = len(casos)

    if total == 0:
        print("[-] No existen juicios pendientes para procesar.")
        return

    print(f"[*] Total de causas a procesar: {total}")

    bot = BotJudicial(repo.config['navegacion']['url_portal'])
    bot.iniciar_navegador(modo_visible=True)

    # Extraer el intervalo de guardado desde la configuración (por defecto 5)
    intervalo_guardado = repo.config.get('sistema', {}).get('intervalo_autoguardado', 5)
    
    exitosos = 0
    casos_fallidos = [] # Estructura para almacenar fallos

    try:
        for i, numero_juicio in enumerate(casos, 1):
            print(f"\n--- CAUSA {i}/{total}: {numero_juicio} ---")
            
            try:
                # Si el bot logra encontrar y procesar el juicio
                if bot.procesar_flujo_judicatura(numero_juicio):
                    datos = bot.extraer_detalles_juicio()
                    
                    if repo.actualizar_caso(numero_juicio, datos):
                        exitosos += 1
                        print(f"[+] Juicio {numero_juicio} guardado exitosamente.")
                    else:
                        print(f"[-] Error al guardar los datos del juicio {numero_juicio} en el repositorio.")
                        casos_fallidos.append(numero_juicio)
                else:
                    print(f"[-] No se pudo procesar el flujo para el juicio {numero_juicio}.")
                    casos_fallidos.append(numero_juicio)

            except Exception as e:
                # Capturamos cualquier error de Playwright o red sin romper el bucle for
                print(f"[!] EXCEPCIÓN crítica en causa {numero_juicio}: {str(e)}")
                casos_fallidos.append(numero_juicio)
            
            # Autoguardado preventivo
            if i % intervalo_guardado == 0:
                print(f"\n[!] Autoguardado preventivo de seguridad ({i}/{total})...")
                repo.guardar()

        print("\n[!] Bucle finalizado. Guardando y exportando informe...")
        repo.guardar()
        repo.exportar_excel()

    finally:
        bot.cerrar_navegador()

    print("[OK] PROCESO COMPLETADO. {} de {} causas procesadas con éxito.".format(exitosos, total))
    
    if casos_fallidos:
        print(f"[!] Hubo {len(casos_fallidos)} causas con errores: {casos_fallidos}")
    print("=" * 60)

if __name__ == "__main__":
    main()