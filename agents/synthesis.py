import os
import json
import requests
import feedparser
from datetime import datetime
from agents.base import BaseAgent

class SynthesisAgent(BaseAgent):
    name = 'SYNTHESIS'
    personality = 'Obsessive, sees connections between molecules and mechanisms others miss. Thinks in reaction pathways and convergent timelines. Gets excited about pre-print convergence.'
    interval_minutes = 45

    def fetch_data(self):
        items = []

        # arXiv API - q-bio and chem-ph
        try:
            for category in ['q-bio', 'chem-ph', 'physics.chem-ph']:
                resp = requests.get(
                    f'http://export.arxiv.org/api/query?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&max_results=5',
                    timeout=15
                )
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:5]:
                        items.append({
                            'source': 'arxiv',
                            'type': 'preprint',
                            'category': category,
                            'title': entry.get('title', '').replace('\n', ' '),
                            'authors': [a.get('name', '') for a in entry.get('authors', [])[:3]],
                            'summary': entry.get('summary', '')[:800],
                            'url': entry.get('id', ''),
                            'published': entry.get('published', ''),
                            'timestamp': datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"[{self.name}] arXiv error: {e}")

        # PubChem API - recent compounds
        try:
            resp = requests.get(
                'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/list/new/JSON?max_records=5',
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if 'PC_Compounds' in data:
                    for compound in data['PC_Compounds'][:5]:
                        cid = compound.get('id', {}).get('id', {}).get('cid', 'unknown')
                        items.append({
                            'source': 'pubchem',
                            'type': 'compound',
                            'cid': cid,
                            'note': f'New compound CID {cid} added to PubChem',
                            'url': f'https://pubchem.ncbi.nlm.nih.gov/compound/{cid}',
                            'timestamp': datetime.utcnow().isoformat()
                        })
        except Exception as e:
            print(f"[{self.name}] PubChem error: {e}")

        # ClinicalTrials.gov API
        try:
            resp = requests.get(
                'https://clinicaltrials.gov/api/v2/studies?filter.overallStatus=RECRUITING&pageSize=5&sort=LastUpdatePostDate:desc',
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for study in data.get('studies', [])[:5]:
                    proto = study.get('protocolSection', {})
                    items.append({
                        'source': 'clinicaltrials',
                        'type': 'trial',
                        'nct_id': proto.get('identificationModule', {}).get('nctId', ''),
                        'title': proto.get('identificationModule', {}).get('briefTitle', ''),
                        'phase': proto.get('designModule', {}).get('phases', ['Unknown'])[0] if proto.get('designModule', {}).get('phases') else 'Unknown',
                        'condition': ', '.join(proto.get('conditionsModule', {}).get('conditions', [])[:2]),
                        'timestamp': datetime.utcnow().isoformat()
                    })
        except Exception as e:
            print(f"[{self.name}] ClinicalTrials error: {e}")

        return items
