import pandas as pd

df = pd.read_csv('data/historico_aprendizaje.csv')
antes = len(df)
print(f'Filas antes de limpieza: {antes}')

# 1. Eliminar jugadores sin equipo real
mask_equipo = df['Equipo'] == 'Desconocido'
print(f'  - Filas con Equipo=Desconocido: {mask_equipo.sum()}')

# 2. Eliminar jugadores con posicion UNK (entrenadores, datos corruptos)
mask_posicion = df['Posicion'].astype(str) == 'UNK'
print(f'  - Filas con Posicion=UNK (entrenadores etc.): {mask_posicion.sum()}')

# 3. Targets negativos (puntuaciones negativas en Biwenger son válidas pero extremas; revisar)
mask_neg_target = df['Target'] < -5
print(f'  - Filas con Target < -5 (outliers extremos): {mask_neg_target.sum()}')

# Aplicar limpieza
df_clean = df[~mask_equipo & ~mask_posicion & ~mask_neg_target].copy()

print(f'\nFilas eliminadas total: {antes - len(df_clean)}')
print(f'Filas resultantes: {len(df_clean)}')
print(f'  Con Target real: {df_clean["Target"].notna().sum()}')
print(f'  Sin Target (pendientes): {df_clean["Target"].isna().sum()}')

print('\nDistribucion de posiciones tras limpieza:')
print(df_clean['Posicion'].value_counts().to_string())

print('\nEquipos presentes:')
print(sorted(df_clean['Equipo'].unique()))

# Guardar
df_clean.to_csv('data/historico_aprendizaje.csv', index=False)
print('\n[OK] historico_aprendizaje.csv actualizado y limpio.')
