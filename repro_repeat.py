import urllib.request, json

BASE = "http://127.0.0.1:5000"

def post(path, payload):
    req = urllib.request.Request(BASE+path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

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

default = datos([
 {"nombre":"Grupo A","materias":["Matemáticas","Física","Química","Historia","Inglés"],"equipo_requerido":{"Matemáticas":"proyector","Física":"proyector","Química":"proyector","Historia":"proyector","Inglés":"proyector"},"alumnos":20},
 {"nombre":"Grupo B","materias":["Programación","Redes","Biología","Literatura","Filosofía"],"equipo_requerido":{"Programación":"computadoras","Redes":"computadoras","Biología":"proyector","Literatura":"proyector","Filosofía":"proyector"},"alumnos":20},
])

# Simulate: generate default -> edit Grupo A (swap Matemáticas for Programación) -> generate -> generate default again
editado = datos([
 {"nombre":"Grupo A","materias":["Física","Química","Historia","Inglés","Programación"],"equipo_requerido":{"Matemáticas":"proyector","Física":"proyector","Química":"proyector","Historia":"proyector","Inglés":"proyector"},"alumnos":20},
 {"nombre":"Grupo B","materias":["Programación","Redes","Biología","Literatura","Filosofía"],"equipo_requerido":{"Programación":"computadoras","Redes":"computadoras","Biología":"proyector","Literatura":"proyector","Filosofía":"proyector"},"alumnos":20},
])

for i, label, datos_payload in [
    (1, "gen1 default", default),
    (2, "gen2 editado", editado),
    (3, "gen3 default again", default),
    (4, "gen4 editado again", editado),
]:
    try:
        d = post("/generar-horario", datos_payload)
        print(f"{label}: total={d.get('total')} no_cubiertas={d.get('total_no_cubiertas')}")
    except Exception as e:
        print(f"{label}: ERROR {e}")
