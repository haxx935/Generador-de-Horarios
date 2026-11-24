import logging
import threading
from collections import defaultdict
from flask import Flask, request, jsonify
from flask_cors import CORS

from horario_generator import HorarioGenerator
from prolog_manager import MAX_CLASES_POR_MATERIA_DIA

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5500", "http://localhost:5500", "null"])
# Punto 4: "null" permite abrir index.html con doble clic (origen file:// -> null).
# Es aceptable solo para uso local. En producción debe quitarse y restringirse a los
# orígenes reales del frontend.
logger = logging.getLogger(__name__)

# Lock global para serializar todo el ciclo de generación (punto 8).
# pyswip usa un único motor Prolog por proceso y no es thread-safe.
_generacion_lock = threading.Lock()

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"]

_EQUIPO_POR_MATERIA = {
    "programación": "computadoras",
    "programacion": "computadoras",
    "redes": "computadoras",
    "contabilidad": "computadoras",
}


def _hora_a_bloque(hora: str) -> str:
    """Convierte una hora 'HH:MM' a la etiqueta de bloque del frontend ('HH-HH+1')."""
    try:
        h = int(str(hora).split(":")[0])
    except (ValueError, AttributeError):
        h = 8
    return f"{h:02d}-{h + 1:02d}"


def _sumar_hora(hora: str) -> str:
    """Devuelve hora + 1 bloque (formato HH:MM)."""
    try:
        h, m = map(int, str(hora).split(":"))
    except (ValueError, AttributeError):
        h, m = 8, 0
    return f"{(h + 1) % 24:02d}:{m:02d}"


def _rangos_horas(entrada: str, salida: str):
    """Genera horas iniciales 'HH:00' en bloques de 1h entre entrada y salida."""
    try:
        hi = int(str(entrada).split(":")[0])
        hf = int(str(salida).split(":")[0])
    except (ValueError, AttributeError):
        hi, hf = 8, 12
    return [f"{h:02d}:00" for h in range(hi, hf)]


def transformar_datos_api_a_prolog(datos: dict) -> dict:
    """Convierte el formato de la API al formato esperado por Prolog/Config."""
    resultado = {"profesores": [], "disponibilidades": [], "salones": [], "grupos": [], "requerimientos": []}

    # Transformar maestros -> profesionales + disponibilidades
    maestros = datos.get("maestros", datos.get("profesores", []))
    for m in maestros:
        materias = m.get("materias", [])
        if not materias:
            # Soportar tanto "materias" (lista) como "materia" (singular).
            materias = [m["materia"]] if "materia" in m else [""]
        for materia in materias:
            profesor = {"nombre": m["nombre"], "materia": materia}
            equipo_map = m.get("equipo_requerido")
            if not isinstance(equipo_map, dict):
                equipo_map = {}
            equipo_profesor = equipo_map.get(materia, "proyector")
            if not isinstance(equipo_profesor, str) or not equipo_profesor.strip():
                equipo_profesor = "proyector"
                logger.warning(
                    f"equipo_requerido no válido para maestro {m['nombre']}/materia {materia}; "
                    f"usando respaldo '{equipo_profesor}'"
                )
            else:
                equipo_profesor = equipo_profesor.strip()
            profesor["equipo_requerido"] = equipo_profesor
            resultado["profesores"].append(profesor)

        disp = m.get("disponibilidad", {})
        if isinstance(disp, dict):
            entrada = disp.get("entrada", "08:00")
            salida = disp.get("salida", "12:00")
        elif isinstance(disp, str):
            entrada, salida = disp, "12:00"
        else:
            entrada, salida = "08:00", "12:00"

        # Una disponibilidad por hora y por día laboral.
        # Si los datos ya traen una lista "disponibilidades" (caso de pruebas),
        # se respeta tal cual; si no, se genera desde disponibilidad.entrada/salida
        # (formato que envía el frontend).
        disp_list = datos.get("disponibilidades")
        if isinstance(disp_list, list) and len(disp_list) > 0:
            for d in disp_list:
                resultado["disponibilidades"].append({
                    "profesor": d["profesor"],
                    "dia": d["dia"],
                    "hora": d["hora"],
                })
        else:
            for dia in DIAS:
                for hora in _rangos_horas(entrada, salida):
                    resultado["disponibilidades"].append({
                        "profesor": m["nombre"],
                        "dia": dia,
                        "hora": hora,
                    })

    # Transformar aulas -> salones
    _EQUIPO_POR_TIPO = {
        "salón": "proyector",
        "laboratorio de computo": "computadoras",
        "auditorio": "proyector",
        "taller": "proyector",
    }
    for a in datos.get("aulas", []):
        equipo = a.get("equipo") or _EQUIPO_POR_TIPO.get(a.get("tipo", ""), "proyector")
        capacidad = a.get("capacidad", 30)
        materias_util = a.get("materias_util", [])
        resultado["salones"].append({
            "nombre": a["nombre"],
            "capacidad": capacidad,
            "equipo": equipo,
            "materias_util": materias_util,
        })

    # Transformar grupos (una entrada grupo_materia por materia)
    for g in datos.get("grupos", []):
        materias = g.get("materias", [])
        if not materias:
            materias = [""]
        for materia in materias:
            equipo_map = g.get("equipo_requerido")
            if not isinstance(equipo_map, dict):
                equipo_map = {}
            equipo_grupo = equipo_map.get(materia, "")
            if isinstance(equipo_grupo, str) and equipo_grupo.strip():
                equipo_requerido = equipo_grupo.strip()
            else:
                equipo_requerido = _EQUIPO_POR_MATERIA.get(materia.lower(), "proyector")
                logger.warning(
                    f"equipo_requerido no válido para grupo {g['nombre']}/materia {materia}; "
                    f"usando respaldo '{equipo_requerido}'"
                )
            resultado["grupos"].append({
                "nombre": g["nombre"],
                "alumnos": g.get("alumnos", 20),
                "materia": materia,
            })
            resultado["requerimientos"].append({"materia": materia, "equipo": equipo_requerido})

    logger.info("Datos transformados de formato API a formato Prolog")

    if "max_clases_por_materia_dia" in datos:
        try:
            resultado["max_clases_por_materia_dia"] = int(datos["max_clases_por_materia_dia"])
        except (ValueError, TypeError):
            resultado["max_clases_por_materia_dia"] = MAX_CLASES_POR_MATERIA_DIA

    return resultado


@app.route("/generar-horario", methods=["POST"])
def generar_horario():
    """Genera un horario académico delegando toda la búsqueda a Prolog.

    Python solo carga los hechos, llama UNA vez al predicado
    generar_horario/1 (backtracking con acumulado por lista) y convierte
    el resultado en objetos Clase y luego en la respuesta JSON.
    """
    datos = request.get_json(silent=True) or {}
    logger.info(f"Recibida solicitud de generación de horario con {len(datos)} campos")

    with _generacion_lock:
        # Transformar datos al formato Prolog
        datos_prolog = transformar_datos_api_a_prolog(datos)

        # Generar horario: todo el razonamiento vive en Prolog
        generador = HorarioGenerator()
        horario = generador.generar_horario(datos_prolog)

        # Convertir objetos Clase al formato de respuesta de la API
        asignaciones = []
        for c in horario:
            asignaciones.append({
                "maestro": c.profesor,
                "materia": c.materia,
                "grupo": c.grupo,
                "aula": c.salon,
                "dia": c.dia,
                "hora_inicio": c.hora,
                "hora_fin": _sumar_hora(c.hora),
                "bloque": _hora_a_bloque(c.hora),
            })

        # --- no_cubiertas mejorado (requisito 7) ---
        # Contar cuántas horas se asignaron realmente a cada par (grupo, materia).
        horas_por_par = defaultdict(int)
        for a in asignaciones:
            horas_por_par[(a["grupo"], a["materia"])] += 1

        # Cada par (grupo, materia) espera exactamente 4 horas (4 sesiones).
        HORAS_ESPERADAS_POR_PAR = 4
        grupos_prolog = datos_prolog.get("grupos", [])
        esperados = {(g["nombre"], g["materia"]) for g in grupos_prolog}

        no_cubiertas = []
        for g, m in sorted(esperados):
            asignadas = horas_por_par.get((g, m), 0)
            if asignadas < HORAS_ESPERADAS_POR_PAR:
                no_cubiertas.append({
                    "grupo": g,
                    "materia": m,
                    "horas_asignadas": asignadas,
                    "horas_faltantes": HORAS_ESPERADAS_POR_PAR - asignadas,
                })

    return jsonify({
        "asignaciones": asignaciones,
        "total": len(asignaciones),
        "no_cubiertas": no_cubiertas,
        "total_no_cubiertas": len(no_cubiertas),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
