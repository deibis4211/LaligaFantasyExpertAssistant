# LALIGA FANTASY EXPERT ASSISTANT

Herramienta analítica premium en Python para dominar LaLiga Fantasy. Utiliza Machine Learning (XGBoost) para predecir el rendimiento de los jugadores, optimiza alineaciones mediante fuerza bruta combinatoria y asesora en el mercado con métricas avanzadas de rentabilidad.

## Arquitectura del Sistema

- `main.py`: Director de orquesta. Orquestra la descarga, entrenamiento e inferencia.
- `core/`: Directorio con la lógica del sistema.
  - `model.py`: **Motor de ML**. Implementa un regresor XGBoost.
  - `data_manager.py`: Gestión de persistencia y snapshots históricos.
  - `scraper.py`: Extractor de datos de la API oficial.
  - `analyzer.py`: Cerebro estratégico y optimizador de alineaciones.
  - `utils.py`: Utilidades y normalización de nombres.
- `data/`: Directorio de persistencia y configuración.
  - `mi_plantilla.txt`: Tu equipo actual.
  - `mercado_hoy.txt`: Jugadores disponibles hoy.
  - `historico_puntos.csv`: Base de datos histórica.
  - `model_xgboost.pkl`: Binario del modelo entrenado.

## Instrucciones de Uso

1. **Instalación de dependencias:**
   ```bash
   pip install pandas requests xgboost scikit-learn joblib thefuzz tabulate
   ```
2. **Configuración:** Escribe los nombres de tus jugadores y los del mercado en sus respectivos archivos `.txt`.
3. **Ejecución:**
   ```bash
   python main.py
   ```

## Funcionalidades de Élite

- **[NUEVO] Motor de Predicción XGBoost (xP):** Olvida las medias simples. El sistema entrena un modelo de IA cada vez que lo arrancas, analizando la racha reciente del jugador frente a su valor de mercado y posición para proyectar su puntuación exacta del próximo partido.
- **[TITULARES] Optimización Táctica Total:** Examina miles de combinaciones tácticas cruzando todas las formaciones legales (3-4-3, 4-4-2, 5-3-2, etc.). Te ofrece el **Top 5 de Onces Ideales** que maximizan los Puntos Esperados (xP).
- **[MERCADO] Algoritmo de Fichajes Pro:** Puntúa a los agentes libres de 0 a 100 evaluando: Forma Reciente (WMA 40%), Tendencia de Mercado a 48h (30%) y Ratio Rentabilidad Puntos/Precio (30%).
- **[OPERACIONES] Alertas de Fuga de Valor:** Detecta automáticamente caídas de valor bursátil (>2%) o desplomes de rendimiento proyectado para recomendar ventas inmediatas y proteger tu presupuesto.

---
*Que la estadística esté de tu lado esta jornada.*
