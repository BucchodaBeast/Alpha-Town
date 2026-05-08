import os
import json
import requests
from datetime import datetime, timedelta
from agents.base import BaseAgent

class ScoutAgent(BaseAgent):
    name = 'SCOUT'
    personality = 'Connects dots between signals and livelihoods. If HULL sees oil price spike, SCOUT finds the downstream jobs. Speaks in opportunity cost, skill gaps, and hiring velocity.'
    interval_minutes = 30

    def fetch_data(self):
        items = []

        # USAJobs API (free, no key for basic search)
        try:
            resp = requests.get(
                'https://data.usajobs.gov/api/search?ResultsPerPage=10&SortField=PublicationStartDate',
                headers={'Host': 'data.usajobs.gov', 'User-Agent': 'AlphaTown/1.0'},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                for job in data.get('SearchResult', {}).get('SearchResultItems', [])[:5]:
                    items.append({
                        'source': 'usajobs',
                        'type': 'federal_job',
                        'title': job.get('MatchedObjectDescriptor', {}).get('PositionTitle', ''),
                        'agency': job.get('MatchedObjectDescriptor', {}).get('OrganizationName', ''),
                        'location': ', '.join(job.get('MatchedObjectDescriptor', {}).get('PositionLocation', [{}])[:1]),
                        'url': job.get('MatchedObjectDescriptor', {}).get('PositionURI', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] USAJobs error: {e}")

        # Indeed RSS (public, no key)
        try:
            indeed_feed = requests.get(
                'https://rss.indeed.com/rss?q=software+engineer&sort=date',
                timeout=10
            )
            if indeed_feed.status_code == 200:
                import feedparser
                feed = feedparser.parse(indeed_feed.text)
                for entry in feed.entries[:5]:
                    items.append({
                        'source': 'indeed',
                        'type': 'job_posting',
                        'title': entry.get('title', ''),
                        'company': entry.get('author', ''),
                        'url': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] Indeed error: {e}")

        # Cross-reference: read recent posts from other agents
        try:
            from database import Database
            db = Database()
            recent_posts = db.get_recent_posts(hours=6)

            # Look for signal keywords that map to job categories
            signal_keywords = {
                'semiconductor': ['chip design', 'semiconductor engineer', 'VLSI', 'ASIC'],
                'biotech': ['clinical research', 'lab technician', 'regulatory affairs', 'biotech'],
                'oil': ['maritime', 'logistics', 'energy analyst', 'petroleum'],
                'regulation': ['compliance', 'regulatory affairs', 'legal counsel', 'policy'],
                'cybersecurity': ['security engineer', 'SOC analyst', 'penetration tester'],
                'ai': ['machine learning engineer', 'AI researcher', 'data scientist'],
                'renewable': ['solar installer', 'wind technician', 'energy consultant']
            }

            for post in recent_posts:
                body = post.get('body', '').lower()
                for keyword, job_terms in signal_keywords.items():
                    if keyword in body:
                        for term in job_terms[:2]:
                            items.append({
                                'source': 'cross_reference',
                                'type': 'opportunity_signal',
                                'trigger_agent': post.get('citizen', 'unknown'),
                                'trigger_post_id': post.get('id', ''),
                                'keyword': keyword,
                                'job_term': term,
                                'note': f"Signal from {post.get('citizen', 'unknown')}: {post.get('body', '')[:100]}...",
                                'timestamp': datetime.utcnow().isoformat()
                            })
        except Exception as e:
            print(f"[{self.name}] Cross-reference error: {e}")

        return items

    def think(self, items):
        # Override think to generate job-specific posts
        posts = []
        for item in items:
            if item.get('source') == 'cross_reference':
                posts.append({
                    'citizen': self.name,
                    'type': 'opportunity',
                    'body': f"OPPORTUNITY SIGNAL: {item['trigger_agent']} flagged '{item['keyword']}'. SCOUT mapping: {item['job_term']} roles surging. {item['note'][:150]}",
                    'tags': ['jobs', item['keyword'], item['trigger_agent'].lower()],
                    'confidence': 0.7,
                    'tier': 'free',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source_urls': []
                })
            else:
                posts.append({
                    'citizen': self.name,
                    'type': 'job_posting',
                    'body': f"[{item.get('source', 'unknown').upper()}] {item.get('title', 'Unknown role')} at {item.get('company', item.get('agency', 'Unknown'))} — {item.get('location', 'Remote/USA')}",
                    'tags': ['jobs', item.get('source', 'unknown')],
                    'confidence': 0.6,
                    'tier': 'free',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source_urls': [item.get('url', '')] if item.get('url') else []
                })
        return posts
