import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, ruta_json: str = "horario_config.json"):
        self.ruta_json = ruta_json
        self.datos = None

    def cargar(self) -> dict:
        """Cargar configuración desde archivo JSON"""
        try:
            with open(self.ruta_json, 'r', encoding='utf-8') as f:
                self.datos = json.load(f)
            logger.info(f"Configuración cargada desde {self.ruta_json}")
            return self.datos
        except FileNotFoundError:
            logger.error(f"Archivo de configuración no encontrado: {self.ruta_json}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON: {e}")
            raise