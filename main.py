import logging
from pathlib import Path

# Configuración del sistema

def configurar_logging():
    """Configurar logging con archivo y salida de consola"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('horario_generator.log'),
            logging.StreamHandler()
        ]
    )

# Importaciones del sistema
from horario_generator import HorarioGenerator
class Main:
    def __init__(self):
        configurar_logging()
        self.generador_horario = HorarioGenerator()

    def ejecutar(self):
        """Función principal que ejecuta todo el proceso"""
        try:
            logger = logging.getLogger(__name__)
            logger.info("=" * 50)
            logger.info("INICIANDO GENERACIÓN DE HORARIOS")
            logger.info("=" * 50)

            # Generar y mostrar el horario
            horario = self.generador_horario.ejecutar()

            logger.info("=" * 50)
            logger.info(f"PROCESO COMPLETADO - Se generaron {len(horario)} clases")
            logger.info("=" * 50)

            return horario

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"ERROR EN EL PROCESO: {e}")
            raise

if __name__ == "__main__":
    main = Main()
    horario = main.ejecutar()
    print(f"\nResumen: Se generaron {len(horario)} clases para el horario académico.")