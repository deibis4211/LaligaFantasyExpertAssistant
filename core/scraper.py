import pandas as pd
import requests

def parse_biwenger_data(data):
    """Parsea el payload JSON de /competitions/la-liga/data en (df, teams_map, teams_raw)."""
    teams_raw = data.get('teams', {})
    teams_map = {str(k): v.get('name') for k, v in teams_raw.items()}
    players = data.get('players', {})

    # Extraer fixtures del próximo partido y estado de jornadas
    seasons_rounds = data.get('season', {}).get('rounds', [])
    rounds_status = {
        int(r['id']): r.get('status', 'pending')
        for r in seasons_rounds
        if r.get('id') is not None
    }

    fixtures = {}
    for t_id, t_data in teams_raw.items():
        t_name = t_data.get('name')
        next_games = t_data.get('nextGames', [])
        if next_games and t_name:
            game = next_games[0]
            h_id = str(game['home']['id'])
            a_id = str(game['away']['id'])
            is_h = (h_id == str(t_id))
            rival_id = a_id if is_h else h_id
            rival_n = teams_map.get(rival_id, "Desconocido")
            game_id = game.get('id')
            round_id = (game.get('round') or {}).get('id')
            fixtures[t_name] = (rival_n, is_h, game_id, round_id)

    players_data = []
    for pid, pdata in players.items():
        name = pdata.get('name', 'Desconocido')
        team_id = str(pdata.get('teamID', ''))
        team = teams_map.get(team_id, "Desconocido")

        valor = pdata.get('price', 0)
        tendencia_abs = pdata.get('priceIncrement', 0)

        try:
            tendencia_pct = round((tendencia_abs / valor) * 100, 2) if valor > 0 else 0.0
        except Exception:
            tendencia_pct = 0.0

        pts_totales = pdata.get('points', 0)
        fitness = pdata.get('fitness', [])
        if not isinstance(fitness, list):
            fitness = []

        # Biwenger devuelve 'fitness' del más reciente al más antiguo: lo invertimos
        # para mantener orden cronológico [hace_5, ..., penúltimo, último].
        p_recientes = []
        for x in reversed(fitness):
            if isinstance(x, int):
                p_recientes.append(x)
            else:
                p_recientes.append(0)  # None, 'sanctioned', 'injured', etc. cuentan como 0 puntos

        p_recientes = p_recientes[-5:]
        while len(p_recientes) < 5:
            p_recientes.insert(0, 0)

        partidos_jugados = pdata.get('playedHome', 0) + pdata.get('playedAway', 0)
        pts_media = round(pts_totales / partidos_jugados, 2) if partidos_jugados > 0 else 0.0

        raw_st = pdata.get('status', 'ok')
        if raw_st == 'injured': estado = 'Lesionado'
        elif raw_st == 'doubt': estado = 'Duda'
        elif raw_st == 'suspended': estado = 'Sancionado'
        elif raw_st == 'warned': estado = 'Apercibido'
        else: estado = 'Disponible'

        pos_id = pdata.get('position', 0)
        pos_map = {1: 'PT', 2: 'DF', 3: 'MC', 4: 'DL'}
        pos = pos_map.get(pos_id, 'UNK')

        # --- FILTROS DE CALIDAD ---
        if team == 'Desconocido' or pos == 'UNK' or valor == 0:
            continue

        rival_info = fixtures.get(team, ("Desconocido", True, None, None))
        rival, is_h, game_id, round_id = rival_info
        localia = 1.0 if is_h else 0.0
        wma_val = round(
            sum(p * w for p, w in zip(p_recientes, range(1, len(p_recientes) + 1)))
            / sum(range(1, len(p_recientes) + 1)),
            2,
        )

        players_data.append({
            'ID': pid,
            'Nombre': name,
            'Equipo': team,
            'Posicion': pos,
            'Valor': valor,
            'Puntos': pts_totales,
            'Media': pts_media,
            'WMA': wma_val,
            'Estado': estado,
            'Tendencia_48h_pct': tendencia_pct * 2,
            'Puntos_Recientes': p_recientes,
            'Rival': rival,
            'Localia': localia,
            'Partidos_Jugados': partidos_jugados,
            'Game_ID': game_id,
            'Round_ID': round_id,
        })

    df_out = pd.DataFrame(players_data)
    df_out.attrs['rounds_status'] = rounds_status
    return df_out, teams_map, teams_raw


def scrape_players():
    print("[*] Iniciando descarga de la base de datos oficial (API web)...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    try:
        response = requests.get('https://biwenger.as.com/api/v2/competitions/la-liga/data?lang=es&score=1', headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            df_out, teams_map, teams_raw = parse_biwenger_data(data)
            print(f"[*] Base de datos descargada con exito: {len(df_out)} jugadores validos (sin entrenadores ni jugadores sin equipo).")
            return df_out, teams_map, teams_raw
    except Exception as e:
        print(f"[!] Error conectando a la API: {e}")
        
    print("[!] Fallo grave intentando obtener la BD. Retornando tabla vacia.")
    return pd.DataFrame(), {}, {}
