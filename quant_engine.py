import yfinance as yf
import pandas as pd
import ta
import numpy as np
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import concurrent.futures

# --- GLOBAL MAPPING ---
US_SECTOR_MAP = {
    # Tech / Chips
    "ASML.AS": {"proxy": "SOXX", "peer": "NVDA"},
    "BESI.AS": {"proxy": "SOXX", "peer": "NVDA"},
    "STM.PA":  {"proxy": "SOXX", "peer": "AMD"},
    "SAP.DE":  {"proxy": "XLK",  "peer": "CRM"},
    "CAP.PA":  {"proxy": "XLK",  "peer": "ACN"}, # Capgemini -> Accenture
    
    # Banks
    "SAN.MC":  {"proxy": "XLF",  "peer": "JPM"},
    "BBVA.MC": {"proxy": "XLF",  "peer": "BAC"},
    "INGA.AS": {"proxy": "XLF",  "peer": "C"},
    "BNP.PA":  {"proxy": "XLF",  "peer": "MS"},
    
    # Auto
    "BMW.DE":  {"proxy": "CARZ", "peer": "TSLA"}, # CARZ is Auto ETF
    "VOW3.DE": {"proxy": "CARZ", "peer": "F"},
    "MBG.DE":  {"proxy": "CARZ", "peer": "TM"},
    
    # Retail / Fashion
    "ITX.MC":  {"proxy": "XLY", "peer": "TJX"}, # Inditex -> Consumer Disc
    "KER.PA":  {"proxy": "XLY", "peer": "NKE"}, # Kering (Luxury)
    "MC.PA":   {"proxy": "XLY", "peer": "TIF"}, 
    
    # Energy
    "TTE.PA":  {"proxy": "XLE", "peer": "XOM"},
    "REP.MC":  {"proxy": "XLE", "peer": "CVX"},
    
    # Industrial
    "SIE.DE":  {"proxy": "XLI", "peer": "GE"},
    
    # Default
    "DEFAULT": {"proxy": "SPY", "peer": "SPY"}
}

class QuantGenesisEngine:
    def __init__(self):
        self.history_years = 5
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.us_market_context = {} 
        self._load_us_context()
        
    def _load_us_context(self):
        """Loads critical US Market data at init."""
        indices = ["^GSPC", "^NDX", "^VIX", "SPY", "QQQ"] # S&P, Nasdaq, Vix, ETFs
        try:
            data = yf.download(indices, period="5d", progress=False)['Close']
            if not data.empty:
               # Get last close percent change
               last_close = data.iloc[-1]
               prev_close = data.iloc[-2]
               pct_change = ((last_close - prev_close) / prev_close) * 100
               self.us_market_context = pct_change.to_dict()
               # VIX is absolute value
               self.us_market_context['^VIX'] = last_close['^VIX']
        except:
            self.us_market_context = {}

    def fetch_deep_history(self, ticker):
        """Fetches 5 years of daily data."""
        try:
            df = yf.Ticker(ticker).history(period="5y")
            if df.empty or len(df) < 500: return None
            return df
        except:
            return None

    def fetch_news_sentiment(self, ticker_symbol):
        """Fetches news and calculates VADER compound score."""
        try:
            ticker = yf.Ticker(ticker_symbol)
            news = ticker.news
            if not news: return 0.0, []
            
            compound_sum = 0
            count = 0
            for item in news[:5]:
                content = item.get('content', item)
                title = content.get('title', item.get('title', ''))
                if title:
                    vs = self.sentiment_analyzer.polarity_scores(title)
                    compound_sum += vs['compound']
                    count += 1
            avg_score = compound_sum / count if count > 0 else 0.0
            return avg_score, news
        except:
            return 0.0, []

    def calculate_atr_stop(self, df, current_price):
        """Calculates dynamic stop loss based on ATR (Multiplier 1.2)."""
        atr_series = ta.volatility.AverageTrueRange(
            high=df['High'], low=df['Low'], close=df['Close'], window=14
        ).average_true_range()
        
        if atr_series.empty: return current_price * 0.95, 0 # Fallback
        
        atr = atr_series.iloc[-1]
        stop_price = current_price - (1.2 * atr)
        return stop_price, atr

    def analyze_current_setup(self, df):
        """Versión 4-Pilares: Retorna Tech Score (0-100)."""
        if len(df) < 200: return 0, ["Datos insuficientes"], df
        
        # Ensure indicators are calculated
        df['EMA_20'] = ta.trend.EMAIndicator(close=df['Close'], window=20).ema_indicator()
        df['SMA_200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        missing = []
        tech_score = 100 # Base Score
        
        # 1. GAP PENALTY (Max -20)
        if prev['Close'] > 0:
            gap = ((last['Open'] - prev['Close']) / prev['Close']) * 100
            if abs(gap) > 1.2:
                tech_score -= 20
                missing.append(f"Gap Excesivo ({gap:.2f}%) [-20]")
        
        # 2. FATIGUE PENALTY (Max -15)
        check_df = df.tail(5).copy()
        check_df['is_green'] = check_df['Close'] > check_df['Open']
        if check_df['is_green'].tail(4).all():
            tech_score -= 15
            missing.append("Fatiga de Tendencia (4 días verdes) [-15]")
        
        # 3. TREND FILTER (Max -30)
        if last['Close'] < last['SMA_200']:
             tech_score -= 30
             missing.append("Tendencia Bajista (Debajo SMA200) [-30]")

        # 4. RSI FILTER (Max -15)
        if last['RSI'] < 40: 
            tech_score -= 15
            missing.append(f"RSI Bajo ({last['RSI']:.1f}) [-15]")
        elif last['RSI'] > 80: 
            tech_score -= 15
            missing.append(f"RSI Extremo ({last['RSI']:.1f}) [-15]")
            
        return max(0, tech_score), missing, df

    def run_backtest_validation(self, df):
        """Simulates strategy."""
        signals = (
            (df['Close'] > df['EMA_20']) &
            (df['EMA_20'] > df['SMA_200']) &
            (df['RSI'] >= 50) & (df['RSI'] <= 70)
        )
        if not signals.any(): return 0, 0
        
        signal_indices = df.index[signals]
        wins = 0
        total_signals = 0
        future_window = 5
        cutoff = len(df) - future_window
        
        for date in signal_indices:
            idx_loc = df.index.get_loc(date)
            if idx_loc >= cutoff: continue
            
            entry = df.iloc[idx_loc]['Close']
            next_days = df.iloc[idx_loc+1 : idx_loc+1+future_window]
            max_p = next_days['High'].max()
            
            if max_p >= entry * 1.02: wins += 1
            total_signals += 1
            
        win_rate = (wins / total_signals * 100) if total_signals > 0 else 0
        return win_rate, total_signals
        
    def check_us_correlation(self, ticker):
        """
        Analyzes US Market impact (40% Weight).
        Returns: impact_score (0-100), message, sector_perf
        """
        mapping = US_SECTOR_MAP.get(ticker, US_SECTOR_MAP["DEFAULT"])
        proxy = mapping['proxy'] # ETF
        peer = mapping['peer']   # Stock
        
        # Determine Tech Sector (Nazdaq Filter)
        is_tech = proxy in ["XLK", "SOXX"]
        ndx_change = self.us_market_context.get('^NDX', 0)
        
        # SAFETY RULE: Nasdaq Crash Filter
        if is_tech and ndx_change < -1.5:
             return 0, f"⛔ BLOQUEO DE APERTURA: Nasdaq cayó un {ndx_change:.2f}% ayer.", -999

        # Get specific peer/proxy data real-time
        try: 
            us_data = yf.download([proxy, peer], period="2d", progress=False)['Close']
            if us_data.empty: return 50, "Sin datos USA", 0
            
            last = us_data.iloc[-1]
            prev = us_data.iloc[-2]
            pct_changes = ((last - prev) / prev) * 100
            
            proxy_chg = pct_changes.get(proxy, 0)
            peer_chg = pct_changes.get(peer, 0)
            
            # Correlation Score Logic
            score = 50 # Neutral base
            
            combined_perf = (proxy_chg + peer_chg) / 2
            
            if combined_perf > 1.0: score = 100 # Strong Boost
            elif combined_perf > 0.5: score = 80
            elif combined_perf > -0.5: score = 60
            elif combined_perf > -1.5: score = 30 # Drag
            else: score = 10 # Crash
            
            impact_msg = f"🇺🇸 Wall Street ({proxy}/{peer}): {combined_perf:.2f}% ayer."
            return score, impact_msg, combined_perf
            
        except:
            return 50, "Error datos USA", 0

    def analyze_ticker_parallel(self, name, ticker):
        """Worker function."""
        try:
            df = self.fetch_deep_history(ticker)
            if df is None: return None
            
            # 1. TECHNICAL PILLAR (25%)
            tech_score, missing, df_calc = self.analyze_current_setup(df)
            
            # 2. HISTORICAL PILLAR (20%)
            win_rate, occurences = self.run_backtest_validation(df_calc)
            
            # 3. SENTIMENT PILLAR (20%)
            v_score, news = self.fetch_news_sentiment(ticker)
            if v_score >= 0.3: sent_score = 100
            elif v_score >= 0.15: sent_score = 80
            elif v_score >= 0.05: sent_score = 50
            else: sent_score = 0
            
            # 4. GLOBAL PILLAR (35%)
            us_score, us_msg, us_perf = self.check_us_correlation(ticker)
            if us_score == 0: missing.append(us_msg) # Safety Block
            
            # --- FINAL CALCULATION (Weighted) ---
            # Global(35) + Tech(25) + Sent(20) + Hist(20)
            final_score = (us_score * 0.35) + (tech_score * 0.25) + (sent_score * 0.20) + (win_rate * 0.20)
            
            return {
                "name": name, 
                "ticker": ticker, 
                "df": df_calc, 
                "missing": missing, 
                "final_score": final_score,
                "scores": {
                    "global": us_score,
                    "tech": tech_score,
                    "sent": sent_score,
                    "hist": win_rate
                },
                "raw_win_rate": win_rate,
                "sentiment_score": v_score,
                "us_impact": us_msg,
                "us_perf": us_perf
            }
        except Exception as e:
            #print(f"Error {ticker}: {e}")
            return None

    def scan_market_parallel(self, tickers_dict, max_workers=10):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(self.analyze_ticker_parallel, name, ticker): ticker 
                for name, ticker in tickers_dict.items()
            }
            for future in concurrent.futures.as_completed(future_to_ticker):
                res = future.result()
                if res: results.append(res)
        return results
