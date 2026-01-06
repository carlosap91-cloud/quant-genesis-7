import yfinance as yf
import pandas as pd
import ta
from datetime import datetime, timedelta
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

class EuroQuantAgent:
    def __init__(self):
        self.risk_per_trade = 0.015  # 1.5% max risk
        
    def fetch_data(self, ticker_symbol):
        """Fetches historical data and news for a given ticker."""
        print(f"{Fore.CYAN}Fetching data for {ticker_symbol}...")
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch 1 year of data to ensure enough for SMA200
            df = ticker.history(period="1y")
            
            if df.empty:
                print(f"{Fore.RED}No data found for {ticker_symbol}.")
                return None, None
            
            # Fetch news (basic sentiment source)
            news = ticker.news
            
            return df, news
        except Exception as e:
            print(f"{Fore.RED}Error fetching data: {e}")
            return None, None

    def calculate_technicals(self, df):
        """Calculates EMA20, SMA200, RSI, and Volume metrics."""
        df['EMA_20'] = ta.trend.EMAIndicator(close=df['Close'], window=20).ema_indicator()
        df['SMA_200'] = ta.trend.SMAIndicator(close=df['Close'], window=200).sma_indicator()
        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
        
        # Volume Moving Average (20 days)
        df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
        
        return df

    def analyze_probability(self, current_data):
        """Calculates a probability score based on technical criteria."""
        score = 0
        checks = 0
        reasons = []

        # 1. Trend Analysis
        price = current_data['Close']
        ema20 = current_data['EMA_20']
        sma200 = current_data['SMA_200']
        
        if price > ema20:
            score += 20
            reasons.append(f"Price ({price:.2f}) > EMA20 ({ema20:.2f}) (Bullish Short-term)")
        else:
            reasons.append(f"Price ({price:.2f}) < EMA20 ({ema20:.2f}) (Bearish Short-term)")
            
        if price > sma200:
            score += 20
            reasons.append(f"Price > SMA200 ({sma200:.2f}) (Bullish Long-term)")
        else:
            reasons.append(f"Price < SMA200 ({sma200:.2f}) (Bearish Long-term)")



        # 2. RSI Analysis (Ideal 55-65)
        rsi = current_data['RSI']
        if 55 <= rsi <= 65:
            score += 30
            reasons.append(f"RSI ({rsi:.2f}) is in ideal entry zone (55-65)")
        elif rsi > 70:
            score -= 10
            reasons.append(f"RSI ({rsi:.2f}) is Overbought (>70)")
        elif rsi < 30:
             reasons.append(f"RSI ({rsi:.2f}) is Oversold (<30) - Potential Rebound")
        else:
            reasons.append(f"RSI ({rsi:.2f}) is neutral")

        # 3. Volume Analysis
        vol_current = current_data['Volume']
        vol_avg = current_data['Vol_SMA_20']
        
        if vol_avg > 0:
            vol_change = (vol_current - vol_avg) / vol_avg
            if vol_change > 0.20:
                score += 30
                reasons.append(f"Volume is {vol_change*100:.1f}% above average (Strong Interest)")
            else:
                 reasons.append(f"Volume is normal ({vol_change*100:.1f}% vs avg)")
        
        return min(max(score, 0), 100), reasons

    def analyze_sentiment(self, news):
        """Basic sentiment display from news headlines."""
        print(f"\n{Fore.YELLOW}--- Sentiment Analysis (Latest News) ---")
        if not news:
            print("No recent news found via yfinance.")
            return

        for item in news[:3]: # Show top 3
            # Handle different yfinance news formats (flat vs nested)
            content = item.get('content', item)
            title = content.get('title', item.get('title', 'No Title'))
            pub_date = content.get('pubDate', item.get('providerPublishTime', 'Unknown Date'))
            
            # Format date if it's a timestamp
            if isinstance(pub_date, int):
                pub_date = datetime.fromtimestamp(pub_date).strftime('%Y-%m-%d')
                
            print(f"- [{pub_date}] {title}")
        print("------------------------------------------")

    def run_analysis(self, ticker_symbol):
        print(f"{Fore.GREEN}Starting Analysis for: {ticker_symbol} (Euro Zone)")
        
        df, news = self.fetch_data(ticker_symbol)
        if df is None:
            return

        df = self.calculate_technicals(df)
        last_row = df.iloc[-1]
        
        prob_score, technical_reasons = self.analyze_probability(last_row)
        
        # Determine specific advice
        price = last_row['Close']
        stop_loss = price * (1 - self.risk_per_trade) # 1.5% below
        
        if prob_score >= 70:
            decision = "COMPRA (BUY)"
            action_color = Fore.GREEN
        elif prob_score >= 40:
            decision = "MANTENER / OBSERVAR"
            action_color = Fore.YELLOW
        else:
            decision = "VENTA / ESPERAR FUERA"
            action_color = Fore.RED

        # Report Generation
        print("\n" + "="*50)
        print(f"{Fore.WHITE}REPORT FOR {ticker_symbol} | {datetime.now().strftime('%Y-%m-%d')}")
        print("="*50)
        
        print(f"\n{Fore.WHITE}1. RESUMEN EJECUTIVO: {action_color}{Style.BRIGHT}{decision}")
        print(f"{Fore.WHITE}2. NIVEL DE PROBABILIDAD: {action_color}{prob_score}%")
        
        print(f"\n{Fore.WHITE}3. NIVELES CLAVE:")
        print(f"   - {Fore.CYAN}Precio Actual: {price:.2f} EUR")
        print(f"   - {Fore.GREEN}Entrada Sugerida: Mercado o Pullback a {last_row['EMA_20']:.2f}")
        print(f"   - {Fore.RED}Stop-Loss (Emergencia -1.5%): {stop_loss:.2f} EUR")
        print(f"   - {Fore.MAGENTA}Resistencia (Take Profit Ref): {df['High'].tail(10).max():.2f} EUR")

        print(f"\n{Fore.WHITE}4. JUSTIFICACIÓN TÉCNICA:")
        for reason in technical_reasons:
            print(f"   - {reason}")
            
        self.analyze_sentiment(news)
        print("\n" + "="*50)

if __name__ == "__main__":
    agent = EuroQuantAgent()
    
    # Example Tickers: SAN.MC (Santander), IBE.MC (Iberdrola), SAP.DE (SAP), MC.PA (LVMH)
    target_ticker = input("Introduce el ticker (ej. SAN.MC, SAP.DE): ").strip()
    if not target_ticker:
        target_ticker = "SAN.MC" # Default to Santander for demo
        
    agent.run_analysis(target_ticker)
