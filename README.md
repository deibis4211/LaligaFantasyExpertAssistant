# LALIGA FANTASY EXPERT ASSISTANT

Herramienta analítica en Python para dominar LaLiga Fantasy. Utiliza Machine Learning (XGBoost) para predecir el rendimiento de los jugadores, optimiza alineaciones mediante fuerza bruta combinatoria y asesora en el mercado con métricas de rentabilidad.

## Arquitectura del Sistema

- `main.py`: ejecución de todo el sistema.
- `core/`: directorio con la lógica del sistema.
  - `model.py`: motor de ML. Implementa un regresor XGBoost.
  - `data_manager.py`: gestión de persistencia y snapshots históricos.
  - `scraper.py`: extractor de datos de la API oficial.
  - `analyzer.py`: optimizador de alineaciones y operaciones de mercado.
  - `utils.py`: utilidades y normalización de nombres (con Fuzzy Search).
- `data/`: directorio de persistencia y configuración.
  - `mi_plantilla.txt`: tu equipo actual.
  - `mercado_hoy.txt`: jugadores disponibles hoy.
  - `historico_puntos.csv`: base de datos histórica (por ahora solo desde la jornada 25).
  - `model_xgboost.pkl`: binario del modelo entrenado.

## Instrucciones de Uso

1. **Instalación de dependencias:**
   ```bash
   pip install pandas requests xgboost scikit-learn joblib thefuzz tabulate
   ```
2. **Configuración:** escribe los nombres de tus jugadores y los del mercado en sus respectivos archivos `.txt`. Gracias al sistema de **Fuzzy Search**, no es necesario que los nombres sean exactos (ej: "Aspas" coincidirá con "Iago Aspas").
3. **Ejecución:**
   ```bash
   python main.py
   ```

## Funcionalidades

- **[NUEVO] Motor de Predicción XGBoost (xP):** olvida las medias simples. El sistema entrena un modelo de IA cada vez que lo arrancas, analizando la racha reciente del jugador frente a su valor de mercado y posición para proyectar su puntuación exacta del próximo partido.
- **[TITULARES] Optimización Táctica Total:** examina miles de combinaciones tácticas cruzando todas las formaciones legales (3-4-3, 4-4-2, 5-3-2, etc.). Te ofrece el **Top 5 de Onces Ideales** que maximizan los Puntos Esperados (xP).
- **[MERCADO] Algoritmo de Fichajes Pro:** puntúa a los agentes libres de 0 a 100 evaluando: Forma Reciente (WMA 40%), Tendencia de Mercado a 48h (30%) y Ratio Rentabilidad Puntos/Precio (30%).
- **[OPERACIONES] Alertas de Fuga de Valor:** detecta automáticamente caídas de valor bursátil (>2%) o desplomes de rendimiento proyectado para recomendar ventas inmediatas y proteger tu presupuesto.