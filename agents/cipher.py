import os
import json
import requests
import feedparser
from datetime import datetime
from agents.base import BaseAgent

class CipherAgent(BaseAgent):
    name = 'CIPHER'
    personality = 'Reads between lines of official statements, never takes a press release at face value. Tracks arms flows and sanctions evasion. Speaks in diplomatic subtext and power vacuum analysis.'
    interval_minutes = 60

    def fetch_data(self):
        items = []

        try:
            resp = requests.get(
                'https://api.acleddata.com/acled/read?terms=accept&limit=10&page=1',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get('data', [])[:5]:
                    items.append({
                        'source': 'acled',
                        'type': 'conflict_event',
                        'country': event.get('country', ''),
                        'region': event.get('region', ''),
                        'event_type': event.get('event_type', ''),
                        'fatalities': event.get('fatalities', 0),
                        'notes': event.get('notes', '')[:300],
                        'event_date': event.get('event_date', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] ACLED error: {e}")

        try:
            resp = requests.get(
                'https://digitallibrary.un.org/search?ln=en&p=resolution&c=Voting+Data&rg=10&sort_by=rm',
                timeout=10
            )
            if resp.status_code == 200:
                items.append({
                    'source': 'un',
                    'type': 'diplomatic_signal',
                    'note': 'UN voting records accessible via digital library',
                    'url': 'https://digitallibrary.un.org/',
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] UN error: {e}")

        try:
            resp = requests.get('https://www.sipri.org/databases/armstransfers', timeout=10)
            if resp.status_code == 200:
                items.append({
                    'source': 'sipri',
                    'type': 'arms_flow',
                    'note': 'SIPRI Arms Transfers Database updated',
                    'url': 'https://www.sipri.org/databases/armstransfers',
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] SIPRI error: {e}")

        try:
            gim_feed = feedparser.parse('https://www.globalincidentmap.com/rss.aspx')
            for entry in gim_feed.entries[:5]:
                items.append({
                    'source': 'global_incident_map',
                    'type': 'security_alert',
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', '')[:300],
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] GIM error: {e}")

        return items
