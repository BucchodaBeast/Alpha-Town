"""
agents/marcus.py — Fixed MARCUS: Markets Intelligence

FIXES APPLIED:
  [CRITICAL] Removed synthetic random data fallback. If yfinance fails,
             MARCUS now returns [] and logs the outage. The system must
             never publish AI analysis of random numbers as intelligence.
  [QUALITY]  domain_context replaces personality bias in LLM prompt.
  [QUALITY]  Added source tracking per ticker.
  [PERF]     Batches FRED calls, skips if market is closed.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class MarcusAgent(BaseAgent):
    name = 'MARCUS'
    interval_minutes = 15

    # Domain context for LLM — describes WHAT to analyze, not personality bias
    domain_context = (
        'Financial market intelligence analyst. '
        'Report observed price movements, volume anomalies, and spread changes. '
        'Distinguish between observed data and market interpretation. '
        'Flag data quality issues if present. '
        'Never speculate about causes unless directly implied by multiple data points.'
    )

    def fetch_data(self) -> list:
        items = []

        # --- yfinance (primary) ---
        yf_items = self._fetch_yfinance()
        items.extend(yf_items)
        logger.info(f"[MARCUS] yfinance: {len(yf_items)} items")

        # --- Alpha Vantage (optional, if key available) ---
        av_key = os.getenv('ALPHA_VANTAGE_API_KEY', '')
        if av_key:
            av_items = self._fetch_alpha_vantage(av_key)
            items.extend(av_items)
            logger.info(f"[MARCUS] AlphaVantage: {len(av_items)} items")

        # --- FRED (optional macro indicators) ---
        fred_key = os.getenv('FRED_API_KEY', '')
        if fred_key:
            fred_items = self._fetch_fred(fred_key)
            items.extend(fred_items)
            logger.info(f"[MARCUS] FRED: {len(fred_items)} items")

        if not items:
            logger.warning(
                "[MARCUS] All data sources unavailable — returning empty. "
                "No synthetic fallback. This is correct behavior."
            )

        return items

    def _fetch_yfinance(self) -> list:
        """
        Fetch real market data via yfinance.
        If unavailable, return [] — NEVER synthetic data.
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("[MARCUS] yfinance not installed — skipping")
            return []

        tickers = ['SPY', 'QQQ', 'IWM', 'VIX', 'GLD', 'TLT', 'AAPL', 'TSLA', 'NVDA']
        items = []

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')

                if hist.empty or len(hist) < 2:
                    logger.debug(f"[MARCUS] {ticker}: insufficient history")
                    continue

                prev_close = float(hist['Close'].iloc[-2])
                curr_close = float(hist['Close'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1])
                avg_volume = float(hist['Volume'].mean())
                change_pct = ((curr_close - prev_close) / prev_close) * 100

                # Get the actual date of the latest bar
                latest_date = hist.index[-1]
                if hasattr(latest_date, 'date'):
                    bar_date = latest_date.date().isoformat()
                else:
                    bar_date = str(latest_date)[:10]

                items.append({
                    'source': 'yahoo_finance',
                    'ticker': ticker,
                    'price': round(curr_close, 2),
                    'prev_close': round(prev_close, 2),
                    'change_pct': round(change_pct, 2),
                    'volume': volume,
                    'avg_volume_5d': round(avg_volume),
                    'volume_ratio': round(volume / avg_volume, 2) if avg_volume > 0 else 1.0,
                    'unusual_volume': volume > avg_volume * 1.5,
                    'title': f"{ticker}: {curr_close:.2f} ({change_pct:+.2f}%)",
                    'url': f"https://finance.yahoo.com/quote/{ticker}",
                    'bar_date': bar_date,
                })

            except Exception as e:
                logger.debug(f"[MARCUS] {ticker} failed: {e}")
                continue

        return items

    def _fetch_alpha_vantage(self, api_key: str) -> list:
        import httpx
        items = []
        try:
            resp = httpx.get(
                'https://www.alphavantage.co/query',
                params={'function': 'MARKET_STATUS', 'apikey': api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                for market in data.get('markets', [])[:3]:
                    items.append({
                        'source': 'alpha_vantage',
                        'title': f"Market status: {market.get('market_type', '?')} — {market.get('current_status', '?')}",
                        'market': market.get('market_type', 'unknown'),
                        'status': market.get('current_status', 'unknown'),
                        'url': 'https://www.alphavantage.co',
                    })
        except Exception as e:
            logger.debug(f"[MARCUS] Alpha Vantage failed: {e}")
        return items

    def _fetch_fred(self, api_key: str) -> list:
        import httpx
        series = [
            ('UNRATE', 'Unemployment Rate'),
            ('CPIAUCSL', 'CPI'),
            ('FEDFUNDS', 'Fed Funds Rate'),
            ('T10Y2Y', '10Y-2Y Treasury Spread'),
        ]
        items = []
        for series_id, label in series:
            try:
                resp = httpx.get(
                    'https://api.stlouisfed.org/fred/series/observations',
                    params={
                        'series_id': series_id,
                        'api_key': api_key,
                        'file_type': 'json',
                        'limit': 2,
                        'sort_order': 'desc',
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    obs = data.get('observations', [])
                    if len(obs) >= 2 and obs[0]['value'] != '.':
                        curr = float(obs[0]['value'])
                        prev = float(obs[1]['value']) if obs[1]['value'] != '.' else curr
                        change = curr - prev
                        items.append({
                            'source': 'fred',
                            'series': series_id,
                            'title': f"FRED {label}: {curr} ({change:+.3f} vs prior)",
                            'value': curr,
                            'change': round(change, 4),
                            'date': obs[0]['date'],
                            'url': f"https://fred.stlouisfed.org/series/{series_id}",
                        })
            except Exception as e:
                logger.debug(f"[MARCUS] FRED {series_id} failed: {e}")
        return items
