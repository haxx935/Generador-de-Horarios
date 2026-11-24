import logging
from typing import Dict, List
from prolog_manager import atom
from config import Config
from models import Profesor, Disponibilidad, Salon, Grupo, Requerimiento

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, config: Config):
        self.config = config

    def cargar_profesores(self, prolog, datos: dict = None) -> List[Profesor]:
        """Cargar profesores desde JSON y conectarlos a Prolog"""
        profesores = []
        profs = datos["profesores"] if datos and "profesores" in datos else self.config.datos["profesores"]
        for p in profs:
            profesor = Profesor(p['nombre'], p['materia'])
            profesores.append(profesor)
            prolog.assertz(profesor.to_prolog_fact())
        logger.info(f"Cargados {len(profesores)} profesores")
        return profesores

    def cargar_disponibilidades(self, prolog, datos: dict = None) -> List[Disponibilidad]:
        """Cargar disponibilidades desde JSON y conectarlas a Prolog"""
        disponibilidades = []
        disp = datos["disponibilidades"] if datos and "disponibilidades" in datos else self.config.datos["disponibilidades"]
        for d in disp:
            disponibilidad = Disponibilidad(d['profesor'], d['dia'], d['hora'])
            disponibilidades.append(disponibilidad)
            prolog.assertz(disponibilidad.to_prolog_fact())
        logger.info(f"Cargadas {len(disponibilidades)} disponibilidades")
        return disponibilidades

    def cargar_salones(self, prolog, datos: dict = None) -> List[Salon]:
        """Cargar salones desde JSON y conectarlos a Prolog.

        Acepta tanto "salones" (formato archivo config) como "aulas"
        (formato enviado por el frontend / transformar_datos_api_a_prolog).
        """
        salones = []
        salons = (
            datos.get("aulas", datos.get("salones", []))
            if datos and ("aulas" in datos or "salones" in datos)
            else (self.config.datos or {}).get("salones", [])
        )
        for s in salons:
            salon = Salon(s['nombre'], s['capacidad'], s['equipo'], s.get('materias_util', []))
            salones.append(salon)
            prolog.assertz(salon.to_prolog_fact())
            for hecho in salon.to_prolog_materia_util():
                prolog.assertz(hecho)
        logger.info(f"Cargados {len(salones)} salones")
        return salones

    def cargar_grupos(self, prolog, datos: dict = None) -> List[Grupo]:
        """Cargar grupos desde JSON y conectar sus hechos a Prolog.

        Deduplicacion por nombre del grupo (punto 5): si el mismo nombre llega
        con tamanos distintos, prevalece el mas reciente (actualizacion) y se
        registra una advertencia en el log.
        """
        grupos = []
        groups = datos["grupos"] if datos and "grupos" in datos else self.config.datos["grupos"]

        # Agrupar entradas por nombre para detectar duplicados y acumular materias.
        entradas_por_nombre: Dict[str, List[dict]] = {}
        for g in groups:
            entradas_por_nombre.setdefault(g['nombre'], []).append(g)

        for nombre, entradas in entradas_por_nombre.items():
            alumnos_list = [e.get('alumnos', 20) for e in entradas]
            if len(set(alumnos_list)) > 1:
                logger.warning(
                    f"Grupo '{nombre}' tiene tamaños distintos {sorted(set(alumnos_list))}; "
                    f"se usa el mas reciente ({alumnos_list[-1]}) como actualizacion."
                )
            # El mas reciente prevalece para los alumnos.
            alumnos = alumnos_list[-1]
            # Soportar tanto "materia" (singular, formato plano de transformar_datos_api_a_prolog)
            # como "materias" (lista, formato directo del frontend/pruebas).
            materias_entradas = []
            for e in entradas:
                if "materias" in e and isinstance(e["materias"], list):
                    materias_entradas.extend(e["materias"])
                elif "materia" in e:
                    materias_entradas.append(e["materia"])
            if not materias_entradas:
                materias_entradas = [""]
            grupo = Grupo(nombre, alumnos, materias_entradas[0])
            grupos.append(grupo)
            # Registrar grupo/2 una sola vez (evitar grupo_materia duplicado de to_prolog_hechos)
            prolog.assertz(f"grupo({atom(nombre)}, {alumnos})")

            # Registrar grupo_materia para cada materia de este nombre.
            for materia in materias_entradas:
                grupo_materia_hecho = f"grupo_materia({atom(nombre)}, {atom(materia)})"
                prolog.assertz(grupo_materia_hecho)

        logger.info(f"Cargados {len(grupos)} grupos")
        return grupos

    def cargar_requerimientos(self, prolog, datos: dict = None) -> List[Requerimiento]:
        """Cargar requerimientos desde JSON y conectarlos a Prolog"""
        requerimientos = []
        reqs = datos["requerimientos"] if datos and "requerimientos" in datos else self.config.datos["requerimientos"]
        seen_req = set()
        for r in reqs:
            clave = (r['materia'], r['equipo'])
            if clave in seen_req:
                continue
            seen_req.add(clave)
            requerimiento = Requerimiento(r['materia'], r['equipo'])
            requerimientos.append(requerimiento)
            prolog.assertz(requerimiento.to_prolog_fact())
        logger.info(f"Cargados {len(requerimientos)} requerimientos")
        return requerimientos

    def cargar_todos_los_datos(self, prolog, datos: dict = None) -> Dict[str, List]:
        """Cargar todos los datos desde JSON y conectarlos a Prolog.

        Si se proporcionan datos, se usan esos en lugar de cargar del archivo de configuración.
        """
        if datos is None:
            logger.info("Cargando hechos desde el archivo JSON...")
            self.config.cargar()
        else:
            logger.info("Cargando hechos desde datos dinámicos...")

        return {
            'profesores': self.cargar_profesores(prolog, datos),
            'disponibilidades': self.cargar_disponibilidades(prolog, datos),
            'salones': self.cargar_salones(prolog, datos),
            'grupos': self.cargar_grupos(prolog, datos),
            'requerimientos': self.cargar_requerimientos(prolog, datos)
        }