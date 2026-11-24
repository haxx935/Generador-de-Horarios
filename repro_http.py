import urllib.request, json

BASE = "http://127.0.0.1:5000"

def post(path, payload):
    req = urllib.request.Request(BASE+path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return None, str(e)

maestros = [
 {"nombre":"Prof. Matemáticas","materias":["Matemáticas"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Matemáticas":"proyector"}},
 {"nombre":"Prof. Física","materias":["Física"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Física":"proyector"}},
 {"nombre":"Prof. Química","materias":["Química"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Química":"proyector"}},
 {"nombre":"Prof. Programación","materias":["Programación"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Programación":"computadoras"}},
 {"nombre":"Prof. Redes","materias":["Redes"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Redes":"computadoras"}},
 {"nombre":"Prof. Historia","materias":["Historia"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Historia":"proyector"}},
 {"nombre":"Prof. Inglés","materias":["Inglés"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Inglés":"proyector"}},
 {"nombre":"Prof. Biología","materias":["Biología"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Biología":"proyector"}},
 {"nombre":"Prof. Literatura","materias":["Literatura"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Literatura":"proyector"}},
 {"nombre":"Prof. Filosofía","materias":["Filosofía"],"disponibilidad":{"entrada":"08:00","salida":"16:00"},"equipo_requerido":{"Filosofía":"proyector"}},
]
aulas = [
 {"nombre":"Aula 101","tipo":"salón","capacidad":30,"equipo":"proyector","materias_util":["Matemáticas","Física","Química","Historia","Inglés","Biología","Literatura","Filosofía"]},
 {"nombre":"Lab 201","tipo":"laboratorio de computo","capacidad":20,"equipo":"computadoras","materias_util":["Programación","Redes"]},
]
def datos(grupos):
    return {"maestros":maestros,"grupos":grupos,"aulas":aulas}

print("health:", post("/health", {}))

default = datos([
 {"nombre":"Grupo A","materias":["Matemáticas","Física","Química","Historia","Inglés"],"equipo_requerido":{"Matemáticas":"proyector","Física":"proyector","Química":"proyector","Historia":"proyector","Inglés":"proyector"},"alumnos":20},
 {"nombre":"Grupo B","materias":["Programación","Redes","Biología","Literatura","Filosofía"],"equipo_requerido":{"Programación":"computadoras","Redes":"computadoras","Biología":"proyector","Literatura":"proyector","Filosofía":"proyector"},"alumnos":20},
])
s, d = post("/generar-horario", default)
print("DEFAULT total:", d.get("total") if isinstance(d, dict) else d, "| no_cubiertas:", d.get("total_no_cubiertas") if isinstance(d, dict) else "")

# EDIT: Grupo A swap Matemáticas for Programación, STALE equipo_requerido (no Programación entry)
editado = datos([
 {"nombre":"Grupo A","materias":["Física","Química","Historia","Inglés","Programación"],"equipo_requerido":{"Matemáticas":"proyector","Física":"proyector","Química":"proyector","Historia":"proyector","Inglés":"proyector"},"alumnos":20},
 {"nombre":"Grupo B","materias":["Programación","Redes","Biología","Literatura","Filosofía"],"equipo_requerido":{"Programación":"computadoras","Redes":"computadoras","Biología":"proyector","Literatura":"proyector","Filosofía":"proyector"},"alumnos":20},
])
s, d = post("/generar-horario", editado)
print("EDIT(stale equipo) total:", d.get("total") if isinstance(d, dict) else d, "| no_cubiertas:", d.get("total_no_cubiertas") if isinstance(d, dict) else "")

# EDIT2: equipo_requerido cleared entirely for Grupo A
editado2 = datos([
 {"nombre":"Grupo A","materias":["Física","Química","Historia","Inglés","Programación"],"equipo_requerido":{},"alumnos":20},
 {"nombre":"Grupo B","materias":["Programación","Redes","Biología","Literatura","Filosofía"],"equipo_requerido":{"Programación":"computadoras","Redes":"computadoras","Biología":"proyector","Literatura":"proyector","Filosofía":"proyector"},"alumnos":20},
])
s, d = post("/generar-horario", editado2)
print("EDIT(empty equipo) total:", d.get("total") if isinstance(d, dict) else d, "| no_cubiertas:", d.get("total_no_cubiertas") if isinstance(d, dict) else "")
