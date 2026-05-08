import os
import json
import requests
from datetime import datetime
from agents.base import BaseAgent

class PulseAgent(BaseAgent):
    name = 'PULSE'
    personality = 'Reads crowds the way a trader reads a chart — pattern first, narrative second. Detects coordinated inauthentic behavior. Speaks in velocity metrics and sentiment deltas.'
    interval_minutes = 20

    def fetch_data(self):
        items = []

        # HackerNews API (free, no key)
        try:
            resp = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=10)
            if resp.status_code == 200:
                top_ids = resp.json()[:10]
                for story_id in top_ids:
                    story_resp = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json', timeout=5)
                    if story_resp.status_code == 200:
                        story = story_resp.json()
                        if story and story.get('title'):
                            items.append({
                                'source': 'hackernews',
                                'type': 'tech_narrative',
                                'title': story.get('title', ''),
                                'score': story.get('score', 0),
                                'comments': story.get('descendants', 0),
                                'url': story.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                                'timestamp': datetime.utcnow().isoformat()
                            })
        except Exception as e:
            print(f"[{self.name}] HN error: {e}")

        # Reddit (public JSON endpoints - no auth needed for read)
        try:
            subreddits = ['wallstreetbets', 'technology', 'worldnews', 'science']
            for sub in subreddits:
                resp = requests.get(f'https://www.reddit.com/r/{sub}/hot.json?limit=5', 
                    headers={'User-Agent': 'AlphaTown/1.0'}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for post in data.get('data', {}).get('children', [])[:3]:
                        p = post.get('data', {})
                        items.append({
                            'source': 'reddit',
                            'type': 'social_signal',
                            'subreddit': sub,
                            'title': p.get('title', ''),
                            'ups': p.get('ups', 0),
                            'comments': p.get('num_comments', 0),
                            'upvote_ratio': p.get('upvote_ratio', 0),
                            'url': f"https://reddit.com{p.get('permalink', '')}",
                            'timestamp': datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"[{self.name}] Reddit error: {e}")

        # Mastodon public timeline (mastodon.social)
        try:
            resp = requests.get('https://mastodon.social/api/v1/trends/statuses?limit=10', timeout=10)
            if resp.status_code == 200:
                for status in resp.json()[:5]:
                    items.append({
                        'source': 'mastodon',
                        'type': 'fediverse_trend',
                        'content': status.get('content', '')[:300],
                        'reblogs': status.get('reblogs_count', 0),
                        'favourites': status.get('favourites_count', 0),
                        'url': status.get('url', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] Mastodon error: {e}")

        return items
