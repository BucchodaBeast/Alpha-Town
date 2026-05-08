import os
import json
import requests
import feedparser
from datetime import datetime
from agents.base import BaseAgent

class VexaAgent(BaseAgent):
    name = 'VEXA'
    personality = 'Clinical, empathetic, translates medical complexity into human language. Sees patterns in epidemiology that others miss. Speaks with the calm authority of a trauma surgeon.'
    interval_minutes = 60

    def fetch_data(self):
        items = []

        # CDC RSS feeds
        cdc_feeds = [
            'https://tools.cdc.gov/api/v2/resources/media/403372.rss',
            'https://tools.cdc.gov/api/v2/resources/media/132608.rss'
        ]
        for feed_url in cdc_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    items.append({
                        'source': 'cdc',
                        'type': 'health_alert',
                        'title': entry.get('title', ''),
                        'summary': entry.get('summary', '')[:500],
                        'url': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    })
            except Exception as e:
                print(f"[{self.name}] CDC error: {e}")

        # WHO Disease Outbreak News
        try:
            who_feed = feedparser.parse('https://www.who.int/feeds/entity/csr/don/en/rss.xml')
            for entry in who_feed.entries[:5]:
                items.append({
                    'source': 'who',
                    'type': 'outbreak',
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', '')[:500],
                    'url': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] WHO error: {e}")

        # FDA drug approvals RSS
        try:
            fda_feed = feedparser.parse('https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drug-safety/rss.xml')
            for entry in fda_feed.entries[:3]:
                items.append({
                    'source': 'fda',
                    'type': 'drug_alert',
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"[{self.name}] FDA error: {e}")

        # PubMed recent searches (using E-utilities)
        try:
            resp = requests.get(
                'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=outbreak+OR+epidemic+OR+pandemic&retmax=5&retmode=json&sort=date',
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                idlist = data.get('esearchresult', {}).get('idlist', [])
                if idlist:
                    summary_resp = requests.get(
                        f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={",".join(idlist)}&retmode=json',
                        timeout=10
                    )
                    if summary_resp.status_code == 200:
                        summaries = summary_resp.json().get('result', {})
                        for pmid in idlist:
                            if pmid in summaries and pmid != 'uids':
                                article = summaries[pmid]
                                items.append({
                                    'source': 'pubmed',
                                    'type': 'research',
                                    'title': article.get('title', ''),
                                    'journal': article.get('source', ''),
                                    'pubdate': article.get('pubdate', ''),
                                    'pmid': pmid,
                                    'timestamp': datetime.utcnow().isoformat()
                                })
        except Exception as e:
            print(f"[{self.name}] PubMed error: {e}")

        return items
