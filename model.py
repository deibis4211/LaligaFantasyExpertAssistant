import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
import os
import joblib

MODEL_FILE = 'model_xgboost.pkl'
ENCODERS_FILE = 'encoders.pkl'

class FantasyPredictor:
    def __init__(self):
        self.model = None
        self.encoders = {}
        
    def _prepare_features(self, df):
        """Convierte columnas categóricas en numéricas."""
        df_ml = df.copy()
        for col in ['Equipo', 'Posicion', 'Rival']:
            if col not in self.encoders:
                self.encoders[col] = LabelEncoder()
                # Aseguramos que 'Desconocido' esté en las clases
                vals = df_ml[col].astype(str).tolist()
                if 'Desconocido' not in vals: vals.append('Desconocido')
                self.encoders[col].fit(vals)
                
            df_ml[col] = df_ml[col].astype(str).map(
                lambda x: self.encoders[col].transform([x])[0] if x in self.encoders[col].classes_ else self.encoders[col].transform(['Desconocido'])[0]
            )
        return df_ml

    def train(self, historical_df):
        print("[*] Entrenando modelo XGBoost...")
        
        # Simulación de features: Usaremos el valor y la posición por ahora
        df_train = self._prepare_features(historical_df)
        
        # Features: Equipo, Posición, Valor, Localía y RIVAL
        features = ['Equipo', 'Posicion', 'Valor', 'Es_Local', 'Rival']
        X = df_train[features]
        y = df_train['Puntos']
        
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            objective='reg:squarederror'
        )
        
        self.model.fit(X, y)
        
        # Guardar modelo y encoders
        joblib.dump(self.model, MODEL_FILE)
        joblib.dump(self.encoders, ENCODERS_FILE)
        print("[*] Modelo entrenado y guardado correctamente.")

    def load(self):
        if os.path.exists(MODEL_FILE) and os.path.exists(ENCODERS_FILE):
            self.model = joblib.load(MODEL_FILE)
            self.encoders = joblib.load(ENCODERS_FILE)
            return True
        return False

    def predict(self, current_df):
        if self.model is None:
            if not self.load():
                print("[!] No hay modelo entrenado. Usando media simple como fallback.")
                return current_df['Media']
        
        df_pred = self._prepare_features(current_df)
        features = ['Equipo', 'Posicion', 'Valor', 'Es_Local', 'Rival']
        X = df_pred[features]
        
        preds = self.model.predict(X)
        return np.maximum(0, preds) # No queremos puntos negativos proyectados
