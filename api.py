from flask import Flask, request, jsonify
from flask_cors import CORS
from horario_generator import HorarioGenerator

app = Flask(__name__)
CORS(app)

generador = HorarioGenerator()


@app.route("/generar-horario", methods=["POST"])
def generar_horario():
    try:
        datos = request.get_json(silent=True) or {}
        # HorarioGenerator ignora el cuerpo y usa horario_config.json directamente.
        # Si quisieras inyectar datos dinámicos, aquí podrías sobrescribir config.datos.
        if datos:
            generador.config.datos = datos

        horario = generador.generar_horario()

        resultado = [
            {
                "Prof": c.profesor,
                "Materia": c.materia,
                "Grupo": c.grupo,
                "Salon": c.salon,
                "Dia": c.dia,
                "Hora": c.hora,
            }
            for c in horario
        ]

        return jsonify({"horario": resultado, "total": len(resultado)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
