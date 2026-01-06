# Agente de Inversión Cuantitativa (Mercado Europeo)

Este proyecto tiene como objetivo construir un agente automatizado que asista en la toma de decisiones de inversión en el mercado europeo, siguiendo estrictos criterios técnicos y de gestión de riesgo.

## Objetivos
*   **Mercado:** Europa (Euronext, DAX, IBEX 35). Moneda: EUR.
*   **Meta:** Libertad financiera para Enero 2026.
*   **Estrategia:** Técnica (Tendencia, RSI, Volumen) + Sentimiento (Noticias).

## Stack Tecnológico Propuesto
*   **Lenguaje:** Python
*   **Datos de Mercado:** `yfinance` (Yahoo Finance)
*   **Análisis Técnico:** `pandas`, `ta` (Technical Analysis library)
*   **Noticias:** Web Scraping / News API
*   **Interfaz:** CLI (Línea de comandos) o Dashboard Web (Streamlit)

## Estado
*   [x] Definición del System Prompt (`system_prompt.md`)
*   [ ] Implementación del script de análisis técnico
*   [ ] Integración de análisis de noticias
*   [ ] Configuración de parámetros de riesgo
