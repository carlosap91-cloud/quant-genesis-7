import pandas as pd
import os
from datetime import datetime

PORTFOLIO_FILE = "portfolio.csv"

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return pd.DataFrame(columns=["Ticker", "Buy_Date", "Buy_Price", "Amount_EUR"])
    return pd.read_csv(PORTFOLIO_FILE)

def add_trade(ticker, price, amount):
    df = load_portfolio()
    new_trade = pd.DataFrame([{
        "Ticker": ticker,
        "Buy_Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Buy_Price": float(price),
        "Amount_EUR": float(amount)
    }])
    df = pd.concat([df, new_trade], ignore_index=True)
    df.to_csv(PORTFOLIO_FILE, index=False)
    return df

def remove_trade(index):
    df = load_portfolio()
    if 0 <= index < len(df):
        df = df.drop(index).reset_index(drop=True)
        df.to_csv(PORTFOLIO_FILE, index=False)
    return df
