from flask import Flask, render_template, request
import yfinance as yf
import sqlite3
import pandas as pd

app = Flask(__name__)

# Create an in-memory SQLite database to cache the results
conn = sqlite3.connect(':memory:', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        latest_price REAL,
        percent_change REAL,
        asset_size REAL,
        nav REAL,
        return_1wk REAL,
        return_1mth REAL,
        return_3mth REAL,
        return_6mth REAL,
        return_1yr REAL,
        return_2yr REAL,
        return_3yr REAL,
        return_5yr REAL,
        return_max REAL,
        rsi REAL,
        macd REAL,
        volume REAL,
        sma REAL,
        ema REAL,
        week52_high REAL,
        week52_low REAL
    )
''')
conn.commit()

def calculate_rsi(data, window=14):
    delta = data['Close'].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_macd(data, short_window=12, long_window=26, signal=9):
    short_ema = data['Close'].ewm(span=short_window, adjust=False).mean()
    long_ema = data['Close'].ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]

@app.route('/')
def home():
    print("Rendering home page.")
    return render_template('index.html')

@app.route('/screener', methods=['POST'])
def screener():
    tickers = request.form.get('tickers').replace(' ', '').split(',')
    print(f"Received tickers: {tickers}")

    stock_data = []

    for ticker in tickers:
        print(f"Processing ticker: {ticker}")
        c.execute('SELECT * FROM stocks WHERE symbol=?', (ticker,))
        cached_data = c.fetchone()

        if cached_data:
            print(f"Found cached data for {ticker}: {cached_data}")
            stock_data.append({
                'symbol': cached_data[0],
                'latest_price': cached_data[1],
                'percent_change': cached_data[2],
                'asset_size': cached_data[3],
                'nav': cached_data[4],
                'return_1wk': cached_data[5],
                'return_1mth': cached_data[6],
                'return_3mth': cached_data[7],
                'return_6mth': cached_data[8],
                'return_1yr': cached_data[9],
                'return_2yr': cached_data[10],
                'return_3yr': cached_data[11],
                'return_5yr': cached_data[12],
                'return_max': cached_data[13],
                'rsi': cached_data[14],
                'macd': cached_data[15],
                'volume': cached_data[16],
                'sma': cached_data[17],
                'ema': cached_data[18],
                'week52_high': cached_data[19],
                'week52_low': cached_data[20]
            })
        else:
            print(f"No cached data for {ticker}. Fetching from Yahoo Finance...")
            stock_info = yf.Ticker(ticker)
            hist = stock_info.history(period="max")

            if not hist.empty:
                latest_price = hist['Close'][-1]
                percent_change = (hist['Close'][-1] - hist['Close'][-2]) / hist['Close'][-2] * 100
                asset_size = 1000  # Dummy data for Asset Size, replace with actual logic
                nav = latest_price  # Dummy data for NAV, replace with actual logic

                def calculate_return(period):
                    if len(hist) > period:
                        return (hist['Close'][-1] - hist['Close'][-period]) / hist['Close'][-period] * 100
                    return None

                returns = {
                    '1wk': calculate_return(5),
                    '1mth': calculate_return(21),
                    '3mth': calculate_return(63),
                    '6mth': calculate_return(126),
                    '1yr': calculate_return(252),
                    '2yr': calculate_return(504),
                    '3yr': calculate_return(756),
                    '5yr': calculate_return(1260),
                    'max': calculate_return(len(hist) - 1) if len(hist) > 1 else None
                }

                rsi = calculate_rsi(hist)
                macd, signal_line = calculate_macd(hist)
                volume = hist['Volume'][-1]
                sma = hist['Close'].rolling(window=50).mean().iloc[-1]
                ema = hist['Close'].ewm(span=50).mean().iloc[-1]
                week52_high = hist['Close'].rolling(window=252).max().iloc[-1]
                week52_low = hist['Close'].rolling(window=252).min().iloc[-1]

                print(f"Fetched data for {ticker}: Latest Price: {latest_price}, Percent Change: {percent_change}")

                c.execute('''
                    INSERT OR REPLACE INTO stocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (ticker, latest_price, percent_change, asset_size, nav, returns['1wk'], returns['1mth'], 
                      returns['3mth'], returns['6mth'], returns['1yr'], returns['2yr'], returns['3yr'], 
                      returns['5yr'], returns['max'], rsi, macd, volume, sma, ema, week52_high, week52_low))
                conn.commit()

                stock_data.append({
                    'symbol': ticker,
                    'latest_price': latest_price,
                    'percent_change': percent_change,
                    'asset_size': asset_size,
                    'nav': nav,
                    'return_1wk': returns['1wk'],
                    'return_1mth': returns['1mth'],
                    'return_3mth': returns['3mth'],
                    'return_6mth': returns['6mth'],
                    'return_1yr': returns['1yr'],
                    'return_2yr': returns['2yr'],
                    'return_3yr': returns['3yr'],
                    'return_5yr': returns['5yr'],
                    'return_max': returns['max'],
                    'rsi': rsi,
                    'macd': macd,
                    'volume': volume,
                    'sma': sma,
                    'ema': ema,
                    'week52_high': week52_high,
                    'week52_low': week52_low
                })

    print("Rendering results page.")
    return render_template('results.html', stock_data=stock_data)

if __name__ == '__main__':
    print("Starting Flask app.")
    app.run(debug=True)
