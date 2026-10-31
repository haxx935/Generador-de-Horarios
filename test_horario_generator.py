"""
Test suite for the refactored HorarioGenerator class.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from horario_generator import HorarioGenerator
from config import Config
from data_loader import DataLoader
from prolog_manager import PrologManager
from scheduler import ScheduleOptimizer
from output_formatter import HorarioFormatter
from models import Clase


class TestHorarioGenerator(unittest.TestCase):
    """Test cases for HorarioGenerator class"""

    def setUp(self):
        self.mock_prolog = Mock()
        self.mock_config = Mock(spec=Config)
        self.mock_config.datos = {}

    def test_generar_horario_llama_componentes_en_orden(self):
        with patch.object(DataLoader, 'cargar_todos_los_datos', return_value={}) as mock_cargar, \
             patch.object(PrologManager, 'asegurar_reglas_definidas') as mock_reglas, \
             patch.object(PrologManager, 'obtener_asignaciones_validas', return_value=[]) as mock_asignar, \
             patch.object(ScheduleOptimizer, 'optimizar_horario', return_value=[]) as mock_optimizar:

            generador = HorarioGenerator.__new__(HorarioGenerator)
            generador.config = self.mock_config
            generador.data_loader = Mock()
            generador.data_loader.cargar_todos_los_datos = mock_cargar
            generador.prolog_manager = Mock()
            generador.prolog_manager.asegurar_reglas_definidas = mock_reglas
            generador.prolog_manager.obtener_asignaciones_validas = mock_asignar
            generador.optimizer = Mock()
            generador.optimizer.optimizar_horario = mock_optimizar

            resultado = generador.generar_horario()

            mock_cargar.assert_called_once_with(generador.prolog_manager.prolog)
            mock_reglas.assert_called_once()
            mock_asignar.assert_called_once()
            mock_optimizar.assert_called_once()
            self.assertEqual(resultado, [])

    def test_optimizar_horario_elimina_duplicados_por_slot(self):
        soluciones = [
            {'Prof': 'ana', 'Materia': 'fisica', 'Grupo': 'grupo_a', 'Salon': 'aula_101', 'Dia': 'lunes', 'Hora': 'h_8_10'},
            {'Prof': 'carlos', 'Materia': 'programacion', 'Grupo': 'grupo_a', 'Salon': 'aula_102', 'Dia': 'lunes', 'Hora': 'h_8_10'},
            {'Prof': 'sofia', 'Materia': 'matematicas', 'Grupo': 'grupo_c', 'Salon': 'aula_101', 'Dia': 'martes', 'Hora': 'h_10_12'},
        ]
        horario = ScheduleOptimizer.optimizar_horario(soluciones)
        self.assertEqual(len(horario), 2)
        self.assertEqual(horario[0].grupo, 'grupo_a')
        self.assertEqual(horario[1].grupo, 'grupo_c')

    def test_clase_slot_key(self):
        clase = Clase('ana', 'fisica', 'grupo_a', 'aula_101', 'lunes', 'h_8_10')
        self.assertEqual(clase.slot_key(), ('grupo_a', 'lunes', 'h_8_10'))

    def test_formatear_y_mostrar_horario_vacio(self):
        with patch('builtins.print') as mock_print:
            HorarioFormatter.formatear_y_mostrar([])
            mock_print.assert_called_once_with(
                "No se pudo generar un horario válido con las restricciones actuales."
            )

    def test_formatear_y_mostrar_horario_con_clases(self):
        clases = [
            Clase('ana', 'fisica', 'grupo_a', 'aula_101', 'lunes', 'h_8_10'),
        ]
        with patch('builtins.print') as mock_print:
            HorarioFormatter.formatear_y_mostrar(clases)
            self.assertTrue(mock_print.called)

    def test_data_loader_carga_todos_los_datos(self):
        mock_prolog = Mock()
        config = Mock(spec=Config)
        config.datos = {
            'profesores': [{'nombre': 'ana', 'materia': 'fisica'}],
            'disponibilidades': [{'profesor': 'ana', 'dia': 'lunes', 'hora': 'h_8_10'}],
            'salones': [{'nombre': 'aula_101', 'capacidad': 40, 'equipo': 'proyector'}],
            'grupos': [{'nombre': 'grupo_a', 'alumnos': 25, 'materia': 'fisica'}],
            'requerimientos': [{'materia': 'fisica', 'equipo': 'proyector'}],
        }
        loader = DataLoader(config)
        loader.cargar_profesores = Mock(return_value=[Mock()])
        loader.cargar_disponibilidades = Mock(return_value=[Mock()])
        loader.cargar_salones = Mock(return_value=[Mock()])
        loader.cargar_grupos = Mock(return_value=[Mock()])
        loader.cargar_requerimientos = Mock(return_value=[Mock()])

        resultado = loader.cargar_todos_los_datos(mock_prolog)

        config.cargar.assert_called_once()
        self.assertIn('profesores', resultado)
        self.assertIn('disponibilidades', resultado)
        self.assertIn('salones', resultado)
        self.assertIn('grupos', resultado)
        self.assertIn('requerimientos', resultado)


if __name__ == "__main__":
    unittest.main()
