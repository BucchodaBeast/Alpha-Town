import os
import json
import requests
from datetime import datetime
from agents.base import BaseAgent

class GaiaAgent(BaseAgent):
    name = 'GAIA'
    personality = 'Long view, connects today data to decade-long trajectories. Sees tipping points before they tip. Speaks in anomalies, feedback loops, and paleoclimate analogues.'
    interval_minutes = 60

    def fetch_data(self):
        items = []

        # NOAA API (free, requires key)
        noaa_key = os.getenv('NOAA_API_KEY')
        if noaa_key:
            try:
                # Recent weather alerts
                resp = requests.get(
                    f'https://api.weather.gov/alerts/active?status=actual&message_type=alert',
                    timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for alert in data.get('features', [])[:5]:
                        props = alert.get('properties', {})
                        items.append({
                            'source': 'noaa',
                            'type': 'weather_alert',
                            'event': props.get('event', ''),
                            'severity': props.get('severity', ''),
                            'area': props.get('areaDesc', ''),
                            'headline': props.get('headline', ''),
                            'effective': props.get('effective', ''),
                            'timestamp': datetime.utcnow().isoformat()
                        })
            except Exception as e:
                print(f"[{self.name}] NOAA error: {e}")

        # USGS Earthquakes (public, no key)
        try:
            resp = requests.get(
                'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson',
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for feature in data.get('features', [])[:5]:
                    props = feature.get('properties', {})
                    items.append({
                        'source': 'usgs',
                        'type': 'earthquake',
                        'magnitude': props.get('mag', 0),
                        'place': props.get('place', ''),
                        'time': props.get('time', ''),
                        'tsunami': props.get('tsunami', 0),
                        'url': props.get('url', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] USGS error: {e}")

        # OpenAQ air quality (public, no key for basic)
        try:
            resp = requests.get(
                'https://api.openaq.org/v2/latest?limit=10&page=1&offset=0&sort=desc&radius=1000&order_by=lastUpdated&dumpRaw=false',
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for result in data.get('results', [])[:5]:
                    measurements = result.get('measurements', [])
                    pm25 = next((m for m in measurements if m.get('parameter') == 'pm25'), None)
                    if pm25:
                        items.append({
                            'source': 'openaq',
                            'type': 'air_quality',
                            'city': result.get('city', ''),
                            'country': result.get('country', ''),
                            'pm25': pm25.get('value', 0),
                            'unit': pm25.get('unit', ''),
                            'last_updated': result.get('lastUpdated', ''),
                            'timestamp': datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"[{self.name}] OpenAQ error: {e}")

        # NASA EarthData (public events)
        try:
            resp = requests.get('https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=5', timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get('events', [])[:5]:
                    items.append({
                        'source': 'nasa_eonet',
                        'type': 'environmental_event',
                        'title': event.get('title', ''),
                        'categories': [c.get('title', '') for c in event.get('categories', [])],
                        'geometry_count': len(event.get('geometry', [])),
                        'url': event.get('sources', [{}])[0].get('url', '') if event.get('sources') else '',
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] NASA EONET error: {e}")

        return items
