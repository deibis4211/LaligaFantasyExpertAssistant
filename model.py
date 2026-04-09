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
        print("[*] Entrenando modelo XGBoost con desglose de racha...")
        
        # Primero preparamos los encoders para tener consistencia
        df_base = self._prepare_features(historical_df)
        
        # Features base para el entrenamiento que el modelo usará
        # Usamos la Media como una fuerte referencia para que la escala sea 0-20
        self.feature_cols = ['Equipo', 'Posicion', 'Valor', 'Es_Local', 'Rival', 'Media']
        
        X_rows = []
        y_rows = []
        
        # Desglosamos cada jugador en hasta 5 muestras (p1 a p5)
        # Esto enseña al modelo que las características resultan en X puntos POR JORNADA
        for _, row in df_base.iterrows():
            for p_col in ['p1', 'p2', 'p3', 'p4', 'p5']:
                puntos_match = row[p_col]
                
                # Para cada partido de la racha, el resto de datos se mantiene
                x_sample = row[self.feature_cols].copy()
                # En el pasado no sabemos quién fue el rival en el snapshot
                # X_rows.append(x_sample)
                X_rows.append(x_sample.values)
                y_rows.append(puntos_match)
        
        X = pd.DataFrame(X_rows, columns=self.feature_cols)
        y = pd.Series(y_rows)
        
        self.model = xgb.XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            objective='reg:squarederror',
            random_state=42
        )
        
        self.model.fit(X, y)
        
        # Guardar modelo y encoders
        joblib.dump(self.model, MODEL_FILE)
        joblib.dump(self.encoders, ENCODERS_FILE)
        print("[*] Modelo entrenado correctamente (Escala: Puntos por jornada).")

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
        
        # Aseguramos que las columnas necesarias existan (especialmente Media)
        if hasattr(self, 'feature_cols'):
            features = self.feature_cols
        else:
            features = ['Equipo', 'Posicion', 'Valor', 'Es_Local', 'Rival', 'Media']
            
        X = df_pred[features]
        
        preds = self.model.predict(X)
        return np.maximum(0, preds) # No queremos puntos negativos proyectados
