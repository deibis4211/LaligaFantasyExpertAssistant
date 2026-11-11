import argparse
from datetime import datetime
import json
import os
import sys
import time
import numpy as np
import pandas as pd
import requests

# Asegurar importaciones desde la raíz del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.data_manager import (
    HISTORICAL_LEARN_FILE,
    _norm_id,
    calculate_trend,
    calculate_volatility,
    calculate_wma,
    save_snapshot,
)
from core.model import FantasyPredictor
from core.scraper import parse_biwenger_data

DATA_URL = 'https://biwenger.as.com/api/v2/competitions/la-liga/data?lang=es&score=1'
SEASON_URL = 'https://biwenger.as.com/api/v2/competitions/la-liga/season?lang=es'
MATCH_URL_FMT = 'https://biwenger.as.com/api/v2/matches/la-liga/{game_id}?lang=es&score=1'
DEFAULT_CACHE_DIR = 'data/matches_cache'


def _format_reset_time(reset_ts):
    if not reset_ts:
        return "desconocida"
    try:
        dt = datetime.fromtimestamp(int(reset_ts))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return str(reset_ts)


def _fetch_json(session, url, timeout=20):
    """Realiza un GET devolviendo (status_code, json_data, rate_info) sin lanzar excepción de red."""
    try:
        resp = session.get(url, timeout=timeout)
    except requests.RequestException as exc:
        print(f"[!] Error de red/timeout al consultar {url}: {exc}")
        return 0, None, {}
    rate_info = {
        'limit': resp.headers.get('X-Rate-Limit-Limit'),
        'remaining': resp.headers.get('X-Rate-Limit-Remaining'),
        'reset': resp.headers.get('X-Rate-Limit-Reset'),
    }
    if resp.status_code == 200:
        return 200, resp.json().get('data', {}), rate_info
    return resp.status_code, None, rate_info


def _load_or_fetch_matches(session, finished_games, cache_dir, delay=0.9, reserve_quota=5):
    """Descarga partidos finalizados secuencialmente usando caché en disco para poder reanudar."""
    os.makedirs(cache_dir, exist_ok=True)
    matches = []
    downloaded = 0
    last_rate = {}

    for idx, (dt, rid, gid) in enumerate(finished_games, 1):
        cache_path = os.path.join(cache_dir, f'{gid}.json')
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                matches.append((dt, rid, gid, json.load(f)))
            continue

        # Detener antes de agotar la cuota para no disparar 429 ni bloquear main.py/app.py
        rem = last_rate.get('remaining')
        if rem is not None and str(rem).isdigit() and int(rem) <= reserve_quota:
            return matches, 'quota_low', idx - 1, last_rate

        if downloaded > 0 and delay > 0:
            time.sleep(delay)

        status, m_data, rate_info = 0, None, {}
        for attempt in range(3):
            if attempt > 0:
                time.sleep(2.0 * attempt)
            status, m_data, rate_info = _fetch_json(session, MATCH_URL_FMT.format(game_id=gid))
            last_rate = rate_info or last_rate
            if status == 429:
                return matches, '429', idx - 1, rate_info
            if status == 200 and m_data:
                break

        if status != 200 or not m_data:
            print(f"[!] Error descargando partido {gid} tras reintentos (HTTP {status}).")
            return matches, 'network_error', idx - 1, last_rate

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(m_data, f, ensure_ascii=False)
        downloaded += 1
        matches.append((dt, rid, gid, m_data))

        if downloaded % 15 == 0:
            rem_str = f" | cuota restante: {rate_info.get('remaining')}" if rate_info.get('remaining') else ""
            print(f"[*] Descargados {idx}/{len(finished_games)} partidos{rem_str}...")

    return matches, None, len(finished_games), last_rate


def reconstruct_season_history(players_df, matches, min_team_games=3, round_labels=None):
    """Reconstruye fila a fila el histórico cronológico libre de fuga de datos y orden inverso."""
    active_players = {int(r['ID']): r for _, r in players_df.iterrows()}
    labels_map = {_norm_id(k): v for k, v in (round_labels or {}).items()}

    # Detectar el primer equipo real de cada jugador y su equipo real por jornada
    initial_team = {}
    round_player_team = {}
    for _, rid, _, m in matches:
        for side in ('home', 'away'):
            t_name = (m.get(side) or {}).get('name')
            for rep in (m.get(side) or {}).get('reports', []):
                pid = (rep.get('player') or {}).get('id')
                if pid is not None and t_name:
                    pid_int = int(pid)
                    if pid_int not in initial_team:
                        initial_team[pid_int] = t_name
                    round_player_team[(rid, pid_int)] = t_name

    # Estado acumulado por jugador y contador de partidos por equipo
    player_state = {}
    for pid, row in active_players.items():
        player_state[pid] = {
            'team': initial_team.get(pid, row['Equipo']),
            'fitness': [],
            'played': 0,
            'points_sum': 0,
        }
    team_games_played = {}

    reconstructed = []
    for dt, rid, gid, m in matches:
        home_obj = m.get('home') or {}
        away_obj = m.get('away') or {}
        home_name = home_obj.get('name', 'Desconocido')
        away_name = away_obj.get('name', 'Desconocido')

        # Mapa de participantes reales de este partido: pid -> (team_name, rival_name, localia, pts)
        match_reports = {}
        for side, team_n, rival_n, loc in (
            ('home', home_name, away_name, 1.0),
            ('away', away_name, home_name, 0.0),
        ):
            for rep in (m.get(side) or {}).get('reports', []):
                p_info = rep.get('player') or {}
                pid = p_info.get('id')
                if pid is None:
                    continue
                pid = int(pid)
                if pid in active_players:
                    player_state[pid]['team'] = team_n
                    raw_pts = rep.get('points')
                    if raw_pts is not None:
                        match_reports[pid] = (team_n, rival_n, loc, float(raw_pts))

        # Evaluar jugadores pertenecientes a alguno de los dos equipos en este momento
        for side_team, opp_team, loc in (
            (home_name, away_name, 1.0),
            (away_name, home_name, 0.0),
        ):
            t_idx = team_games_played.get(side_team, 0)
            for pid, st in player_state.items():
                if st['team'] != side_team:
                    continue
                # Si en esta misma jornada el jugador debutó ya con otro club, evitar fila fantasma
                if (rid, pid) in round_player_team and round_player_team[(rid, pid)] != side_team:
                    st['team'] = round_player_team[(rid, pid)]
                    continue

                did_play = pid in match_reports and match_reports[pid][0] == side_team
                pts = match_reports[pid][3] if did_play else 0.0

                # Emitir muestra solo cuando el equipo ya tiene >= min_team_games partidos previos
                # y el jugador participó en el encuentro o ya había debutado (evita saturar PT/DF de 0->0)
                if t_idx >= min_team_games and (did_play or st['played'] > 0):
                    hist_window = st['fitness'][-5:]
                    while len(hist_window) < 5:
                        hist_window.insert(0, 0)
                    cur_media = round(st['points_sum'] / st['played'], 2) if st['played'] > 0 else 0.0
                    p_meta = active_players[pid]

                    reconstructed.append({
                        'ID': pid,
                        'Nombre': p_meta['Nombre'],
                        'Equipo': side_team,
                        'Posicion': p_meta['Posicion'],
                        'Valor': float(p_meta['Valor']),
                        'Media': cur_media,
                        'WMA': calculate_wma(hist_window),
                        'Tendencia': calculate_trend(hist_window),
                        'Volatilidad': calculate_volatility(hist_window),
                        'Rival': opp_team,
                        'Localia': loc,
                        'Partidos_Jugados': st['played'],
                        'Game_ID': _norm_id(gid),
                        'Round_ID': _norm_id(rid),
                        'Round_Label': labels_map.get(_norm_id(rid), _norm_id(rid)),
                        'Match_Date': dt,
                        'Target': pts,
                    })

                # Actualizar estado tras el partido
                st['fitness'].append(int(round(pts)))
                if did_play:
                    st['played'] += 1
                    st['points_sum'] += int(round(pts))

            team_games_played[side_team] = t_idx + 1

    return pd.DataFrame(reconstructed)


def rebuild_historico(delay=0.9, cache_dir=DEFAULT_CACHE_DIR, min_team_games=3, retrain=True):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

    print("[*] Descargando jugadores y calendario de la temporada desde Biwenger...")
    s_data, data_payload, rate_data = _fetch_json(session, DATA_URL)
    if s_data != 200 or not data_payload:
        reset_at = _format_reset_time(rate_data.get('reset'))
        print(f"[!] No se pudo descargar /data de Biwenger (HTTP {s_data}).")
        if s_data == 429:
            print(f"[!] Cuota agotada. Reinicio reportado por Biwenger: {reset_at} (evita reintentar antes para no reiniciar la ventana).")
        return False

    s_season, season_payload, rate_season = _fetch_json(session, SEASON_URL)
    if s_season != 200 or not season_payload:
        reset_at = _format_reset_time(rate_season.get('reset'))
        print(f"[!] No se pudo descargar /season de Biwenger (HTTP {s_season}). Reinicio: {reset_at}")
        return False

    players_df, _, teams_raw = parse_biwenger_data(data_payload)
    finished_games = []
    round_labels = {}
    for rnd in season_payload.get('rounds', []):
        rid = rnd.get('id')
        if rid is not None:
            round_labels[_norm_id(rid)] = rnd.get('short') or rnd.get('name') or _norm_id(rid)
        for g in rnd.get('games', []):
            if g.get('status') == 'finished' and g.get('id') is not None:
                finished_games.append((g.get('date', 0), rid, g['id']))
    finished_games.sort(key=lambda x: (x[0], x[2]))

    print(f"[*] Partidos finalizados encontrados: {len(finished_games)} (caché en '{cache_dir}', cuota restante: {rate_season.get('remaining', '?')}).")
    matches, stop_reason, done_count, last_rate = _load_or_fetch_matches(session, finished_games, cache_dir, delay=delay)

    if stop_reason:
        reset_at = _format_reset_time(last_rate.get('reset'))
        print(
            f"[!] Detenido ({stop_reason}) tras procesar {done_count}/{len(finished_games)} partidos. "
            f"Los partidos ya descargados quedan en caché; vuelve a ejecutar tras {reset_at}."
        )
        return False

    hist_df = reconstruct_season_history(players_df, matches, min_team_games=min_team_games, round_labels=round_labels)
    if hist_df.empty:
        print("[!] No se generaron muestras reconstruidas.")
        return False

    os.makedirs(os.path.dirname(HISTORICAL_LEARN_FILE), exist_ok=True)
    hist_df.to_csv(HISTORICAL_LEARN_FILE, index=False)
    print(f"[*] Histórico reconstruido con éxito: {len(hist_df)} muestras limpias y cronológicas.")

    # Añadir filas pendientes para la próxima jornada usando el pipeline unificado
    train_df = save_snapshot(players_df, teams_raw)
    print(f"[*] Snapshot actual añadido. Filas listas para entrenamiento: {len(train_df)}")

    if retrain:
        predictor = FantasyPredictor()
        predictor.train(train_df, save=True, verbose=True)

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reconstruye historico_aprendizaje.csv desde la API de Biwenger.')
    parser.add_argument('--delay', type=float, default=0.9, help='Pausa en segundos entre peticiones a /matches (default: 0.9)')
    parser.add_argument('--cache-dir', default=DEFAULT_CACHE_DIR, help='Directorio caché de partidos JSON')
    parser.add_argument('--min-team-games', type=int, default=3, help='Partidos previos mínimos del equipo antes de generar muestras')
    parser.add_argument('--no-train', action='store_true', help='No reentrenar los modelos tras reconstruir el CSV')
    args = parser.parse_args()

    ok = rebuild_historico(
        delay=args.delay,
        cache_dir=args.cache_dir,
        min_team_games=args.min_team_games,
        retrain=not args.no_train,
    )
    sys.exit(0 if ok else 1)
