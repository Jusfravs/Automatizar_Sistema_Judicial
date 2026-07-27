# scratch/analizar_diagnostico.py
import re
from bs4 import BeautifulSoup

def analizar():
    print("============================================================")
    print("[DIAGNOSTICO] ANALISIS DE ERRORES EN diagnostico_output.html")
    print("============================================================")

    with open("diagnostico_output.html", "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    print("\n--- 1. MENSAJES DE ERROR Y ADVERTENCIAS EN EL DOM ---")
    mensajes = soup.find_all(attrs={"class": re.compile(r"error|alert|invalid|warn|sr-only", re.I)})
    for m in mensajes:
        txt = m.get_text(strip=True)
        if txt:
            print(f"[!] Clase: {m.get('class')} | ID: {m.get('id')} | Texto: '{txt}'")

    print("\n--- 2. ESTADO DE LOS BOTONES DEL FORMULARIO ---")
    botones = soup.find_all("button")
    for btn in botones:
        txt = btn.get_text(strip=True)
        disabled = btn.get("disabled")
        aria = btn.get("aria-label")
        cls = btn.get("class")
        print(f"[*] Texto: '{txt}' | Disabled: {disabled} | Aria-Label: '{aria}' | Clases: {cls}")

    print("\n--- 3. DETECCIÓN DE ELEMENTOS RECAPTCHA ---")
    captchas = soup.find_all(re.compile(r"recaptcha", re.I))
    for c in captchas:
        print(f"[*] Elemento Captcha: <{c.name}> | ID: {c.get('id')} | Clases: {c.get('class')}")

    print("\n--- 4. NOTAS O ADVERTENCIAS LEGALES ---")
    notas = soup.find_all(class_=re.compile(r"nota", re.I))
    for n in notas:
        print(f"[*] Nota: {n.get_text(strip=True)}")

if __name__ == "__main__":
    analizar()
