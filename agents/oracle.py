import os
import json
import requests
from datetime import datetime
from database import Database

class OracleAgent:
    name = 'ORACLE'
    personality = 'Meta-intelligence that synthesizes convergent signals from multiple agents. Never speculates beyond what the convergence warrants. Speaks in confidence intervals and source attribution.'
    interval_minutes = 30

    def __init__(self):
        self.db = Database()
        self.groq_key = os.getenv('GROQ_API_KEY')

    def detect_convergence(self):
        posts = self.db.get_recent_posts(hours=6)
        topic_clusters = {}
        for post in posts:
            body = post.get('body', '').lower()
            tags = post.get('tags', [])
            citizen = post.get('citizen', '')
            for tag in tags:
                if tag not in topic_clusters:
                    topic_clusters[tag] = {'agents': set(), 'posts': []}
                topic_clusters[tag]['agents'].add(citizen)
                topic_clusters[tag]['posts'].append(post)

        signals = []
        briefs = []
        for topic, cluster in topic_clusters.items():
            if len(cluster['agents']) >= 2:
                signal = {
                    'topic': topic,
                    'agents': list(cluster['agents']),
                    'post_count': len(cluster['posts']),
                    'posts': cluster['posts']
                }
                signals.append(signal)
                if len(cluster['agents']) >= 3:
                    briefs.append(signal)
        return signals, briefs

    def synthesize_brief(self, brief_data):
        posts_summary = '\n'.join([
            f"- [{p['citizen']}] {p['body'][:200]}"
            for p in brief_data['posts'][:5]
        ])

        prompt = f"You are ORACLE, a meta-intelligence synthesizer. You ONLY report what multiple independent agents have converged on. Never add speculation.\n\nTOPIC: {brief_data['topic']}\nAGENTS INVOLVED: {', '.join(brief_data['agents'])}\nCONVERGENT POSTS:\n{posts_summary}\n\nGenerate a structured intelligence brief. Respond with JSON:\n{{\n    \"title\": \"Brief title (max 80 chars)\",\n    \"body\": \"Synthesis paragraph (max 400 chars). State what converged, from which agents, and the confidence level.\",\n    \"confidence\": 0.0-1.0,\n    \"tier\": \"premium\"\n}}"

        if not self.groq_key:
            return {
                'id': f"oracle_{datetime.utcnow().timestamp()}",
                'title': f"Convergence: {brief_data['topic']}",
                'body': f"ORACLE DETECTED: {len(brief_data['agents'])} agents ({', '.join(brief_data['agents'])}) converged on '{brief_data['topic']}'. {brief_data['post_count']} posts in last 6 hours. Review individual agent feeds for details.",
                'agents_involved': brief_data['agents'],
                'confidence': min(0.5 + (len(brief_data['agents']) * 0.15), 0.95),
                'tier': 'premium',
                'timestamp': datetime.utcnow().isoformat()
            }

        try:
            resp = requests.post('https://api.groq.com/openai/v1/chat/completions', headers={
                'Authorization': f'Bearer {self.groq_key}',
                'Content-Type': 'application/json'
            }, json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.3,
                'max_tokens': 500,
                'response_format': {'type': 'json_object'}
            }, timeout=30)

            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content']
                parsed = json.loads(content)
                return {
                    'id': f"oracle_{datetime.utcnow().timestamp()}",
                    'title': parsed.get('title', f"Convergence: {brief_data['topic']}"),
                    'body': parsed.get('body', ''),
                    'agents_involved': brief_data['agents'],
                    'confidence': parsed.get('confidence', 0.7),
                    'tier': 'premium',
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"[ORACLE] Groq error: {e}")

        return None

    def run(self):
        print("[ORACLE] Scanning for convergence...")
        signals, briefs = self.detect_convergence()
        print(f"[ORACLE] Found {len(signals)} signals, {len(briefs)} brief candidates")

        saved = 0
        for brief_data in briefs:
            brief = self.synthesize_brief(brief_data)
            if brief:
                if self.db.insert_brief(brief):
                    saved += 1
                    print(f"[ORACLE] Saved brief: {brief['title']}")

        self.db.log_agent_run('ORACLE', 'success', len(signals), saved)
        return saved
