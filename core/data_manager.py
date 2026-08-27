import pandas as pd
import numpy as np
import os

HISTORICAL_LEARN_FILE = 'data/historico_aprendizaje.csv'

def extract_fixtures(teams_raw):
    """Extrae el calendario real desde la metadata de la API de Biwenger."""
    fixtures = {}
    id_to_name = {str(t_id): t_data['name'] for t_id, t_data in teams_raw.items()}
    
    for t_id, t_data in teams_raw.items():
        team_name = t_data['name']
        next_games = t_data.get('nextGames', [])
        
        if next_games:
            game = next_games[0]
            home_id = str(game['home']['id'])
            away_id = str(game['away']['id'])
            
            is_home = (home_id == str(t_id))
            rival_id = away_id if is_home else home_id
            rival_name = id_to_name.get(rival_id, "Desconocido")
            
            fixtures[team_name] = (rival_name, is_home)
            
    return fixtures

def calculate_wma(points):
    if not points: return 0.0
    n = len(points)
    weights = list(range(1, n + 1))
    return round(sum(p * w for p, w in zip(points, weights)) / sum(weights), 2)

def calculate_trend(points):
    if len(points) < 3: return 0.0
    return float(points[-1] - points[-3])

def calculate_volatility(points):
    if len(points) < 2: return 0.0
    return round(float(np.std(points)), 2)

def save_snapshot(df, teams_raw):
    """Guarda el histórico desglosando y acumulando la racha de forma y emparejando resultados."""
    fixtures = extract_fixtures(teams_raw)
    
    if os.path.exists(HISTORICAL_LEARN_FILE):
        try:
            learn_df = pd.read_csv(HISTORICAL_LEARN_FILE)
        except:
            learn_df = pd.DataFrame()
    else:
        learn_df = pd.DataFrame()
        
    new_rows = []
    
    # Si está vacío el histórico de aprendizaje, hacemos cold-start
    if learn_df.empty:
        for _, row in df.iterrows():
            fitness = row.get('Puntos_Recientes', [0,0,0,0,0])
            if not isinstance(fitness, list): fitness = [0,0,0,0,0]
            while len(fitness) < 5: fitness.insert(0, 0)
            fitness = fitness[-5:]
            
            # Muestra 1: Predicción de p4 (Jornada 1) usando p1-p3 como entrada
            p1_3 = fitness[:3]
            new_rows.append({
                'ID': int(row['ID']),
                'Nombre': row['Nombre'],
                'Equipo': row['Equipo'],
                'Posicion': row['Posicion'],
                'Valor': float(row['Valor']),
                'Media': float(row['Media']),
                'WMA': calculate_wma(p1_3),
                'Tendencia': calculate_trend(p1_3),
                'Volatilidad': calculate_volatility(p1_3),
                'Rival': 'Desconocido',
                'Localia': 0.5,
                'Target': float(fitness[-2])
            })
            
            # Muestra 2: Predicción de p5 (Jornada 2) usando p1-p4 como entrada
            p1_4 = fitness[:4]
            new_rows.append({
                'ID': int(row['ID']),
                'Nombre': row['Nombre'],
                'Equipo': row['Equipo'],
                'Posicion': row['Posicion'],
                'Valor': float(row['Valor']),
                'Media': float(row['Media']),
                'WMA': calculate_wma(p1_4),
                'Tendencia': calculate_trend(p1_4),
                'Volatilidad': calculate_volatility(p1_4),
                'Rival': 'Desconocido',
                'Localia': 0.5,
                'Target': float(fitness[-1])
            })
            
    updated_learn_rows = []
    if not learn_df.empty:
        updated_learn_rows = learn_df.to_dict('records')
        
    for _, row in df.iterrows():
        pid = int(row['ID'])
        fitness = row.get('Puntos_Recientes', [0,0,0,0,0])
        if not isinstance(fitness, list): fitness = [0,0,0,0,0]
        while len(fitness) < 5: fitness.insert(0, 0)
        fitness = fitness[-5:]
        
        # 1. Intentar actualizar el Target de registros pendientes anteriores del jugador
        if updated_learn_rows:
            for r in updated_learn_rows:
                if int(r['ID']) == pid and pd.isna(r['Target']):
                    r['Target'] = float(fitness[-1])
                    
        # 2. Crear el registro para el partido que viene (upcoming)
        eq = row['Equipo']
        rival_info = fixtures.get(eq, ("Desconocido", True))
        rival = rival_info[0]
        localia = 1.0 if rival_info[1] else 0.0
        
        new_rows.append({
            'ID': pid,
            'Nombre': row['Nombre'],
            'Equipo': row['Equipo'],
            'Posicion': row['Posicion'],
            'Valor': float(row['Valor']),
            'Media': float(row['Media']),
            'WMA': calculate_wma(fitness),
            'Tendencia': calculate_trend(fitness),
            'Volatilidad': calculate_volatility(fitness),
            'Rival': rival,
            'Localia': localia,
            'Target': np.nan
        })
        
    if updated_learn_rows:
        combined_df = pd.DataFrame(updated_learn_rows)
        combined_df = pd.concat([combined_df, pd.DataFrame(new_rows)], ignore_index=True)
    else:
        combined_df = pd.DataFrame(new_rows)
        
    # Evitar duplicados exactos en el set de aprendizaje
    combined_df = combined_df.drop_duplicates(subset=['ID', 'WMA', 'Tendencia', 'Volatilidad', 'Rival', 'Localia', 'Target'], keep='first')
    combined_df.to_csv(HISTORICAL_LEARN_FILE, index=False)
    
    # Retornar los datos con Target para el entrenamiento del modelo
    return combined_df[combined_df['Target'].notna()].copy()
