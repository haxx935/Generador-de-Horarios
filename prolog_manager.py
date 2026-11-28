import logging
import os
import re
import threading
from typing import List, Dict

# En Windows, pyswip necesita saber dónde está SWI-Prolog (libswipl.dll).
# Debe definirse ANTES de importar pyswip.
if os.name == "nt" and "SWI_HOME_DIR" not in os.environ:
    _swipl = r"C:\Program Files\swipl"
    if os.path.isdir(_swipl):
        os.environ["SWI_HOME_DIR"] = _swipl

from pyswip import Prolog

logger = logging.getLogger(__name__)

# Días laborables y cupos máximos.
DIAS_LABORALES = ["lunes", "martes", "miercoles", "jueves", "viernes"]
MAX_CLASES_POR_MATERIA_DIA = 2
MAX_CLASES_SEMANA = 4
LIMITE_INFERENCIAS = 2000000

# Predicados dinámicos (hechos y reglas que se cargan en tiempo de ejecución).
PREDICADOS_DINAMICOS = [
    "profesor/2",
    "disponible/3",
    "salon/3",
    "materia_util/2",
    "grupo/2",
    "grupo_materia/2",
    "requiere/2",
    "dia/1",
    "adecuado/3",
    "asignacion_valida/6",
    "generar_horario/1",
    "sesiones_requeridas/1",
    "contar_candidatos/2",
    "ordenar_por_restriccion/2",
    "asignar_una/5",
    "asignar_todas/3",
    "mejor_parcial/3",
    "empalme_acumulado/6",
    "cupo_dia_acumulado/5",
    "cupo_semana_acumulado/4",
]

# Predicados de autorización. Se declaran por separado (NO en PREDICADOS_DINAMICOS)
# para que la creación de un HorarioGenerator no borre usuarios ni sesiones activas:
# todos los PrologManager comparten un único motor pyswip por proceso.
PREDICADOS_AUTORIZACION = [
    "usuario_registrado/6",  # (Id, Usuario, Hash, Salt, Rol, Activo)
    "rol_permitido/2",       # (Rol, Portal)
    "sesion_activa/3",       # (Token, Id, Rol)
    "credencial_valida/4",   # (Usuario, HashCalculado, Id, Rol)
    "usuario_permitido/3",   # (Usuario, Id, Rol)
    "acceso_permitido/3",    # (Token, Portal, Rol)
    "token_valido/1",        # (Token)
    "sesion_id/2",           # (Token, Id)
    "sesion_rol/2",          # (Token, Rol)
]

# Reglas (no hechos de datos) que se recompilan al crear un AuthService.
# usuario_registrado/6 y sesion_activa/3 se gestionan explícitamente desde
# auth_service.py y por eso NO se incluyen aquí.
REGLAS_AUTORIZACION = [
    "rol_permitido/2",
    "credencial_valida/4",
    "usuario_permitido/3",
    "acceso_permitido/3",
    "token_valido/1",
    "sesion_id/2",
    "sesion_rol/2",
]


def atom(valor) -> str:
    """Convierte un valor a átomo Prolog seguro (con comillas simples)."""
    texto = str(valor).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{texto}'"


class PrologManager:
    _lock = threading.Lock()

    def __init__(self):
        self.prolog = Prolog()
        self._reglas_definidas = False
        self._reglas_autorizacion_definidas = False
        self._preparar_base()

    # ------------------------------------------------------------------
    # Preparación
    # ------------------------------------------------------------------
    def _preparar_base(self):
        """Declara predicados dinámicos y borra datos/reglas previas.

        pyswip comparte un único motor Prolog por proceso; sin esta limpieza
        dos instancias duplicarían hechos y reglas.
        """
        for pred in PREDICADOS_DINAMICOS:
            list(self.prolog.query(f"dynamic({pred})"))
            nombre, aridad = pred.split("/")
            variables = ", ".join(["_"] * int(aridad))
            list(self.prolog.query(f"retractall({nombre}({variables}))"))

    def asegurar_reglas_definidas(self):
        """Asegura que las reglas lógicas estén definidas en Prolog."""
        if not self._reglas_definidas:
            self._definir_reglas()
            self._reglas_definidas = True

    def asegurar_reglas_autorizacion(self):
        """Declara y compila las reglas declarativas de acceso y sesión.

        Estas reglas viven en el mismo motor Prolog que el generador de horarios.
        Se declaran una sola vez por instancia; los hechos de usuario/sesión se
        cargan desde ``auth_service.py`` y no se confunden con los hechos del
        horario.
        """
        with PrologManager._lock:
            if not self._reglas_autorizacion_definidas:
                for pred in PREDICADOS_AUTORIZACION:
                    list(self.prolog.query(f"dynamic({pred})"))
                self._definir_reglas_autorizacion()
                self._reglas_autorizacion_definidas = True

    def _definir_reglas_autorizacion(self):
        """Reglas Prolog para credenciales, roles permitidos y sesiones activas."""
        logger.info("--- DECLARACIÓN DE REGLAS DE AUTORIZACIÓN ---")

        # Evita reglas duplicadas si se crea más de un AuthService en el proceso.
        for pred in REGLAS_AUTORIZACION:
            nombre, aridad = pred.split("/")
            variables = ", ".join(["_"] * int(aridad))
            list(self.prolog.query(f"retractall({nombre}({variables}))"))

        # Un rol sólo puede entrar a su propio portal.
        self.prolog.assertz(r"rol_permitido(jefe, jefe)")
        self.prolog.assertz(r"rol_permitido(maestro, maestro)")
        self.prolog.assertz(r"rol_permitido(alumno, alumno)")

        # La contraseña se valida en Python por ser PBKDF2; Prolog comprueba
        # que el hash calculado coincide con el guardado y que el usuario está activo.
        self.prolog.assertz(
            r"credencial_valida(Usuario, HashCalculado, Id, Rol) :- "
            r"usuario_registrado(Id, Usuario, HashGuardado, _, Rol, true), "
            r"HashGuardado == HashCalculado"
        )

        # Regla de compatibilidad para registros heredados con contraseña en texto plano.
        self.prolog.assertz(
            r"usuario_permitido(Usuario, Id, Rol) :- "
            r"usuario_registrado(Id, Usuario, _, _, Rol, true), "
            r"rol_permitido(Rol, _)"
        )

        # Una sesión sólo es válida si tiene token activo Y un rol autorizado.
        self.prolog.assertz(
            r"acceso_permitido(Token, Portal, Rol) :- "
            r"sesion_activa(Token, _, Rol), "
            r"rol_permitido(Rol, Portal)"
        )
        self.prolog.assertz(r"token_valido(Token) :- sesion_activa(Token, _, _)")
        self.prolog.assertz(r"sesion_id(Token, Id) :- sesion_activa(Token, Id, _)")
        self.prolog.assertz(r"sesion_rol(Token, Rol) :- sesion_activa(Token, _, Rol)")

        logger.info("Reglas de autorización compiladas correctamente")

    def _definir_reglas(self):
        """Define todas las reglas lógicas del sistema de horarios en Prolog.

        La búsqueda del horario vive ahora íntegramente en Prolog:
        - generar_horario/1 es el punto de entrada.
        - Las sesiones se construyen una a una con backtracking.
        - El acumulado viaja como argumento de lista (no assertz/retractall
          durante la búsqueda).

        Nota: los strings pasados a assertz NO llevan punto final (.) porque
        pyswip ya envuelve el término en assertz(...).
        """
        logger.info("--- DECLARACIÓN DE REGLAS LÓGICAS ---")

        # 1. Adecuación de salón (restricción dura).
        self.prolog.assertz(
            r"adecuado(Salon, Alumnos, Materia) :- "
            r"salon(Salon, Capacidad, EquipoSalon), "
            r"requiere(Materia, EquipoRequerido), "
            r"(\+ materia_util(Salon, _) ; materia_util(Salon, Materia)), "
            r"Capacidad >= Alumnos, "
            r"EquipoSalon = EquipoRequerido"
        )

        # 2. Días laborables.
        for d in DIAS_LABORALES:
            self.prolog.assertz(f"dia({atom(d)})")

        # 3. asignacion_valida/6 (mantenida para consulta individual/compatibilidad).
        self.prolog.assertz(
            r"asignacion_valida(Prof, Materia, Grupo, Salon, Dia, Hora) :- "
            r"profesor(Prof, Materia), "
            r"grupo_materia(Grupo, Materia), "
            r"grupo(Grupo, Alumnos), "
            r"disponible(Prof, Dia, Hora), "
            r"adecuado(Salon, Alumnos, Materia)"
        )

        # 4. Empalme contra el acumulado (lista de sesiones ya asignadas).
        self.prolog.assertz(
            r"empalme_acumulado(Prof, Grupo, Salon, Dia, Hora, Acumulado) :- "
            r"member(sesion(Prof, _, _, _, Dia, Hora), Acumulado)"
        )
        self.prolog.assertz(
            r"empalme_acumulado(Prof, Grupo, Salon, Dia, Hora, Acumulado) :- "
            r"member(sesion(_, _, Grupo, _, Dia, Hora), Acumulado)"
        )
        self.prolog.assertz(
            r"empalme_acumulado(Prof, Grupo, Salon, Dia, Hora, Acumulado) :- "
            r"member(sesion(_, _, _, Salon, Dia, Hora), Acumulado)"
        )

        # 5. Cupo diario acumulado (máx. 2 horas de una misma materia al día por grupo).
        self.prolog.assertz(
            r"cupo_dia_acumulado(Grupo, Dia, Materia, Max, Acumulado) :- "
            r"findall(_, member(sesion(_, Materia, Grupo, _, Dia, _), Acumulado), Lista), "
            r"length(Lista, N), "
            r"N < Max"
        )

        # 6. Cupo semanal acumulado (máx. 4 horas de una misma materia a la semana por grupo).
        self.prolog.assertz(
            r"cupo_semana_acumulado(Grupo, Materia, Max, Acumulado) :- "
            r"findall(_, member(sesion(_, Materia, Grupo, _, _, _), Acumulado), Lista), "
            r"length(Lista, N), "
            r"N < Max"
        )

        # 7. Contar candidatos de una sesión (heurística: menos candidatos = más restringida).
        self.prolog.assertz(
            r"contar_candidatos(sesion(Prof, Materia, Grupo, _, _, _), N) :- "
            r"findall(_, (dia(Dia), disponible(Prof, Dia, Hora), grupo(Grupo, Alumnos), adecuado(Salon, Alumnos, Materia)), C), "
            r"length(C, N)"
        )

        # 8. Ordenar sesiones por restricción (keysort ascendente por conteo de candidatos).
        self.prolog.assertz(
            r"ordenar_por_restriccion(Sesiones, Ordenadas) :- "
            r"maplist(contar_candidatos, Sesiones, Conteos), "
            r"pairs_keys_values(Pares, Conteos, Sesiones), "
            r"keysort(Pares, OrdenadasPares), "
            r"pairs_values(OrdenadasPares, Ordenadas)"
        )

        # 9. Asignar una sesión dada el acumulado actual (genera Día/Hora/Salón por backtracking).
        self.prolog.assertz(
            r"asignar_una(Prof, Materia, Grupo, Acumulado, sesion(Prof, Materia, Grupo, Salon, Dia, Hora)) :- "
            r"dia(Dia), "
            r"disponible(Prof, Dia, Hora), "
            r"grupo(Grupo, Alumnos), "
            r"adecuado(Salon, Alumnos, Materia), "
            r"\+ empalme_acumulado(Prof, Grupo, Salon, Dia, Hora, Acumulado), "
            r"cupo_dia_acumulado(Grupo, Dia, Materia, 2, Acumulado), "
            r"cupo_semana_acumulado(Grupo, Materia, 4, Acumulado)"
        )

        # 10. Asignar todas las sesiones recursivamente con backtracking y acumulado por lista.
        self.prolog.assertz(
            r"asignar_todas([], Horario, Horario)"
        )
        self.prolog.assertz(
            r"asignar_todas([Sesion|Resto], Acumulado, Horario) :- "
            r"Sesion = sesion(Prof, Materia, Grupo, _, _, _), "
            r"asignar_una(Prof, Materia, Grupo, Acumulado, NuevaSesion), "
            r"asignar_todas(Resto, [NuevaSesion|Acumulado], Horario)"
        )

        # 11. Mejor solución parcial (intenta asignar en orden, salta si no puede;
        #     once/1 evita el backtracking exponencial al tomar una opción por sesión).
        self.prolog.assertz(
            r"mejor_parcial([], Acumulado, Acumulado)"
        )
        self.prolog.assertz(
            r"mejor_parcial([Sesion|Resto], Acumulado, Mejor) :- "
            r"Sesion = sesion(Prof, Materia, Grupo, _, _, _), "
            r"(   once(asignar_una(Prof, Materia, Grupo, Acumulado, NuevaSesion)), "
            r"    mejor_parcial(Resto, [NuevaSesion|Acumulado], Mejor) "
            r";   mejor_parcial(Resto, Acumulado, Mejor) "
            r")"
        )

        # 12. Predicado principal: generar_horario(Horario).
        #     Construye sesiones (4 por par grupo-materia), ordena por restricción,
        #     intenta solución completa con límite de inferencias, si falla devuelve
        #     la mejor parcial.
        self.prolog.assertz(
            r"generar_horario(Horario) :- "
            r"sesiones_requeridas(Sesiones), "
            r"ordenar_por_restriccion(Sesiones, SesionesOrd), "
            r"(   call_with_inference_limit(asignar_todas(SesionesOrd, [], Horario), "
            f"{LIMITE_INFERENCIAS}, _) -> true "
            r";   mejor_parcial(SesionesOrd, [], Horario) "
            r")"
        )

        # 13. Sesiones requeridas: 4 por cada par (grupo, materia) con profesor disponible.
        self.prolog.assertz(
            r"sesiones_requeridas(Sesiones) :- "
            r"findall(sesion(Prof, Materia, Grupo, _, _, _), "
            r"(grupo_materia(Grupo, Materia), profesor(Prof, Materia), between(1, 4, _)), Sesiones)"
        )

        logger.info("Reglas compiladas correctamente")

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def generar_horario_prolog(self) -> List[Dict]:
        """Llama UNA vez a generar_horario/1 y devuelve la lista de sesiones asignadas.

        Cada elemento es un dict con claves: Prof, Materia, Grupo, Salon, Dia, Hora.
        """
        with self._lock:
            list(self.prolog.query("retractall(clase_registrada(_, _, _, _, _, _))"))
            resultados = list(self.prolog.query("generar_horario(Horario)"))
            if not resultados:
                return []

            horario_term = resultados[0]["Horario"]
            asignaciones: List[Dict] = []
            for sesion_term in self._iterar_lista_prolog(horario_term):
                args = self._args_de_termino(sesion_term)
                if len(args) >= 6:
                    asignaciones.append({
                        "Prof": str(args[0]),
                        "Materia": str(args[1]),
                        "Grupo": str(args[2]),
                        "Salon": str(args[3]),
                        "Dia": str(args[4]),
                        "Hora": str(args[5]),
                    })
            return asignaciones

    # --- utilidades internas para leer términos de pyswip -------------
    @staticmethod
    def _iterar_lista_prolog(term):
        """Itera sobre una lista de Prolog devuelta por pyswip.

        Maneja listas nativas de Python, términos encadenados
        .(Cabeza, Cola), vacías [] y strings 'sesion(...)'.
        """
        if isinstance(term, list):
            for elemento in term:
                yield elemento
            return

        functor = getattr(term, "functor", None)
        args = getattr(term, "args", None)

        if functor == "[]" or (isinstance(term, str) and term == "[]"):
            return
        if functor == "." and args and len(args) == 2:
            cabeza, cola = args
            yield cabeza
            yield from PrologManager._iterar_lista_prolog(cola)
        else:
            yield term

    @staticmethod
    def _args_de_termino(term):
        """Devuelve los argumentos de un término compuesto, o [] si no tiene.

        pyswip puede devolver átomos como strings planos (p. ej.
        'sesion(Prof, Materia, Grupo, Salon, Dia, Hora)'); en ese caso se
        hace un parseo ligero por comas (los valores no contienen comas).
        """
        if isinstance(term, str):
            m = re.match(r"\w+\((.*)\)\s*$", term.strip())
            if m:
                return [a.strip().strip("'") for a in m.group(1).split(",")]
            return []
        args = getattr(term, "args", None)
        if args is None:
            return []
        return list(args)

    # --- compatibilidad con la API anterior (legacy) ------------------
    def obtener_asignaciones_validas(self, max_clases_por_materia_dia: int = MAX_CLASES_POR_MATERIA_DIA) -> List[Dict]:
        """Devuelve las asignaciones generadas por Prolog (interfaz legacy)."""
        return self.generar_horario_prolog()
