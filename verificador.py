import os
import requests
from supabase import create_client, Client

# --- CONFIGURACIÓN USANDO VARIABLES DE ENTORNO ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")

# Inicializar cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def obtener_perdedores_ligamx():
    """Consulta la API de fútbol y devuelve nombres de equipos que perdieron recientemente."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': API_FOOTBALL_KEY
    }
    
    # Parámetros para la Liga MX (ID 262)
    # Nota: Ajustamos la temporada al año actual 2026
    params = {
        "league": "262",
        "season": "2026", 
        "last": 10  # Revisamos los últimos 10 partidos jugados
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        partidos = response.json().get('response', [])
        
        perdedores = []
        for p in partidos:
            status = p['fixture']['status']['short']
            if status == 'FT':  # Full Time (Partido terminado)
                home = p['teams']['home']
                away = p['teams']['away']
                goles_home = p['goals']['home']
                goles_away = p['goals']['away']
                
                if goles_home < goles_away:
                    perdedores.append(home['name'])
                elif goles_away < goles_home:
                    perdedores.append(away['name'])
        
        return list(set(perdedores))
    except Exception as e:
        print(f"Error al consultar la API: {e}")
        return []

def actualizar_vidas():
    print("Iniciando verificación de jornada...")
    
    equipos_que_perdieron = obtener_perdedores_ligamx()
    if not equipos_que_perdieron:
        print("No se detectaron perdedores nuevos.")
        return

    print(f"Equipos que perdieron recientemente: {equipos_que_perdieron}")

    for nombre_equipo in equipos_que_perdieron:
        # 1. Buscar el ID del equipo en nuestra tabla
        res_equipo = supabase.table("equipos_ligamx").select("id").eq("nombre", nombre_equipo).execute()
        
        if res_equipo.data:
            id_equipo = res_equipo.data[0]['id']
            
            # 2. Buscar usuarios que eligieron a este equipo y que aún tengan estatus 'pendiente'
            selecciones = supabase.table("selecciones") \
                .select("user_id") \
                .eq("equipo_id", id_equipo) \
                .eq("estatus", "pendiente") \
                .execute()
            
            for sel in selecciones.data:
                u_id = sel['user_id']
                
                # 3. Restar vida al usuario
                perfil = supabase.table("perfiles").select("vidas").eq("id", u_id).single().execute()
                vidas_actuales = perfil.data['vidas']
                
                if vidas_actuales > 0:
                    nuevas_vidas = vidas_actuales - 1
                    supabase.table("perfiles").update({
                        "vidas": nuevas_vidas,
                        "eliminado": True if nuevas_vidas == 0 else False
                    }).eq("id", u_id).execute()
                
                # 4. Marcar la selección como 'fallo'
                supabase.table("selecciones").update({"estatus": "fallo"}) \
                    .eq("user_id", u_id).eq("equipo_id", id_equipo).execute()
                
                print(f"Usuario {u_id} perdió una vida por culpa de {nombre_equipo}")

if __name__ == "__main__":
    actualizar_vidas()