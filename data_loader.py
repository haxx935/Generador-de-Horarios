import logging
from typing import Dict, List
from config import Config
from models import Profesor, Disponibilidad, Salon, Grupo, Requerimiento

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, config: Config):
        self.config = config

    def cargar_profesores(self, prolog) -> List[Profesor]:
        """Cargar profesores desde JSON y conectarlos a Prolog"""
        profesores = []
        for p in self.config.datos["profesores"]:
            profesor = Profesor(p['nombre'], p['materia'])
            profesores.append(profesor)
            prolog.assertz(profesor.to_prolog_fact())
        logger.info(f"Cargados {len(profesores)} profesores")
        return profesores

    def cargar_disponibilidades(self, prolog) -> List[Disponibilidad]:
        """Cargar disponibilidades desde JSON y conectarlas a Prolog"""
        disponibilidades = []
        for d in self.config.datos["disponibilidades"]:
            disponibilidad = Disponibilidad(d['profesor'], d['dia'], d['hora'])
            disponibilidades.append(disponibilidad)
            prolog.assertz(disponibilidad.to_prolog_fact())
        logger.info(f"Cargadas {len(disponibilidades)} disponibilidades")
        return disponibilidades

    def cargar_salones(self, prolog) -> List[Salon]:
        """Cargar salones desde JSON y conectarlos a Prolog"""
        salones = []
        for s in self.config.datos["salones"]:
            salon = Salon(s['nombre'], s['capacidad'], s['equipo'])
            salones.append(salon)
            prolog.assertz(salon.to_prolog_fact())
        logger.info(f"Cargados {len(salones)} salones")
        return salones

    def cargar_grupos(self, prolog) -> List[Grupo]:
        """Cargar grupos desde JSON y conectar sus hechos a Prolog"""
        grupos = []
        for g in self.config.datos["grupos"]:
            grupo = Grupo(g['nombre'], g['alumnos'], g['materia'])
            grupos.append(grupo)
            for hecho in grupo.to_prolog_hechos():
                prolog.assertz(hecho)
        logger.info(f"Cargados {len(grupos)} grupos")
        return grupos

    def cargar_requerimientos(self, prolog) -> List[Requerimiento]:
        """Cargar requerimientos desde JSON y conectarlos a Prolog"""
        requerimientos = []
        for r in self.config.datos["requerimientos"]:
            requerimiento = Requerimiento(r['materia'], r['equipo'])
            requerimientos.append(requerimiento)
            prolog.assertz(requerimiento.to_prolog_fact())
        logger.info(f"Cargados {len(requerimientos)} requerimientos")
        return requerimientos

    def cargar_todos_los_datos(self, prolog) -> Dict[str, List]:
        """Cargar todos los datos desde JSON y conectarlos a Prolog"""
        logger.info("Cargando hechos desde el archivo JSON...")
        self.config.cargar()
        
        return {
            'profesores': self.cargar_profesores(prolog),
            'disponibilidades': self.cargar_disponibilidades(prolog),
            'salones': self.cargar_salones(prolog),
            'grupos': self.cargar_grupos(prolog),
            'requerimientos': self.cargar_requerimientos(prolog)
        }