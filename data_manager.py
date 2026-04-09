import pandas as pd
import os

HISTORICAL_FILE = 'historico_puntos.csv'

def extract_fixtures(teams_raw):
    """Extrae el calendario real desde la metadata de la API de Biwenger."""
    fixtures = {}
    
    # Creamos un mapa de ID a Nombre para resolver los IDs de los partidos
    id_to_name = {str(t_id): t_data['name'] for t_id, t_data in teams_raw.items()}
    
    for t_id, t_data in teams_raw.items():
        team_name = t_data['name']
        next_games = t_data.get('nextGames', [])
        
        if next_games:
            game = next_games[0] # El más próximo
            home_id = str(game['home']['id'])
            away_id = str(game['away']['id'])
            
            is_home = (home_id == str(t_id))
            rival_id = away_id if is_home else home_id
            rival_name = id_to_name.get(rival_id, "Desconocido")
            
            fixtures[team_name] = (rival_name, is_home)
            
    return fixtures

def save_snapshot(df):
    """Guarda el histórico persistiendo los datos obtenidos."""
    new_data = []
    
    for _, row in df.iterrows():
        fitness = row.get('Puntos_Recientes', [])
        for i, pts in enumerate(fitness):
            new_data.append({
                'ID': row['ID'],
                'Nombre': row['Nombre'],
                'Equipo': row['Equipo'],
                'Posicion': row['Posicion'],
                'Jornada_Relativa': i,
                'Puntos': pts,
                'Valor': row['Valor'],
                'Rival': row.get('Rival', 'Desconocido'),
                'Es_Local': row.get('Es_Local', 0)
            })
    
    new_df = pd.DataFrame(new_data)
    
    if os.path.exists(HISTORICAL_FILE):
        old_df = pd.read_csv(HISTORICAL_FILE)
        combined = pd.concat([old_df, new_df]).drop_duplicates(subset=['ID', 'Jornada_Relativa'], keep='last')
        combined.to_csv(HISTORICAL_FILE, index=False)
    else:
        new_df.to_csv(HISTORICAL_FILE, index=False)
    
    return new_df
