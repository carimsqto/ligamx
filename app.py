from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Permitir llamadas desde el frontend

@app.route('/api/calendario-ligamx')
def obtener_calendario():
    """Endpoint para obtener el calendario de la jornada actual de Liga MX"""
    try:
        api_key = os.environ.get("API_FOOTBALL_KEY")
        if not api_key:
            return jsonify({"error": "API key no configurada"}), 500
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': api_key
        }
        
        # Obtener fecha actual y buscar partidos cercanos
        hoy = datetime.now()
        params = {
            "league": "262",
            "season": "2026",
            "from": hoy.strftime('%Y-%m-%d'),
            "to": (hoy + timedelta(days=7)).strftime('%Y-%m-%d')  # Próximos 7 días
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        return jsonify({
            "success": True,
            "partidos": data.get('response', [])
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
