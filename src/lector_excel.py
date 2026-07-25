# src/lector_excel.py
from src.gestor_casos import GestorCasos

class LectorCasos(GestorCasos):
    """Alias para mantener compatibilidad con el proyecto original."""
    def extraer_casos_a_procesar(self):
        return self.obtener_casos_pendientes()