import logging
import threading
from collections import defaultdict
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, g, redirect, send_file, abort
from flask_cors import CORS

from auth_service import AuthService
from auth_store import ROLES_VALIDOS
from horario_generator import HorarioGenerator
from prolog_manager import MAX_CLASES_POR_MATERIA_DIA

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1:5000", "null"], supports_credentials=True)
# Punto 4: "null" permite abrir index.html con doble clic (origen file:// -> null).
# Es aceptable solo para uso local. En producción debe quitarse y restringirse a los
# orígenes reales del frontend.
logger = logging.getLogger(__name__)

# Lock global para serializar todo el ciclo de generación (punto 8).
# pyswip usa un único motor Prolog por proceso y no es thread-safe.
_generacion_lock = threading.Lock()

# Servicio de autenticación: usa el mismo motor Prolog y carga usuarios.json.
AUTH = AuthService()

# Último horario generado; se filtra por rol en /api/horario.
_ultimo_horario = []

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"]

_EQUIPO_POR_MATERIA = {
    "programación": "computadoras",
    "programacion": "computadoras",
    "redes": "computadoras",
    "contabilidad": "computadoras",
}


# ----------------------------------------------------------------------
# Sesión y control de acceso por roles
# ----------------------------------------------------------------------
def _token_de_solicitud():
    """Token enviado por el frontend (Bearer, cabecera propia o cookie)."""
    cabecera = request.headers.get("Authorization", "")
    if cabecera.lower().startswith("bearer "):
        return cabecera[7:].strip()
    return request.headers.get("X-Session-Token") or request.cookies.get("sid")


def requiere_sesion(roles=None):
    """Exige una sesión válida (y, si se indica, uno de los roles permitidos).

    No hay modo de prueba que omita esta comprobación: sin token válido la
    petición se rechaza siempre, incluso con ``TESTING=True``.
    """

    def decorador(func):
        @wraps(func)
        def envoltorio(*args, **kwargs):
            token = _token_de_solicitud()
            sesion = AUTH.obtener_sesion(token) if token else None
            if sesion is None:
                mensaje = "Inicia sesión para continuar." if token is None else "Sesión inválida o expirada."
                return jsonify({"error": mensaje}), 401
            if roles and sesion["rol"] not in roles:
                return jsonify({"error": "Tu rol no tiene acceso a este recurso."}), 403
            g.sesion = sesion
            return func(*args, **kwargs)

        return envoltorio

    return decorador


def _respuesta_con_token(datos: dict, codigo: int = 200):
    """Respuesta JSON que también fija la cookie de sesión para las rutas HTML."""
    respuesta = jsonify(datos)
    respuesta.set_cookie("sid", datos["token"], httponly=True, samesite="Lax")
    respuesta.status_code = codigo
    return respuesta


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
@requiere_sesion(roles=("jefe",))
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

        # El jefe acaba de generar el horario: queda disponible para que
        # maestros y alumnos vean SU parte filtrada en /api/horario.
        _ultimo_horario[:] = asignaciones

    return jsonify({
        "asignaciones": asignaciones,
        "total": len(asignaciones),
        "no_cubiertas": no_cubiertas,
        "total_no_cubiertas": len(no_cubiertas),
    })


# ----------------------------------------------------------------------
# API de autenticación y datos por rol
# ----------------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    datos = request.get_json(silent=True) or {}
    usuario = str(datos.get("usuario", "")).strip()
    contrasena = datos.get("contrasena", "")

    if not usuario or not contrasena:
        return jsonify({"error": "Ingresa usuario y contraseña."}), 400

    sesion = AUTH.login(usuario, contrasena)
    if not sesion:
        return jsonify({"error": "Usuario o contraseña incorrectos."}), 401
    return _respuesta_con_token(sesion)


@app.route("/api/login-demo", methods=["POST"])
def api_login_demo():
    datos = request.get_json(silent=True) or {}
    rol = str(datos.get("rol", "")).strip().lower()
    if rol not in ROLES_VALIDOS:
        return jsonify({"error": "Rol de demostración no válido."}), 400

    sesion = AUTH.login_demo(rol)
    if not sesion:
        return jsonify({"error": "No hay usuario de prueba para ese rol."}), 404
    return _respuesta_con_token(sesion)


@app.route("/api/logout", methods=["POST"])
@requiere_sesion()
def api_logout():
    AUTH.logout(_token_de_solicitud())
    respuesta = jsonify({"ok": True})
    respuesta.delete_cookie("sid")
    return respuesta


@app.route("/api/session", methods=["GET"])
def api_session():
    """La sesión se conserva en el navegador (sessionStorage/cookie)."""
    token = _token_de_solicitud()
    sesion = AUTH.obtener_sesion(token) if token else None
    if not sesion:
        return jsonify({"autenticado": False})
    return jsonify({"autenticado": True, "usuario": sesion["usuario"]})


@app.route("/api/horario", methods=["GET"])
@requiere_sesion()
def api_horario():
    """Devuelve el horario filtrado automáticamente según el rol activo."""
    sesion = getattr(g, "sesion", None)
    if not sesion:
        return jsonify({"autenticado": False, "total": 0, "asignaciones": []})

    with _generacion_lock:
        asignaciones = list(_ultimo_horario)

    usuario = sesion["usuario"]
    if sesion["rol"] == "maestro":
        nombre = usuario.get("nombre")
        asignaciones = [a for a in asignaciones if a.get("maestro") == nombre]
    elif sesion["rol"] == "alumno":
        grupo = usuario.get("grupo")
        asignaciones = [a for a in asignaciones if a.get("grupo") == grupo]

    return jsonify({
        "rol": sesion["rol"],
        "usuario": usuario,
        "total": len(asignaciones),
        "asignaciones": asignaciones,
    })


# ----------------------------------------------------------------------
# Rutas/vistas protegidas: el backend decide qué portal se sirve
# ----------------------------------------------------------------------
def _sin_cache(respuesta):
    """Evita que el navegador guarde versiones viejas del HTML/CSS/JS."""
    respuesta.headers["Cache-Control"] = "no-store, max-age=0"
    return respuesta


def _servir_index():
    return _sin_cache(send_file(Path(__file__).with_name("index.html")))


@app.route("/", methods=["GET"])
def index():
    token = _token_de_solicitud()
    sesion = AUTH.obtener_sesion(token) if token else None
    if sesion:
        return redirect(f"/{sesion['rol']}")
    return _servir_index()


@app.route("/style.css", methods=["GET"])
def archivo_css():
    return _sin_cache(send_file(Path(__file__).with_name("style.css"), mimetype="text/css"))


@app.route("/app.js", methods=["GET"])
def archivo_js():
    return _sin_cache(send_file(Path(__file__).with_name("app.js"), mimetype="application/javascript"))


@app.route("/<portal>", methods=["GET"], strict_slashes=False)
def portal_protegido(portal):
    if portal not in ROLES_VALIDOS:
        abort(404)

    # /jefe/ debe redirigir a /jefe: así los recursos relativos (style.css,
    # app.js) siguen resolviendo desde la raíz y no desde /jefe/.
    if request.path.endswith("/"):
        return redirect(request.path.rstrip("/"))

    token = _token_de_solicitud()
    sesion = AUTH.obtener_sesion(token) if token else None
    if not sesion:
        return redirect("/")
    if sesion["rol"] != portal:
        return redirect(f"/{sesion['rol']}")
    return _servir_index()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
