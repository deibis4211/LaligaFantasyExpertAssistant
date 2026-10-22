import pandas as pd

df = pd.read_csv('data/historico_aprendizaje.csv')
col_target = 'Target'

print(f'Total filas: {len(df)}')
print(f'Con Target real: {df[col_target].notna().sum()}')
print(f'Sin Target (pendientes): {df[col_target].isna().sum()}')
print()

# 1. Jugadores con Equipo Desconocido
desc_eq = df[df['Equipo'] == 'Desconocido']
print(f'=== Filas con Equipo=Desconocido: {len(desc_eq)} ===')
if not desc_eq.empty:
    resumen = desc_eq[['Nombre', 'Posicion', 'Equipo', 'Rival', 'WMA', 'Target']].drop_duplicates(subset='Nombre')
    print(resumen.to_string(index=False))
else:
    print('Ninguna')

print()

# 2. Jugadores con Rival Desconocido pero WMA real (no cold-start)
desc_rival = df[(df['Rival'] == 'Desconocido') & (df['WMA'] > 0)]
print(f'=== Filas con Rival=Desconocido y WMA>0 (datos reales sin rival): {len(desc_rival)} ===')
if not desc_rival.empty:
    resumen2 = desc_rival[['Nombre', 'Posicion', 'Equipo', 'WMA', 'Localia', 'Target']].drop_duplicates(subset='Nombre')
    print(resumen2.to_string(index=False))
else:
    print('Ninguna')

print()

# 3. Distribución de equipos en el dataset
print('=== Distribución de equipos (Top 25) ===')
print(df['Equipo'].value_counts().head(25).to_string())

print()

# 4. Distribución de rivales
print('=== Rivales más comunes ===')
print(df['Rival'].value_counts().head(10).to_string())
