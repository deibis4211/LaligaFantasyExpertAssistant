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
            teams = {str(k): v.get('name') for k, v in data.get('teams', {}).items()}
            players = data.get('players', {})
            
            for pid, pdata in players.items():
                name = pdata.get('name', 'Desconocido')
                team_id = str(pdata.get('teamID', ''))
                team = teams.get(team_id, "Desconocido")
                
                valor = pdata.get('price', 0)
                tendencia_abs = pdata.get('priceIncrement', 0)
                
                try:
                    tendencia_pct = round((tendencia_abs / valor) * 100, 2) if valor > 0 else 0.0
                except:
                    tendencia_pct = 0.0
                    
                tendencia_cat = 'Subida' if tendencia_abs > 0 else ('Bajada' if tendencia_abs < 0 else 'Estable')
                
                pts_totales = pdata.get('points', 0)
                
                fitness = pdata.get('fitness', [])
                if not isinstance(fitness, list): fitness = []
                p_recientes = [x if isinstance(x, int) else 0 for x in fitness]
                
                partidos_jugados = pdata.get('playedHome', 0) + pdata.get('playedAway', 0)
                if partidos_jugados > 0:
                    pts_media = round(pts_totales / partidos_jugados, 2)
                else:
                    pts_media = 0.0
                    
                raw_st = pdata.get('status', 'ok')
                if raw_st == 'injured': estado = 'Lesionado'
                elif raw_st == 'doubt': estado = 'Duda'
                elif raw_st == 'suspended': estado = 'Sancionado'
                elif raw_st == 'warned': estado = 'Apercibido'
                else: estado = 'Disponible'
                
                pos_id = pdata.get('position', 0)
                if pos_id == 1: pos = 'PT'
                elif pos_id == 2: pos = 'DF'
                elif pos_id == 3: pos = 'MC'
                elif pos_id == 4: pos = 'DL'
                else: pos = 'UNK'

                players_data.append({
                    'Nombre': name, 'Equipo': team, 'Posicion': pos, 'Valor': valor, 
                    'Tendencia': tendencia_cat, 'Puntos': pts_totales, 
                    'Media': pts_media, 'Estado': estado,
                    'Tendencia_48h_pct': tendencia_pct * 2,
                    'Puntos_Recientes': p_recientes
                })
            print(f"[*] Base de datos descargada con exito: {len(players_data)} jugadores oficiales.")
            return pd.DataFrame(players_data)
    except Exception as e:
        print(f"[!] Error conectando a la API: {e}")
        
    print("[!] Fallo grave intentando obtener la BD. Retornando tabla vacia.")
    return pd.DataFrame()
