import logging
import os
from typing import List, Dict

# En Windows, pyswip necesita saber dónde está SWI-Prolog (libswipl.dll).
# Debe definirse ANTES de importar pyswip.
if os.name == "nt" and "SWI_HOME_DIR" not in os.environ:
    _swipl = r"C:\Program Files\swipl"
    if os.path.isdir(_swipl):
        os.environ["SWI_HOME_DIR"] = _swipl

from pyswip import Prolog

logger = logging.getLogger(__name__)

# Predicados que se modifican en tiempo de ejecución (nombre/aridad).
PREDICADOS_DINAMICOS = [
    "profesor/2",
    "disponible/3",
    "salon/3",
    "grupo/2",
    "grupo_materia/2",
    "requiere/2",
    "clase_registrada/6",
    "adecuado/3",
    "sin_empalme/5",
    "asignacion_valida/6",
]


def atom(valor) -> str:
    """Convierte un valor a átomo Prolog seguro (con comillas simples)."""
    texto = str(valor).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{texto}'"


class PrologManager:
    def __init__(self):
        self.prolog = Prolog()
        self._reglas_definidas = False
        self._preparar_base()

    # ------------------------------------------------------------------
    # Preparación
    # ------------------------------------------------------------------
    def _preparar_base(self):
        """Declara los predicados como dinámicos y borra datos previos.

        pyswip comparte un único motor Prolog por proceso, así que sin esto
        dos instancias (por ejemplo en los tests) duplicarían hechos y reglas.
        """
        for pred in PREDICADOS_DINAMICOS:
            list(self.prolog.query(f"dynamic({pred})"))
            nombre, aridad = pred.split("/")
            variables = ", ".join(["_"] * int(aridad))
            list(self.prolog.query(f"retractall({nombre}({variables}))"))

    def asegurar_reglas_definidas(self):
        """Asegurar que las reglas lógicas estén definidas en Prolog"""
        if not self._reglas_definidas:
            self._definir_reglas()
            self._reglas_definidas = True

    def _definir_reglas(self):
        """Definir todas las reglas lógicas para el sistema de horarios"""
        logger.info("--- DECLARACIÓN DE REGLAS LÓGICAS ---")

        # Cadenas crudas (r"...") para que \+ llegue tal cual a Prolog.

        # 1. Adecuación de espacio (restricción dura)
        self.prolog.assertz(
            r"adecuado(Salon, Alumnos, Materia) :- "
            r"salon(Salon, Capacidad, EquipoSalon), "
            r"requiere(Materia, EquipoRequerido), "
            r"Capacidad >= Alumnos, "
            r"EquipoSalon = EquipoRequerido"
        )

        # 2. Negación por fallo: no debe existir una clase ya registrada con el
        #    mismo profesor, grupo o salón en el mismo día y hora.
        self.prolog.assertz(
            r"sin_empalme(Prof, Grupo, Salon, Dia, Hora) :- "
            r"\+ clase_registrada(Prof, _, _, _, Dia, Hora), "
            r"\+ clase_registrada(_, _, Grupo, _, Dia, Hora), "
            r"\+ clase_registrada(_, _, _, Salon, Dia, Hora)"
        )

        # 3. Asignación válida (sin considerar empalmes; eso lo hace sin_empalme)
        self.prolog.assertz(
            r"asignacion_valida(Prof, Materia, Grupo, Salon, Dia, Hora) :- "
            r"profesor(Prof, Materia), "
            r"grupo_materia(Grupo, Materia), "
            r"grupo(Grupo, Alumnos), "
            r"disponible(Prof, Dia, Hora), "
            r"adecuado(Salon, Alumnos, Materia)"
        )

        logger.info("Reglas compiladas correctamente")

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def _sin_empalme(self, sol: Dict) -> bool:
        consulta = (
            f"sin_empalme({atom(sol['Prof'])}, {atom(sol['Grupo'])}, "
            f"{atom(sol['Salon'])}, {atom(sol['Dia'])}, {atom(sol['Hora'])})"
        )
        return len(list(self.prolog.query(consulta, maxresult=1))) > 0

    def _registrar_clase(self, sol: Dict):
        self.prolog.assertz(
            f"clase_registrada({atom(sol['Prof'])}, {atom(sol['Materia'])}, "
            f"{atom(sol['Grupo'])}, {atom(sol['Salon'])}, "
            f"{atom(sol['Dia'])}, {atom(sol['Hora'])})"
        )

    def obtener_asignaciones_validas(self) -> List[Dict]:
        """Devuelve solo las asignaciones que pasan sin_empalme.

        Flujo:
          1. Se traen todas las candidatas de asignacion_valida/6.
          2. Por cada una se consulta sin_empalme/5.
          3. Si pasa, se registra con assertz(clase_registrada(...)), de modo
             que la siguiente candidata ya "ve" la anterior.
        """
        logger.info("Generando horario libre de conflictos...")

        # Limpiar registros de ejecuciones anteriores
        list(self.prolog.query("retractall(clase_registrada(_, _, _, _, _, _))"))

        # list() cierra la consulta; así podemos hacer assertz/queries después
        candidatas = list(
            self.prolog.query(
                "asignacion_valida(Prof, Materia, Grupo, Salon, Dia, Hora)"
            )
        )

        aceptadas: List[Dict] = []
        for sol in candidatas:
            if self._sin_empalme(sol):
                self._registrar_clase(sol)
                aceptadas.append(sol)

        logger.info(
            f"{len(aceptadas)} de {len(candidatas)} candidatas sin empalmes"
        )
        return aceptadas