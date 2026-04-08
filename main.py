from scraper import scrape_players
from analyzer import analyze_plantilla, analyze_market
from utils import load_user_list
from tabulate import tabulate

def main():
    print("="*65)
    print("LALIGA FANTASY EXPERT ASSISTANT")
    print("="*65)
    
    df = scrape_players()
    
    plantilla_file = 'mi_plantilla.txt'
    mercado_file = 'mercado_hoy.txt'
    presupuesto = 18000000
    
    plantilla = load_user_list(plantilla_file)
    mercado = load_user_list(mercado_file)
        
    print(f"[*] Jugadores leidos en plantilla: {len(plantilla)}")
    print(f"[*] Jugadores leidos en mercado: {len(mercado)}")
    
    if df.empty:
        return
        
    top_5_onces, alertas = analyze_plantilla(df, plantilla)
    recomendaciones = analyze_market(df, mercado, presupuesto)
    
    print("\n\n" + "="*65)
    print(" [TITULARES] TOP 5 FORMACIONES IDEALES PARA LA JORNADA ")
    print("="*65)
    if top_5_onces:
        print("Filtrados lesionados y sancionados. Optimizando WMA (Estado Forma).\n")
        for idx, (f_name, wma_tot, max_once) in enumerate(top_5_onces):
            print(f"--- OPCION #{idx+1} | FORMACION: {f_name} | FORMA ESPERADA (WMA): {wma_tot} pts ---")
            view_once = max_once[['Nombre', 'Equipo', 'Posicion', 'Estado', 'Media', 'WMA_Forma', 'Valor']]
            print(tabulate(view_once, headers='keys', tablefmt='psql', showindex=False))
            print() # Espacio en blanco entre onces
    else:
        print("[!] No hay jugadores suficientes en la plantilla para formar un once legal (Falta Portero o posiciones clave).")
        

    print("\n\n" + "="*65)
    print(" [MERCADO] RECOMENDACIONES DE FICHAJES (CRITERIO 100 PTS) ")
    print("="*65)
    if not recomendaciones.empty:
        view_merc = recomendaciones[['Nombre', 'Nota_Fichaje_100', 'Valor', 'Asequible', 'Tendencia_48h_pct', 'Media']]
        print(tabulate(view_merc, headers='keys', tablefmt='psql', showindex=False))
        print(f"Presupuesto Disponible: {presupuesto:,} | Formula: Forma(40) + Tend(30) + Rentab(30)")
    else:
        print("[!] El mercado esta vacio.")


    print("\n\n" + "="*65)
    print(" [OPERACIONES] ALERTAS DE VENTA RECOMENDADAS ")
    print("="*65)
    if not alertas.empty:
        view_alertas = alertas[['Nombre', 'Estado', 'Tendencia_48h_pct', 'WMA_Forma', 'Motivo_Venta']]
        print(tabulate(view_alertas, headers='keys', tablefmt='psql', showindex=False))
    else:
        print("Tu equipo actual esta sano, en forma y no pierde valor drasticamente. Todo en orden!")
        
    print("\n" + "="*65)
    print(" Proceso finalizado. Que tengas una jornada perfecta.")
    print("="*65 + "\n")

if __name__ == '__main__':
    main()
