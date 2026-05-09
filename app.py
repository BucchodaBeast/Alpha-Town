"""
app.py — Fixed Alpha Town Flask Backend

FIXES APPLIED:
  [SECURITY] /api/trigger/* now requires X-Admin-Key header.
             Anonymous callers can no longer exhaust Groq quota.
  [PERF]     trigger_agent() and trigger_all() run agents in background
             threads — no longer blocks the request thread.
  [PERF]     /api/stats uses SQL COUNT queries instead of loading 1000 posts.
  [ARCH]     /api/agent-runs routes through Database class (not direct sqlite3)
             so it works correctly with both SQLite and Supabase.
  [RELIABILITY] scheduler.start() wrapped in try/except so app starts even
                if scheduler has a config issue.
"""

import os
import json
import logging
import threading
import functools
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory, abort
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
])

# Use a strong random key in production — do not use 'dev-key-change-me'
_secret = os.getenv('SECRET_KEY', '')
if not _secret:
    import secrets
    _secret = secrets.token_hex(32)
    logger.warning("SECRET_KEY not set — using ephemeral key (sessions won't persist across restarts)")
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
# Auth guard
# ---------------------------------------------------------------------------

def require_admin(f):
    """
    Protect admin endpoints with ADMIN_API_KEY.
    Check X-Admin-Key header or ?key= query param.
    If ADMIN_API_KEY is not set in environment, all trigger calls are blocked.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_KEY:
            # No admin key configured — block all admin endpoints
            logger.warning(f"Admin endpoint {request.path} called but ADMIN_API_KEY not configured")
            return jsonify({'error': 'Admin access not configured'}), 403

        provided = (
            request.headers.get('X-Admin-Key') or
            request.args.get('key') or
            ''
        )
        if provided != ADMIN_KEY:
            logger.warning(f"Admin endpoint {request.path} — invalid key from {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Config:
    SCHEDULER_API_ENABLED = False  # Disable public scheduler API
    SCHEDULER_TIMEZONE = 'UTC'

app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)

for name, agent in AGENTS.items():
    scheduler.add_job(
        id=f'run_{name.lower()}',
        func=agent.run,
        trigger='interval',
        minutes=agent.interval_minutes,
        max_instances=1,
        coalesce=True,  # Skip missed runs instead of stacking them
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
# Static file serving
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# ---------------------------------------------------------------------------
# Public API endpoints
# ---------------------------------------------------------------------------

@app.route('/api/health')
def health():
    """Health check — also verifies DB connectivity."""
    db_ok = False
    try:
        # Quick DB ping
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
            'domain': getattr(agent, 'domain_context', agent.personality)[:120],
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

    # Deserialize JSON fields for consistent API response
    for post in posts:
        for field in ('tags', 'source_urls', 'facts', 'inferences'):
            val = post.get(field)
            if isinstance(val, str):
                try:
                    post[field] = json.loads(val) if val else []
                except (json.JSONDecodeError, ValueError):
                    post[field] = []

    return jsonify(posts)


@app.route('/api/posts/<citizen>')
def get_agent_posts(citizen):
    try:
        limit = max(1, min(int(request.args.get('limit', 50)), 200))
    except ValueError:
        limit = 50

    citizen_upper = citizen.upper()
    if citizen_upper not in AGENTS and citizen_upper != 'ORACLE':
        return jsonify({'error': f'Unknown agent: {citizen}'}), 404

    posts = db.get_posts(citizen=citizen_upper, limit=limit)

    for post in posts:
        for field in ('tags', 'source_urls', 'facts', 'inferences'):
            val = post.get(field)
            if isinstance(val, str):
                try:
                    post[field] = json.loads(val) if val else []
                except (json.JSONDecodeError, ValueError):
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
                except (json.JSONDecodeError, ValueError):
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
    """
    FIXED: Uses COUNT queries instead of loading 1000 posts into memory.
    """
    try:
        stats = db.get_stats()
        return jsonify({
            **stats,
            'agents_online': len(AGENTS),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error(f"Stats endpoint error: {e}")
        return jsonify({'error': 'Stats unavailable'}), 500


@app.route('/api/agent-runs')
def get_agent_runs():
    """
    FIXED: Routes through Database class so it works with both SQLite and Supabase.
    Previously called sqlite3.connect() directly, silently returning empty results
    when using Supabase.
    """
    try:
        runs = db.get_agent_runs(limit=50)
        return jsonify(runs)
    except Exception as e:
        logger.error(f"Agent runs error: {e}")
        return jsonify([])


# ---------------------------------------------------------------------------
# Admin-protected trigger endpoints
# ---------------------------------------------------------------------------

@app.route('/api/trigger/<agent_name>', methods=['POST'])
@require_admin
def trigger_agent(agent_name):
    """
    Trigger an agent run in a background thread.
    FIXED: Was synchronous and blocked the Flask thread for minutes.
           Now fires a daemon thread and returns immediately.
    FIXED: Protected by ADMIN_KEY.
    """
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
    """
    Trigger all agents in background threads (staggered to reduce Groq rate limit hits).
    FIXED: Was fully synchronous — locked Flask for 5-10 minutes.
    FIXED: Protected by ADMIN_KEY.
    """
    triggered = []

    def _run_all():
        import time
        all_agents = list(AGENTS.items()) + [('ORACLE', ORACLE)]
        for i, (name, agent) in enumerate(all_agents):
            try:
                # Stagger starts to avoid concurrent Groq calls
                if i > 0:
                    time.sleep(3)
                logger.info(f"Trigger-all: starting {name}")
                agent.run()
            except Exception as e:
                logger.error(f"Trigger-all: {name} failed: {e}")

    thread = threading.Thread(target=_run_all, daemon=True, name="trigger-all")
    thread.start()

    return jsonify({
        'status': 'triggered_all',
        'agents': list(AGENTS.keys()) + ['ORACLE'],
        'message': 'All agents running in background (staggered)',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
