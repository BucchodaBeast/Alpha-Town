import os
import json
import hashlib
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from database import Database

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

class BaseAgent(ABC):
    name = 'BaseAgent'
    personality = 'A neutral intelligence agent.'
    interval_minutes = 60

    def __init__(self):
        self.db = Database()

    @abstractmethod
    def fetch_data(self):
        pass

    def deduplicate(self, items):
        new_items = []
        for item in items:
            item_str = json.dumps(item, sort_keys=True, default=str)
            item_hash = hashlib.md5(item_str.encode()).hexdigest()
            if not self.db.check_seen(self.name, item_hash):
                self.db.mark_seen(self.name, item_hash)
                new_items.append(item)
        return new_items

    def think(self, items):
        if not items:
            return []
        if not GROQ_API_KEY:
            return [{
                'citizen': self.name,
                'type': 'signal',
                'body': f"[{self.name}] Raw data: {json.dumps(item, default=str)[:500]}",
                'tags': [self.name.lower(), 'raw'],
                'confidence': 0.5,
                'tier': 'free',
                'timestamp': datetime.utcnow().isoformat(),
                'source_urls': []
            } for item in items[:3]]

        posts = []
        for item in items[:5]:
            try:
                prompt = f"You are {self.name}, an AI agent with this personality: {self.personality}\n\nAnalyze this data and generate a structured intelligence post. Be concise, insightful, and write in character.\n\nData: {json.dumps(item, default=str)}\n\nRespond ONLY with valid JSON in this exact format:\n{{\n    \"type\": \"signal|alert|breakthrough\",\n    \"body\": \"Your analysis here (max 280 chars)\",\n    \"tags\": [\"tag1\", \"tag2\"],\n    \"confidence\": 0.0-1.0,\n    \"tier\": \"free|premium\",\n    \"source_urls\": [\"url1\"]\n}}"

                resp = requests.post(GROQ_URL, headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json'
                }, json={
                    'model': 'llama-3.3-70b-versatile',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 400,
                    'response_format': {'type': 'json_object'}
                }, timeout=30)

                if resp.status_code == 200:
                    content = resp.json()['choices'][0]['message']['content']
                    parsed = json.loads(content)
                    posts.append({
                        'citizen': self.name,
                        'type': parsed.get('type', 'signal'),
                        'body': parsed.get('body', 'No analysis generated'),
                        'tags': parsed.get('tags', [self.name.lower()]),
                        'confidence': parsed.get('confidence', 0.5),
                        'tier': parsed.get('tier', 'free'),
                        'timestamp': datetime.utcnow().isoformat(),
                        'source_urls': parsed.get('source_urls', [])
                    })
            except Exception as e:
                print(f"[{self.name}] Groq error: {e}")
                continue
        return posts

    def save(self, posts):
        saved = 0
        for post in posts:
            if self.db.insert_post(post):
                saved += 1
        return saved

    def run(self):
        print(f"[{self.name}] Starting run...")
        try:
            items = self.fetch_data()
            print(f"[{self.name}] Fetched {len(items)} items")
            new_items = self.deduplicate(items)
            print(f"[{self.name}] {len(new_items)} new items after dedup")
            posts = self.think(new_items)
            print(f"[{self.name}] Generated {len(posts)} posts")
            saved = self.save(posts)
            print(f"[{self.name}] Saved {saved} posts")
            self.db.log_agent_run(self.name, 'success', len(items), saved)
            return saved
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            self.db.log_agent_run(self.name, 'error', error=str(e))
            return 0
