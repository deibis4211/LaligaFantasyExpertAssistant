import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
import sys
import os

# Asegurar importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.model import FantasyPredictor

def evaluate_models():
    historical_file = 'data/historico_aprendizaje.csv'
    if not os.path.exists(historical_file):
        print("[!] No existe el archivo de histórico de aprendizaje en data/historico_aprendizaje.csv")
        return

    df = pd.read_csv(historical_file)
    df_eval = df[df['Target'].notna()].copy()
    
    if df_eval.empty:
        print("[!] El dataset no contiene suficientes registros con Target válido.")
        return
        
    print("=" * 70)
    print(f"   EVALUACIÓN DE PRECISIÓN DE MODELOS (Total Muestras: {len(df_eval)})")
    print("=" * 70)
    
    # 1. Evaluación mediante K-Fold Cross Validation (5 folds)
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    y_true_all = []
    y_pred_model_all = []
    y_pred_media_all = []
    
    positions = ['PT', 'DF', 'MC', 'DL']
    pos_results = {p: {'y_true': [], 'y_pred_model': [], 'y_pred_media': []} for p in positions}

    for fold, (train_idx, val_idx) in enumerate(kf.split(df_eval), 1):
        train_data = df_eval.iloc[train_idx].copy()
        val_data = df_eval.iloc[val_idx].copy()
        
        # Instanciar y entrenar
        predictor = FantasyPredictor()
        predictor.train(train_data)
        
        # Predecir sobre validación
        val_preds = predictor.predict(val_data)
        val_data['Prediccion'] = val_preds
        
        y_true_all.extend(val_data['Target'].values)
        y_pred_model_all.extend(val_preds)
        y_pred_media_all.extend(val_data['Media'].values)
        
        # Desglose por posición
        for pos in positions:
            sub = val_data[val_data['Posicion'].astype(str) == pos]
            if not sub.empty:
                pos_results[pos]['y_true'].extend(sub['Target'].values)
                pos_results[pos]['y_pred_model'].extend(sub['Prediccion'].values)
                pos_results[pos]['y_pred_media'].extend(sub['Media'].values)

    # Convertir a arrays numpy
    y_true_all = np.array(y_true_all)
    y_pred_model_all = np.array(y_pred_model_all)
    y_pred_media_all = np.array(y_pred_media_all)
    
    # Calcular Métricas Globales
    mae_model = mean_absolute_error(y_true_all, y_pred_model_all)
    rmse_model = np.sqrt(mean_squared_error(y_true_all, y_pred_model_all))
    r2_model = r2_score(y_true_all, y_pred_model_all)
    corr_model = np.corrcoef(y_true_all, y_pred_model_all)[0, 1]
    
    mae_media = mean_absolute_error(y_true_all, y_pred_media_all)
    rmse_media = np.sqrt(mean_squared_error(y_true_all, y_pred_media_all))
    r2_media = r2_score(y_true_all, y_pred_media_all)
    corr_media = np.corrcoef(y_true_all, y_pred_media_all)[0, 1]
    
    # Porcentaje de acierto según tolerancia
    acc_exact = np.mean(np.round(y_pred_model_all) == y_true_all) * 100
    acc_tol_1 = np.mean(np.abs(y_pred_model_all - y_true_all) <= 1.0) * 100
    acc_tol_2 = np.mean(np.abs(y_pred_model_all - y_true_all) <= 2.0) * 100

    acc_exact_b = np.mean(np.round(y_pred_media_all) == y_true_all) * 100
    acc_tol_1_b = np.mean(np.abs(y_pred_media_all - y_true_all) <= 1.0) * 100
    acc_tol_2_b = np.mean(np.abs(y_pred_media_all - y_true_all) <= 2.0) * 100

    print("\n--- PORCENTAJE DE PRECISION TOTAL / ACIERTO ---")
    print(f"{'Criterio de Acierto':<25} | {'XGBoost (Modelo)':<18} | {'Media Simple (Baseline)':<22} | {'Diferencia':<10}")
    print("-" * 80)
    print(f"{'Acierto Exacto (puntos=Y)':<25} | {acc_exact:<17.2f}% | {acc_exact_b:<21.2f}% | {acc_exact - acc_exact_b:+.2f}%")
    print(f"{'Precision con Margen ±1 pto':<25} | {acc_tol_1:<17.2f}% | {acc_tol_1_b:<21.2f}% | {acc_tol_1 - acc_tol_1_b:+.2f}%")
    print(f"{'Precision con Margen ±2 ptos':<25} | {acc_tol_2:<17.2f}% | {acc_tol_2_b:<21.2f}% | {acc_tol_2 - acc_tol_2_b:+.2f}%")

    print("\n--- METRICAS GLOBALES DE PRECISION ---")
    print(f"{'Metrica':<15} | {'XGBoost (Modelo)':<18} | {'Media Simple (Baseline)':<22} | {'Mejora %':<10}")
    print("-" * 72)
    print(f"{'MAE (Error)':<15} | {mae_model:<18.3f} | {mae_media:<22.3f} | {((mae_media - mae_model)/mae_media)*100:+.2f}%")
    print(f"{'RMSE':<15} | {rmse_model:<18.3f} | {rmse_media:<22.3f} | {((rmse_media - rmse_model)/rmse_media)*100:+.2f}%")
    print(f"{'R2 (Explicacion)':<15} | {r2_model:<18.3f} | {r2_media:<22.3f} | N/A")
    print(f"{'Correlacion r':<15} | {corr_model:<18.3f} | {corr_media:<22.3f} | N/A")
    
    print("\n--- DESGLOSE DE PRECISION POR POSICION ---")
    print(f"{'Posicion':<8} | {'N Muestras':<11} | {'MAE Modelo':<12} | {'MAE Media':<12} | {'Acc ±1 pto':<12} | {'Mejora MAE %':<12}")
    print("-" * 80)
    
    for pos in positions:
        yt = np.array(pos_results[pos]['y_true'])
        yp_m = np.array(pos_results[pos]['y_pred_model'])
        yp_b = np.array(pos_results[pos]['y_pred_media'])
        
        if len(yt) > 0:
            m_mae = mean_absolute_error(yt, yp_m)
            b_mae = mean_absolute_error(yt, yp_b)
            acc_p = np.mean(np.abs(yp_m - yt) <= 1.0) * 100
            imp = ((b_mae - m_mae) / b_mae) * 100 if b_mae > 0 else 0.0
            print(f"{pos:<8} | {len(yt):<11} | {m_mae:<12.3f} | {b_mae:<12.3f} | {acc_p:<11.2f}% | {imp:+.2f}%")

    print("\n" + "=" * 70)

if __name__ == '__main__':
    evaluate_models()
