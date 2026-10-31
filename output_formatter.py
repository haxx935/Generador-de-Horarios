from typing import List
from models import Clase
class HorarioFormatter:
    @staticmethod
    def formatear_y_mostrar(horario: List[Clase]):
        """Formatear y mostrar el horario generado"""
        if horario:
            print(f"¡Se generó un horario con {len(horario)} clases sin empalmes!\n")
            for i, clase in enumerate(horario, 1):
                print(f"Clase {i}:")
                print(f"  - Profesor: {clase.profesor.capitalize()}")
                print(f"  - Materia:  {clase.materia.capitalize()}")
                print(f"  - Grupo:    {clase.grupo.replace('_', ' ').upper()}")
                print(f"  - Salón:    {clase.salon.replace('_', ' ').upper()}")
                print(f"  - Día/Hora: {clase.dia.capitalize()} ({clase.hora})")
                print("-" * 40)
        else:
            print("No se pudo generar un horario válido con las restricciones actuales.")