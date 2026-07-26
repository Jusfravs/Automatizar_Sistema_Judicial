# src/agente_extractor.py
import os
import re
from bs4 import BeautifulSoup


class AgenteExtractor:
    """
    Agente Extractor Offline: Parseador de archivos HTML locales con BeautifulSoup.
    Extrae la fecha de inicio del juicio, la etapa procesal, la fase procesal y el historial de actuaciones.
    """
    ARBOL_PROCESAL = {
        # Etapa 6: Liquidez y embargo
        "CONGELAMIENTO": ("6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS"),
        "RETENCION": ("6 LIQUIDACION Y EMBARGO", "6.5 CONGELAMIENTO DE CUENTAS"),
        "REMATE": ("6 LIQUIDACION Y EMBARGO", "6.4 REMATE"),
        "EMBARGO": ("6 LIQUIDACION Y EMBARGO", "6.3 EMBARGO"),
        "MANDAMIENTO": ("6 LIQUIDACION Y EMBARGO", "6.2 MANDAMIENTO DE EJECUCION"),
        "LIQUIDADOR": ("6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR"),
        "LIQUIDACION": ("6 LIQUIDACION Y EMBARGO", "6.1 LIQUIDACION PERITO LIQUIDADOR"),
        
        # Etapa 5: Sentencia
        "EJECUTORIA": ("5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA"),
        "EJECUTORIADA": ("5 SENTENCIA", "5.3 SENTENCIA EJECUTORIADA"),
        "APELACION": ("5 SENTENCIA", "5.2 APELACION"),
        "SENTENCIA": ("5 SENTENCIA", "5.1 SENTENCIA EMITIDA POR EL JUEZ"),
        
        # Etapa 4: Audiencia
        "FIJACION": ("4 AUDIENCIA", "4.1 FIJACION FECHA AUDIENCIA"),
        "AUDIENCIA": ("4 AUDIENCIA", "4.2 AUDIENCIA"),
        
        # Etapa 3: Contestación
        "CONTESTACION": ("3 CONTESTACION", "3.1 CONTESTACION"),
        
        # Etapa 2: Citación
        "PRENSA": ("2 CITACION", "2.2 CITACION POR PRENSA"),
        "CITACION": ("2 CITACION", "2.1 CITACION"),
        "CITAR": ("2 CITACION", "2.1 CITACION"),
        
        # Etapa 1: Presentación y calificación
        "CALIFICACION": ("1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION"),
        "CALIFICA": ("1 PRESENTACION Y CALIFICACION", "1.3 CALIFICACION"),
        "DEMANDA": ("1 PRESENTACION Y CALIFICACION", "1.1 PRESENTAR DEMANDA")
    }

    def procesar_archivo_html(self, ruta_html):
        """
        Lee el archivo HTML local en ruta_html, parsea con BeautifulSoup (lxml)
        y retorna un diccionario unificado con los datos extraídos.
        """
        resultado = {
            "FECHA INICIO JUICIO": None,
            "FECHA INICIAL FASE ACTUAL": None,
            "ETAPA_PROCESAL": None,
            "FASE_PROCESAL": None,
            "HISTORIAL_ACTUACIONES": []
        }

        if not os.path.exists(ruta_html):
            print(f"[ERROR AGENTE EXTRACTOR] No existe el archivo: {ruta_html}")
            return resultado

        try:
            with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
                contenido_html = f.read()

            # Usar parser lxml o html.parser de respaldo
            try:
                soup = BeautifulSoup(contenido_html, "lxml")
            except Exception:
                soup = BeautifulSoup(contenido_html, "html.parser")

            # 1. Extraer Fecha de Inicio General del proceso
            for elem in soup.find_all(text=re.compile(r"Fecha de ingreso|Fecha ingreso|Fecha presentación|Fecha inicio", re.IGNORECASE)):
                parent_text = elem.parent.get_text(strip=True) if elem.parent else str(elem)
                m = re.search(r'\d{2}/\d{2}/\d{4}', parent_text)
                if m:
                    resultado["FECHA INICIO JUICIO"] = m.group(0)
                    break
                if elem.parent and elem.parent.next_sibling:
                    sib_text = elem.parent.next_sibling.get_text(strip=True) if hasattr(elem.parent.next_sibling, 'get_text') else str(elem.parent.next_sibling)
                    m_s = re.search(r'\d{2}/\d{2}/\d{4}', sib_text)
                    if m_s:
                        resultado["FECHA INICIO JUICIO"] = m_s.group(0)
                        break

            # 2. Extraer historial de actuaciones
            actuaciones = []
            filas = soup.find_all("tr")

            for fila in filas:
                cols = fila.find_all(["td", "th"])
                if len(cols) >= 2:
                    txt_col0 = cols[0].get_text(strip=True)
                    txt_col1 = cols[1].get_text(strip=True)
                else:
                    txt_row = fila.get_text(strip=True)
                    parts = [p.strip() for p in txt_row.split("\n") if p.strip()]
                    if len(parts) >= 2:
                        txt_col0, txt_col1 = parts[0], parts[1]
                    else:
                        continue

                m_f = re.search(r'\d{2}/\d{2}/\d{4}', txt_col0)
                if not m_f:
                    m_f = re.search(r'\d{2}/\d{2}/\d{4}', txt_col0 + " " + txt_col1)

                if m_f:
                    fecha_act = m_f.group(0)
                    detalle_act = txt_col1.upper()
                    if "DETALLE" not in detalle_act or "RAZON" in detalle_act or "ABANDONO" in detalle_act:
                        actuaciones.append({"fecha": fecha_act, "detalle": detalle_act})

            # Si no se encontraron filas tr, usar escáner de texto plano
            if not actuaciones:
                texto_pagina = soup.get_text("\n", strip=True)
                lineas = [linea.strip() for linea in texto_pagina.split("\n") if linea.strip()]
                for idx, line in enumerate(lineas):
                    m_f = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                    if m_f:
                        fecha_act = m_f.group(1)
                        linea_limpia = re.sub(r'\d{2}/\d{2}/\d{4}(\s+\d{2}:\d{2})?', '', line).strip()
                        if len(linea_limpia) > 3:
                            detalle_act = linea_limpia.upper()
                        elif (idx + 1) < len(lineas):
                            detalle_act = lineas[idx + 1].upper()
                        else:
                            detalle_act = ""

                        if "FECHA DE INGRESO" not in detalle_act and "BUSQUEDA" not in detalle_act:
                            actuaciones.append({"fecha": fecha_act, "detalle": detalle_act})

            resultado["HISTORIAL_ACTUACIONES"] = actuaciones

            # Si no se encontró FECHA INICIO JUICIO arriba, tomar la fecha de la actuación más antigua
            if not resultado["FECHA INICIO JUICIO"] and actuaciones:
                resultado["FECHA INICIO JUICIO"] = actuaciones[-1]["fecha"]

            # 3. Mapear con Árbol Procesal
            estado_encontrado = False
            for item in actuaciones:
                fecha_act = item["fecha"]
                detalle_act = item["detalle"]
                for palabra_clave, (etapa, fase) in self.ARBOL_PROCESAL.items():
                    if palabra_clave in detalle_act:
                        resultado["FECHA INICIAL FASE ACTUAL"] = fecha_act
                        resultado["ETAPA_PROCESAL"] = etapa
                        resultado["FASE_PROCESAL"] = fase
                        estado_encontrado = True
                        break
                if estado_encontrado:
                    break

            # Fallback si no hubo coincidencia en Árbol Procesal pero hay actuaciones
            if not estado_encontrado and actuaciones:
                resultado["FECHA INICIAL FASE ACTUAL"] = actuaciones[0]["fecha"]
                resultado["ETAPA_PROCESAL"] = "ESTADO DESCONOCIDO"
                resultado["FASE_PROCESAL"] = actuaciones[0]["detalle"][:100]

            return resultado

        except Exception as e:
            print(f"[ERROR AGENTE EXTRACTOR] Error al procesar {ruta_html}: {e}")
            return resultado
