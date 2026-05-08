import os
import json
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_apscheduler import APScheduler
from dotenv import load_dotenv

load_dotenv()

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
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-me')

AGENTS = {
    'MARCUS': MarcusAgent(),
    'RAZOR': RazorAgent(),
    'VEXA': VexaAgent(),
    'SYNTHESIS': SynthesisAgent(),
    'KRON': KronAgent(),
    'WATT': WattAgent(),
    'HULL': HullAgent(),
    'PULSE': PulseAgent(),
    'STATUTE': StatuteAgent(),
    'SCOUT': ScoutAgent(),
    'PARCEL': ParcelAgent(),
    'GAIA': GaiaAgent(),
    'ODDS': OddsAgent(),
    'CIPHER': CipherAgent(),
}

ORACLE = OracleAgent()
db = Database()

class Config:
    SCHEDULER_API_ENABLED = True
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
        max_instances=1
    )

scheduler.add_job(
    id='run_oracle',
    func=ORACLE.run,
    trigger='interval',
    minutes=ORACLE.interval_minutes,
    max_instances=1
)

scheduler.start()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'alive', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/agents')
def list_agents():
    return jsonify({
        name: {
            'name': agent.name,
            'personality': agent.personality,
            'interval_minutes': agent.interval_minutes
        }
        for name, agent in AGENTS.items()
    })

@app.route('/api/posts')
def get_posts():
    citizen = request.args.get('citizen')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    posts = db.get_posts(citizen=citizen, limit=limit, offset=offset)
    return jsonify(posts)

@app.route('/api/posts/<citizen>')
def get_agent_posts(citizen):
    limit = int(request.args.get('limit', 50))
    posts = db.get_posts(citizen=citizen.upper(), limit=limit)
    return jsonify(posts)

@app.route('/api/briefs')
def get_briefs():
    limit = int(request.args.get('limit', 20))
    briefs = db.get_briefs(limit=limit)
    return jsonify(briefs)

@app.route('/api/jobs')
def get_jobs():
    limit = int(request.args.get('limit', 50))
    jobs = db.get_jobs(limit=limit)
    return jsonify(jobs)

@app.route('/api/agent-runs')
def get_agent_runs():
    import sqlite3
    conn = sqlite3.connect('alphatown.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT 50')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{k: row[k] for k in row.keys()} for row in rows])

@app.route('/api/trigger/<agent_name>', methods=['POST'])
def trigger_agent(agent_name):
    agent_name = agent_name.upper()
    if agent_name == 'ORACLE':
        count = ORACLE.run()
        return jsonify({'agent': 'ORACLE', 'items_processed': count})
    if agent_name in AGENTS:
        count = AGENTS[agent_name].run()
        return jsonify({'agent': agent_name, 'items_processed': count})
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/api/trigger/all', methods=['POST'])
def trigger_all():
    results = {}
    for name, agent in AGENTS.items():
        try:
            count = agent.run()
            results[name] = {'status': 'success', 'items': count}
        except Exception as e:
            results[name] = {'status': 'error', 'error': str(e)}
    ORACLE.run()
    return jsonify(results)

@app.route('/api/stats')
def get_stats():
    all_posts = db.get_posts(limit=1000)
    briefs = db.get_briefs(limit=100)
    agent_counts = {}
    for post in all_posts:
        c = post.get('citizen', 'UNKNOWN')
        agent_counts[c] = agent_counts.get(c, 0) + 1
    return jsonify({
        'total_posts': len(all_posts),
        'total_briefs': len(briefs),
        'agent_activity': agent_counts,
        'agents_online': len(AGENTS),
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
