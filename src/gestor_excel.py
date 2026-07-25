# src/gestor_excel.py
from src.gestor_casos import GestorCasos

class GestorExcel(GestorCasos):
    """Alias para mantener compatibilidad con el proyecto original."""
    def actualizar_juicio(self, numero_juicio, datos_extraidos):
        return self.actualizar_caso(numero_juicio, datos_extraidos)

    def guardar_cambios(self):
        return self.guardar()

    def exportar_a_excel(self):
        return self.exportar_excel()