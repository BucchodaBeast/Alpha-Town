import os
import json
import requests
from datetime import datetime
from agents.base import BaseAgent

class ParcelAgent(BaseAgent):
    name = 'PARCEL'
    personality = 'Thinks in decades, sees every building permit as a 30-year bet. Reads zoning maps like fortune tellers read palms. Speaks in cap rates, absorption rates, and demographic destiny.'
    interval_minutes = 120

    def fetch_data(self):
        items = []

        # Census Bureau building permits (public API)
        try:
            resp = requests.get(
                'https://api.census.gov/data/2023/cbp?get=NAME,EMP,ESTAB&for=state:*&key=',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                # Parse header + data rows
                if len(data) > 1:
                    for row in data[1:6]:
                        items.append({
                            'source': 'census',
                            'type': 'business_patterns',
                            'state': row[0],
                            'employees': row[1],
                            'establishments': row[2],
                            'timestamp': datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"[{self.name}] Census error: {e}")

        # FHFA House Price Index
        try:
            resp = requests.get(
                'https://www.fhfa.gov/DataTools/Downloads/Documents/HPI/HPI_master.csv',
                timeout=15
            )
            if resp.status_code == 200:
                lines = resp.text.split('\n')
                if len(lines) > 1:
                    # Get most recent entries
                    header = lines[0]
                    recent = lines[-5:]
                    for line in recent:
                        if line.strip():
                            cols = line.split(',')
                            if len(cols) > 5:
                                items.append({
                                    'source': 'fhfa',
                                    'type': 'price_index',
                                    'region': cols[1] if len(cols) > 1 else 'unknown',
                                    'index_value': cols[5] if len(cols) > 5 else '0',
                                    'period': cols[3] if len(cols) > 3 else '',
                                    'timestamp': datetime.utcnow().isoformat()
                                })
        except Exception as e:
            print(f"[{self.name}] FHFA error: {e}")

        # Zillow Research data (free CSV)
        try:
            resp = requests.get(
                'https://files.zillowstatic.com/research/public_csvs/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv',
                timeout=15
            )
            if resp.status_code == 200:
                lines = resp.text.split('\n')
                if len(lines) > 1:
                    header = lines[0].split(',')
                    latest_month = header[-1] if header else 'unknown'
                    for line in lines[1:6]:
                        if line.strip():
                            cols = line.split(',')
                            if len(cols) > 5:
                                items.append({
                                    'source': 'zillow',
                                    'type': 'home_value',
                                    'region': cols[1] if len(cols) > 1 else 'unknown',
                                    'latest_value': cols[-1] if cols[-1] else '0',
                                    'month': latest_month,
                                    'timestamp': datetime.utcnow().isoformat()
                                })
        except Exception as e:
            print(f"[{self.name}] Zillow error: {e}")

        return items
