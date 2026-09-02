import os
import json
import requests
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
LEAGUES_FILE = 'data/leagues.json'
PRESUPUESTO = 18000000
OLLAMA_URL = "http://localhost:11434/api/chat"

# Helper to manage leagues.json
def load_leagues_data():
    if not os.path.exists(LEAGUES_FILE):
        p_list = load_user_list(PLANTILLA_FILE)
        m_list = load_user_list(MERCADO_FILE)
        initial_data = {
            "active": "Liga Principal",
            "leagues": {
                "Liga Principal": {
                    "plantilla": p_list,
                    "mercado": m_list
                }
            }
        }
        save_leagues_data(initial_data)
        return initial_data
    
    try:
        with open(LEAGUES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        p_list = load_user_list(PLANTILLA_FILE)
        m_list = load_user_list(MERCADO_FILE)
        return {
            "active": "Liga Principal",
            "leagues": {
                "Liga Principal": {
                    "plantilla": p_list,
                    "mercado": m_list
                }
            }
        }

def save_leagues_data(leagues_data):
    with open(LEAGUES_FILE, 'w', encoding='utf-8') as f:
        json.dump(leagues_data, f, ensure_ascii=False, indent=2)
        
    active_name = leagues_data.get("active", "Liga Principal")
    active_league = leagues_data.get("leagues", {}).get(active_name, {"plantilla": [], "mercado": []})
    
    with open(PLANTILLA_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(active_league.get("plantilla", [])))
    with open(MERCADO_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(active_league.get("mercado", [])))

def initialize_data(force_refresh=False):
    if force_refresh or DATA_CACHE["df"] is None:
        print("[*] Inicializando base de datos desde la API de Biwenger...")
        df, teams_map, teams_raw = scrape_players()
        if df.empty:
            raise HTTPException(status_code=500, detail="No se pudo conectar con la API de Biwenger.")
        DATA_CACHE["df"] = df
        DATA_CACHE["teams_map"] = teams_map
        DATA_CACHE["teams_raw"] = teams_raw
        
        hist_df = save_snapshot(df, teams_raw)
        predictor = FantasyPredictor()
        predictor.train(hist_df)
    return DATA_CACHE["df"], DATA_CACHE["teams_map"], DATA_CACHE["teams_raw"]

@app.on_event("startup")
async def startup_event():
    try:
        load_leagues_data()
        initialize_data()
    except Exception as e:
        print(f"[!] Error en inicialización de arranque: {e}")

@app.get("/api/data")
def get_dashboard_data():
    df, _, teams_raw = initialize_data()
    
    leagues_data = load_leagues_data()
    active_name = leagues_data.get("active", "Liga Principal")
    active_league = leagues_data.get("leagues", {}).get(active_name, {"plantilla": [], "mercado": []})
    
    plantilla_names = active_league.get("plantilla", [])
    mercado_names = active_league.get("mercado", [])
    
    top_5_onces, alertas = analyze_plantilla(df, plantilla_names)
    recomendaciones = analyze_market(df, mercado_names, PRESUPUESTO)
    
    lista_db = df['Nombre'].tolist()
    plantilla_names_matched = []
    from core.utils import get_fuzzy_match
    for name in plantilla_names:
        match = get_fuzzy_match(name, lista_db)
        if match:
            plantilla_names_matched.append(match)
            
    df_plantilla = df[df['Nombre'].isin(plantilla_names_matched)].copy()
    
    predictor = FantasyPredictor()
    if predictor.load():
        if not df_plantilla.empty:
            df_plantilla['xP'] = predictor.predict(df_plantilla)
            plantilla_list = df_plantilla.to_dict('records')
        else:
            plantilla_list = []
    else:
        if not df_plantilla.empty:
            df_plantilla['xP'] = df_plantilla['Puntos_Recientes'].apply(lambda x: sum(x)/len(x) if x else 0)
            plantilla_list = df_plantilla.to_dict('records')
        else:
            plantilla_list = []

    onces_response = []
    for form_name, xp_tot, once_df in top_5_onces:
        onces_response.append({
            "formacion": form_name,
            "xp_total": float(xp_tot),
            "once": once_df.to_dict('records')
        })
        
    return {
        "active_league": active_name,
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

@app.get("/api/leagues")
def get_leagues():
    data = load_leagues_data()
    return {
        "active": data.get("active", "Liga Principal"),
        "leagues": list(data.get("leagues", {}).keys())
    }

@app.post("/api/leagues/switch")
def switch_league(payload: dict):
    target_name = payload.get("name")
    data = load_leagues_data()
    if target_name not in data.get("leagues", {}):
        raise HTTPException(status_code=404, detail="La liga especificada no existe.")
    
    data["active"] = target_name
    save_leagues_data(data)
    return {"status": "success", "active": target_name}

@app.post("/api/leagues/create")
def create_league(payload: dict):
    new_name = payload.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="El nombre de la liga no puede estar vacío.")
    
    data = load_leagues_data()
    if new_name in data.get("leagues", {}):
        raise HTTPException(status_code=400, detail="Ya existe una liga con ese nombre.")
    
    data["leagues"][new_name] = {"plantilla": [], "mercado": []}
    data["active"] = new_name
    save_leagues_data(data)
    return {"status": "success", "active": new_name}

@app.post("/api/leagues/delete")
def delete_league(payload: dict):
    target_name = payload.get("name")
    data = load_leagues_data()
    
    leagues_dict = data.get("leagues", {})
    if len(leagues_dict) <= 1:
        raise HTTPException(status_code=400, detail="No puedes eliminar la única liga disponible.")
    
    if target_name in leagues_dict:
        del leagues_dict[target_name]
        if data["active"] == target_name:
            data["active"] = list(leagues_dict.keys())[0]
        save_leagues_data(data)
        return {"status": "success", "active": data["active"]}
    
    raise HTTPException(status_code=404, detail="Liga no encontrada.")

@app.post("/api/clear")
def clear_list(payload: dict):
    target = payload.get("target")
    data = load_leagues_data()
    active_name = data.get("active", "Liga Principal")
    
    if target == "plantilla":
        data["leagues"][active_name]["plantilla"] = []
    elif target == "mercado":
        data["leagues"][active_name]["mercado"] = []
    else:
        raise HTTPException(status_code=400, detail="Target debe ser 'plantilla' o 'mercado'.")
        
    save_leagues_data(data)
    return {"status": "success"}

@app.post("/api/chat")
def chat_with_assistant(payload: dict):
    user_message = payload.get("message", "").strip()
    model_name = payload.get("model", "gemma2:2b")
    history = payload.get("history", [])

    if not user_message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    # 1. Obtener contexto en vivo de la liga activa
    dash_data = get_dashboard_data()
    active_league = dash_data.get("active_league", "Liga Principal")
    presupuesto = dash_data.get("presupuesto", 18000000)
    plantilla = dash_data.get("plantilla", [])
    mercado = dash_data.get("mercado", [])
    onces = dash_data.get("onces_ideales", [])
    alertas = dash_data.get("alertas", [])

    # Formatear contexto en texto estructurado
    plantilla_summary = ", ".join([f"{p['Nombre']} ({p['Posicion']}, {p['Equipo']}, Media: {p['Media']}, xP: {p.get('xP', 0):.1f}, Estado: {p['Estado']})" for p in plantilla]) if plantilla else "Sin jugadores en plantilla."
    mercado_summary = ", ".join([f"{p['Nombre']} ({p['Posicion']}, {p['Equipo']}, Valor: {p['Valor']:,}€, Score: {p.get('Nota_Fichaje_100', 0):.1f}/100)" for p in mercado]) if mercado else "Sin jugadores en el mercado."
    top_once_summary = f"Formación {onces[0]['formacion']} con {onces[0]['xp_total']:.1f} xP total" if onces else "No hay alineación legal suficiente."
    alertas_summary = ", ".join([f"{p['Nombre']} ({p.get('Motivo_Venta', 'Revisar')})" for p in alertas]) if alertas else "Sin alertas activas."

    context_str = f"""
DATOS DE LA LIGA ACTIVA ("{active_league}"):
- Presupuesto Disponible: {presupuesto:,} €
- Mi Plantilla Actual ({len(plantilla)} jugadores): {plantilla_summary}
- Mercado Recomendado Hoy ({len(mercado)} jugadores): {mercado_summary}
- Mejor Once Proyectado: {top_once_summary}
- Alertas de Venta Sugeridas: {alertas_summary}
"""

    system_prompt = """Eres 'Míster AI', un analista táctico experto en LaLiga Fantasy y Biwenger.
Tu objetivo es aconsejar al usuario sobre sus alineaciones, pujas de mercado, ventas y estrategia fantasy.

REGLAS DE RESPUESTA:
1. Responde siempre en español con un tono cercano, deportivo, profesional y experto.
2. Basate estrictamente en los DATOS DE LA LIGA ACTIVA proporcionados arriba para dar respuestas precisas.
3. Si el usuario te hace una pregunta totalmente ajena al fútbol o LaLiga Fantasy (ej. recetas de cocina, historia general, código informático), rehúsala amablemente en una sola frase indicando que solo estás entrenado para estrategia táctica Fantasy.
4. Sé conciso y directo (máximo 2 a 3 párrafos o puntos clave) para que sea ágil de leer.
"""

    # Construir historial para Ollama
    messages = [{"role": "system", "content": system_prompt + "\n\n" + context_str}]
    for msg in history[-6:]: # Mantener últimos 6 mensajes de conversación
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    try:
        ollama_res = requests.post(
            OLLAMA_URL,
            json={
                "model": model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.6
                }
            },
            timeout=45
        )

        if ollama_res.status_code == 200:
            res_json = ollama_res.json()
            reply = res_json.get("message", {}).get("content", "No pude generar una respuesta.")
            return {
                "status": "success",
                "reply": reply,
                "model": model_name
            }
        else:
            raise HTTPException(status_code=500, detail=f"Ollama devolvió un código de error: {ollama_res.status_code}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar con Ollama. Asegúrate de que Ollama está ejecutándose en tu PC en http://localhost:11434."
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail=f"El modelo '{model_name}' tardó demasiado en responder. Si es la primera vez que lo usas, dale unos segundos para cargar en memoria e inténtalo de nuevo."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
def refresh_data():
    try:
        df, _, _ = initialize_data(force_refresh=True)
        return {"status": "success", "message": "Datos y modelos XGBoost actualizados en tiempo real."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    data = load_leagues_data()
    active_name = data.get("active", "Liga Principal")
    active_league = data.get("leagues", {}).get(active_name, {"plantilla": [], "mercado": []})
    return {
        "active_league": active_name,
        "plantilla": active_league.get("plantilla", []),
        "mercado": active_league.get("mercado", [])
    }

@app.post("/api/config")
def save_config(config: dict):
    try:
        data = load_leagues_data()
        active_name = data.get("active", "Liga Principal")
        
        if active_name not in data["leagues"]:
            data["leagues"][active_name] = {"plantilla": [], "mercado": []}
            
        if "plantilla" in config:
            data["leagues"][active_name]["plantilla"] = config["plantilla"]
        if "mercado" in config:
            data["leagues"][active_name]["mercado"] = config["mercado"]
            
        save_leagues_data(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
