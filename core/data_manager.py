import pandas as pd
import numpy as np
import os

HISTORICAL_LEARN_FILE = 'data/historico_aprendizaje.csv'
TRACKING_COLS = ['Partidos_Jugados', 'Game_ID', 'Round_ID']


def _norm_id(val):
    """Normaliza IDs leídos de CSV o API (evita desajustes int/float/str como '50830.0')."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == 'nan':
        return None
    if s.endswith('.0') and s[:-2].lstrip('-').isdigit():
        return s[:-2]
    return s


def _norm_int(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _normalize_fitness(fitness):
    """Garantiza una lista de 5 enteros en orden cronológico [más_antiguo, ..., más_reciente]."""
    if not isinstance(fitness, list):
        return [0, 0, 0, 0, 0]
    cleaned = [int(x) if isinstance(x, (int, float, np.integer, np.floating)) and not pd.isna(x) else 0 for x in fitness]
    cleaned = cleaned[-5:]
    while len(cleaned) < 5:
        cleaned.insert(0, 0)
    return cleaned


def extract_fixtures(teams_raw):
    """Extrae el calendario real desde la metadata de la API de Biwenger."""
    fixtures = {}
    id_to_name = {str(t_id): t_data['name'] for t_id, t_data in teams_raw.items() if isinstance(t_data, dict) and 'name' in t_data}

    for t_id, t_data in teams_raw.items():
        if not isinstance(t_data, dict) or 'name' not in t_data:
            continue
        team_name = t_data['name']
        next_games = t_data.get('nextGames', [])

        if next_games:
            game = next_games[0]
            home_id = str(game['home']['id'])
            away_id = str(game['away']['id'])

            is_home = (home_id == str(t_id))
            rival_id = away_id if is_home else home_id
            rival_name = id_to_name.get(rival_id, "Desconocido")
            game_id = _norm_id(game.get('id'))
            round_id = _norm_id((game.get('round') or {}).get('id'))

            fixtures[team_name] = (rival_name, is_home, game_id, round_id)

    return fixtures


def calculate_wma(points):
    if not points:
        return 0.0
    n = len(points)
    weights = list(range(1, n + 1))
    return round(sum(p * w for p, w in zip(points, weights)) / sum(weights), 2)


def calculate_trend(points):
    if len(points) < 3:
        return 0.0
    return float(points[-1] - points[-3])


def calculate_volatility(points):
    if len(points) < 2:
        return 0.0
    return round(float(np.std(points)), 2)


def _compute_team_elapsed(pending_rows, current_by_id):
    """Calcula cuántos partidos disputó cada equipo desde cada Game_ID pendiente."""
    deltas_by_team_game = {}
    for r in pending_rows:
        prev_gid = _norm_id(r.get('Game_ID'))
        prev_pj = _norm_int(r.get('Partidos_Jugados'))
        pid = _norm_int(r.get('ID'))
        if prev_gid is None or pid not in current_by_id:
            continue
        cur = current_by_id[pid]
        if cur['Game_ID'] == prev_gid:
            continue
        key = (r.get('Equipo'), prev_gid)
        deltas_by_team_game.setdefault(key, [])
        if prev_pj is not None and cur['Partidos_Jugados'] is not None:
            diff = cur['Partidos_Jugados'] - prev_pj
            if diff >= 0:
                deltas_by_team_game[key].append(diff)

    team_elapsed = {}
    for key, diffs in deltas_by_team_game.items():
        pos_diffs = [d for d in diffs if d > 0]
        team_elapsed[key] = max(pos_diffs) if pos_diffs else 1
    return team_elapsed


def save_snapshot(df, teams_raw):
    """Guarda el histórico acumulando la racha de forma y emparejando cada jornada sin duplicados."""
    fixtures = extract_fixtures(teams_raw)
    rounds_status = {_norm_id(k): v for k, v in (df.attrs.get('rounds_status', {}) or {}).items()}

    if os.path.exists(HISTORICAL_LEARN_FILE):
        try:
            learn_df = pd.read_csv(HISTORICAL_LEARN_FILE)
        except Exception:
            learn_df = pd.DataFrame()
    else:
        learn_df = pd.DataFrame()

    if not learn_df.empty:
        for col in TRACKING_COLS:
            if col not in learn_df.columns:
                learn_df[col] = np.nan

    # Construir índice rápido del estado actual por jugador
    current_by_id = {}
    for _, row in df.iterrows():
        pid = int(row['ID'])
        fitness = _normalize_fitness(row.get('Puntos_Recientes'))
        eq = row['Equipo']
        rival_info = fixtures.get(eq, ("Desconocido", True, None, None))
        rival = rival_info[0]
        localia = 1.0 if rival_info[1] else 0.0
        game_id = _norm_id(row.get('Game_ID')) or rival_info[2]
        round_id = _norm_id(row.get('Round_ID')) or rival_info[3]
        pj = _norm_int(row.get('Partidos_Jugados'))

        current_by_id[pid] = {
            'ID': pid,
            'Nombre': row['Nombre'],
            'Equipo': eq,
            'Posicion': row['Posicion'],
            'Valor': float(row['Valor']),
            'Media': float(row['Media']),
            'WMA': calculate_wma(fitness),
            'Tendencia': calculate_trend(fitness),
            'Volatilidad': calculate_volatility(fitness),
            'Rival': rival,
            'Localia': localia,
            'Partidos_Jugados': pj,
            'Game_ID': game_id,
            'Round_ID': round_id,
            'fitness': fitness,
        }

    new_rows = []
    updated_learn_rows = []
    pending_cur_game_pids = set()

    if learn_df.empty:
        # Cold-start: construir muestras iniciales con orden cronológico correcto
        for pid, cur in current_by_id.items():
            fitness = cur['fitness']
            p1_3 = fitness[:3]
            new_rows.append({
                'ID': pid,
                'Nombre': cur['Nombre'],
                'Equipo': cur['Equipo'],
                'Posicion': cur['Posicion'],
                'Valor': cur['Valor'],
                'Media': cur['Media'],
                'WMA': calculate_wma(p1_3),
                'Tendencia': calculate_trend(p1_3),
                'Volatilidad': calculate_volatility(p1_3),
                'Rival': 'Desconocido',
                'Localia': 0.5,
                'Partidos_Jugados': np.nan,
                'Game_ID': f'cold_{pid}_1',
                'Round_ID': np.nan,
                'Target': float(fitness[-2]),
            })

            p1_4 = fitness[:4]
            new_rows.append({
                'ID': pid,
                'Nombre': cur['Nombre'],
                'Equipo': cur['Equipo'],
                'Posicion': cur['Posicion'],
                'Valor': cur['Valor'],
                'Media': cur['Media'],
                'WMA': calculate_wma(p1_4),
                'Tendencia': calculate_trend(p1_4),
                'Volatilidad': calculate_volatility(p1_4),
                'Rival': 'Desconocido',
                'Localia': 0.5,
                'Partidos_Jugados': np.nan,
                'Game_ID': f'cold_{pid}_2',
                'Round_ID': np.nan,
                'Target': float(fitness[-1]),
            })
    else:
        existing_records = learn_df.to_dict('records')
        pending_records = [r for r in existing_records if pd.isna(r.get('Target'))]
        team_elapsed = _compute_team_elapsed(pending_records, current_by_id)

        for r in existing_records:
            if pd.notna(r.get('Target')):
                r['Game_ID'] = _norm_id(r.get('Game_ID'))
                r['Round_ID'] = _norm_id(r.get('Round_ID'))
                updated_learn_rows.append(r)
                continue

            pid = _norm_int(r.get('ID'))
            prev_gid = _norm_id(r.get('Game_ID'))
            prev_rid = _norm_id(r.get('Round_ID'))

            # Descartar filas pendientes legacy sin Game_ID para no contaminar con jornadas incorrectas
            if prev_gid is None:
                continue

            if pid not in current_by_id:
                # Conservar la fila pendiente solo si su jornada sigue pendiente
                if rounds_status.get(prev_rid) != 'finished':
                    r['Game_ID'] = prev_gid
                    r['Round_ID'] = prev_rid
                    updated_learn_rows.append(r)
                continue

            cur = current_by_id[pid]
            same_upcoming_game = (prev_gid == cur['Game_ID'])
            round_finished = (rounds_status.get(prev_rid) == 'finished')

            if not round_finished and (same_upcoming_game or cur['Game_ID'] is None):
                # Misma jornada aún sin disputar/cerrar: actualizar snapshot previo sin rellenar Target
                for field in ('Nombre', 'Equipo', 'Posicion', 'Valor', 'Media', 'WMA', 'Tendencia', 'Volatilidad', 'Rival', 'Localia', 'Partidos_Jugados', 'Round_ID'):
                    r[field] = cur[field]
                r['Game_ID'] = prev_gid
                r['Target'] = np.nan
                updated_learn_rows.append(r)
                if same_upcoming_game:
                    pending_cur_game_pids.add(pid)
            else:
                # El partido pendiente ya terminó: recuperar el Target exacto si está en la ventana de 5 partidos
                diff = team_elapsed.get((r.get('Equipo'), prev_gid), 1)
                if 1 <= diff <= 5:
                    r['Game_ID'] = prev_gid
                    r['Round_ID'] = prev_rid
                    r['Target'] = float(cur['fitness'][-diff])
                    updated_learn_rows.append(r)
                # Si diff > 5, el resultado real salió de la ventana de fitness y se descarta la fila huérfana

    # Crear una única fila pendiente para el próximo partido de cada jugador si aún no existe
    for pid, cur in current_by_id.items():
        if pid in pending_cur_game_pids:
            continue
        if cur['Game_ID'] is None:
            continue
        if rounds_status.get(cur['Round_ID']) == 'finished':
            continue

        new_rows.append({
            'ID': pid,
            'Nombre': cur['Nombre'],
            'Equipo': cur['Equipo'],
            'Posicion': cur['Posicion'],
            'Valor': cur['Valor'],
            'Media': cur['Media'],
            'WMA': cur['WMA'],
            'Tendencia': cur['Tendencia'],
            'Volatilidad': cur['Volatilidad'],
            'Rival': cur['Rival'],
            'Localia': cur['Localia'],
            'Partidos_Jugados': cur['Partidos_Jugados'],
            'Game_ID': cur['Game_ID'],
            'Round_ID': cur['Round_ID'],
            'Target': np.nan,
        })

    combined_df = pd.DataFrame(updated_learn_rows + new_rows)
    if combined_df.empty:
        return combined_df

    combined_df['Game_ID'] = combined_df['Game_ID'].apply(_norm_id)
    combined_df['Round_ID'] = combined_df['Round_ID'].apply(_norm_id)

    # Deduplicar SIN incluir Target en la clave para impedir pares contradictorios
    has_gid = combined_df['Game_ID'].notna()
    tagged_df = combined_df[has_gid].drop_duplicates(subset=['ID', 'Game_ID'], keep='last')
    legacy_df = combined_df[~has_gid].drop_duplicates(
        subset=['ID', 'Equipo', 'Media', 'WMA', 'Tendencia', 'Volatilidad', 'Rival', 'Localia'],
        keep='first'
    )
    combined_df = pd.concat([legacy_df, tagged_df], ignore_index=True)

    combined_df.to_csv(HISTORICAL_LEARN_FILE, index=False)
    return combined_df[combined_df['Target'].notna()].copy()
