import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.scraper import scrape_players
from core.analyzer import analyze_plantilla, analyze_market
from core.utils import load_user_list
from core.data_manager import save_snapshot
from core.model import FantasyPredictor

app = FastAPI(title="LaLiga Fantasy Expert Assistant API")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global cache for data
DATA_CACHE = {
    "df": None,
    "teams_map": None,
    "teams_raw": None,
}

PLANTILLA_FILE = 'data/mi_plantilla.txt'
MERCADO_FILE = 'data/mercado_hoy.txt'
PRESUPUESTO = 18000000

def initialize_data(force_refresh=False):
    if force_refresh or DATA_CACHE["df"] is None:
        print("[*] Inicializando base de datos desde la API de Biwenger...")
        df, teams_map, teams_raw = scrape_players()
        if df.empty:
            raise HTTPException(status_code=500, detail="No se pudo conectar con la API de Biwenger.")
        DATA_CACHE["df"] = df
        DATA_CACHE["teams_map"] = teams_map
        DATA_CACHE["teams_raw"] = teams_raw
        
        # ML: Guardar e inicializar modelos
        hist_df = save_snapshot(df, teams_raw)
        predictor = FantasyPredictor()
        predictor.train(hist_df)
    return DATA_CACHE["df"], DATA_CACHE["teams_map"], DATA_CACHE["teams_raw"]

@app.on_event("startup")
async def startup_event():
    # Cargar datos al iniciar
    try:
        initialize_data()
    except Exception as e:
        print(f"[!] Error en inicialización de arranque: {e}")

@app.get("/api/data")
def get_dashboard_data():
    df, _, teams_raw = initialize_data()
    
    plantilla_names = load_user_list(PLANTILLA_FILE)
    mercado_names = load_user_list(MERCADO_FILE)
    
    # Análisis de plantilla y mercado
    top_5_onces, alertas = analyze_plantilla(df, plantilla_names)
    recomendaciones = analyze_market(df, mercado_names, PRESUPUESTO)
    
    # Resolver nombres con Fuzzy Match para garantizar coincidencia con la DB
    lista_db = df['Nombre'].tolist()
    plantilla_names_matched = []
    from core.utils import get_fuzzy_match
    for name in plantilla_names:
        match = get_fuzzy_match(name, lista_db)
        if match:
            plantilla_names_matched.append(match)
            
    df_plantilla = df[df['Nombre'].isin(plantilla_names_matched)].copy()
    
    # Resolver xP para plantilla completa
    predictor = FantasyPredictor()
    if predictor.load():
        if not df_plantilla.empty:
            df_plantilla['xP'] = predictor.predict(df_plantilla)
            plantilla_list = df_plantilla.to_dict('records')
        else:
            plantilla_list = []
    else:
        # Fallback a WMA
        if not df_plantilla.empty:
            df_plantilla['xP'] = df_plantilla['Puntos_Recientes'].apply(lambda x: sum(x)/len(x) if x else 0)
            plantilla_list = df_plantilla.to_dict('records')
        else:
            plantilla_list = []

    # Formatear Top 5 Onces
    onces_response = []
    for form_name, xp_tot, once_df in top_5_onces:
        onces_response.append({
            "formacion": form_name,
            "xp_total": float(xp_tot),
            "once": once_df.to_dict('records')
        })
        
    return {
        "presupuesto": PRESUPUESTO,
        "plantilla": plantilla_list,
        "mercado": recomendaciones.to_dict('records') if not recomendaciones.empty else [],
        "alertas": alertas.to_dict('records') if not alertas.empty else [],
        "onces_ideales": onces_response
    }

@app.get("/api/players/all")
def get_all_players():
    df, _, _ = initialize_data()
    df_all = df.copy()
    
    predictor = FantasyPredictor()
    if predictor.load():
        try:
            df_all['xP'] = predictor.predict(df_all)
        except Exception as e:
            print(f"[!] Error prediciendo xP para todos los jugadores: {e}")
            df_all['xP'] = df_all['WMA']
    else:
        df_all['xP'] = df_all['WMA']
        
    teams_list = sorted(list(df_all['Equipo'].unique()))
    players_list = df_all.to_dict('records')
    
    return {
        "teams": teams_list,
        "players": players_list
    }

@app.post("/api/refresh")
def refresh_data():
    try:
        df, _, _ = initialize_data(force_refresh=True)
        return {"status": "success", "message": "Datos y modelos XGBoost actualizados en tiempo real."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    # Retorna nombres de plantilla y mercado para editarlos desde la UI
    return {
        "plantilla": load_user_list(PLANTILLA_FILE),
        "mercado": load_user_list(MERCADO_FILE)
    }

@app.post("/api/config")
def save_config(config: dict):
    # Permite guardar cambios a plantilla y mercado desde la UI
    try:
        if "plantilla" in config:
            with open(PLANTILLA_FILE, 'w', encoding='utf-8') as f:
                f.write("\n".join(config["plantilla"]))
        if "mercado" in config:
            with open(MERCADO_FILE, 'w', encoding='utf-8') as f:
                f.write("\n".join(config["mercado"]))
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
