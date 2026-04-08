# LALIGA FANTASY EXPERT ASSISTANT

Herramienta analítica en Python para administrar de manera experta un equipo de LaLiga Fantasy. Extrae datos oficiales, optimiza alineaciones mediante fuerza bruta combinatoria y asesora en el mercado usando cálculos de rentabilidad y pura especulación.

## Arquitectura

- `main.py`: director del programa. Ejecutar este archivo para iniciar el dashboard.
- `scraper.py`: extrae a tiempo real los conectándose a la API oficial de Biwenger (+500 jugadores).
- `analyzer.py`: motor estadístico. Optimiza las formaciones y evalúa si una inversión es buena.
- `utils.py`: herramientas auxiliares, en especial corrección de nombres mal tecleados en los TXT.
- `mi_plantilla.txt`: carga inicial de tu equipo actual (1 nombre por línea).
- `mercado_hoy.txt`: listado de jugadores disponibles para comprar hoy.

## Instrucciones de Uso

1. Abre tu terminal.
2. Instala las dependencias necesarias: `pip install pandas requests beautifulsoup4 thefuzz tabulate`
3. Escribe los nombres de los jugadores en los .txt.
4. Ejecuta: `python main.py`

## Funcionalidades Principales

- **[TITULARES] Optimización Combinatoria de Alineaciones:** no elige un "11 inicial" basándose solo en coger a los mejores, en su lugar toma tus jugadores sanos y mediante la matemática examina CIENTOS DE MILES de combinaciones tácticas teóricas cruzando todas las formaciones posibles (4-3-3, 3-5-2, 5-4-1, etc.). Te devuelve **los 5 esquemas** que mayor puntuación Media Móvil proyectada te darán este domingo.
- **[MERCADO] Ranking Especulativo 0-100:** puntúa a los agentes libres evaluando: Forma Reciente (40%), Especulación de subida de precio a las 48h (30%) y Rentabilidad Puntuación/Coste (30%).
- **[OPERACIONES] Alertas de Fuga de Valor:** escanea tu plantilla a diario reportando caídas súbitas en bolsa (desplomes >2%) o caídas terribles de rendimiento (<70% frente a la media habitual) para que vendas y no pierdas valor económico y no arruines tu presupuesto.
