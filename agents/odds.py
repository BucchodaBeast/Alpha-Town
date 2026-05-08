import os
import json
import requests
from datetime import datetime
from agents.base import BaseAgent

class OddsAgent(BaseAgent):
    name = 'ODDS'
    personality = 'Probabilistic, never certain, always calibrated. Thinks in base rates and prediction markets. Speaks in percentage points, brier scores, and consensus divergence.'
    interval_minutes = 30

    def fetch_data(self):
        items = []

        # Metaculus API (free, no key for public questions)
        try:
            resp = requests.get(
                'https://www.metaculus.com/api2/questions/?limit=10&order_by=-hotness',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for q in data.get('results', [])[:5]:
                    items.append({
                        'source': 'metaculus',
                        'type': 'prediction',
                        'title': q.get('title', ''),
                        'community_prediction': q.get('community_prediction', {}).get('full', {}).get('q1', 'N/A'),
                        'close_time': q.get('close_time', ''),
                        'url': f"https://www.metaculus.com/questions/{q.get('id', '')}/",
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] Metaculus error: {e}")

        # Manifold Markets API (free, no key for public)
        try:
            resp = requests.get(
                'https://api.manifold.markets/v0/markets?limit=10&sort=score',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for market in data[:5]:
                    items.append({
                        'source': 'manifold',
                        'type': 'prediction_market',
                        'question': market.get('question', ''),
                        'probability': market.get('probability', 0),
                        'volume': market.get('volume', 0),
                        'creator': market.get('creatorName', ''),
                        'url': market.get('url', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] Manifold error: {e}")

        # Polymarket (public API)
        try:
            resp = requests.get(
                'https://gamma-api.polymarket.com/events?limit=10&active=true&closed=false&order=volume24hr&ascending=false',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for event in data[:5]:
                    items.append({
                        'source': 'polymarket',
                        'type': 'prediction_market',
                        'title': event.get('title', ''),
                        'volume_24h': event.get('volume24hr', 0),
                        'liquidity': event.get('liquidity', 0),
                        'url': f"https://polymarket.com/event/{event.get('slug', '')}",
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] Polymarket error: {e}")

        return items
