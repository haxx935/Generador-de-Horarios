"""Persistencia de usuarios del Generador Inteligente de Horarios.

El archivo ``usuarios.json`` es la única fuente de datos de credenciales y
perfiles. Si no existe, está vacío o no tiene una estructura válida, se crea
automáticamente con usuarios de ejemplo para los tres roles del sistema.

Las contraseñas nunca se guardan en texto plano: se almacena un hash PBKDF2
con sal por usuario. Se mantiene compatibilidad con registros antiguos que
tuvieran el campo ``contrasena`` para no romper datos ya creados.
"""

import hashlib
import json
import logging
import secrets
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

RUTA_USUARIOS = Path(__file__).with_name("usuarios.json")
ROLES_VALIDOS = ("jefe", "maestro", "alumno")
ITERACIONES_HASH = 120_000

# Usuarios de ejemplo usados para crear usuarios.json la primera vez.
# Las contraseñas demo se documentan en README.md.
USUARIOS_DEMO = [
    {
        "id": "jefe-001",
        "usuario": "jefe",
        "contrasena": "jefe123",
        "nombre": "Lic. Ana Torres",
        "rol": "jefe",
        "activo": True,
        "area": "Área Académica",
    },
    {
        "id": "maestro-001",
        "usuario": "maestro",
        "contrasena": "maestro123",
        "nombre": "Prof. Matemáticas",
        "rol": "maestro",
        "activo": True,
        "materias": ["Matemáticas"],
    },
    {
        "id": "alumno-001",
        "usuario": "alumno",
        "contrasena": "alumno123",
        "nombre": "Carlos López",
        "rol": "alumno",
        "activo": True,
        "semestre": 3,
        "grupo": "Grupo A",
        "materias_aprobadas": ["Matemáticas", "Física", "Historia"],
        "kardex": [
            {"materia": "Matemáticas", "calificacion": 9, "semestre": 1},
            {"materia": "Física", "calificacion": 8, "semestre": 2},
            {"materia": "Historia", "calificacion": 9, "semestre": 2},
        ],
    },
]

CAMPOS_PRIVADOS = {"contrasena", "contrasena_hash", "salt"}


def generar_salt() -> str:
    """Devuelve una sal aleatoria en hexadecimal."""
    return secrets.token_hex(16)


def hash_contrasena(contrasena: str, salt: str) -> str:
    """Calcula el hash PBKDF2-SHA256 de una contraseña con su sal."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        contrasena.encode("utf-8"),
        bytes.fromhex(salt),
        ITERACIONES_HASH,
    ).hex()


def _construir_usuarios_iniciales() -> List[Dict]:
    """Convierte los usuarios demo a registros persistentes con hash."""
    usuarios = []
    for original in USUARIOS_DEMO:
        registro = {clave: valor for clave, valor in original.items() if clave != "contrasena"}
        sal = generar_salt()
        registro["salt"] = sal
        registro["contrasena_hash"] = hash_contrasena(original["contrasena"], sal)
        usuarios.append(registro)
    return usuarios


def crear_estructura_inicial(ruta: Path = RUTA_USUARIOS) -> Dict:
    """Escribe ``usuarios.json`` con la estructura inicial válida."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = {"usuarios": _construir_usuarios_iniciales()}
    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
    logger.info("Creada estructura inicial de usuarios en %s", ruta)
    return datos


def _usuario_valido(usuario) -> bool:
    """Valida los campos obligatorios de un registro de usuario."""
    if not isinstance(usuario, dict):
        return False
    if not all(isinstance(usuario.get(c), str) and usuario[c].strip() for c in ("id", "usuario", "rol")):
        return False
    if usuario["rol"] not in ROLES_VALIDOS:
        logger.warning("Usuario '%s' con rol desconocido '%s'; se ignora", usuario.get("usuario"), usuario.get("rol"))
        return False
    if not (usuario.get("contrasena_hash") and usuario.get("salt")) and not isinstance(usuario.get("contrasena"), str):
        logger.warning("Usuario '%s' sin credencial válida; se ignora", usuario.get("usuario"))
        return False
    return True


def cargar_usuarios(ruta: Path = RUTA_USUARIOS) -> List[Dict]:
    """Lee y valida usuarios.json; lo crea si no existe, está vacío o es inválido."""
    ruta = Path(ruta)
    datos = None

    if ruta.exists():
        contenido = ruta.read_text(encoding="utf-8").strip()
        if contenido:
            try:
                datos = json.loads(contenido)
            except json.JSONDecodeError as exc:
                logger.warning("JSON de usuarios inválido (%s); se regenera", exc)
                datos = None

    if not isinstance(datos, dict) or not isinstance(datos.get("usuarios"), list):
        datos = crear_estructura_inicial(ruta)

    usuarios = [u for u in datos["usuarios"] if _usuario_valido(u)]

    if not usuarios:
        logger.warning("No hay usuarios válidos en %s; se regenera el archivo", ruta)
        usuarios = crear_estructura_inicial(ruta)["usuarios"]

    for usuario in usuarios:
        usuario.setdefault("activo", True)
        usuario.setdefault("nombre", usuario["usuario"])

    return usuarios


def verificar_contrasena(usuario: Dict, contrasena: str) -> bool:
    """Compara de forma segura la contraseña recibida con la almacenada."""
    if not isinstance(contrasena, str):
        return False

    hash_guardado = usuario.get("contrasena_hash")
    salt = usuario.get("salt")
    if isinstance(hash_guardado, str) and isinstance(salt, str):
        try:
            return secrets.compare_digest(hash_contrasena(contrasena, salt), hash_guardado)
        except ValueError:
            logger.warning("Salt inválido para el usuario '%s'", usuario.get("usuario"))
            return False

    # Compatibilidad con registros heredados que guardaban contraseña en texto plano.
    anterior = usuario.get("contrasena")
    if isinstance(anterior, str):
        return secrets.compare_digest(contrasena, anterior)
    return False


def datos_publicos(usuario: Dict) -> Dict:
    """Copia del usuario sin campos sensibles, lista para enviar al frontend."""
    return {clave: valor for clave, valor in usuario.items() if clave not in CAMPOS_PRIVADOS}


def buscar_por_usuario(usuarios: List[Dict], nombre_usuario: str) -> Optional[Dict]:
    """Busca un usuario por su identificador de acceso (insensible a mayúsculas)."""
    objetivo = str(nombre_usuario or "").strip().lower()
    for usuario in usuarios:
        if str(usuario.get("usuario", "")).lower() == objetivo:
            return usuario
    return None


def buscar_por_id(usuarios: List[Dict], identificador: str) -> Optional[Dict]:
    """Busca un usuario por su id."""
    objetivo = str(identificador or "").strip()
    for usuario in usuarios:
        if str(usuario.get("id", "")) == objetivo:
            return usuario
    return None


def primer_usuario_por_rol(usuarios: List[Dict], rol: str) -> Optional[Dict]:
    """Devuelve el primer usuario activo con el rol solicitado (acceso demo)."""
    for usuario in usuarios:
        if usuario.get("rol") == rol and usuario.get("activo", True):
            return usuario
    return None
