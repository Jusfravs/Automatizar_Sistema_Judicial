# src/gestor_casos.py
import os
import json
import pandas as pd

class GestorCasos:
    """
    Repositorio CRUD de datos para la lectura, actualización y persistencia del reporte.
    """
    def __init__(self, ruta_config="config.json"):
        with open(ruta_config, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        rutas = self.config.get('rutas', {})
        self.ruta_csv = rutas.get('archivo_csv', 'data/reporte_trabajo.csv')
        self.ruta_excel = rutas.get('archivo_origen', 'data/REPORTE JUICIOS PARA REVISIÓN JULIO.xlsx')
        self.ruta_final = rutas.get('archivo_excel_final', 'data/REPORTE_PROCESADO_FINAL.xlsx')
        self.hoja = rutas.get('hoja_lectura', 'migrado')
        self.filtros = self.config.get('filtros_activos', {})

        self._inicializar_csv()
        self.df = pd.read_csv(self.ruta_csv, low_memory=False)
        self.df.columns = [str(c).strip() for c in self.df.columns]

    def _inicializar_csv(self):
        """CREATE: Genera el CSV de trabajo desde el Excel original si no existe."""
        if not os.path.exists(self.ruta_csv) and os.path.exists(self.ruta_excel):
            print("[*] Inicializando base de datos CSV desde Excel...")
            df_excel = pd.read_excel(self.ruta_excel, sheet_name=self.hoja, header=1)
            df_excel.to_csv(self.ruta_csv, index=False, encoding='utf-8-sig')

    def obtener_casos_pendientes(self):
        """READ: Obtiene la lista de números de juicio que cumplen con los filtros."""
        col_estado = 'ESTADO.1' if 'ESTADO.1' in self.df.columns else 'ESTADO'
        
        suc = str(self.filtros.get('sucursal', '')).strip().upper()
        ofi = str(self.filtros.get('oficina', '')).strip().upper()
        est = str(self.filtros.get('estado_judicial', '')).strip().upper()

        df_filtrado = self.df[
            (self.df['SUCURSAL'].astype(str).str.strip().str.upper() == suc) &
            (self.df['OFICINA'].astype(str).str.strip().str.upper() == ofi) &
            (self.df[col_estado].astype(str).str.strip().str.upper() == est)
        ]

        casos = df_filtrado['NUMERO_JUICIO'].dropna().astype(str).str.strip().tolist()

        # Aplicar punto de partida si fue especificado
        inicio = self.filtros.get('inicio_desde_juicio')
        if inicio:
            inicio_limpio = str(inicio).replace("-", "").strip()
            idx = next((i for i, c in enumerate(casos) if str(c).replace("-", "").strip() == inicio_limpio), None)
            if idx is not None:
                print(f"[*] Reanudando desde causa '{inicio}' (Caso #{idx + 1} de {len(casos)}).")
                casos = casos[idx:]

        return casos

    def actualizar_caso(self, numero_juicio, datos):
        """UPDATE: Inyecta en la fila correspondiente los datos extraídos."""
        mask = self.df['NUMERO_JUICIO'].astype(str).str.strip() == str(numero_juicio).strip()
        if mask.any():
            idx = self.df[mask].index[0]
            for col, val in datos.items():
                if val is not None:
                    if col not in self.df.columns:
                        self.df[col] = None
                    self.df.at[idx, col] = val
            return True
        return False

    def guardar(self):
        """SAVE: Persiste los cambios en la base CSV de trabajo."""
        try:
            self.df.to_csv(self.ruta_csv, index=False, encoding='utf-8-sig')
        except Exception as e:
            print(f"[ERROR] No se pudo guardar CSV: {e}")

    def exportar_excel(self):
        """EXPORT: Genera el Excel .xlsx consolidado final."""
        print(f"[*] Exportando informe final a: {self.ruta_final}")
        self.df.to_excel(self.ruta_final, index=False, sheet_name=self.hoja)
        print(f"[✅] ¡Archivo Excel final generado exitosamente!")
