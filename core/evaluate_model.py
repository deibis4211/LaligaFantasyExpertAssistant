from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
import sys
import os

# Asegurar importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.model import FantasyPredictor

EVAL_HISTORY_FILE = 'data/historial_evaluaciones.csv'
WALK_FORWARD_FILE = 'data/evaluacion_por_jornada.csv'


def _norm_round(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.endswith('.0') and s[:-2].lstrip('-').isdigit():
        return s[:-2]
    return s or None


def _evaluate_walk_forward(df_eval, min_train_rows=300, min_round_rows=80, save_history=True):
    """Entrena con jornadas pasadas (< k) y evalúa sobre cada jornada nueva (k) en orden cronológico."""
    if 'Round_ID' not in df_eval.columns:
        return None, None

    df_seq = df_eval[df_eval['Round_ID'].notna()].copy()
    if df_seq.empty:
        return None, None

    df_seq['_rid'] = df_seq['Round_ID'].apply(_norm_round)
    df_seq = df_seq[df_seq['_rid'].notna()].copy()
    if df_seq['_rid'].nunique() < 2:
        return None, None

    has_date = 'Match_Date' in df_seq.columns and df_seq['Match_Date'].notna().any()
    if has_date:
        df_seq['_dt'] = pd.to_numeric(df_seq['Match_Date'], errors='coerce')
        round_order = (
            df_seq.groupby('_rid', sort=False)['_dt']
            .min()
            .sort_values(kind='mergesort')
            .index.tolist()
        )
    else:
        round_order = df_seq['_rid'].drop_duplicates().tolist()

    order_map = {rid: idx for idx, rid in enumerate(round_order)}
    df_seq['_r_order'] = df_seq['_rid'].map(order_map)

    rows_summary = []
    yt_all, yp_all, ym_all = [], [], []

    for rid in round_order:
        r_ord = order_map[rid]
        val_data = df_seq[df_seq['_r_order'] == r_ord].copy()
        if len(val_data) < min_round_rows:
            continue

        if has_date and val_data['_dt'].notna().any():
            val_min_dt = val_data['_dt'].min()
            train_data = df_seq[(df_seq['_r_order'] < r_ord) & (df_seq['_dt'] < val_min_dt)].copy()
        else:
            train_data = df_seq[df_seq['_r_order'] < r_ord].copy()

        if len(train_data) < min_train_rows:
            continue

        predictor = FantasyPredictor()
        predictor.train(train_data, save=False, verbose=False)
        preds = predictor.predict(val_data)

        yt = val_data['Target'].values
        ym = val_data['Media'].values
        mae_m = mean_absolute_error(yt, preds)
        mae_b = mean_absolute_error(yt, ym)
        rmse_m = np.sqrt(mean_squared_error(yt, preds))
        acc_1 = np.mean(np.abs(preds - yt) <= 1.0) * 100
        imp = ((mae_b - mae_m) / mae_b) * 100 if mae_b > 0 else 0.0

        label = rid
        if 'Round_Label' in val_data.columns and val_data['Round_Label'].notna().any():
            label = str(val_data['Round_Label'].dropna().iloc[0])

        rows_summary.append((label, rid, len(train_data), len(val_data), mae_m, mae_b, imp, acc_1, rmse_m))
        yt_all.extend(yt)
        yp_all.extend(preds)
        ym_all.extend(ym)

    last_label = None
    if 'Round_Label' in df_seq.columns and df_seq['Round_Label'].notna().any():
        last_label = str(df_seq.loc[df_seq['_r_order'] == df_seq['_r_order'].max(), 'Round_Label'].dropna().iloc[0])
    else:
        last_label = round_order[-1]

    if not rows_summary:
        print("\n--- EVOLUCIÓN JORNADA A JORNADA (WALK-FORWARD) ---")
        print("[!] Aún no hay suficientes jornadas etiquetadas consecutivas (se requieren >= 300 muestras previas).")
        return None, last_label

    print("\n--- EVOLUCIÓN JORNADA A JORNADA (ENTRENA EN PASADO -> EVALÚA EN JORNADA NUEVA) ---")
    print(f"{'Jornada':<10} | {'N Train':<8} | {'N Test':<7} | {'MAE Mod':<9} | {'MAE Media':<9} | {'Mejora %':<9} | {'Acc ±1':<8} | {'RMSE Mod':<8}")
    print("-" * 85)
    for label, _, n_tr, n_te, mae_m, mae_b, imp, acc_1, rmse_m in rows_summary:
        print(f"{label:<10} | {n_tr:<8} | {n_te:<7} | {mae_m:<9.3f} | {mae_b:<9.3f} | {imp:+8.2f}% | {acc_1:6.2f}%  | {rmse_m:<8.3f}")

    yt_np, yp_np, ym_np = np.array(yt_all), np.array(yp_all), np.array(ym_all)
    wf_mae_m = mean_absolute_error(yt_np, yp_np)
    wf_mae_b = mean_absolute_error(yt_np, ym_np)
    wf_rmse_m = np.sqrt(mean_squared_error(yt_np, yp_np))
    wf_acc_1 = np.mean(np.abs(yp_np - yt_np) <= 1.0) * 100
    wf_imp = ((wf_mae_b - wf_mae_m) / wf_mae_b) * 100 if wf_mae_b > 0 else 0.0
    print("-" * 85)
    print(f"{'TOTAL WF':<10} | {'-':<8} | {len(yt_np):<7} | {wf_mae_m:<9.3f} | {wf_mae_b:<9.3f} | {wf_imp:+8.2f}% | {wf_acc_1:6.2f}%  | {wf_rmse_m:<8.3f}")

    if save_history:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        wf_df = pd.DataFrame([
            {
                'Jornada': label,
                'Round_ID': rid,
                'N_Train': n_tr,
                'N_Test': n_te,
                'MAE_Modelo': round(mae_m, 3),
                'MAE_Media': round(mae_b, 3),
                'Mejora_pct': round(imp, 2),
                'Acc_1pto': round(acc_1, 2),
                'RMSE_Modelo': round(rmse_m, 3),
                'Fecha_Eval': now_str,
            }
            for label, rid, n_tr, n_te, mae_m, mae_b, imp, acc_1, rmse_m in rows_summary
        ])
        os.makedirs(os.path.dirname(WALK_FORWARD_FILE), exist_ok=True)
        wf_df.to_csv(WALK_FORWARD_FILE, index=False)

    return {
        'WF_MAE': round(wf_mae_m, 3),
        'WF_MAE_Media': round(wf_mae_b, 3),
        'WF_Mejora_pct': round(wf_imp, 2),
        'WF_Acc_1pto': round(wf_acc_1, 2),
        'WF_RMSE': round(wf_rmse_m, 3),
    }, last_label


def _save_eval_history(entry):
    """Guarda el resumen de evaluación en historial_evaluaciones.csv (actualiza si no hubo cambios de jornada/muestras)."""
    os.makedirs(os.path.dirname(EVAL_HISTORY_FILE), exist_ok=True)
    if os.path.exists(EVAL_HISTORY_FILE):
        try:
            hist_df = pd.read_csv(EVAL_HISTORY_FILE)
        except Exception:
            hist_df = pd.DataFrame()
    else:
        hist_df = pd.DataFrame()

    if not hist_df.empty:
        last = hist_df.iloc[-1]
        same_samples = int(last.get('Total_Muestras', -1)) == int(entry['Total_Muestras'])
        same_round = str(last.get('Ultima_Jornada', '')) == str(entry['Ultima_Jornada'])
        if same_samples and same_round:
            for k, v in entry.items():
                hist_df.loc[hist_df.index[-1], k] = v
        else:
            hist_df = pd.concat([hist_df, pd.DataFrame([entry])], ignore_index=True)
    else:
        hist_df = pd.DataFrame([entry])

    hist_df.to_csv(EVAL_HISTORY_FILE, index=False)

    print("\n--- HISTÓRICO DE EVALUACIONES GUARDADAS ---")
    recent = hist_df.tail(10)
    print(f"{'Fecha':<19} | {'Jornada':<8} | {'Muestras':<8} | {'KF MAE':<7} | {'Mejora %':<9} | {'KF R2':<6} | {'WF MAE':<7}")
    print("-" * 80)
    for _, r in recent.iterrows():
        wf_mae = f"{r['WF_MAE']:.3f}" if pd.notna(r.get('WF_MAE')) else "-"
        print(
            f"{str(r['Fecha']):<19} | {str(r['Ultima_Jornada']):<8} | {int(r['Total_Muestras']):<8} | "
            f"{r['KF_MAE']:<7.3f} | {r['KF_Mejora_pct']:+8.2f}% | {r['KF_R2']:<6.3f} | {wf_mae:<7}"
        )


def evaluate_models(save_history=True):
    historical_file = 'data/historico_aprendizaje.csv'
    if not os.path.exists(historical_file):
        print("[!] No existe el archivo de histórico de aprendizaje en data/historico_aprendizaje.csv")
        return

    df = pd.read_csv(historical_file)
    df_eval = df[df['Target'].notna() & df['Media'].notna()].copy()
    
    if df_eval.empty:
        print("[!] El dataset no contiene suficientes registros con Target válido.")
        return
        
    print("=" * 85)
    print(f"   EVALUACIÓN DE PRECISIÓN DE MODELOS (Total Muestras: {len(df_eval)})")
    print("=" * 85)

    # 1. Evaluación temporal jornada tras jornada (sin fuga de futuro)
    wf_metrics, last_round_label = _evaluate_walk_forward(df_eval, save_history=save_history)

    # 2. Evaluación global mediante K-Fold Cross Validation (5 folds)
    print("\n--- VALIDACIÓN CRUZADA GLOBAL (5-FOLD) ---")
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    y_true_all = []
    y_pred_model_all = []
    y_pred_media_all = []
    
    positions = ['PT', 'DF', 'MC', 'DL']
    pos_results = {p: {'y_true': [], 'y_pred_model': [], 'y_pred_media': []} for p in positions}

    for fold, (train_idx, val_idx) in enumerate(kf.split(df_eval), 1):
        train_data = df_eval.iloc[train_idx].copy()
        val_data = df_eval.iloc[val_idx].copy()
        
        # Instanciar y entrenar sin sobrescribir los modelos de producción en data/
        predictor = FantasyPredictor()
        predictor.train(train_data, save=False, verbose=(fold == 1))
        
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
    
    pos_mae = {}
    for pos in positions:
        yt = np.array(pos_results[pos]['y_true'])
        yp_m = np.array(pos_results[pos]['y_pred_model'])
        yp_b = np.array(pos_results[pos]['y_pred_media'])
        
        if len(yt) > 0:
            m_mae = mean_absolute_error(yt, yp_m)
            b_mae = mean_absolute_error(yt, yp_b)
            acc_p = np.mean(np.abs(yp_m - yt) <= 1.0) * 100
            imp = ((b_mae - m_mae) / b_mae) * 100 if b_mae > 0 else 0.0
            pos_mae[pos] = round(m_mae, 3)
            print(f"{pos:<8} | {len(yt):<11} | {m_mae:<12.3f} | {b_mae:<12.3f} | {acc_p:<11.2f}% | {imp:+.2f}%")

    if save_history:
        kf_imp = ((mae_media - mae_model) / mae_media) * 100 if mae_media > 0 else 0.0
        entry = {
            'Fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Total_Muestras': int(len(df_eval)),
            'Ultima_Jornada': last_round_label or '-',
            'KF_MAE': round(mae_model, 3),
            'KF_MAE_Media': round(mae_media, 3),
            'KF_Mejora_pct': round(kf_imp, 2),
            'KF_RMSE': round(rmse_model, 3),
            'KF_R2': round(r2_model, 3),
            'KF_Corr_r': round(corr_model, 3),
            'KF_Acc_Exact': round(acc_exact, 2),
            'KF_Acc_1pto': round(acc_tol_1, 2),
            'KF_Acc_2ptos': round(acc_tol_2, 2),
            'WF_MAE': wf_metrics['WF_MAE'] if wf_metrics else np.nan,
            'WF_MAE_Media': wf_metrics['WF_MAE_Media'] if wf_metrics else np.nan,
            'WF_Mejora_pct': wf_metrics['WF_Mejora_pct'] if wf_metrics else np.nan,
            'WF_Acc_1pto': wf_metrics['WF_Acc_1pto'] if wf_metrics else np.nan,
            'WF_RMSE': wf_metrics['WF_RMSE'] if wf_metrics else np.nan,
            'PT_MAE': pos_mae.get('PT', np.nan),
            'DF_MAE': pos_mae.get('DF', np.nan),
            'MC_MAE': pos_mae.get('MC', np.nan),
            'DL_MAE': pos_mae.get('DL', np.nan),
        }
        _save_eval_history(entry)
        print(f"\n[*] Registro guardado en {EVAL_HISTORY_FILE}" + (f" y {WALK_FORWARD_FILE}" if wf_metrics else ""))

    print("\n" + "=" * 85)

if __name__ == '__main__':
    evaluate_models()
