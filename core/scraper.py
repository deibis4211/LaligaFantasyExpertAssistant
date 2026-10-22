import pandas as pd
import requests

def scrape_players():
    print("[*] Iniciando descarga de la base de datos oficial (API web)...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    players_data = []

    try:
        response = requests.get('https://biwenger.as.com/api/v2/competitions/la-liga/data?lang=es&score=1', headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            teams_map = {str(k): v.get('name') for k, v in data.get('teams', {}).items()}
            players = data.get('players', {})
            
            # Extraer fixtures del próximo partido
            fixtures = {}
            for t_id, t_data in data.get('teams', {}).items():
                t_name = t_data['name']
                next_games = t_data.get('nextGames', [])
                if next_games:
                    game = next_games[0]
                    h_id = str(game['home']['id'])
                    a_id = str(game['away']['id'])
                    is_h = (h_id == str(t_id))
                    rival_id = a_id if is_h else h_id
                    rival_n = teams_map.get(rival_id, "Desconocido")
                    fixtures[t_name] = (rival_n, is_h)
            
            for pid, pdata in players.items():
                name = pdata.get('name', 'Desconocido')
                team_id = str(pdata.get('teamID', ''))
                team = teams_map.get(team_id, "Desconocido")
                
                valor = pdata.get('price', 0)
                tendencia_abs = pdata.get('priceIncrement', 0)
                
                try:
                    tendencia_pct = round((tendencia_abs / valor) * 100, 2) if valor > 0 else 0.0
                except:
                    tendencia_pct = 0.0
                
                pts_totales = pdata.get('points', 0)
                fitness = pdata.get('fitness', [])
                if not isinstance(fitness, list): fitness = []
                
                # Convert fitness to numbers, handling strings like 'sanctioned'
                p_recientes = []
                for x in fitness:
                    if isinstance(x, int): p_recientes.append(x)
                    elif x is None: p_recientes.append(0)
                    else: p_recientes.append(0) # 'sanctioned', 'injured', etc. count as 0 points
                
                # Fill with 0s if less than 5 matches
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
                # Descartar jugadores sin equipo real en LaLiga
                if team == 'Desconocido':
                    continue
                # Descartar entrenadores y registros con posición inválida
                if pos == 'UNK':
                    continue
                # Descartar jugadores sin valor de mercado (inactivos/retirados)
                if valor == 0:
                    continue

                # Obtener rival y localia
                rival_info = fixtures.get(team, ("Desconocido", True))
                rival = rival_info[0]
                localia = 1.0 if rival_info[1] else 0.0

                players_data.append({
                    'ID': pid,
                    'Nombre': name, 
                    'Equipo': team, 
                    'Posicion': pos, 
                    'Valor': valor, 
                    'Puntos': pts_totales, 
                    'Media': pts_media, 
                    'Estado': estado,
                    'Tendencia_48h_pct': tendencia_pct * 2,
                    'Puntos_Recientes': p_recientes,
                    'Rival': rival,
                    'Localia': localia
                })
            print(f"[*] Base de datos descargada con exito: {len(players_data)} jugadores validos (sin entrenadores ni jugadores sin equipo).")
            return pd.DataFrame(players_data), teams_map, data.get('teams', {})
    except Exception as e:
        print(f"[!] Error conectando a la API: {e}")
        
    print("[!] Fallo grave intentando obtener la BD. Retornando tabla vacia.")
    return pd.DataFrame(), {}, {}
