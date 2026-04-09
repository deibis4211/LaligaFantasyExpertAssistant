import itertools
import pandas as pd
from core.utils import get_fuzzy_match
from core.model import FantasyPredictor

def analyze_plantilla(df, plantilla_names):
    plantilla_names_matched = []
    lista_db = df['Nombre'].tolist()
    
    for name in plantilla_names:
        match = get_fuzzy_match(name, lista_db)
        if match: plantilla_names_matched.append(match)
        
    mi_eq = df[df['Nombre'].isin(plantilla_names_matched)].copy()
    
    if mi_eq.empty:
        return [], pd.DataFrame()
    
    predictor = FantasyPredictor()
    if predictor.load():
        mi_eq['xP'] = predictor.predict(mi_eq)
    else:
        # Fallback a WMA si no hay modelo entrenado aún
        weights = [0.1, 0.15, 0.2, 0.25, 0.3]
        def calc_wma(puntos_recientes):
            if not puntos_recientes: return 0
            p = puntos_recientes[-5:]
            w = weights[-len(p):]
            if sum(w) > 0:
                w = [x/sum(w) for x in w]
            return round(sum(x*y for x, y in zip(p, w)), 2)
        mi_eq['xP'] = mi_eq['Puntos_Recientes'].apply(calc_wma)
    
    disponibles = mi_eq[~mi_eq['Estado'].isin(['Lesionado', 'Sancionado'])].copy()
    
    # Formaciones validas: PT siempre 1. (DF, MC, DL) sumando 10
    formaciones = [
        (4, 4, 2), (4, 3, 3), (3, 4, 3), 
        (3, 5, 2), (4, 5, 1), (5, 4, 1), (5, 3, 2)
    ]
    
    pt_disp = disponibles[disponibles['Posicion'] == 'PT']
    df_disp = disponibles[disponibles['Posicion'] == 'DF']
    mc_disp = disponibles[disponibles['Posicion'] == 'MC']
    dl_disp = disponibles[disponibles['Posicion'] == 'DL']
    
    onces_posibles = []
    
    if not pt_disp.empty:
        for pt_idx in range(len(pt_disp)):
            portero = pt_disp.iloc[[pt_idx]]
            
            for (f_df, f_mc, f_dl) in formaciones:
                if len(df_disp) >= f_df and len(mc_disp) >= f_mc and len(dl_disp) >= f_dl:
                    df_combs = itertools.combinations(range(len(df_disp)), f_df)
                    mc_combs = itertools.combinations(range(len(mc_disp)), f_mc)
                    dl_combs = itertools.combinations(range(len(dl_disp)), f_dl)
                    
                    # Truco: usar product para evaluar TODAS las combinaciones puras
                    for c_df, c_mc, c_dl in itertools.product(df_combs, mc_combs, dl_combs):
                        best_df = df_disp.iloc[list(c_df)]
                        best_mc = mc_disp.iloc[list(c_mc)]
                        best_dl = dl_disp.iloc[list(c_dl)]
                        
                        once_df = pd.concat([portero, best_df, best_mc, best_dl])
                        total_xp = once_df['xP'].sum()
                        form_name = f"{f_df}-{f_mc}-{f_dl}"
                        
                        onces_posibles.append((form_name, round(total_xp, 2), once_df))
    
    # Ordenar todos los Onces teoricos posibles por WMA (forma proyectada total) de mayor a menor
    onces_posibles.sort(key=lambda x: x[1], reverse=True)
    
    # Filtrar combinaciones idénticas (ya que iteramos, puede haber ordenación idéntica si hay jugadores repetidos, no es el caso en pandas, pero lo tomamos directo)
    top_5_onces = onces_posibles[:5]
    
    # Alertas de Venta
    alertas = mi_eq[
        (mi_eq['Tendencia_48h_pct'] < -2.0) | 
        (mi_eq['Estado'].isin(['Lesionado', 'Sancionado'])) |
        (mi_eq['xP'] < mi_eq['Media'] * 0.7)
    ].copy()
    
    alertas['Motivo_Venta'] = ""
    alertas.loc[alertas['Tendencia_48h_pct'] < -2.0, 'Motivo_Venta'] += "Bajada fuerte de valor. "
    alertas.loc[alertas['Estado'].isin(['Lesionado', 'Sancionado']), 'Motivo_Venta'] += "No disponible (Baja). "
    alertas.loc[alertas['xP'] < alertas['Media'] * 0.7, 'Motivo_Venta'] += "Bajo rendimiento proyectado. "
    
    return top_5_onces, alertas

def analyze_market(df, mercado_names, budget):
    mercado_names_matched = []
    lista_db = df['Nombre'].tolist()
    
    for name in mercado_names:
        match = get_fuzzy_match(name, lista_db)
        if match: mercado_names_matched.append(match)
        
    mercado = df[df['Nombre'].isin(mercado_names_matched)].copy()
    
    if mercado.empty:
        return pd.DataFrame()
        
    max_pts = df['Media'].max() or 1
    
    def score_player(row):
        wma = 0
        if row['Puntos_Recientes']:
            p = row['Puntos_Recientes'][-3:]
            wma = sum(p) / len(p)
            
        forma = min(40, max(0, (wma / max_pts) * 40))
        
        tendencia_raw = row['Tendencia_48h_pct']
        if tendencia_raw > 2.0:
            tendencia = 30
        elif tendencia_raw > 0:
            tendencia = 15 + (tendencia_raw/2) * 15
        elif tendencia_raw > -1.0:
            tendencia = 5
        else:
            tendencia = 0
            
        if row['Valor'] > 0:
            rentabilidad_ratio = (row['Media'] * 1000000) / row['Valor']
            rentabilidad = min(30, max(0, rentabilidad_ratio * 10))
        else:
            rentabilidad = 0
            
        return round(forma + tendencia + rentabilidad, 1)

    mercado['Nota_Fichaje_100'] = mercado.apply(score_player, axis=1)
    mercado['Asequible'] = mercado['Valor'].apply(lambda v: 'SI' if v <= budget else 'NO')
    
    return mercado.sort_values(by='Nota_Fichaje_100', ascending=False)
