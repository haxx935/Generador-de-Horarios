import logging
from typing import List
from config import Config
from data_loader import DataLoader
from prolog_manager import PrologManager
from scheduler import ScheduleOptimizer
from output_formatter import HorarioFormatter
from models import Clase

logger = logging.getLogger(__name__)

class HorarioGenerator:
    def __init__(self, ruta_config: str = "horario_config.json"):
        self.config = Config(ruta_config)
        self.data_loader = DataLoader(self.config)
        self.prolog_manager = PrologManager()
        self.optimizer = ScheduleOptimizer()
        self.formatter = HorarioFormatter()

    def generar_horario(self) -> List[Clase]:
        """Generar horario optimizado aplicando todas las restricciones"""
        try:
            # Cargar todos los datos desde JSON
            datos = self.data_loader.cargar_todos_los_datos(self.prolog_manager.prolog)
            
            # Asegurar que las reglas lógicas estén definidas
            self.prolog_manager.asegurar_reglas_definidas()
            
            # Obtener todas las asignaciones válidas de Prolog
            soluciones = self.prolog_manager.obtener_asignaciones_validas()
            
            # Optimizar para evitar duplicados de grupos
            horario_optimo = self.optimizer.optimizar_horario(soluciones)
            
            logger.info(f"Horario generado con {len(horario_optimo)} clases")
            return horario_optimo
            
        except Exception as e:
            logger.error(f"Error al generar horario: {e}")
            raise

    def ejecutar(self):
        """Ejecutar todo el proceso de generación de horario"""
        horario = self.generar_horario()
        self.formatter.formatear_y_mostrar(horario)
        return horario