"""Pruebas del módulo de inicio de sesión, sesiones y enrutamiento por roles."""

import json
import os
import sys

# Asegurar que se importan los módulos de la raíz del proyecto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import api  # noqa: E402
import auth_store  # noqa: E402
from auth_service import AuthService  # noqa: E402
from prolog_manager import PrologManager, atom  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth():
    """Servicio de autenticación sobre el usuarios.json del proyecto.

    Todos los PrologManager comparten el motor pyswip del proceso, por lo que
    las pruebas que consultan la API usan el mismo archivo que ``api.AUTH``.
    """
    return AuthService()


@pytest.fixture
def cliente():
    api.app.config["TESTING"] = True
    with api.app.test_client() as cliente_http:
        yield cliente_http


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Persistencia en usuarios.json
# ---------------------------------------------------------------------------

def test_crea_usuarios_iniciales_cuando_no_existe(tmp_path):
    ruta = tmp_path / "usuarios.json"
    usuarios = auth_store.cargar_usuarios(ruta)

    assert ruta.exists()
    assert {u["rol"] for u in usuarios} == {"jefe", "maestro", "alumno"}
    assert all(u.get("contrasena_hash") and u.get("salt") for u in usuarios)
    assert all("contrasena" not in u for u in usuarios)


def test_crea_usuarios_cuando_archivo_esta_vacio(tmp_path):
    ruta = tmp_path / "usuarios.json"
    ruta.write_text("   ", encoding="utf-8")

    usuarios = auth_store.cargar_usuarios(ruta)

    assert len(usuarios) == 3
    assert usuarios[1]["rol"] == "maestro"
    assert "materias" in usuarios[1]
    assert usuarios[2]["rol"] == "alumno"
    assert "semestre" in usuarios[2]
    assert "materias_aprobadas" in usuarios[2]


def test_verificacion_de_contrasenas(auth):
    usuario = auth_store.buscar_por_usuario(auth.usuarios, "jefe")

    assert auth_store.verificar_contrasena(usuario, "jefe123")
    assert not auth_store.verificar_contrasena(usuario, "incorrecta")


# ---------------------------------------------------------------------------
# Reglas declarativas en Prolog
# ---------------------------------------------------------------------------

def test_reglas_de_roles_en_prolog(auth):
    with PrologManager._lock:
        resultado = list(auth.prolog_manager.prolog.query("rol_permitido(Rol, Portal)"))
    pares = {(str(r["Rol"]), str(r["Portal"])) for r in resultado}
    assert pares == {("jefe", "jefe"), ("maestro", "maestro"), ("alumno", "alumno")}


def test_regla_credencial_valida_en_prolog(auth):
    usuario = auth_store.buscar_por_usuario(auth.usuarios, "alumno")
    calculado = auth_store.hash_contrasena("alumno123", usuario["salt"])
    consulta = (
        f"credencial_valida({atom(usuario['usuario'])}, "
        f"{atom(calculado)}, Id, Rol)"
    )
    with PrologManager._lock:
        resultado = list(auth.prolog_manager.prolog.query(consulta))
    assert resultado and str(resultado[0]["Rol"]) == "alumno"


# ---------------------------------------------------------------------------
# Login, sesión y logout
# ---------------------------------------------------------------------------

def test_login_valido_e_invalido(auth):
    sesion = auth.login("jefe", "jefe123")
    assert sesion and sesion["usuario"]["rol"] == "jefe"
    assert "contrasena_hash" not in sesion["usuario"]

    assert auth.login("jefe", "mala") is None
    assert auth.login("no-existe", "jefe123") is None


def test_sesion_y_acceso_segun_rol_en_prolog(auth):
    sesion = auth.login("maestro", "maestro123")
    token = sesion["token"]

    actual = auth.obtener_sesion(token)
    assert actual["rol"] == "maestro"
    assert auth.puede_acceder(token, "maestro")
    assert not auth.puede_acceder(token, "jefe")
    assert not auth.puede_acceder(token, "alumno")

    auth.logout(token)
    assert auth.obtener_sesion(token) is None


def test_login_demo_para_cada_rol(auth):
    for rol in ("jefe", "maestro", "alumno"):
        sesion = auth.login_demo(rol)
        assert sesion["usuario"]["rol"] == rol
        assert auth.obtener_sesion(sesion["token"])["rol"] == rol


# ---------------------------------------------------------------------------
# API y protección de rutas
# ---------------------------------------------------------------------------

def test_api_login_y_sesion(cliente):
    respuesta = cliente.post("/api/login", json={"usuario": "jefe", "contrasena": "jefe123"})
    assert respuesta.status_code == 200
    token = respuesta.get_json()["token"]

    sesion = cliente.get("/api/session", headers=_bearer(token))
    assert sesion.get_json()["autenticado"] is True
    assert sesion.get_json()["usuario"]["rol"] == "jefe"

    cliente.post("/api/logout", headers=_bearer(token))
    assert cliente.get("/api/session", headers=_bearer(token)).get_json()["autenticado"] is False


def test_api_login_incorrecto(cliente):
    respuesta = cliente.post("/api/login", json={"usuario": "jefe", "contrasena": "mala"})
    assert respuesta.status_code == 401
    assert "incorrectos" in respuesta.get_json()["error"]


def test_api_login_demo(cliente):
    respuesta = cliente.post("/api/login-demo", json={"rol": "alumno"})
    assert respuesta.status_code == 200
    assert respuesta.get_json()["usuario"]["rol"] == "alumno"


def test_cookie_es_httponly(cliente):
    respuesta = cliente.post("/api/login", json={"usuario": "jefe", "contrasena": "jefe123"})
    cookie = respuesta.headers["Set-Cookie"]
    assert "sid=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_token_hostil_no_burla_las_reglas(cliente):
    """Un token con comillas no debe poder inyectar términos Prolog."""
    for token in ["', true).", "x', true, 'y", "a\\', fail)."]:
        respuesta = cliente.get("/api/session", headers=_bearer(token))
        assert respuesta.status_code == 200
        assert respuesta.get_json()["autenticado"] is False


def test_ruta_de_otro_rol_redirige(cliente):
    token = cliente.post("/api/login-demo", json={"rol": "maestro"}).get_json()["token"]

    respuesta = cliente.get("/maestro", headers={"Cookie": f"sid={token}"})
    assert respuesta.status_code == 200

    respuesta = cliente.get("/jefe", headers={"Cookie": f"sid={token}"})
    assert respuesta.status_code in (302, 303)
    assert respuesta.headers["Location"] == "/maestro"


def test_ruta_sin_sesion_redirige_a_login(cliente, monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", False)
    respuesta = cliente.get("/alumno")
    assert respuesta.status_code in (302, 303)
    assert respuesta.headers["Location"] == "/"


def test_generar_horario_rechaza_a_maestro(cliente):
    token = cliente.post("/api/login-demo", json={"rol": "maestro"}).get_json()["token"]
    respuesta = cliente.post(
        "/generar-horario", json={}, headers=_bearer(token)
    )
    assert respuesta.status_code == 403
    assert "rol" in respuesta.get_json()["error"]


def test_generar_horario_sin_sesion_requiere_login(cliente, monkeypatch):
    monkeypatch.setitem(api.app.config, "TESTING", False)
    respuesta = cliente.post("/generar-horario", json={})
    assert respuesta.status_code == 401


def test_testing_no_omite_la_autenticacion(cliente):
    """Ni siquiera con TESTING=True se puede saltar la comprobación de sesión."""
    assert api.app.config["TESTING"] is True
    assert cliente.post("/generar-horario", json={}).status_code == 401
    assert cliente.get("/api/horario").status_code == 401


def test_ruta_con_barra_final_redirige(cliente):
    token = cliente.post("/api/login-demo", json={"rol": "maestro"}).get_json()["token"]
    respuesta = cliente.get("/maestro/", headers={"Cookie": f"sid={token}"})
    assert respuesta.status_code in (302, 303)
    assert respuesta.headers["Location"] == "/maestro"


def test_index_sirve_html_y_recursos_estaticos(cliente):
    """La raíz y las rutas de portal deben cargar CSS/JS (interfaz con estilo)."""
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)
    assert 'href="style.css"' in html
    assert 'src="app.js"' in html

    css = cliente.get("/style.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["Content-Type"]
    assert "no-store" in css.headers["Cache-Control"]

    js = cliente.get("/app.js")
    assert js.status_code == 200
    assert "javascript" in js.headers["Content-Type"]
    assert "no-store" in js.headers["Cache-Control"]


def test_cambios_en_usuarios_json_se_aplican_sin_reiniciar(tmp_path):
    """Editar usuarios.json (por ejemplo una contraseña) se refleja al entrar."""
    ruta = tmp_path / "usuarios.json"
    servicio = AuthService(ruta_usuarios=ruta)
    try:
        assert servicio.login("jefe", "jefe123")

        datos = json.loads(ruta.read_text(encoding="utf-8"))
        usuario = datos["usuarios"][0]
        sal = auth_store.generar_salt()
        usuario["salt"] = sal
        usuario["contrasena_hash"] = auth_store.hash_contrasena("nueva123", sal)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

        assert servicio.login("jefe", "jefe123") is None
        assert servicio.login("jefe", "nueva123")
    finally:
        # Este servicio compartió el motor Prolog con api.AUTH: se restauran
        # los hechos del archivo del proyecto para no afectar otras pruebas.
        api.AUTH.recargar_usuarios()


def test_api_horario_filtra_por_rol(cliente, monkeypatch):
    horario = [
        {"maestro": "Prof. Matemáticas", "grupo": "Grupo A", "materia": "Matemáticas"},
        {"maestro": "Prof. Física", "grupo": "Grupo B", "materia": "Física"},
    ]
    monkeypatch.setattr(api, "_ultimo_horario", horario)

    token_maestro = cliente.post("/api/login-demo", json={"rol": "maestro"}).get_json()["token"]
    datos = cliente.get("/api/horario", headers=_bearer(token_maestro)).get_json()
    assert datos["total"] == 1
    assert datos["asignaciones"][0]["maestro"] == "Prof. Matemáticas"

    token_alumno = cliente.post("/api/login-demo", json={"rol": "alumno"}).get_json()["token"]
    datos = cliente.get("/api/horario", headers=_bearer(token_alumno)).get_json()
    assert datos["total"] == 1
    assert datos["asignaciones"][0]["grupo"] == "Grupo A"

    token_jefe = cliente.post("/api/login-demo", json={"rol": "jefe"}).get_json()["token"]
    datos = cliente.get("/api/horario", headers=_bearer(token_jefe)).get_json()
    assert datos["total"] == 2
