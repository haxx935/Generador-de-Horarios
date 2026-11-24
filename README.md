# Generador de Horarios Académicos

Backend en Flask + pyswip (SWI-Prolog) y frontend estático (HTML/JS/CSS) para
generar horarios escolares mediante programación lógica.

## Requisitos

Ver `requirements.txt`:
- pyswip==0.3.3
- flask==3.1.3
- flask-cors==6.0.5

Además se necesita SWI-Prolog instalado y accesible (en Windows, `prolog_manager.py`
configura `SWI_HOME_DIR` automáticamente si encuentra `C:\Program Files\swipl`).

## Ejecutar

```bash
python -m pip install -r requirements.txt
python api.py
# o python main.py
```

El backend expone:
- `POST /generar-horario` con la configuración (maestros, grupos, aulas).
- `GET /health`

El frontend es `index.html`, consumiendo `http://127.0.0.1:5000`.

## Formato de datos del API

El cuerpo de la solicitud a `POST /generar-horario` debe contener:

```json
{
  "maestros": [
    {
      "nombre": "Prof. Matemáticas",
      "materias": ["Matemáticas"],
      "disponibilidad": { "entrada": "08:00", "salida": "14:00" },
      "equipo_requerido": { "Matemáticas": "proyector" }
    }
  ],
  "grupos": [
    {
      "nombre": "Grupo A",
      "materias": ["Matemáticas", "Física", "Química", "Historia", "Inglés"],
      "equipo_requerido": {
        "Matemáticas": "proyector",
        "Física": "proyector",
        "Química": "proyector",
        "Historia": "proyector",
        "Inglés": "proyector"
      }
    }
  ],
  "aulas": [
    {
      "nombre": "Aula 101",
      "tipo": "salón",
      "capacidad": 30,
      "equipo": "proyector",
      "materias_util": ["Matemáticas", "Física", "Química", "Historia", "Inglés"]
    }
  ]
}
```

Campos opcionales:
- `equipo_requerido`: diccionario `{materia: equipo}`. Si no se envía para una materia,
  se usa el diccionario de respaldo `_EQUIPO_POR_MATERIA` y, finalmente, `"proyector"`.
- `max_clases_por_materia_dia`: tope de horas diarias por materia y grupo (por defecto `2`).

## Reglas del horario (ahora en Prolog)

Toda la selección del horario vive ahora en el motor Prolog mediante **búsqueda
recursiva con retroceso (backtracking)** y un acumulado de clases asignadas que viaja
como argumento de lista (sin `assertz`/`retractall` durante la búsqueda). El punto de
entrada es el predicado `generar_horario/1`.

- **Sesiones requeridas**: se construyen 4 sesiones por cada par (grupo, materia)
  de `grupo_materia/2`.
- **Máximo 2 horas por día y materia** por grupo (regla `cupo_dia_acumulado` sobre el acumulado).
- **Máximo 4 horas por semana y materia** por grupo (regla `cupo_semana_acumulado` sobre el acumulado).
- **Sin empalmes**: un profesor, grupo o aula no puede tener dos clases el mismo día y hora
  (regla `empalme_acumulado` consultada contra el acumulado).
- **Adecuación de aula**: capacidad suficiente, equipo requerido igual al del salón, y la
  materia debe estar en `materias_util` del salón (regla `adecuado/3`).
- **Disponibilidad del profesor**: solo se asignan bloques dentro de `disponible/3`.
- **Heurística**: las sesiones se ordenan por cantidad de candidatos (menos candidatos =
  más restringida, se asignan primero) mediante `ordenar_por_restriccion/2`.
- **Límite de inferencias**: `call_with_inference_limit/3` acota el costo de la búsqueda.
- **Solución parcial**: si no existe solución completa, se devuelve la mejor parcial
  encontrada (`mejor_parcial/3`) y `no_cubiertas` reporta los pares grupo-materia con
  menos de 4 horas, indicando cuántas horas faltaron.
- **Respuesta**: incluye `asignaciones` (clases generadas), `total`, `no_cubiertas`
  (con `horas_asignadas` y `horas_faltantes`) y `total_no_cubiertas`.

## CORS y origen "null"

En `api.py` la CORS se configura con `origins=[..., "null"]`.

El valor `"null"` permite abrir `index.html` con doble clic (protocolo `file://`,
que el navegador expone como origen opaco `"null"`). Es aceptable sólo para uso
local/desarrollo.

**En producción quitar `"null"` y restringir los orígenes a los del frontend real**,
pues `"null"` aceptaría peticiones de cualquier página con origen opaco.

## Archivos del proyecto

| Archivo | Propósito |
|---------|-----------|
| `api.py` | Backend Flask, endpoint `/generar-horario` y `/health` |
| `prolog_manager.py` | Motor Prolog: hechos, reglas y predicado `generar_horario/1` con backtracking |
| `data_loader.py` | Carga de hechos en Prolog, deduplicación de grupos por nombre |
| `models.py` | Modelos de datos (Profesor, Disponibilidad, Salon, Grupo, Requerimiento, Clase) |
| `config.py` | Lectura de `horario_config.json` |
| `horario_generator.py` | Carga hechos, llama una vez a Prolog y convierte el resultado en objetos Clase |
| `scheduler.py` | Mantenido por retrocompatibilidad (ya no se usa en el flujo principal) |
| `output_formatter.py` | Mantenido por retrocompatibilidad (ya no se usa en el flujo principal) |
| `main.py` | Punto de entrada |
| `app.js`, `index.html`, `style.css` | Frontend estático |
| `horario_config.json` | Datos por defecto del sistema |
| `requirements.txt` | Dependencias de Python |
| `tests/test_prolog.py` | Pruebas automáticas (pytest) |
| `README.md` | Este documento |

## Pruebas

```bash
python -m pip install pytest
python -m pytest tests/test_prolog.py -v
```

Cubre: ausencia de empalmes (profesor, grupo, aula), topes diarios y semanales,
cobertura completa (40 clases con datos de `app.js`), consistencia entre llamadas
repetidas, solución parcial cuando no hay horario completo, y endpoints de la API.
