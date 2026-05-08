import os
import json
import requests
from datetime import datetime
from agents.base import BaseAgent

class HullAgent(BaseAgent):
    name = 'HULL'
    personality = 'Old school, reads the physical world, does not trust paper. Knows every shipping lane by heart. Speaks in deadweight tonnage, port calls, and bunker prices.'
    interval_minutes = 60

    def fetch_data(self):
        items = []

        # UN Comtrade (free, public API)
        try:
            resp = requests.get(
                'https://comtrade.un.org/api/get?ps=recent&r=all&p=0&rg=all&fmt=json',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                dataset = data.get('dataset', [])[:5]
                for row in dataset:
                    items.append({
                        'source': 'un_comtrade',
                        'type': 'trade_flow',
                        'reporter': row.get('rtTitle', ''),
                        'commodity': row.get('cmdDescE', ''),
                        'value': row.get('TradeValue', 0),
                        'period': row.get('period', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] UN Comtrade error: {e}")

        # World Bank commodity prices
        try:
            commodities = ['CRUDE_BRENT', 'CRUDE_WTI', 'GOLD', 'COPPER']
            for comm in commodities:
                resp = requests.get(
                    f'https://api.worldbank.org/v2/country/all/indicator/{comm}?format=json&date=2023:2024&per_page=2',
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1 and data[1]:
                        latest = data[1][0]
                        items.append({
                            'source': 'world_bank',
                            'type': 'commodity_price',
                            'commodity': comm,
                            'value': latest.get('value', 0),
                            'date': latest.get('date', ''),
                            'timestamp': datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"[{self.name}] World Bank error: {e}")

        # MarineTraffic free AIS (limited, via public page)
        try:
            resp = requests.get('https://www.marinetraffic.com/en/ais/home/centerx:0/centery:0/zoom:4', timeout=10)
            if resp.status_code == 200:
                items.append({
                    'source': 'marinetraffic',
                    'type': 'ais_status',
                    'note': 'Global AIS tracking active',
                    'url': 'https://www.marinetraffic.com',
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] MarineTraffic error: {e}")

        return items
