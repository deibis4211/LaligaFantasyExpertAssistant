import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
import os
import joblib

ENCODERS_FILE = 'data/encoders.pkl'

class FantasyPredictor:
    def __init__(self):
        self.models = {}
        self.encoders = {}
        
    def _prepare_encoders(self, df):
        """Entrena y aplica LabelEncoders en base a columnas."""
        df_ml = df.copy()
        df_ml['Posicion_raw'] = df_ml['Posicion'].astype(str)
        
        # LabelEncoder único para Equipo y Rival para asegurar consistencia
        if 'TeamEncoder' not in self.encoders:
            self.encoders['TeamEncoder'] = LabelEncoder()
            todos_equipos = pd.concat([df_ml['Equipo'], df_ml['Rival']]).astype(str).tolist()
            if 'Desconocido' not in todos_equipos: todos_equipos.append('Desconocido')
            self.encoders['TeamEncoder'].fit(todos_equipos)
            
        if 'Posicion' not in self.encoders:
            self.encoders['Posicion'] = LabelEncoder()
            posiciones = df_ml['Posicion'].astype(str).tolist()
            if 'UNK' not in posiciones: posiciones.append('UNK')
            self.encoders['Posicion'].fit(posiciones)
            
        df_ml['Equipo'] = df_ml['Equipo'].astype(str).map(
            lambda x: self.encoders['TeamEncoder'].transform([x])[0] if x in self.encoders['TeamEncoder'].classes_ else self.encoders['TeamEncoder'].transform(['Desconocido'])[0]
        )
        df_ml['Rival'] = df_ml['Rival'].astype(str).map(
            lambda x: self.encoders['TeamEncoder'].transform([x])[0] if x in self.encoders['TeamEncoder'].classes_ else self.encoders['TeamEncoder'].transform(['Desconocido'])[0]
        )
        df_ml['Posicion'] = df_ml['Posicion'].astype(str).map(
            lambda x: self.encoders['Posicion'].transform([x])[0] if x in self.encoders['Posicion'].classes_ else self.encoders['Posicion'].transform(['UNK'])[0]
        )
        return df_ml

    def _prepare_features(self, df):
        """Prepara las variables avanzadas y codificaciones para la predicción."""
        df_ml = df.copy()
        df_ml['Posicion_raw'] = df_ml['Posicion'].astype(str)
        
        # Calcular variables avanzadas de forma a partir de Puntos_Recientes si es necesario
        if 'WMA' not in df_ml.columns and 'Puntos_Recientes' in df_ml.columns:
            from core.data_manager import calculate_wma, calculate_trend, calculate_volatility
            wma_list, trend_list, vol_list = [], [], []
            for _, r in df_ml.iterrows():
                fitness = r['Puntos_Recientes']
                if not isinstance(fitness, list): fitness = [0,0,0,0,0]
                while len(fitness) < 5: fitness.insert(0, 0)
                fitness = fitness[-5:]
                
                wma_list.append(calculate_wma(fitness))
                trend_list.append(calculate_trend(fitness))
                vol_list.append(calculate_volatility(fitness))
            df_ml['WMA'] = wma_list
            df_ml['Tendencia'] = trend_list
            df_ml['Volatilidad'] = vol_list
            
        if 'Rival' not in df_ml.columns:
            df_ml['Rival'] = 'Desconocido'
        if 'Localia' not in df_ml.columns:
            df_ml['Localia'] = 0.5
            
        df_ml['Equipo'] = df_ml['Equipo'].astype(str).map(
            lambda x: self.encoders['TeamEncoder'].transform([x])[0] if x in self.encoders['TeamEncoder'].classes_ else self.encoders['TeamEncoder'].transform(['Desconocido'])[0]
        )
        df_ml['Rival'] = df_ml['Rival'].astype(str).map(
            lambda x: self.encoders['TeamEncoder'].transform([x])[0] if x in self.encoders['TeamEncoder'].classes_ else self.encoders['TeamEncoder'].transform(['Desconocido'])[0]
        )
        df_ml['Posicion'] = df_ml['Posicion'].astype(str).map(
            lambda x: self.encoders['Posicion'].transform([x])[0] if x in self.encoders['Posicion'].classes_ else self.encoders['Posicion'].transform(['UNK'])[0]
        )
        return df_ml

    def train(self, historical_df):
        print("[*] Entrenando modelos XGBoost especializados por posición (4 en total)...")
        
        # Preparar encoders
        df_base = self._prepare_encoders(historical_df)
        self.feature_cols = ['Equipo', 'Posicion', 'Valor', 'Media', 'WMA', 'Tendencia', 'Volatilidad', 'Rival', 'Localia']
        
        positions = ['PT', 'DF', 'MC', 'DL']
        for pos in positions:
            df_pos = df_base[df_base['Posicion_raw'] == pos].copy()
            
            if not df_pos.empty:
                X = df_pos[self.feature_cols]
                y = df_pos['Target']
                model = xgb.XGBRegressor(
                    n_estimators=200,
                    learning_rate=0.05,
                    max_depth=4,
                    objective='reg:squarederror',
                    random_state=42
                )
                model.fit(X, y)
                file_path = f'data/model_{pos.lower()}.pkl'
                joblib.dump(model, file_path)
                self.models[pos] = model
                print(f"[*] Modelo para {pos} entrenado correctamente.")
            else:
                print(f"[!] Sin datos suficientes para entrenar el modelo de {pos}.")
            
        # Guardar codificadores
        joblib.dump(self.encoders, ENCODERS_FILE)

    def load(self):
        positions = ['PT', 'DF', 'MC', 'DL']
        loaded_count = 0
        for pos in positions:
            file_path = f'data/model_{pos.lower()}.pkl'
            if os.path.exists(file_path):
                self.models[pos] = joblib.load(file_path)
                loaded_count += 1
                
        if loaded_count == len(positions) and os.path.exists(ENCODERS_FILE):
            self.encoders = joblib.load(ENCODERS_FILE)
            return True
        return False

    def predict(self, current_df):
        positions = ['PT', 'DF', 'MC', 'DL']
        if len(self.models) < len(positions):
            if not self.load():
                print("[!] No hay modelos entrenados. Usando media simple como fallback.")
                return current_df['Media']
        
        df_pred = self._prepare_features(current_df)
        features = ['Equipo', 'Posicion', 'Valor', 'Media', 'WMA', 'Tendencia', 'Volatilidad', 'Rival', 'Localia']
        
        preds = np.zeros(len(df_pred))
        
        for pos in positions:
            is_pos = df_pred['Posicion_raw'] == pos
            if is_pos.any() and pos in self.models:
                preds[is_pos] = self.models[pos].predict(df_pred.loc[is_pos, features])
            elif is_pos.any():
                preds[is_pos] = df_pred.loc[is_pos, 'Media']
                
        return np.maximum(0, preds)
