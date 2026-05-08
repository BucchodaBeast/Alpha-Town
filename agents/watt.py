import os
import json
import requests
from datetime import datetime
from agents.base import BaseAgent

class WattAgent(BaseAgent):
    name = 'WATT'
    personality = 'Systems thinker, understands that energy is the only real currency. Sees grid stress before operators do. Speaks in load factors, baseload, and marginal costs.'
    interval_minutes = 60

    def fetch_data(self):
        items = []

        # EIA API (free, requires key)
        eia_key = os.getenv('EIA_API_KEY')
        if eia_key:
            try:
                # Electricity generation by source
                resp = requests.get(
                    f'https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/?frequency=hourly&data[0]=value&facets[respondent][]=US48&start={datetime.utcnow().strftime("%Y-%m-%d")}T00&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=10&api_key={eia_key}',
                    timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for row in data.get('response', {}).get('data', [])[:5]:
                        items.append({
                            'source': 'eia',
                            'type': 'grid_data',
                            'fuel_type': row.get('fueltype', 'unknown'),
                            'value_mwh': row.get('value', 0),
                            'period': row.get('period', ''),
                            'timestamp': datetime.utcnow().isoformat()
                        })
            except Exception as e:
                print(f"[{self.name}] EIA error: {e}")

        # Global Power Plant Database (public CSV via API proxy)
        try:
            resp = requests.get('https://wri-dataportal-prod.s3.amazonaws.com/manual/global_power_plant_database_v_1_3.zip', timeout=10)
            if resp.status_code == 200:
                items.append({
                    'source': 'wri_power_plants',
                    'type': 'database_update',
                    'note': 'Global Power Plant Database accessible',
                    'url': 'https://datasets.wri.org/dataset/globalpowerplantdatabase',
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] WRI error: {e}")

        # ENTSO-E transparency (public, no key for some endpoints)
        try:
            resp = requests.get(
                'https://transparency.entsoe.eu/api?documentType=A65&processType=A16&outBiddingZone_Domain=10Y1001A1001A82H&periodStart=202401010000&periodEnd=202401020000&securityToken=',
                timeout=10
            )
            if resp.status_code == 200:
                items.append({
                    'source': 'entsoe',
                    'type': 'grid_transparency',
                    'note': 'ENTSO-E grid data available',
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] ENTSO-E error: {e}")

        return items
