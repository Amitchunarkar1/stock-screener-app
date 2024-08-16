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
    try:
        # Define stock lists
        NIFTY50_TICKERS = [
           'ADANIENT.NS','ADANIPORTS.NS','APOLLOHOSP.NS','ASIANPAINT.NS','AXISBANK.NS','BAJAJ-AUTO.NS','BAJFINANCE.NS','BAJAJFINSV.NS','BPCL.NS','BHARTIARTL.NS','BRITANNIA.NS','CIPLA.NS','COALINDIA.NS','DIVISLAB.NS','DRREDDY.NS','EICHERMOT.NS','GRASIM.NS','HCLTECH.NS','HDFCBANK.NS','HDFCLIFE.NS','HEROMOTOCO.NS','HINDALCO.NS','HINDUNILVR.NS','ICICIBANK.NS','ITC.NS','INDUSINDBK.NS','INFY.NS','JSWSTEEL.NS','KOTAKBANK.NS','LTIM.NS','LT.NS','M&M.NS','MARUTI.NS','NTPC.NS','NESTLEIND.NS','ONGC.NS','POWERGRID.NS','RELIANCE.NS','SBILIFE.NS','SHRIRAMFIN.NS','SBIN.NS','SUNPHARMA.NS','TCS.NS','TATACONSUM.NS','TATAMOTORS.NS','TATASTEEL.NS','TECHM.NS','TITAN.NS','ULTRACEMCO.NS','WIPRO'
        ]

        ETF = [
           'TECH.NS','HDFCNIFIT.NS','IT.NS','FINIETF.NS','AXISTECETF.NS','ITBEES.NS','GSEC10IETF.NS','MON100.NS','ITETFADD.NS','ITIETF.NS','ITETF.NS','SBISILVER.NS','ABSLBANETF.NS','NIFITETF.NS','TNIDETF.NS','GSEC5IETF.NS','MAFANG.NS','SBIETFQLTY.NS','SBIETFIT.NS','GOLDCASE.NS','UTISENSETF.NS','LOWVOL1.NS','GOLD1.NS','MOHEALTH.NS','LICNMID100.NS','UTISXN50.NS','PVTBANKADD.NS','MASPTOP50.NS','IVZINNIFTY.NS','ABGSEC.NS','SILVER1.NS','NV20IETF.NS','NIFTYQLITY.NS','TATAGOLD.NS','SILVERBEES.NS','SILVRETF.NS','CONSUMBEES.NS','CONSUMIETF.NS','HDFCGROWTH.NS','ESILVER.NS','TATSILV.NS','MID150CASE.NS','GOLDIETF.NS','GOLDETF.NS','ALPL30IETF.NS','AXISILVER.NS','SDL24BEES.NS','SILVERADD.NS','GROWEV.NS','SENSEXIETF.NS','SETFGOLD.NS','QGOLDHALF.NS','GOLDBEES.NS','NV20BEES.NS','EBBETF0433.NS','HDFCGOLD.NS','SENSEXETF.NS','NIFTYIETF.NS','EGOLD.NS','NEXT50IETF.NS','GOLDSHARE.NS','MNC.NS','UTINIFTETF.NS','LTGILTBEES.NS','SENSEXADD.NS','SILVERIETF.NS','SILVER.NS','NEXT50.NS','BSLSENETFG.NS','NIFTY1.NS','NIFTY50ADD.NS','MIDSELIETF.NS','GOLDETFADD.NS','UTINEXT50.NS','GILT5YBEES.NS','EBBETF0431.NS','AXSENSEX.NS','TOP100CASE.NS','LOWVOLIETF.NS','ABSLNN50ET.NS','BSLNIFTY.NS','SDL26BEES.NS','HDFCSENSEX.NS','PSUBNKIETF.NS','ESG.NS','DIVOPPBEES.NS','BBNPPGOLD.NS','AUTOBEES.NS','SHARIABEES.NS','HDFCNEXT50.NS','AXISGOLD.NS','QNIFTY.NS','NIF100IETF.NS','SBIETFPB.NS','JUNIORBEES.NS','AUTOIETF.NS','HDFCNIF100.NS','NIF5GETF.NS','IDFNIFTYET.NS','MOMOMENTUM.NS','BSLGOLDETF.NS','NIF100BEES.NS','NIFTYBETF.NS','SETFNIF50.NS','LIQUIDCASE.NS','CONS.NS','MOMENTUM.NS','LIQUID1.NS','LIQUIDADD.NS','NIFTYETF.NS','BANKIETF.NS','LIQUIDSHRI.NS','LICNETFN50.NS','LIQUIDBEES.NS','ABSLLIQUID.NS','BFSI.NS','GSEC10YEAR.NS','LIQUIDSBI.NS','LIQUIDBETF.NS','LIQUID.NS','LIQUIDIETF.NS','LIQUIDETF.NS','HDFCSILVER.NS','UTIBANKETF.NS','HDFCLIQUID.NS','PSUBNKBEES.NS','NIFTYBEES.NS','EBBETF0430.NS','SETFNN50.NS','MONQ50.NS','EVINDIA.NS','HDFCPSUBK.NS','MONIFTY500.NS','INFRABEES.NS','EQUAL50ADD.NS','MOSMALL250.NS','IVZINGOLD.NS','HDFCNIFTY.NS','LICMFGOLD.NS','SETFNIFBK.NS','MOM30IETF.NS','LICNETFGSC.NS','AXISCETF.NS','PSUBANK.NS','BANKBETF.NS','HDFCVALUE.NS','MAHKTECH.NS','EBBETF0425.NS','MOQUALITY.NS','AXISNIFTY.NS','BSE500IETF.NS','BANKBEES.NS','SBIETFCON.NS','HDFCLOWVOL.NS','INFRAIETF.NS','ALPHA.NS','SETF10GILT.NS','MOLOWVOL.NS','LOWVOL.NS','AXISBNKETF.NS','FMCGIETF.NS','MOVALUE.NS','SBINEQWETF.NS','BANKNIFTY1.NS','QUAL30IETF.NS','NAVINIFTY.NS','HDFCMID150.NS','HNGSNGBEES.NS','NETF.NS','OILIETF.NS','MOREALTY.NS','NV20.NS','MOM100.NS','NV20.NS','PVTBANIETF.NS','BANKETF.NS','AXISBPSETF.NS','HDFCQUAL.NS','NPBET.NS','HDFCNIFBAN.NS','MOM50.NS','BBETF0432.NS','BANKETFADD.NS','PSUBANKADD.NS','HDFCMOMENT.NS','HDFCPVTBAN.NS','HDFCSML250.NS','MID150BEES.NS','ICICIB22.NS','MIDQ50ADD.NS','HDFCBSE500.NS','ABSLPSE.NS','LICNFNHGP.NS','HEALTHADD.NS','NIFMID150.NS','MIDCAPIETF.NS','BBNPNBETF.NS','MIDCAP.NS','PHARMABEES.NS','MIDCAPETF.NS','SMALLCAP.NS','HEALTHY.NS','MAKEINDIA.NS','MIDSMALL.NS','COMMOIETF.NS','MOGSEC.NS','ALPHAETF.NS','LICNETFSEN.NS','NIF10GETF.NS','AXISHCETF.NS','HEALTHIETF.NS','CPSEETF.NS','SILVERETF.NS'           
        ]

        NIFTY100_TICKERS = [
            'RELIANCE.NS',
            'TCS.NS',
            'HDFCBANK.NS',
            'INFY.NS',
            'ICICIBANK.NS',
            # Add other Nifty 100 stocks here
        ]

        AUTOMOBILE_TICKERS = [
            'BAJAJ-AUTO.NS',
            'TATAMOTORS.NS',
            'MARUTI.NS',
            # Add other Automobile stocks here
        ]

        ENERGY_TICKERS = [
            'ONGC.NS',
            'RELIANCE.NS',
            'GAIL.NS',
            # Add other Energy stocks here
        ]

        BANKING_TICKERS = [
            'SBIN.NS',
            'HDFCBANK.NS',
            'ICICIBANK.NS',
            # Add other Banking stocks here
        ]

        IT_TICKERS = [
            'TCS.NS',
            'INFY.NS',
            'WIPRO.NS',
            # Add other IT stocks here
        ]

        PHARMA_TICKERS = [
            'SUNPHARMA.NS',
            'DRREDDY.NS',
            'CIPLA.NS',
            # Add other Pharma stocks here
        ]

        # Pass static stock lists to the template
        return render_template(
            'index.html',
            nifty50_stocks=NIFTY50_TICKERS,
            nifty100_stocks=NIFTY100_TICKERS,
            automobile_stocks=AUTOMOBILE_TICKERS,
            energy_stocks=ENERGY_TICKERS,
            banking_stocks=BANKING_TICKERS,
            it_stocks=IT_TICKERS,
            etf=ETF,
            pharma_stocks=PHARMA_TICKERS
        )    
    except Exception as e:
        # Handle potential errors
        print(f"Error rendering home page: {e}")
        return "An error occurred while loading the page.", 500


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
