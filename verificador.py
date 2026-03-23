import os
import requests
from supabase import create_client, Client

# --- CONFIGURACIÓN ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "TU_SUPABASE_URL_AQUI")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "TU_SUPABASE_KEY_AQUI")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://www.thesportsdb.com/api/v1/json/123"
LIGA_MX_ID = "4350"

# Nombres con acento que vienen de la API → como están en la base de datos
NORMALIZAR_NOMBRES = {
    'Mazatlán':             'Mazatlan',
    'León':                 'Leon',
    'Querétaro':            'Queretaro',
    'Querétaro FC':         'Queretaro FC',
    'FC Juárez':            'FC Juarez',
    'Atlético de San Luis': 'Atletico San Luis',
    'Atletico de San Luis': 'Atletico San Luis',
    'Atlético San Luis':    'Atletico San Luis',
    'Atlético':             'Atletico San Luis',
}

def normalizar_nombre(nombre):
    return NORMALIZAR_NOMBRES.get(nombre, nombre)


def obtener_jornada_mas_reciente():
    """
    Busca la jornada más reciente que tenga partidos terminados en 2026
    y que aún tenga selecciones pendientes en la base de datos.
    Así evitamos procesar dos veces la misma jornada.
    """
    # Buscar selecciones pendientes y agrupar por jornada
    selecciones = supabase.table("selecciones") \
        .select("jornada") \
        .eq("estatus", "pendiente") \
        .execute()

    if not selecciones.data:
        print("No hay selecciones pendientes que procesar.")
        return None

    # Obtener jornadas únicas pendientes ordenadas de menor a mayor
    jornadas_pendientes = sorted(set(s['jornada'] for s in selecciones.data))
    print(f"Jornadas con selecciones pendientes: {jornadas_pendientes}")

    # Revisar cada jornada pendiente y ver si ya terminaron sus partidos
    for jornada in jornadas_pendientes:
        url = f"{BASE_URL}/eventsround.php?id={LIGA_MX_ID}&r={jornada}&s=2025-2026"
        response = requests.get(url)
        eventos = response.json().get('events', []) or []

        # Filtrar solo partidos de 2026 (Clausura)
        eventos_2026 = [e for e in eventos if e.get('dateEvent', '').startswith('2026')]

        if not eventos_2026:
            continue

        # Verificar si todos los partidos de la jornada ya terminaron
        terminados = [e for e in eventos_2026 if e.get('intHomeScore') not in (None, '')]
        
        if len(terminados) == len(eventos_2026) and len(terminados) > 0:
            print(f"Jornada {jornada}: todos los partidos terminados ({len(terminados)}/{len(eventos_2026)})")
            return jornada, eventos_2026
        else:
            print(f"Jornada {jornada}: {len(terminados)}/{len(eventos_2026)} partidos terminados, aún no se procesa.")

    return None


def obtener_perdedores_de_jornada(eventos):
    """Analiza los eventos y devuelve lista de equipos perdedores."""
    perdedores = []

    for p in eventos:
        goles_local  = p.get('intHomeScore')
        goles_visita = p.get('intAwayScore')

        if goles_local is None or goles_local == '':
            continue

        goles_local  = int(goles_local)
        goles_visita = int(goles_visita)
        local  = normalizar_nombre(p.get('strHomeTeam', ''))
        visita = normalizar_nombre(p.get('strAwayTeam', ''))

        print(f"  Partido: {local} {goles_local} - {goles_visita} {visita}")

        if goles_local < goles_visita:
            perdedores.append(local)
        elif goles_visita < goles_local:
            perdedores.append(visita)
        # Empate: nadie pierde vida

    return list(set(perdedores))


def actualizar_vidas():
    print("=" * 50)
    print("Iniciando verificación de jornada...")
    print("=" * 50)

    # 1. Buscar la jornada más reciente con partidos terminados y selecciones pendientes
    resultado = obtener_jornada_mas_reciente()

    if not resultado:
        print("No hay jornadas listas para procesar.")
        return

    jornada, eventos = resultado
    print(f"\nProcesando Jornada {jornada}...\n")

    # 2. Obtener todos los perfiles activos
    todos_perfiles = supabase.table("perfiles") \
        .select("id, vidas") \
        .eq("eliminado", False) \
        .execute()
    todos_user_ids = set(p['id'] for p in todos_perfiles.data)

    # 3. Obtener usuarios que SÍ escogieron en esta jornada
    selecciones_jornada = supabase.table("selecciones") \
        .select("user_id, equipo_id, equipos_ligamx(nombre)") \
        .eq("jornada", jornada) \
        .execute()
    users_con_seleccion = set(s['user_id'] for s in selecciones_jornada.data)

    # 4. Penalizar usuarios que NO escogieron equipo
    users_sin_seleccion = todos_user_ids - users_con_seleccion
    for u_id in users_sin_seleccion:
        perfil = next(p for p in todos_perfiles.data if p['id'] == u_id)
        vidas_actuales = perfil['vidas']
        nuevas_vidas = max(0, vidas_actuales - 1)

        supabase.table("perfiles").update({
            "vidas": nuevas_vidas,
            "eliminado": nuevas_vidas == 0
        }).eq("id", u_id).execute()

        # Insertar fila con estatus 'fallo' para que se pinte rojo en la tabla
        supabase.table("selecciones").insert({
            "user_id": u_id,
            "equipo_id": None,
            "jornada": jornada,
            "estatus": "Pelas"
        }).execute()

        print(f"  Usuario {u_id} perdió una vida por no escoger equipo. Vidas: {nuevas_vidas}")

    # 5. Obtener perdedores de esa jornada
    equipos_que_perdieron = obtener_perdedores_de_jornada(eventos)

    if not equipos_que_perdieron:
        print("No hubo perdedores esta jornada (todos empataron).")
        supabase.table("selecciones") \
            .update({"estatus": "acierto"}) \
            .eq("jornada", jornada) \
            .eq("estatus", "pendiente") \
            .execute()
        return

    print(f"\nEquipos que perdieron en Jornada {jornada}: {equipos_que_perdieron}\n")

    # 6. Marcar como 'acierto' los que NO perdieron
    for sel in selecciones_jornada.data:
        if sel.get('estatus') == 'fallo':
            continue
        nombre_equipo = sel.get('equipos_ligamx', {}).get('nombre', '')
        if nombre_equipo and nombre_equipo not in equipos_que_perdieron:
            supabase.table("selecciones") \
                .update({"estatus": "acierto"}) \
                .eq("user_id", sel['user_id']) \
                .eq("jornada", jornada) \
                .execute()
            print(f"  Usuario {sel['user_id']} acertó con {nombre_equipo}")

    # 7. Restar vidas a los que eligieron equipos perdedores
    for nombre_equipo in equipos_que_perdieron:
        res_equipo = supabase.table("equipos_ligamx") \
            .select("id") \
            .eq("nombre", nombre_equipo) \
            .execute()

        if not res_equipo.data:
            print(f"  Equipo '{nombre_equipo}' no encontrado en la base de datos.")
            continue

        id_equipo = res_equipo.data[0]['id']

        selecciones_perdedor = supabase.table("selecciones") \
            .select("user_id") \
            .eq("equipo_id", id_equipo) \
            .eq("jornada", jornada) \
            .eq("estatus", "pendiente") \
            .execute()

        for sel in selecciones_perdedor.data:
            u_id = sel['user_id']

            perfil = supabase.table("perfiles") \
                .select("vidas") \
                .eq("id", u_id) \
                .single() \
                .execute()

            vidas_actuales = perfil.data['vidas']
            nuevas_vidas = max(0, vidas_actuales - 1)

            supabase.table("perfiles").update({
                "vidas": nuevas_vidas,
                "eliminado": nuevas_vidas == 0
            }).eq("id", u_id).execute()

            supabase.table("selecciones") \
                .update({"estatus": "fallo"}) \
                .eq("user_id", u_id) \
                .eq("jornada", jornada) \
                .execute()

            print(f"  Usuario {u_id} perdió una vida por {nombre_equipo}. Vidas: {nuevas_vidas}")

    print(f"\nJornada {jornada} procesada correctamente.")


if __name__ == "__main__":
    actualizar_vidas()
