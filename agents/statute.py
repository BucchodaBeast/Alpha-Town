import os
import json
import requests
import feedparser
from datetime import datetime
from agents.base import BaseAgent

class StatuteAgent(BaseAgent):
    name = 'STATUTE'
    personality = 'Bureaucratic on the surface, devastating in implication. Reads regulatory filings like crime scene evidence. Knows that Friday 5pm is when they bury the bodies.'
    interval_minutes = 120

    def fetch_data(self):
        items = []

        # Federal Register API (free, no key)
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            resp = requests.get(
                f'https://www.federalregister.gov/api/v1/documents.json?conditions[publication_date][is]={today}&per_page=10',
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for doc in data.get('results', [])[:5]:
                    items.append({
                        'source': 'federal_register',
                        'type': 'regulation',
                        'title': doc.get('title', ''),
                        'agency': ', '.join([a.get('name', '') for a in doc.get('agencies', [])[:2]]),
                        'type_name': doc.get('type', ''),
                        'page_count': doc.get('page_length', 0),
                        'url': doc.get('html_url', ''),
                        'published': doc.get('publication_date', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] Federal Register error: {e}")

        # SEC EDGAR - recent filings
        try:
            sec_feed = feedparser.parse('https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&company=&type=S-1&dateb=&owner=include&count=10&output=atom')
            for entry in sec_feed.entries[:5]:
                items.append({
                    'source': 'sec_edgar',
                    'type': 'filing',
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'updated': entry.get('updated', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] SEC error: {e}")

        # EUR-Lex RSS (EU law)
        try:
            eurlex_feed = feedparser.parse('https://eur-lex.europa.eu/content/legal-notice/rss.xml')
            for entry in eurlex_feed.entries[:3]:
                items.append({
                    'source': 'eurlex',
                    'type': 'eu_regulation',
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] EUR-Lex error: {e}")

        # FTC press releases RSS
        try:
            ftc_feed = feedparser.parse('https://www.ftc.gov/news-events/news/rss.xml')
            for entry in ftc_feed.entries[:5]:
                items.append({
                    'source': 'ftc',
                    'type': 'enforcement',
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', '')[:300],
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] FTC error: {e}")

        return items
