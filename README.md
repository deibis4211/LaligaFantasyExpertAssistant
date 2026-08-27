# ⚽ LALIGA FANTASY EXPERT ASSISTANT

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Machine Learning](https://img.shields.io/badge/ML-XGBoost-orange.svg)

Herramienta analítica avanzada en Python para dominar en **LaLiga Fantasy**. Utiliza Machine Learning (XGBoost) para predecir el rendimiento de los jugadores, optimiza tus alineaciones mediante fuerza bruta combinatoria y te asesora en el mercado con métricas matemáticas de rentabilidad.

---

## 🚀 Funcionalidades Principales

- 🧠 **Motor de Predicción XGBoost (xP):** Olvida las medias simples. El sistema entrena un modelo de IA en tiempo real cada vez que lo arrancas. Analiza la racha reciente del jugador, su valor de mercado y posición para proyectar su puntuación exacta del próximo partido.
- 📋 **Optimización Táctica Total:** Examina miles de combinaciones tácticas cruzando todas las formaciones legales (3-4-3, 4-4-2, 5-3-2, etc.). Te ofrece el **Top 5 de Onces Ideales** que maximizan los Puntos Esperados (xP).
- 🛒 **Algoritmo de Fichajes:** Puntúa a los jugadores disponibles en el mercado de 0 a 100 evaluando tres factores clave: 
  - Forma Reciente (WMA 40%)
  - Tendencia de Mercado a 48h (30%)
  - Ratio de Rentabilidad Puntos/Precio (30%)
- 🚨 **Alertas de Fuga de Valor:** Detecta automáticamente caídas de valor bruscas (>2%) o desplomes de rendimiento proyectado para recomendarte ventas inmediatas y proteger tu presupuesto.

---

## 🏗️ Arquitectura del Sistema

```text
📁 fantasy/
├── 📄 main.py               # Ejecución principal del sistema
├── 📁 core/                 # Lógica principal
│   ├── model.py             # Motor de ML (XGBoost Regressor)
│   ├── data_manager.py      # Gestión de persistencia y snapshots
│   ├── scraper.py           # Extractor de datos de la API oficial
│   ├── analyzer.py          # Optimizador de alineaciones y mercado
│   └── utils.py             # Utilidades y búsqueda difusa (Fuzzy Search)
├── 📁 data/                 # Directorio de datos locales
│   ├── mi_plantilla.txt     # [Tu equipo actual]
│   └── mercado_hoy.txt      # [Jugadores en tu mercado]
└── 📄 README.md             # Documentación
```

---

## ⚙️ Instrucciones de Uso

### 1. Instalación de dependencias
Asegúrate de tener Python instalado y ejecuta:
```bash
pip install pandas requests xgboost scikit-learn joblib thefuzz tabulate
```

### 2. Configuración de tus datos
Dentro de la carpeta `data/`, edita los siguientes archivos (si no existen, el programa los creará vacíos la primera vez):
- `mi_plantilla.txt`: Escribe el nombre de los jugadores de tu equipo actual (uno por línea).
- `mercado_hoy.txt`: Escribe los nombres de los jugadores que están libres en tu mercado hoy.

> **💡 Nota sobre los nombres:** 
> Gracias al sistema de **Fuzzy Search**, no es estrictamente necesario que los nombres sean exactos. Por ejemplo, escribir "Aspas" coincidirá automáticamente con "Iago Aspas" de la base de datos oficial. Sin embargo, asegúrate de utilizar el nombre/apellido correcto (ej. "Swedberg" en lugar de "Wiliot").

### 3. Ejecución
Inicia el asistente ejecutando el archivo principal:
```bash
python main.py
```

---

## 📜 Licencia

Este proyecto está licenciado bajo la **GNU General Public License v3.0 (GPLv3)**. 
Esto significa que puedes usar, modificar y distribuir el código de forma gratuita, incluso comercialmente, pero cualquier software derivado o modificado a partir de este **debe** distribuirse bajo la misma licencia y compartir su código fuente.

Consulta el archivo [LICENSE](LICENSE) para más detalles.