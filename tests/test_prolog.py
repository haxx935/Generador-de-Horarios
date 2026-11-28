"""Pruebas automáticas para el generador de horarios (búsqueda en Prolog con backtracking).

Cubre:
  - Choques: sin empalme de profesor, grupo ni salón en mismo día y hora.
  - Topes por día: máximo 2 horas de una misma materia al día por grupo.
  - Topes por semana: máximo 4 horas de una misma materia a la semana por grupo.
  - Cobertura: con datos por defecto se generan 40 clases (10 pares × 4 h),
    sin empalmes y no_cubiertas vacío.
  - Llamadas repetidas: resultados consistentes, sin estado residual.
  - Caso sin solución completa: se devuelve solución parcial y no_cubiertas
    reporta horas faltantes por par grupo-materia.
"""

import sys
import os

# Asegurar que se importan los módulos del proyecto (raíz).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from prolog_manager import PrologManager  # noqa: E402
from data_loader import DataLoader  # noqa: E402
from config import Config  # noqa: E402
from horario_generator import HorarioGenerator  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures y helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def prolog():
    """ProblogManager fresco por prueba (limpia estado de pyswip en __init__)."""
    m = PrologManager()
    m.asegurar_reglas_definidas()
    return m


@pytest.fixture
def datos_por_defecto():
    """Datos mínimos y válidos para generar un horario completo (10 pares × 4 h = 40 clases)."""
    return {
        "profesores": [
            {"nombre": "Prof. Matemáticas", "materia": "Matemáticas", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Física", "materia": "Física", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Química", "materia": "Química", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Programación", "materia": "Programación", "equipo_requerido": "computadoras",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Redes", "materia": "Redes", "equipo_requerido": "computadoras",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Historia", "materia": "Historia", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Inglés", "materia": "Inglés", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Biología", "materia": "Biología", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Literatura", "materia": "Literatura", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
            {"nombre": "Prof. Filosofía", "materia": "Filosofía", "equipo_requerido": "proyector",
             "disponibilidad": {"entrada": "08:00", "salida": "16:00"}},
        ],
        "disponibilidades": [],  # se regenera desde disponibilidad.entrada/salida en transformar_datos_api_a_prolog
        "aulas": [
            {"nombre": "Aula 101", "capacidad": 30, "equipo": "proyector", "materias_util": ["Matemáticas", "Física", "Química", "Historia", "Inglés", "Biología", "Literatura", "Filosofía"]},
            {"nombre": "Lab 201", "capacidad": 20, "equipo": "computadoras", "materias_util": ["Programación", "Redes"]},
        ],
        "grupos": [
            {"nombre": "Grupo A", "alumnos": 30, "materias": ["Matemáticas", "Física", "Química", "Historia", "Inglés"]},
            {"nombre": "Grupo B", "alumnos": 20, "materias": ["Programación", "Redes", "Biología", "Literatura", "Filosofía"]},
        ],
        "requerimientos": [
            {"materia": "Matemáticas", "equipo": "proyector"},
            {"materia": "Física", "equipo": "proyector"},
            {"materia": "Química", "equipo": "proyector"},
            {"materia": "Programación", "equipo": "computadoras"},
            {"materia": "Redes", "equipo": "computadoras"},
            {"materia": "Historia", "equipo": "proyector"},
            {"materia": "Inglés", "equipo": "proyector"},
            {"materia": "Biología", "equipo": "proyector"},
            {"materia": "Literatura", "equipo": "proyector"},
            {"materia": "Filosofía", "equipo": "proyector"},
        ],
    }


def _llenar_disponibilidades_completas(datos):
    """Cada profesor disponible todos los días de 08:00 a 16:00."""
    dias = ["lunes", "martes", "miercoles", "jueves", "viernes"]
    datos["disponibilidades"] = []
    for p in datos["profesores"]:
        for d in dias:
            for h in range(8, 16):
                datos["disponibilidades"].append({
                    "profesor": p["nombre"],
                    "dia": d,
                    "hora": f"{h:02d}:00",
                })


# ---------------------------------------------------------------------------
# Pruebas de restricciones duras
# ---------------------------------------------------------------------------

def test_no_hay_empalme_de_profesor(prolog, datos_por_defecto):
    """Ningún profesor da dos clases el mismo día y hora."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    DataLoader(Config()).cargar_todos_los_datos(prolog.prolog, datos_por_defecto)
    asignaciones = prolog.generar_horario_prolog()

    slots_profesor = {}
    for a in asignaciones:
        clave = (a["Prof"], a["Dia"], a["Hora"])
        assert clave not in slots_profesor, f"Empalme de profesor {clave}"
        slots_profesor[clave] = a


def test_no_hay_empalme_de_grupo(prolog, datos_por_defecto):
    """Ningún grupo tiene dos clases el mismo día y hora."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    DataLoader(Config()).cargar_todos_los_datos(prolog.prolog, datos_por_defecto)
    asignaciones = prolog.generar_horario_prolog()

    slots_grupo = {}
    for a in asignaciones:
        clave = (a["Grupo"], a["Dia"], a["Hora"])
        assert clave not in slots_grupo, f"Empalme de grupo {clave}"
        slots_grupo[clave] = a


def test_no_hay_empalme_de_salon(prolog, datos_por_defecto):
    """Ningún salón aloja dos clases el mismo día y hora."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    DataLoader(Config()).cargar_todos_los_datos(prolog.prolog, datos_por_defecto)
    asignaciones = prolog.generar_horario_prolog()

    slots_salon = {}
    for a in asignaciones:
        clave = (a["Salon"], a["Dia"], a["Hora"])
        assert clave not in slots_salon, f"Empalme de salón {clave}"
        slots_salon[clave] = a


def test_tope_diario_por_materia(prolog, datos_por_defecto):
    """Máximo 2 horas de una misma materia al día por grupo."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    DataLoader(Config()).cargar_todos_los_datos(prolog.prolog, datos_por_defecto)
    asignaciones = prolog.generar_horario_prolog()

    conteo = {}
    for a in asignaciones:
        clave = (a["Grupo"], a["Dia"], a["Materia"])
        conteo[clave] = conteo.get(clave, 0) + 1
    for clave, n in conteo.items():
        assert n <= 2, f"Tope diario excedido en {clave}: {n} horas"


def test_tope_semanal_por_materia(prolog, datos_por_defecto):
    """Máximo 4 horas de una misma materia a la semana por grupo."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    DataLoader(Config()).cargar_todos_los_datos(prolog.prolog, datos_por_defecto)
    asignaciones = prolog.generar_horario_prolog()

    conteo = {}
    for a in asignaciones:
        clave = (a["Grupo"], a["Materia"])
        conteo[clave] = conteo.get(clave, 0) + 1
    for clave, n in conteo.items():
        assert n <= 4, f"Tope semanal excedido en {clave}: {n} horas"


# ---------------------------------------------------------------------------
# Pruebas de cobertura y contrato de API
# ---------------------------------------------------------------------------

def test_cobertura_40_clases_sin_defaults(api_client, datos_por_defecto):
    """Con datos por defecto: 40 clases, 10 pares × 4 h, sin empalmes, no_cubiertas vacío."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    generador = HorarioGenerator()
    horario = generador.generar_horario(datos_por_defecto)

    assert len(horario) == 40, f"Se esperaban 40 clases, se generaron {len(horario)}"

    # Verificar 10 pares únicos (grupo, materia)
    pares = set((c.grupo, c.materia) for c in horario)
    assert len(pares) == 10, f"Se esperaban 10 pares grupo-materia, se encontraron {len(pares)}"

    # Cada par debe tener exactamente 4 clases
    from collections import Counter
    conteo_pares = Counter((c.grupo, c.materia) for c in horario)
    for par, n in conteo_pares.items():
        assert n == 4, f"El par {par} tiene {n} clases, se esperaban 4"

    # Sin empalmes (re-verificación a nivel de objetos Clase)
    slots_profesor = set()
    slots_grupo = set()
    slots_salon = set()
    for c in horario:
        kp = (c.profesor, c.dia, c.hora)
        kg = (c.grupo, c.dia, c.hora)
        ks = (c.salon, c.dia, c.hora)
        assert kp not in slots_profesor, f"Empalme profesor: {kp}"
        assert kg not in slots_grupo, f"Empalme grupo: {kg}"
        assert ks not in slots_salon, f"Empalme salón: {ks}"
        slots_profesor.add(kp)
        slots_grupo.add(kg)
        slots_salon.add(ks)


def test_llamadas_repetidas_consistentes(datos_por_defecto):
    """Dos generaciones consecutivas con los mismos datos dan 40 clases y sin estado residual."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    resultados = []
    for _ in range(2):
        generador = HorarioGenerator()
        horario = generador.generar_horario(datos_por_defecto)
        resultados.append(len(horario))

    assert resultados[0] == 40
    assert resultados[1] == 40
    assert resultados[0] == resultados[1]


# ---------------------------------------------------------------------------
# Caso sin solución completa -> solución parcial
# ---------------------------------------------------------------------------

def test_sin_solucion_devuelve_parcial_y_no_cubiertas(prolog):
    """Caso claramente imposible: 4 sesiones requeridas pero solo 2 bloques
    disponibles (un profesor disponible 2 horas). Se espera solución parcial
    (2 clases) y no_cubiertas con horas_faltantes = 2."""
    datos = {
        "profesores": [
            {"nombre": "Prof. Matemáticas", "materia": "Matemáticas", "equipo_requerido": "proyector"},
        ],
        "disponibilidades": [
            {"profesor": "Prof. Matemáticas", "dia": "lunes", "hora": "08:00"},
            {"profesor": "Prof. Matemáticas", "dia": "lunes", "hora": "09:00"},
        ],
        "salones": [
            {"nombre": "Aula 101", "capacidad": 30, "equipo": "proyector", "materias_util": ["Matemáticas"]},
        ],
        "grupos": [
            {"nombre": "Grupo A", "alumnos": 30, "materias": ["Matemáticas"]},
        ],
        "requerimientos": [
            {"materia": "Matemáticas", "equipo": "proyector"},
        ],
    }
    DataLoader(Config()).cargar_todos_los_datos(prolog.prolog, datos)
    asignaciones = prolog.generar_horario_prolog()

    # Debe devolver una solución parcial (menos de 4)
    assert 0 < len(asignaciones) < 4, f"Se esperaba una solución parcial, se obtuvieron {len(asignaciones)}"

    # Verificar que no hay empalmes incluso en la parcial
    slots_salon = set()
    for a in asignaciones:
        clave = (a["Salon"], a["Dia"], a["Hora"])
        assert clave not in slots_salon, f"Empalme en solución parcial: {clave}"
        slots_salon.add(clave)


# ---------------------------------------------------------------------------
# Test de cliente API (integración con Flask)
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Cliente Flask autenticado como jefe (el generador es sólo para jefe)."""
    from api import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        token = client.post("/api/login-demo", json={"rol": "jefe"}).get_json()["token"]
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        yield client


def test_api_respuesta_40_clases(api_client, datos_por_defecto):
    """POST /generar-horario con datos por defecto: 40 clases, no_cubiertas vacío."""
    _llenar_disponibilidades_completas(datos_por_defecto)
    resp = api_client.post("/generar-horario", json=datos_por_defecto)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 40, f"Se esperaban 40 clases, API devolvió {data['total']}"
    assert data["total_no_cubiertas"] == 0, f"no_cubiertas debería estar vacío, tiene {data['total_no_cubiertas']}"

    # Sin empalmes en la respuesta JSON
    slots_profesor = set()
    slots_grupo = set()
    slots_salon = set()
    for a in data["asignaciones"]:
        kp = (a["maestro"], a["dia"], a["hora_inicio"])
        kg = (a["grupo"], a["dia"], a["hora_inicio"])
        ks = (a["aula"], a["dia"], a["hora_inicio"])
        assert kp not in slots_profesor
        assert kg not in slots_grupo
        assert ks not in slots_salon
        slots_profesor.add(kp)
        slots_grupo.add(kg)
        slots_salon.add(ks)


def test_api_no_cubiertas_reporta_faltantes(api_client):
    """no_cubiertas reporta pares con menos de 4 horas e indica cuántas faltan."""
    datos = {
        "profesores": [
            {"nombre": "Prof. Matemáticas", "materia": "Matemáticas", "equipo_requerido": "proyector"},
        ],
        "disponibilidades": [
            {"profesor": "Prof. Matemáticas", "dia": "lunes", "hora": "08:00"},
            {"profesor": "Prof. Matemáticas", "dia": "lunes", "hora": "09:00"},
        ],
        "aulas": [
            {"nombre": "Aula 101", "capacidad": 30, "equipo": "proyector", "materias_util": ["Matemáticas"]},
        ],
        "grupos": [
            {"nombre": "Grupo A", "alumnos": 30, "materias": ["Matemáticas"]},
        ],
        "requerimientos": [
            {"materia": "Matemáticas", "equipo": "proyector"},
        ],
    }
    # Solo 2 bloques disponibles (lunes 08:00 y 09:00). Tope diario: 2.
    # Se asignan como máximo 2 clases de 4 esperadas → faltan 2.
    resp = api_client.post("/generar-horario", json=datos)
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["total_no_cubiertas"] >= 1
    entrada = data["no_cubiertas"][0]
    assert "grupo" in entrada
    assert "materia" in entrada
    assert "horas_asignadas" in entrada
    assert "horas_faltantes" in entrada
    assert entrada["horas_asignadas"] < 4
    assert entrada["horas_faltantes"] == 4 - entrada["horas_asignadas"]


def test_health_endpoint(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
