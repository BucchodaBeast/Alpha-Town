import os
import json
import requests
import feedparser
from datetime import datetime
from agents.base import BaseAgent

class RazorAgent(BaseAgent):
    name = 'RAZOR'
    personality = 'Aggressive, contrarian, reads order flow like body language. Sees manipulation everywhere. Speaks in trading slang and military metaphors. Trusts no headline.'
    interval_minutes = 30

    def fetch_data(self):
        items = []

        # SEC EDGAR - recent Form 4 (insider trading) via RSS
        try:
            sec_feed = feedparser.parse('https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=only&count=40&output=atom')
            for entry in sec_feed.entries[:10]:
                items.append({
                    'source': 'sec_edgar',
                    'type': 'insider_filing',
                    'title': entry.get('title', ''),
                    'company': entry.get('title', '').split(' - ')[0] if ' - ' in entry.get('title', '') else 'Unknown',
                    'filing_date': entry.get('updated', ''),
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] SEC feed error: {e}")

        # FINRA short interest data (public page scrape)
        try:
            resp = requests.get('https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data', timeout=10)
            if resp.status_code == 200:
                items.append({
                    'source': 'finra',
                    'type': 'short_interest_summary',
                    'note': 'FINRA short sale volume data updated',
                    'url': 'https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data',
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] FINRA error: {e}")

        # Unusual Whales free feed (Twitter/X RSS proxy)
        try:
            uw_feed = feedparser.parse('https://nitter.net/unusual_whales/rss')
            for entry in uw_feed.entries[:5]:
                items.append({
                    'source': 'unusual_whales',
                    'type': 'options_flow',
                    'content': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] Unusual Whales error: {e}")

        return items
