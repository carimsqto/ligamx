from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests
from datetime import datetime, timedelta
import jwt
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)  # Permitir llamadas desde el frontend

# Configuración Supabase con SERVICE ROLE KEY
SUPABASE_URL = "https://povaakggggoeewgqfyot.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvdmFha2dnZ2dvZWV3Z3FmeW90Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEyMzM4MywiZXhwIjoyMDg3Njk5MzgzfQ.zBwW-M-0S3IsPn8SepkXm7OalXGL6NovsqVriZzBXDQ"
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@app.route('/api/calendario-ligamx')
def obtener_calendario():
    """Endpoint para obtener el calendario de la jornada actual de Liga MX"""
    try:
        # API key configurada directamente para pruebas
        api_key = "662aa4742dmshf1b492eb2aa8fc7p150df8jsnb71cc562854a"
        # api_key = os.environ.get("API_FOOTBALL_KEY")  # Descomentar para producción
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': api_key
        }
        
        # Obtener fecha actual y buscar partidos en un rango más amplio
        hoy = datetime.now()
        params = {
            # "league": "262",  # Comentado para probar API general
            "from": (hoy - timedelta(days=30)).strftime('%Y-%m-%d'),  # 30 días antes
            "to": (hoy + timedelta(days=30)).strftime('%Y-%m-%d')     # 30 días después
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # Debug: mostrar qué devuelve la API
        print(f"Status code: {response.status_code}")
        print(f"Response data: {data}")
        
        # Si no hay partidos, usar datos de ejemplo
        partidos = data.get('response', [])
        if not partidos:
            print("No se encontraron partidos, usando datos de ejemplo")
            partidos = [
                {
                    "fixture": {
                        "date": "2026-03-08T20:00:00+00:00",
                        "venue": {"name": "Estadio Azteca"}
                    },
                    "teams": {
                        "home": {"name": "Club América"},
                        "away": {"name": "Chivas"}
                    }
                },
                {
                    "fixture": {
                        "date": "2026-03-09T19:00:00+00:00",
                        "venue": {"name": "Estadio Akron"}
                    },
                    "teams": {
                        "home": {"name": "Chivas"},
                        "away": {"name": "Tigres"}
                    }
                },
                {
                    "fixture": {
                        "date": "2026-03-10T21:00:00+00:00",
                        "venue": {"name": "Estadio Universitario"}
                    },
                    "teams": {
                        "home": {"name": "Tigres"},
                        "away": {"name": "Monterrey"}
                    }
                }
            ]
        
        return jsonify({
            "success": True,
            "partidos": partidos
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/admin/delete-seleccion', methods=['DELETE', 'OPTIONS'])
def delete_seleccion():
    """Endpoint para que el admin borre selecciones de usuarios"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Obtener token del header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token no proporcionado'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Decodificar token JWT para obtener email
        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            user_email = decoded_token.get('email')
            
            if user_email != 'greenday_115@hotmail.com':
                return jsonify({'error': 'No autorizado - Solo admin'}), 403
                
        except Exception as jwt_error:
            return jsonify({'error': 'Token inválido'}), 401
        
        # Obtener datos del body
        data = request.get_json()
        user_id = data.get('userId')
        jornada = data.get('jornada')
        
        if not user_id or not jornada:
            return jsonify({'error': 'Faltan userId y jornada'}), 400
        
        # Ejecutar delete con service role key
        result = supabase_admin.table('selecciones').delete().eq('user_id', user_id).eq('jornada', jornada).execute()
        
        if hasattr(result, 'error') and result.error:
            return jsonify({'error': str(result.error)}), 500
        
        return jsonify({'success': True, 'message': 'Selección borrada correctamente'})
        
    except Exception as e:
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba para verificar que el servidor funciona"""
    return jsonify({
        'message': 'Endpoint funciona',
        'server': 'Render',
        'status': 'OK',
        'routes': [str(rule) for rule in app.url_map.iter_rules()]
    })

@app.route('/api/verificar', methods=['POST'])
def verificar_jornada():
    """Endpoint para correr el verificador manualmente desde el panel admin"""
    try:
        import subprocess
        resultado = subprocess.run(
            ['python', 'verificador.py'],
            capture_output=True, text=True, timeout=60
        )
        if resultado.returncode == 0:
            return jsonify({
                "success": True,
                "mensaje": "Verificacion completada. " + resultado.stdout[-200:].strip()
            })
        else:
            return jsonify({
                "success": False,
                "error": resultado.stderr[-300:].strip()
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
