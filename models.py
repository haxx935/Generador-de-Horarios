from typing import List, Dict

from prolog_manager import atom


class Profesor:
    def __init__(self, nombre: str, materia: str):
        self.nombre = nombre
        self.materia = materia

    def to_prolog_fact(self) -> str:
        return f"profesor({atom(self.nombre)}, {atom(self.materia)})"


class Disponibilidad:
    def __init__(self, profesor: str, dia: str, hora: str):
        self.profesor = profesor
        self.dia = dia
        self.hora = hora

    def to_prolog_fact(self) -> str:
        return f"disponible({atom(self.profesor)}, {atom(self.dia)}, {atom(self.hora)})"


class Salon:
    def __init__(self, nombre: str, capacidad: int, equipo: str, materias_util=None):
        self.nombre = nombre
        self.capacidad = capacidad
        self.equipo = equipo
        self.materias_util = materias_util or []

    def to_prolog_fact(self) -> str:
        return f"salon({atom(self.nombre)}, {self.capacidad}, {atom(self.equipo)})"

    def to_prolog_materia_util(self) -> List[str]:
        return [
            f"materia_util({atom(self.nombre)}, {atom(m)})"
            for m in self.materias_util
        ]


class Grupo:
    def __init__(self, nombre: str, alumnos: int, materia: str):
        self.nombre = nombre
        self.alumnos = alumnos
        self.materia = materia

    def to_prolog_hechos(self) -> List[str]:
        return [
            f"grupo({atom(self.nombre)}, {self.alumnos})",
            f"grupo_materia({atom(self.nombre)}, {atom(self.materia)})"
        ]


class Requerimiento:
    def __init__(self, materia: str, equipo: str):
        self.materia = materia
        self.equipo = equipo

    def to_prolog_fact(self) -> str:
        return f"requiere({atom(self.materia)}, {atom(self.equipo)})"
class Clase:
    def __init__(self, profesor: str, materia: str, grupo: str, salon: str, dia: str, hora: str):
        self.profesor = profesor
        self.materia = materia
        self.grupo = grupo
        self.salon = salon
        self.dia = dia
        self.hora = hora

    def slot_key(self):
        return (self.grupo, self.dia, self.hora)

    def to_prolog_solution(self) -> Dict:
        return {
            'Prof': self.profesor,
            'Materia': self.materia,
            'Grupo': self.grupo,
            'Salon': self.salon,
            'Dia': self.dia,
            'Hora': self.hora
        }