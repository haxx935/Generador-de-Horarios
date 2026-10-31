import logging
from typing import List, Dict, Set, Tuple
from models import Clase

logger = logging.getLogger(__name__)

class ScheduleOptimizer:
    @staticmethod
    def optimizar_horario(soluciones: List[Dict]) -> List[Clase]:
        """Optimizar el horario evitando duplicados de grupos en mismo día/hora"""
        horario_final: List[Clase] = []
        slot_ocupados: Set[Tuple[str, str, str]] = set()

        for sol in soluciones:
            clase = Clase(
                profesor=sol['Prof'],
                materia=sol['Materia'],
                grupo=sol['Grupo'],
                salon=sol['Salon'],
                dia=sol['Dia'],
                hora=sol['Hora']
            )
            clave_slot = clase.slot_key()

            if clave_slot not in slot_ocupados:
                slot_ocupados.add(clave_slot)
                horario_final.append(clase)

        return horario_final