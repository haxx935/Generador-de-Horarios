import logging
from typing import List, Optional
from config import Config
from data_loader import DataLoader
from prolog_manager import PrologManager
from models import Clase

logger = logging.getLogger(__name__)


class HorarioGenerator:
    """Generador de horarios académicos.

    La selección del horario vive ahora íntegramente en Prolog:
    1. Python carga los hechos en el motor Prolog.
    2. Se llama UNA vez al predicado generar_horario/1, que construye
       las sesiones requeridas (4 por par grupo-materia) y las asigna
       recursivamente con backtracking y acumulado por lista.
    3. Python convierte el resultado en objetos Clase.
    """

    def __init__(self, ruta_config: str = "horario_config.json"):
        self.config = Config(ruta_config)
        self.data_loader = DataLoader(self.config)
        self.prolog_manager = PrologManager()

    def generar_horario(self, datos: dict = None) -> List[Clase]:
        """Genera el horario delegando toda la búsqueda a Prolog.

        Args:
            datos: dict con datos de entrada (maestros, grupos, aulas, etc.).
                   Si es None, se carga desde horario_config.json.

        Returns:
            Lista de objetos Clase con la asignación completa.
        """
        try:
            # 1. Cargar hechos en Prolog desde los datos de entrada o del JSON.
            self.data_loader.cargar_todos_los_datos(self.prolog_manager.prolog, datos)

            # 2. Definir reglas lógicas en Prolog.
            self.prolog_manager.asegurar_reglas_definidas()

            # 3. Llamada ÚNICA a Prolog: genera el horario completo con backtracking.
            resultados = self.prolog_manager.generar_horario_prolog()

            # 4. Convertir cada resultado en objeto Clase.
            horario: List[Clase] = [
                Clase(
                    profesor=r["Prof"],
                    materia=r["Materia"],
                    grupo=r["Grupo"],
                    salon=r["Salon"],
                    dia=r["Dia"],
                    hora=r["Hora"],
                )
                for r in resultados
            ]

            logger.info(f"Horario generado con {len(horario)} clases (búsqueda en Prolog)")
            return horario

        except Exception as e:
            logger.error(f"Error al generar horario: {e}")
            raise

    def ejecutar(self) -> List[Clase]:
        """Ejecuta el proceso completo usando la configuración por defecto."""
        horario = self.generar_horario()
        logger.info(f"Resumen: Se generaron {len(horario)} clases para el horario académico.")
        return horario
