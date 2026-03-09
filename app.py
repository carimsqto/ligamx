from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================================
# TheSportsDB - API GRATUITA, no necesitas cuenta ni tarjeta
# Liga MX ID en TheSportsDB = 4350
# Clave gratuita = 123
# ============================================================
BASE_URL = "https://www.thesportsdb.com/api/v1/json/123"
LIGA_MX_ID = "4350"


@app.route('/api/calendario-ligamx')
def obtener_calendario():
    """Devuelve los próximos partidos de Liga MX"""
    try:
        # Partidos programados de la jornada actual
        url = f"{BASE_URL}/eventsnextleague.php"
        params = {"id": LIGA_MX_ID}

        response = requests.get(url, params=params)
        data = response.json()

        partidos_raw = data.get('events', []) or []

        # Convertimos al mismo formato que usaba tu frontend
        partidos = []
        for p in partidos_raw:
            partidos.append({
                "fixture": {
                    "date": p.get("strTimestamp") or p.get("dateEvent"),
                    "venue": {"name": p.get("strVenue", "Estadio por definir")}
                },
                "teams": {
                    "home": {"name": p.get("strHomeTeam")},
                    "away": {"name": p.get("strAwayTeam")}
                },
                "goals": {
                    "home": p.get("intHomeScore"),
                    "away": p.get("intAwayScore")
                },
                "jornada": p.get("intRound"),
                "estatus": p.get("strStatus", "")
            })

        return jsonify({"success": True, "partidos": partidos})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/resultados-ligamx')
def obtener_resultados():
    """Devuelve los últimos resultados terminados de Liga MX"""
    try:
        url = f"{BASE_URL}/eventspastleague.php"
        params = {"id": LIGA_MX_ID}

        response = requests.get(url, params=params)
        data = response.json()

        partidos_raw = data.get('events', []) or []

        perdedores = []
        ganadores = []
        resultados = []

        for p in partidos_raw:
            goles_local = p.get("intHomeScore")
            goles_visita = p.get("intAwayScore")

            # Solo partidos que ya terminaron (tienen marcador)
            if goles_local is None or goles_visita is None:
                continue

            goles_local = int(goles_local)
            goles_visita = int(goles_visita)
            local = p.get("strHomeTeam")
            visita = p.get("strAwayTeam")

            if goles_local < goles_visita:
                perdedores.append(local)
                ganadores.append(visita)
            elif goles_visita < goles_local:
                perdedores.append(visita)
                ganadores.append(local)
            # Si empatan, nadie pierde en el survivor

            resultados.append({
                "local": local,
                "visita": visita,
                "goles_local": goles_local,
                "goles_visita": goles_visita,
                "jornada": p.get("intRound"),
                "fecha": p.get("dateEvent")
            })

        return jsonify({
            "success": True,
            "perdedores": list(set(perdedores)),
            "ganadores": list(set(ganadores)),
            "resultados": resultados
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
