import os
import json
import requests
from datetime import datetime, timedelta
from agents.base import BaseAgent

class MarcusAgent(BaseAgent):
    name = 'MARCUS'
    personality = 'Cold, precise, never wrong about what the data says. Wrong about what it means. Speaks in clipped, data-dense sentences. Treats market sentiment as a disease to be diagnosed.'
    interval_minutes = 15

    def fetch_data(self):
        items = []

        # Yahoo Finance via yfinance (mock data if unavailable)
        try:
            import yfinance as yf
            tickers = ['SPY', 'QQQ', 'IWM', 'VIX', 'GLD', 'TLT', 'AAPL', 'TSLA', 'NVDA']
            for ticker in tickers:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='2d')
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    curr_close = hist['Close'].iloc[-1]
                    volume = hist['Volume'].iloc[-1]
                    change_pct = ((curr_close - prev_close) / prev_close) * 100
                    items.append({
                        'source': 'yahoo_finance',
                        'ticker': ticker,
                        'price': round(curr_close, 2),
                        'change_pct': round(change_pct, 2),
                        'volume': int(volume),
                        'unusual_volume': volume > hist['Volume'].mean() * 1.5,
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] yfinance error: {e}")
            # Fallback: generate synthetic market data for demo
            import random
            for ticker in ['SPY', 'QQQ', 'VIX']:
                items.append({
                    'source': 'yahoo_finance_fallback',
                    'ticker': ticker,
                    'price': round(random.uniform(100, 500), 2),
                    'change_pct': round(random.uniform(-3, 3), 2),
                    'volume': int(random.uniform(1000000, 50000000)),
                    'unusual_volume': random.random() > 0.7,
                    'timestamp': datetime.utcnow().isoformat()
                })

        # Alpha Vantage (free tier - market overview)
        av_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if av_key:
            try:
                resp = requests.get(
                    f'https://www.alphavantage.co/query?function=MARKET_STATUS&apikey={av_key}',
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if 'markets' in data:
                        for market in data['markets'][:3]:
                            items.append({
                                'source': 'alpha_vantage',
                                'market': market.get('market_type', 'unknown'),
                                'status': market.get('current_status', 'unknown'),
                                'note': market.get('notes', ''),
                                'timestamp': datetime.utcnow().isoformat()
                            })
            except Exception as e:
                print(f"[{self.name}] Alpha Vantage error: {e}")

        # FRED Economic Data
        fred_key = os.getenv('FRED_API_KEY')
        if fred_key:
            try:
                series = ['UNRATE', 'CPIAUCSL', 'FEDFUNDS', 'T10Y2Y']
                for s in series:
                    resp = requests.get(
                        f'https://api.stlouisfed.org/fred/series/observations?series_id={s}&api_key={fred_key}&file_type=json&limit=2&sort_order=desc',
                        timeout=10
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if 'observations' in data and len(data['observations']) >= 2:
                            latest = data['observations'][0]
                            prev = data['observations'][1]
                            items.append({
                                'source': 'fred',
                                'series': s,
                                'value': latest['value'],
                                'date': latest['date'],
                                'change': round(float(latest['value']) - float(prev['value']), 4) if latest['value'] != '.' else 0,
                                'timestamp': datetime.utcnow().isoformat()
                            })
            except Exception as e:
                print(f"[{self.name}] FRED error: {e}")

        return items
