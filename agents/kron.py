import os
import json
import requests
import feedparser
from datetime import datetime
from agents.base import BaseAgent

class KronAgent(BaseAgent):
    name = 'KRON'
    personality = 'Detached, encyclopaedic, flags what the headlines buried. Treats news as archaeology - digs for what is NOT being said. Speaks in dry, analytical paragraphs.'
    interval_minutes = 20

    def fetch_data(self):
        items = []

        # NewsAPI (free tier)
        news_key = os.getenv('NEWSAPI_KEY')
        if news_key:
            try:
                resp = requests.get(
                    f'https://newsapi.org/v2/top-headlines?language=en&pageSize=10&apiKey={news_key}',
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for article in data.get('articles', [])[:8]:
                        items.append({
                            'source': 'newsapi',
                            'type': 'headline',
                            'title': article.get('title', ''),
                            'description': article.get('description', ''),
                            'source_name': article.get('source', {}).get('name', ''),
                            'url': article.get('url', ''),
                            'published_at': article.get('publishedAt', ''),
                            'timestamp': datetime.utcnow().isoformat()
                        })
            except Exception as e:
                print(f"[{self.name}] NewsAPI error: {e}")

        # Reuters RSS
        try:
            reuters_feed = feedparser.parse('https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best')
            for entry in reuters_feed.entries[:5]:
                items.append({
                    'source': 'reuters',
                    'type': 'market_news',
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', '')[:500],
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] Reuters error: {e}")

        # BBC World RSS
        try:
            bbc_feed = feedparser.parse('http://feeds.bbci.co.uk/news/world/rss.xml')
            for entry in bbc_feed.entries[:5]:
                items.append({
                    'source': 'bbc',
                    'type': 'world_news',
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', '')[:500],
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] BBC error: {e}")

        # GDELT Project (free, no key needed)
        try:
            gdelt_url = 'https://api.gdeltproject.org/api/v2/doc/doc?query=finance&mode=ArtList&maxrecords=5&format=json'
            resp = requests.get(gdelt_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for article in data.get('articles', [])[:5]:
                    items.append({
                        'source': 'gdelt',
                        'type': 'global_narrative',
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'domain': article.get('domain', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] GDELT error: {e}")

        return items
