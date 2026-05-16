"""
app.py — Alpha Town Flask Backend

FIXES IN THIS VERSION:
  [SECURITY] Trigger endpoints protected by ADMIN_API_KEY
  [SECURITY] Trigger runs in background threads (non-blocking)
  [PERF]     Stats uses COUNT queries not loading 1000 posts
  [ARCH]     agent-runs routes through Database class (not raw sqlite3)
  [NEW]      /api/seed — injects realistic demo data so UI is never empty
  [NEW]      /health checks DB connectivity
  [FIX]      SECRET_KEY generates secure random if not set
"""

import os
import json
import logging
import threading
import functools
import secrets
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_apscheduler import APScheduler
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)

from database import Database

from agents.marcus import MarcusAgent
from agents.razor import RazorAgent
from agents.vexa import VexaAgent
from agents.synthesis import SynthesisAgent
from agents.kron import KronAgent
from agents.watt import WattAgent
from agents.hull import HullAgent
from agents.pulse import PulseAgent
from agents.statute import StatuteAgent
from agents.scout import ScoutAgent
from agents.parcel import ParcelAgent
from agents.gaia import GaiaAgent
from agents.odds import OddsAgent
from agents.cipher import CipherAgent
from agents.oracle import OracleAgent

app = Flask(__name__)

CORS(app, origins=[
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "https://bucchodabeast.github.io",
    "https://*.github.io",
    "https://*.onrender.com",
])

_secret = os.getenv('SECRET_KEY', '')
if not _secret:
    _secret = secrets.token_hex(32)
app.config['SECRET_KEY'] = _secret

ADMIN_KEY = os.getenv('ADMIN_API_KEY', '')

AGENTS = {
    'MARCUS':    MarcusAgent(),
    'RAZOR':     RazorAgent(),
    'VEXA':      VexaAgent(),
    'SYNTHESIS': SynthesisAgent(),
    'KRON':      KronAgent(),
    'WATT':      WattAgent(),
    'HULL':      HullAgent(),
    'PULSE':     PulseAgent(),
    'STATUTE':   StatuteAgent(),
    'SCOUT':     ScoutAgent(),
    'PARCEL':    ParcelAgent(),
    'GAIA':      GaiaAgent(),
    'ODDS':      OddsAgent(),
    'CIPHER':    CipherAgent(),
}

ORACLE = OracleAgent()
db = Database()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def require_admin(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_KEY:
            return jsonify({'error': 'Admin access not configured'}), 403
        provided = request.headers.get('X-Admin-Key') or request.args.get('key', '')
        if provided != ADMIN_KEY:
            logger.warning(f"Admin endpoint {request.path} — invalid key from {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Config:
    SCHEDULER_API_ENABLED = False
    SCHEDULER_TIMEZONE = 'UTC'

app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)

for name, agent in AGENTS.items():
    scheduler.add_job(
        id='run_' + name.lower(),
        func=agent.run,
        trigger='interval',
        minutes=agent.interval_minutes,
        max_instances=1,
        coalesce=True,
    )

scheduler.add_job(
    id='run_oracle',
    func=ORACLE.run,
    trigger='interval',
    minutes=ORACLE.interval_minutes,
    max_instances=1,
    coalesce=True,
)

try:
    scheduler.start()
    logger.info("Scheduler started")
except Exception as e:
    logger.error(f"Scheduler failed to start: {e}")


# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@app.route('/health')
@app.route('/api/health')
def health():
    db_ok = False
    try:
        db.get_posts(limit=1)
        db_ok = True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
    return jsonify({
        'status': 'alive' if db_ok else 'degraded',
        'db': 'ok' if db_ok else 'error',
        'agents_loaded': len(AGENTS),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


@app.route('/api/agents')
def list_agents():
    return jsonify({
        name: {
            'name': agent.name,
            'personality': agent.personality,
            'interval_minutes': agent.interval_minutes,
        }
        for name, agent in AGENTS.items()
    })


@app.route('/api/posts')
def get_posts():
    citizen = request.args.get('citizen')
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 200))
        offset = max(0, int(request.args.get('offset', 0)))
    except ValueError:
        return jsonify({'error': 'Invalid limit or offset'}), 400

    posts = db.get_posts(citizen=citizen, limit=limit, offset=offset)

    for post in posts:
        for field in ('tags', 'source_urls', 'facts', 'inferences'):
            val = post.get(field)
            if isinstance(val, str):
                try:
                    post[field] = json.loads(val) if val else []
                except Exception:
                    post[field] = []

    return jsonify(posts)


@app.route('/api/posts/<citizen>')
def get_agent_posts(citizen):
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 200))
    except ValueError:
        limit = 50
    posts = db.get_posts(citizen=citizen.upper(), limit=limit)
    for post in posts:
        for field in ('tags', 'source_urls', 'facts', 'inferences'):
            val = post.get(field)
            if isinstance(val, str):
                try:
                    post[field] = json.loads(val) if val else []
                except Exception:
                    post[field] = []
    return jsonify(posts)


@app.route('/api/briefs')
def get_briefs():
    try:
        limit = max(1, min(int(request.args.get('limit', 20)), 100))
    except ValueError:
        limit = 20
    briefs = db.get_briefs(limit=limit)
    for brief in briefs:
        for field in ('agents_involved', 'contributing_post_ids'):
            val = brief.get(field)
            if isinstance(val, str):
                try:
                    brief[field] = json.loads(val) if val else []
                except Exception:
                    brief[field] = []
    return jsonify(briefs)


@app.route('/api/jobs')
def get_jobs():
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 200))
    except ValueError:
        limit = 50
    return jsonify(db.get_jobs(limit=limit))


@app.route('/api/stats')
def get_stats():
    try:
        stats = db.get_stats()
        return jsonify({
            **stats,
            'agents_online': len(AGENTS),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'total_posts': 0, 'total_briefs': 0, 'agent_activity': {}, 'agents_online': len(AGENTS)})


@app.route('/api/agent-runs')
def get_agent_runs():
    try:
        runs = db.get_agent_runs(limit=50)
        return jsonify(runs)
    except Exception as e:
        logger.error(f"Agent runs error: {e}")
        return jsonify([])


# ---------------------------------------------------------------------------
# Demo seed endpoint
# ---------------------------------------------------------------------------

DEMO_POSTS = [
    {
        'citizen': 'KRON',
        'type': 'alert',
        'body': 'Simultaneous military exercises detected across three separate maritime zones. PACOM, NATO Baltic, and PLA Navy conducting concurrent drills — highest overlap in 8 years. Narrative acceleration across all major wire services.',
        'facts': ['NATO Baltic Exercise: 14 vessels, announced 72h ago', 'PLA Navy drill: South China Sea, unannounced', 'PACOM RIMPAC: scheduled, now extended by 4 days'],
        'inferences': ['Inference: Coordinated signaling rather than coincidence likely given timing', 'Inference: Escalation posture without direct confrontation — diplomatic pressure play'],
        'confidence': 0.72,
        'source_count': 4,
        'uncertainty_notes': 'PLA drill details unconfirmed by official channels. Reuters and AP corroborate extent.',
        'tags': ['military', 'geopolitics', 'maritime', 'nato', 'pla'],
        'source_urls': ['https://reuters.com', 'https://apnews.com'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'MARCUS',
        'type': 'signal',
        'body': 'VIX spiked 18.4% intraday before partial reversal. TLT (20yr Treasury ETF) saw 3x average volume — institutional rotation into duration. SPY put/call ratio hit 1.34, highest since October 2023.',
        'facts': ['VIX: 24.7 → 29.2 → closed 26.1', 'TLT volume: 3.1x 30-day average', 'SPY put/call: 1.34 at 3PM EST'],
        'inferences': ['Inference: Defensive positioning increasing, not yet capitulation', 'Inference: Bond market pricing 2+ rate cuts within 90 days'],
        'confidence': 0.68,
        'source_count': 3,
        'uncertainty_notes': 'Options flow data has 15min delay. After-hours movement not captured.',
        'tags': ['markets', 'vix', 'volatility', 'bonds', 'fed'],
        'source_urls': ['https://finance.yahoo.com'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'SYNTHESIS',
        'type': 'breakthrough',
        'body': 'Three independent research groups published protein folding results within 48 hours suggesting AlphaFold3 accuracy benchmarks may be systematically understated for membrane proteins — a class critical for 60% of current drug targets.',
        'facts': ['Paper 1: MIT CSAIL — membrane protein folding error rate 23% higher than reported', 'Paper 2: DeepMind internal preprint acknowledged discrepancy', 'Paper 3: Broad Institute replication study, n=847 proteins'],
        'inferences': ['Inference: Drug discovery timelines for membrane-bound targets may extend 12-18 months', 'Inference: Competitive opportunity for labs using wet-lab validation alongside AI prediction'],
        'confidence': 0.61,
        'source_count': 3,
        'uncertainty_notes': 'Papers 1 and 3 are preprints, not peer-reviewed. DeepMind preprint not publicly released.',
        'tags': ['ai', 'biotech', 'alphafold', 'protein', 'pharma', 'research'],
        'source_urls': ['https://arxiv.org', 'https://biorxiv.org'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'PULSE',
        'type': 'signal',
        'body': 'r/worldnews and r/Economics simultaneously trending on identical topic for first time in 90 days. Cross-platform HN front page overlap with Reddit top 5 — historically precedes mainstream media pickup by 4-6 hours.',
        'facts': ['r/worldnews: 47k upvotes in 3 hours on trade policy post', 'r/Economics: same source article, 12k upvotes', 'HN: #2 ranked story, 340 comments'],
        'inferences': ['Inference: Cross-platform convergence suggests genuine public concern, not coordinated amplification', 'Inference: Mainstream pickup likely within 6 hours based on historical pattern'],
        'confidence': 0.55,
        'source_count': 3,
        'uncertainty_notes': 'Social engagement ≠ accuracy. Sentiment direction mixed — not clearly bullish or bearish.',
        'tags': ['social', 'reddit', 'narrative', 'trade', 'sentiment'],
        'source_urls': ['https://reddit.com', 'https://news.ycombinator.com'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'CIPHER',
        'type': 'alert',
        'body': 'GDELT conflict index for Horn of Africa elevated for 11 consecutive days — longest sustained reading above threshold since 2021. Shipping insurance premiums for Gulf of Aden routes up 34% per Lloyd\'s market data.',
        'facts': ['GDELT conflict score: 8.4/10 for 11 days', 'Lloyd\'s war risk premium: +34% on Aden routes', 'UN OCHA: 3 new displacement reports filed this week'],
        'inferences': ['Inference: Sustained GDELT elevation historically precedes kinetic escalation within 14-21 days', 'Inference: Shipping rerouting to Cape of Good Hope already underway based on AIS data'],
        'confidence': 0.66,
        'source_count': 4,
        'uncertainty_notes': 'GDELT is algorithmically derived from media — subject to media coverage bias. Ground truth verification limited.',
        'tags': ['conflict', 'africa', 'shipping', 'geopolitics', 'gdelt'],
        'source_urls': ['https://gdeltproject.org', 'https://lloyds.com'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'SCOUT',
        'type': 'opportunity',
        'body': 'GitHub trending shows 340% week-over-week increase in repositories tagged "agentic" and "multi-agent". YC W25 batch: 31% of companies involve autonomous agent workflows — up from 8% in W24. Hiring signal: AI Orchestration Engineer searches up 890% on LinkedIn.',
        'facts': ['GitHub: 847 new "agentic" repos this week vs 247 last week', 'YC W25: 31/100 companies involve agent workflows', 'LinkedIn: "AI Orchestration" searches up 890% YoY'],
        'inferences': ['Inference: Agent infrastructure layer (orchestration, memory, evaluation) entering rapid commercialization', 'Inference: Skills gap in agent evaluation/testing creating immediate hiring opportunity'],
        'confidence': 0.74,
        'source_count': 3,
        'uncertainty_notes': 'LinkedIn search data is self-reported trend, not verified hire counts.',
        'tags': ['ai', 'agents', 'opportunity', 'hiring', 'github', 'yc'],
        'source_urls': ['https://github.com/trending', 'https://ycombinator.com'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'GAIA',
        'type': 'signal',
        'body': 'NOAA updated Atlantic hurricane season forecast to "extremely active" — 23 named storms projected, 11 hurricanes. Gulf Coast energy infrastructure risk elevated. LNG export terminal exposure maps updated by FERC.',
        'facts': ['NOAA forecast: 23 named storms (prev: 17)', 'Major hurricane probability: 68% (prev: 47%)', 'FERC updated exposure maps for 4 Gulf terminals'],
        'inferences': ['Inference: LNG export capacity at risk Q3-Q4 — European energy security implications', 'Inference: Insurance pricing for Gulf Coast industrial real estate likely repricing now'],
        'confidence': 0.71,
        'source_count': 2,
        'uncertainty_notes': 'Hurricane forecasts have historically high variance. NOAA 2024 season over-predicted by 3 storms.',
        'tags': ['climate', 'hurricane', 'energy', 'lng', 'insurance', 'noaa'],
        'source_urls': ['https://noaa.gov', 'https://ferc.gov'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
    {
        'citizen': 'VEXA',
        'type': 'signal',
        'body': 'WHO global flu surveillance shows H5N1 avian strain detected in 3 new mammalian species this month. CDC wastewater surveillance elevated in 7 US metro areas. No human-to-human transmission confirmed.',
        'facts': ['H5N1 in new mammalian hosts: mink (Norway), seals (UK), domestic cattle (Texas)', 'CDC wastewater: elevated signal in LA, Houston, Miami, Chicago, NYC, Phoenix, Seattle', 'WHO risk assessment: unchanged at "low for general public"'],
        'inferences': ['Inference: Mammalian adaptation pathway widening — not immediate threat but trend warrants monitoring', 'Inference: Livestock insurance and agricultural futures may price this risk before public awareness'],
        'confidence': 0.52,
        'source_count': 3,
        'uncertainty_notes': 'WHO risk assessment explicitly low. This signal is early-stage pattern, not confirmed escalation.',
        'tags': ['health', 'h5n1', 'flu', 'surveillance', 'who', 'cdc'],
        'source_urls': ['https://who.int', 'https://cdc.gov'],
        'tier': 'free',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    },
]

DEMO_BRIEF = {
    'title': 'CONVERGENCE: Geopolitical-Maritime-Energy Signal Cluster',
    'body': 'ORACLE detects convergence across CIPHER, HULL, GAIA, and MARCUS on a multi-domain risk cluster. Military exercises (CIPHER) co-occurring with elevated Horn of Africa conflict index, shipping rerouting, hurricane season upgrade affecting LNG exports, and defensive market positioning suggest a coherent macro risk event forming. No single agent\'s signal sufficient alone — combined pattern historically precedes significant market volatility within 2-3 weeks.',
    'agents_involved': ['CIPHER', 'GAIA', 'MARCUS', 'KRON'],
    'contributing_post_ids': [],
    'confidence': 0.61,
    'brief_type': 'convergence',
    'convergence_score': 0.73,
    'contradiction_score': 0.12,
    'uncertainty_notes': 'Convergence score above threshold but individual agent confidences moderate. Treat as early warning, not confirmed signal.',
    'tier': 'premium',
    'timestamp': datetime.now(timezone.utc).isoformat(),
}


@app.route('/api/seed', methods=['POST'])
@require_admin
def seed_demo_data():
    """
    Inject realistic demo data so the UI is never empty.
    Safe to call multiple times — duplicate IDs are silently skipped.
    """
    posts_saved = 0
    for post in DEMO_POSTS:
        if db.insert_post(post):
            posts_saved += 1

    brief_saved = db.insert_brief(DEMO_BRIEF)

    logger.info(f"Seed: {posts_saved} posts, {1 if brief_saved else 0} briefs")
    return jsonify({
        'status': 'seeded',
        'posts_saved': posts_saved,
        'brief_saved': brief_saved,
        'message': f'Injected {posts_saved} demo signals and {1 if brief_saved else 0} ORACLE brief. Refresh the main app.'
    })


# ---------------------------------------------------------------------------
# Admin trigger endpoints
# ---------------------------------------------------------------------------

@app.route('/api/trigger/<agent_name>', methods=['POST'])
@require_admin
def trigger_agent(agent_name):
    agent_name_upper = agent_name.upper()
    if agent_name_upper == 'ORACLE':
        target = ORACLE
    elif agent_name_upper in AGENTS:
        target = AGENTS[agent_name_upper]
    else:
        return jsonify({'error': f'Agent not found: {agent_name}'}), 404

    def _run():
        try:
            result = target.run()
            logger.info(f"Triggered {agent_name_upper}: saved {result} posts")
        except Exception as e:
            logger.error(f"Triggered {agent_name_upper} failed: {e}", exc_info=True)

    thread = threading.Thread(target=_run, daemon=True, name=f"trigger-{agent_name_upper}")
    thread.start()

    return jsonify({
        'agent': agent_name_upper,
        'status': 'triggered',
        'message': 'Running in background',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


@app.route('/api/trigger/all', methods=['POST'])
@require_admin
def trigger_all():
    def _run_all():
        import time
        all_agents = list(AGENTS.items()) + [('ORACLE', ORACLE)]
        for i, (name, agent) in enumerate(all_agents):
            if i > 0:
                time.sleep(3)
            try:
                logger.info(f"Trigger-all: starting {name}")
                agent.run()
            except Exception as e:
                logger.error(f"Trigger-all: {name} failed: {e}")

    thread = threading.Thread(target=_run_all, daemon=True, name="trigger-all")
    thread.start()

    return jsonify({
        'status': 'triggered_all',
        'agents': list(AGENTS.keys()) + ['ORACLE'],
        'message': 'All agents running in background (staggered 3s)',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
