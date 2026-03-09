import os
import requests
from supabase import create_client, Client

# --- CONFIGURACIÓN ---
# Puedes poner estos valores directamente aquí para pruebas,
# o usar variables de entorno para producción (más seguro)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "TU_SUPABASE_URL_AQUI")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "TU_SUPABASE_KEY_AQUI")

# TheSportsDB - GRATIS, sin registro, sin tarjeta
# Liga MX ID = 4350
BASE_URL = "https://www.thesportsdb.com/api/v1/json/123"
LIGA_MX_ID = "4350"

# Inicializar Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def obtener_perdedores_ligamx():
    """
    Consulta TheSportsDB y devuelve una lista de equipos
    que perdieron en los últimos partidos de Liga MX.
    """
    url = f"{BASE_URL}/eventspastleague.php"
    params = {"id": LIGA_MX_ID}

    try:
        response = requests.get(url, params=params)
        partidos = response.json().get('events', []) or []

        perdedores = []

        for p in partidos:
            # Solo partidos terminados (tienen marcador numérico)
            goles_local = p.get("intHomeScore")
            goles_visita = p.get("intAwayScore")

            if goles_local is None or goles_visita is None:
                continue

            goles_local = int(goles_local)
            goles_visita = int(goles_visita)
            local = p.get("strHomeTeam")
            visita = p.get("strAwayTeam")

            print(f"  Partido: {local} {goles_local} - {goles_visita} {visita}")

            if goles_local < goles_visita:
                perdedores.append(local)
            elif goles_visita < goles_local:
                perdedores.append(visita)
            # Los empates no cuentan como derrota en el survivor

        # Quitamos duplicados con set()
        return list(set(perdedores))

    except Exception as e:
        print(f"Error al consultar la API: {e}")
        return []


def actualizar_vidas():
    """
    Compara los equipos perdedores con las selecciones de los usuarios
    y les resta una vida si su equipo perdió.
    """
    print("=" * 50)
    print("Iniciando verificación de jornada...")
    print("=" * 50)

    equipos_que_perdieron = obtener_perdedores_ligamx()

    if not equipos_que_perdieron:
        print("No se detectaron perdedores. ¿Ya se jugaron los partidos?")
        return

    print(f"\nEquipos que perdieron: {equipos_que_perdieron}\n")

    for nombre_equipo in equipos_que_perdieron:

        # 1. Buscar el ID del equipo en nuestra tabla de Supabase
        res_equipo = supabase.table("equipos_ligamx") \
            .select("id") \
            .eq("nombre", nombre_equipo) \
            .execute()

        if not res_equipo.data:
            print(f"  Equipo '{nombre_equipo}' no encontrado en la base de datos. Revisa que el nombre coincida exactamente.")
            continue

        id_equipo = res_equipo.data[0]['id']

        # 2. Buscar usuarios que eligieron este equipo con estatus 'pendiente'
        selecciones = supabase.table("selecciones") \
            .select("user_id") \
            .eq("equipo_id", id_equipo) \
            .eq("estatus", "pendiente") \
            .execute()

        if not selecciones.data:
            print(f"  Nadie eligió a {nombre_equipo} esta jornada.")
            continue

        for sel in selecciones.data:
            u_id = sel['user_id']

            # 3. Obtener las vidas actuales del usuario
            perfil = supabase.table("perfiles") \
                .select("vidas") \
                .eq("id", u_id) \
                .single() \
                .execute()

            vidas_actuales = perfil.data['vidas']
            nuevas_vidas = max(0, vidas_actuales - 1)  # No puede bajar de 0

            # 4. Actualizar vidas en Supabase
            supabase.table("perfiles").update({
                "vidas": nuevas_vidas,
                "eliminado": nuevas_vidas == 0  # True si se quedó sin vidas
            }).eq("id", u_id).execute()

            # 5. Marcar la selección como 'fallo'
            supabase.table("selecciones").update({"estatus": "fallo"}) \
                .eq("user_id", u_id) \
                .eq("equipo_id", id_equipo) \
                .execute()

            print(f"  Usuario {u_id} perdió una vida por {nombre_equipo}. Vidas restantes: {nuevas_vidas}")

    print("\n¡Verificación completada!")


if __name__ == "__main__":
    actualizar_vidas()
