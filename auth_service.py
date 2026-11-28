"""Servicio de autenticación apoyado en la capa lógica del proyecto.

``usuarios.json`` guarda credenciales y perfiles. ``PrologManager`` evalúa las
reglas declarativas de acceso (roles y sesión activa). Python sólo calcula el
hash PBKDF2 de la contraseña recibida y consulta esas reglas.
"""

import logging
import secrets
from pathlib import Path
from typing import Dict, List, Optional

from auth_store import (
    ROLES_VALIDOS,
    buscar_por_id,
    buscar_por_usuario,
    cargar_usuarios,
    datos_publicos,
    hash_contrasena,
    primer_usuario_por_rol,
    verificar_contrasena,
)
from prolog_manager import PrologManager, atom

logger = logging.getLogger(__name__)


class AuthService:
    """Gestiona usuarios, credenciales y sesiones usando reglas Prolog."""

    def __init__(self, gestor: Optional[PrologManager] = None, ruta_usuarios=None):
        self.prolog_manager = gestor or PrologManager()
        self.ruta_usuarios = Path(ruta_usuarios) if ruta_usuarios else None
        self.usuarios: List[Dict] = self._leer_usuarios()

        # asegurar_reglas_autorizacion ya toma el lock internamente.
        self.prolog_manager.asegurar_reglas_autorizacion()
        with PrologManager._lock:
            self._cargar_hechos_usuarios()

    # ------------------------------------------------------------------
    # Usuarios y hechos Prolog
    # ------------------------------------------------------------------
    def _leer_usuarios(self) -> List[Dict]:
        if self.ruta_usuarios is None:
            return cargar_usuarios()
        return cargar_usuarios(self.ruta_usuarios)

    def _cargar_hechos_usuarios(self):
        """Publica los usuarios de usuarios.json como hechos en Prolog."""
        prolog = self.prolog_manager.prolog
        list(prolog.query("retractall(usuario_registrado(_, _, _, _, _, _))"))

        for usuario in self.usuarios:
            activo = "true" if usuario.get("activo", True) else "false"
            hecho = (
                f"usuario_registrado({atom(usuario['id'])}, {atom(usuario['usuario'])}, "
                f"{atom(usuario.get('contrasena_hash', ''))}, {atom(usuario.get('salt', ''))}, "
                f"{atom(usuario['rol'])}, {activo})"
            )
            prolog.assertz(hecho)
        logger.info("Cargados %d usuarios en la base lógica", len(self.usuarios))

    def recargar_usuarios(self) -> List[Dict]:
        """Vuelve a leer usuarios.json y actualiza los hechos en Prolog."""
        with PrologManager._lock:
            self.usuarios = self._leer_usuarios()
            self._cargar_hechos_usuarios()
        return self.usuarios

    # ------------------------------------------------------------------
    # Consultas a las reglas Prolog
    # ------------------------------------------------------------------
    def _consultar(self, consulta: str) -> List[Dict]:
        with PrologManager._lock:
            return list(self.prolog_manager.prolog.query(consulta))

    def _credencial_en_prolog(self, usuario: Dict, contrasena: str) -> bool:
        """Evalúa la regla credencial_valida/4 (o usuario_permitido/3 si es legacy)."""
        hash_guardado = usuario.get("contrasena_hash")
        salt = usuario.get("salt")
        if isinstance(hash_guardado, str) and isinstance(salt, str):
            try:
                calculado = hash_contrasena(contrasena, salt)
            except ValueError:
                return False
            consulta = (
                f"credencial_valida({atom(usuario['usuario'])}, {atom(calculado)}, Id, Rol)"
            )
            return bool(self._consultar(consulta))

        # Compatibilidad con usuarios heredados con contraseña en texto plano.
        return bool(
            self._consultar(
                f"usuario_permitido({atom(usuario['usuario'])}, Id, Rol)"
            )
        )

    # ------------------------------------------------------------------
    # Sesiones
    # ------------------------------------------------------------------
    def _crear_sesion(self, usuario: Dict) -> Optional[Dict]:
        """Verifica el rol con Prolog, crea un token y lo registra como hecho."""
        permitido = self._consultar(
            f"rol_permitido({atom(usuario['rol'])}, Portal)"
        )
        if not permitido:
            logger.warning("Rol no permitido: %s", usuario.get("rol"))
            return None

        token = secrets.token_urlsafe(32)
        with PrologManager._lock:
            self.prolog_manager.prolog.assertz(
                f"sesion_activa({atom(token)}, {atom(usuario['id'])}, {atom(usuario['rol'])})"
            )
        return {"token": token, "usuario": datos_publicos(usuario)}

    def login(self, nombre_usuario: str, contrasena: str) -> Optional[Dict]:
        """Valida credenciales contra usuarios.json y las reglas Prolog."""
        # usuarios.json es la fuente de verdad: si se editó mientras el
        # servidor estaba corriendo, se refleja en el próximo inicio de sesión.
        self.recargar_usuarios()
        usuario = buscar_por_usuario(self.usuarios, nombre_usuario)
        if not usuario or not usuario.get("activo", True):
            return None
        if not verificar_contrasena(usuario, contrasena):
            return None
        if not self._credencial_en_prolog(usuario, contrasena):
            return None
        return self._crear_sesion(usuario)

    def login_demo(self, rol: str) -> Optional[Dict]:
        """Acceso rápido de un clic para un usuario de prueba del rol dado."""
        self.recargar_usuarios()
        if rol not in ROLES_VALIDOS:
            return None
        usuario = primer_usuario_por_rol(self.usuarios, rol)
        if not usuario:
            return None
        return self._crear_sesion(usuario)

    def obtener_sesion(self, token: Optional[str]) -> Optional[Dict]:
        """Devuelve la sesión activa sólo si Prolog autoriza el token y el portal."""
        if not token:
            return None

        autorizados = self._consultar(
            f"acceso_permitido({atom(token)}, Portal, Rol)"
        )
        if not autorizados:
            return None

        ids = self._consultar(f"sesion_id({atom(token)}, Id)")
        if not ids:
            return None

        identificador = str(ids[0]["Id"])
        rol = str(autorizados[0]["Rol"])
        usuario = buscar_por_id(self.usuarios, identificador)
        if not usuario or not usuario.get("activo", True):
            return None

        return {
            "token": token,
            "id": identificador,
            "rol": rol,
            "portal": str(autorizados[0]["Portal"]),
            "usuario": datos_publicos(usuario),
        }

    def puede_acceder(self, token: str, portal: str) -> bool:
        """¿El token tiene acceso al portal solicitado? (regla acceso_permitido/3)."""
        return bool(
            self._consultar(
                f"acceso_permitido({atom(token)}, {atom(portal)}, Rol)"
            )
        )

    def logout(self, token: Optional[str]):
        """Elimina el hecho de sesión activa, invalidando el token."""
        if not token:
            return
        with PrologManager._lock:
            list(
                self.prolog_manager.prolog.query(
                    f"retractall(sesion_activa({atom(token)}, _, _))"
                )
            )

    def obtener_usuario_por_id(self, identificador: str) -> Optional[Dict]:
        """Perfil público de un usuario por id (para filtrar vistas)."""
        usuario = buscar_por_id(self.usuarios, identificador)
        return datos_publicos(usuario) if usuario else None
