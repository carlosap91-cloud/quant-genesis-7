import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from tickers import MARKET_MAPPING
from quant_engine import QuantGenesisEngine
from macro_guard import MacroGuard

# Configuración Visual
st.set_page_config(page_title="Quant-Genesis 6.0", layout="wide")
st.markdown("""
<style>
    body { background-color: #0e1117; color: #e0e0e0; }
    .verdict-card {
        background: linear-gradient(135deg, #1c2128 0%, #2d333b 100%);
        padding: 25px; border-radius: 15px; border: 2px solid #00ff00;
        box-shadow: 0 4px 20px rgba(0, 255, 0, 0.3); margin-bottom: 25px;
    }
    .metric-box { 
        border: 1px solid #333; 
        padding: 15px; 
        border-radius: 10px; 
        background: #1c2128; 
        color: #ffffff !important; 
    }
</style>
""", unsafe_allow_html=True)

engine = QuantGenesisEngine()
guard = MacroGuard()

# Estado Global
us = engine.us_market_context
st.markdown(f"""
<div style="text-align:center; padding:10px; background:#000; border-bottom:1px solid #333; color:white;">
    🇺🇸 S&P500: {us.get('^GSPC',0):.2f}% | Nasdaq: {us.get('^NDX',0):.2f}% | VIX: {us.get('VIX',15):.2f}
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🎮 Centro de Mando")
    mode = st.radio("Módulo:", ["🔍 PREDICTOR TOTAL", "🧮 CALCULADORA", "💼 CARTERA"])
    market = st.selectbox("Universo", list(MARKET_MAPPING.keys()))
    tickers = MARKET_MAPPING[market]

if mode == "🔍 PREDICTOR TOTAL":
    st.title("🛡️ QUANT-GENESIS 6.0")
    
    # Initialize Session State
    if 'scan_results' not in st.session_state:
        st.session_state['scan_results'] = None

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("�️ BORRAR", type="secondary"):
            st.session_state['scan_results'] = None
            st.rerun()
            
    with c2:
        if st.button("�🚀 EJECUTAR ESCANEO GLOBAL", type="primary"):
            with st.spinner("Analizando Correlación Transatlántica..."):
                results = engine.scan_market_parallel(tickers)
                results.sort(key=lambda x: -x['final_score'])
                st.session_state['scan_results'] = results
                st.rerun()

    # Display Results from State
    if st.session_state['scan_results']:
        results = st.session_state['scan_results']
        
        # 1. THE VERDICT (Winner)
        winner = results[0]
        if winner['final_score'] >= 60:
            last_p = winner['df'].iloc[-1]['Close']
            stop, _ = engine.calculate_atr_stop(winner['df'], last_p)
            
            # Tarjeta Ganadora
            st.markdown(f"""<div class="verdict-card">
                <h2 style="color:#00ff00;">🏆 MEJOR OPCIÓN: {winner['name']}</h2>
                <h1>Score: {winner['final_score']:.1f}%</h1>
                <hr style="border-color:#444;">
                <div style="display:flex; justify-content:space-between; font-size:0.9em;">
                    <span>🌍 GLOBAL: {winner['scores']['global']}</span>
                    <span>📈 TÉCNICO: {winner['scores']['tech']}</span>
                    <span>🧠 SENTIM: {winner['scores']['sent']}</span>
                    <span>📚 HIST: {winner['scores']['hist']:.0f}</span>
                </div>
            </div>""", unsafe_allow_html=True)
            
            # Gráfico Plotly
            df_plot = winner['df'].tail(40)
            fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], 
                            high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
            fig.add_hline(y=last_p*1.02, line_dash="dash", line_color="green", annotation_text="TAKE PROFIT")
            fig.add_hline(y=stop, line_dash="dash", line_color="red", annotation_text="STOP LOSS")
            fig.update_layout(template="plotly_dark", height=400, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Entrada", f"{last_p:.2f}€")
            c2.metric("Objetivo (+2%)", f"{last_p*1.02:.2f}€")
            c3.metric("Stop ATR", f"{stop:.2f}€")
            
            st.info(f"🔌 {winner['us_impact']} | 📰 Sentimiento: {winner['sentiment_score']:.2f}")
            if winner['missing']: st.warning(f"⚠️ Alertas: {', '.join(winner['missing'])}")
        else:
            st.error("⚠️ Ningún activo supera el 60% de probabilidad. Mercado Peligroso.")

        # 2. RUNNER-UPS (Rest of opportunities > 60%)
        st.markdown("---")
        st.subheader("📋 Otras Oportunidades (El Radar)")
        
        valid_candidates = [r for r in results[1:] if r['final_score'] >= 60]
        
        if valid_candidates:
            for c in valid_candidates:
                lp = c['df'].iloc[-1]['Close']
                st_p, _ = engine.calculate_atr_stop(c['df'], lp)
                
                with st.container():
                     glob = c['scores']['global']
                     tech = c['scores']['tech']
                     sent = c['scores']['sent']
                     st.markdown(f"""
                    <div class="metric-box">
                        <strong style="font-size:1.2em;">{c['name']} ({c['ticker']})</strong>
                        <span style="float:right; color:#ffd700; font-weight:bold;">Score: {c['final_score']:.1f}%</span>
                        <div style="margin-top:5px; font-size:0.8em; color:#aaa;">
                            Glo: {glob} | Tec: {tech} | Sen: {sent}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                     c1, c2, c3 = st.columns(3)
                     c1.metric("Precio", f"{lp:.2f}€")
                     c2.metric("Stop ATR", f"{st_p:.2f}€")
                     c3.metric("Sentimiento", f"{c['sentiment_score']:.2f}")
        else:
            st.info("No hay más activos que cumplan los criterios mínimos (>60%).")

    elif st.session_state['scan_results'] is not None:
         st.warning("No se encontraron resultados válidos.")

elif mode == "🧮 CALCULADORA":
    st.header("🧮 Gestión de Riesgo Profesional")
    
    with st.expander("❓ ¿Cómo funciona esta calculadora?"):
        st.markdown("""
        **Objetivo:** No arruinarte nunca. 
        Esta herramienta te dice cuántas acciones comprar para que, si el precio cae y toca tu **Stop Loss**, solo pierdas el dinero que tú hayas decidido (normalmente el 1% de tus ahorros).
        """)

    # --- ENTRADA DE DATOS ---
    st.markdown("### 1️⃣ Datos de tu Cuenta")
    col1, col2 = st.columns(2)
    # Ahora sin mínimo de 1000€, puedes poner desde 1€
    capital = col1.number_input("Capital Total Disponible (€)", min_value=1.0, value=500.0, step=50.0)
    riesgo = col2.slider("Riesgo por operación (%)", 0.5, 3.0, 1.0, help="Se recomienda el 1% para proteger tu dinero.")

    st.markdown("---")
    st.markdown("### 2️⃣ Datos de la Operación (Copia del Predictor)")
    col3, col4 = st.columns(2)
    p_ent = col3.number_input("Precio de Compra (Entrada) €", min_value=0.01, value=202.05)
    p_stop = col4.number_input("Precio de Stop Loss (Salida) €", min_value=0.0, value=197.27)

    # --- CÁLCULO Y RESULTADOS ---
    if st.button("🧮 CALCULAR TAMAÑO DE POSICIÓN", type="primary"):
        # Euros máximos que estamos dispuestos a perder
        riesgo_eur = capital * (riesgo/100)
        # Pérdida real por cada acción comprada
        per_acc = p_ent - p_stop
        
        if per_acc > 0:
            # Cálculo de acciones (redondeado hacia abajo por seguridad)
            shares = int(riesgo_eur / per_acc)
            total_invertir = shares * p_ent
            
            st.markdown("---")
            if total_invertir > capital:
                st.error(f"⚠️ **Atención:** Para este riesgo necesitarías invertir {total_invertir:.2f}€, pero solo tienes {capital:.2f}€. El sistema te protege impidiendo una inversión superior a tus ahorros.")
            elif shares == 0:
                st.warning("⚠️ **Capital bajo:** Con este riesgo no puedes comprar ni 1 acción. Considera subir un poco el riesgo o buscar acciones más baratas.")
            else:
                st.success(f"### ✅ DEBERÍAS COMPRAR: {shares} ACCIONES")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Inversión Necesaria", f"{total_invertir:.2f} €")
                c2.metric("Riesgo en Euros", f"-{riesgo_eur:.2f} €", delta_color="inverse")
                c3.metric("Pérdida por acción", f"-{per_acc:.2f} €")
                
                st.info(f"💡 **Estrategia:** Si compras {shares} acciones y el precio cae a {p_stop:.2f}€, perderás exactamente {riesgo_eur:.2f}€. Tu capital restante será de {(capital - riesgo_eur):.2f}€.")
        else:
            st.error("❌ El Stop Loss debe ser menor al precio de compra.")