import pandas as pd
import os

HISTORICAL_FILE = 'data/historico_puntos.csv'

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
    """Guarda el histórico desglosando la racha de puntos (p1-p5)."""
    new_data = []
    
    for _, row in df.iterrows():
        fitness = row.get('Puntos_Recientes', [0,0,0,0,0])
        # Asegurar longitud 5
        while len(fitness) < 5: fitness.insert(0, 0)
        fitness = fitness[-5:]
        
        new_data.append({
            'ID': row['ID'],
            'Nombre': row['Nombre'],
            'Equipo': row['Equipo'],
            'Posicion': row['Posicion'],
            'Puntos': row['Puntos'],
            'Media': row['Media'],
            'Valor': row['Valor'],
            'p1': fitness[0], 'p2': fitness[1], 'p3': fitness[2], 'p4': fitness[3], 'p5': fitness[4]
        })
    
    new_df = pd.DataFrame(new_data)
    
    # Sobrescribimos o añadimos (por ahora snapshot simple para entrenar bien la racha)
    new_df.to_csv(HISTORICAL_FILE, index=False)
    return new_df
