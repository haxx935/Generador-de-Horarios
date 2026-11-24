import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from api import transformar_datos_api_a_prolog
from horario_generator import HorarioGenerator

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"]

def make_datos(grupos_materias):
    """grupos_materias: dict nombre_grupo -> list de materias"""
    maestros = [
        {"nombre": "Prof. Matemáticas", "materias": ["Matemáticas"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Matemáticas": "proyector"}},
        {"nombre": "Prof. Física", "materias": ["Física"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Física": "proyector"}},
        {"nombre": "Prof. Química", "materias": ["Química"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Química": "proyector"}},
        {"nombre": "Prof. Programación", "materias": ["Programación"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Programación": "computadoras"}},
        {"nombre": "Prof. Redes", "materias": ["Redes"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Redes": "computadoras"}},
        {"nombre": "Prof. Historia", "materias": ["Historia"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Historia": "proyector"}},
        {"nombre": "Prof. Inglés", "materias": ["Inglés"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Inglés": "proyector"}},
        {"nombre": "Prof. Biología", "materias": ["Biología"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Biología": "proyector"}},
        {"nombre": "Prof. Literatura", "materias": ["Literatura"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Literatura": "proyector"}},
        {"nombre": "Prof. Filosofía", "materias": ["Filosofía"], "disponibilidad": {"entrada": "08:00", "salida": "16:00"}, "equipo_requerido": {"Filosofía": "proyector"}},
    ]
    aulas = [
        {"nombre": "Aula 101", "tipo": "salón", "capacidad": 30, "equipo": "proyector", "materias_util": ["Matemáticas", "Física", "Química", "Historia", "Inglés", "Biología", "Literatura", "Filosofía"]},
        {"nombre": "Lab 201", "tipo": "laboratorio de computo", "capacidad": 20, "equipo": "computadoras", "materias_util": ["Programación", "Redes"]},
    ]
    grupos = []
    for nombre, mats in grupos_materias.items():
        equipos = {m: ("computadoras" if m in ("Programación", "Redes") else "proyector") for m in mats}
        grupos.append({"nombre": nombre, "materias": mats, "equipo_requerido": equipos, "alumnos": 20})
    return {"maestros": maestros, "grupos": grupos, "aulas": aulas}


def run(grupos_materias, label):
    datos = make_datos(grupos_materias)
    datos_prolog = transformar_datos_api_a_prolog(datos)
    gen = HorarioGenerator()
    horario = gen.generar_horario(datos_prolog)
    print(f"[{label}] clases generadas: {len(horario)}")
    for c in horario:
        print("   ", c.grupo, c.materia, c.profesor, c.salon, c.dia, c.hora)
    print()


if __name__ == "__main__":
    default = {
        "Grupo A": ["Matemáticas", "Física", "Química", "Historia", "Inglés"],
        "Grupo B": ["Programación", "Redes", "Biología", "Literatura", "Filosofía"],
    }
    run(default, "default (igual a app.js)")

    # Modificar Grupo A: quitar Matemáticas, agregar Programación (que usa computadoras)
    modificado = {
        "Grupo A": ["Física", "Química", "Historia", "Inglés", "Programación"],
        "Grupo B": ["Programación", "Redes", "Biología", "Literatura", "Filosofía"],
    }
    run(modificado, "Grupo A cambia Matemáticas->Programación")

    # Grupo A solo una materia
    run({"Grupo A": ["Matemáticas"]}, "Grupo A solo Matemáticas")
