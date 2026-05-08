import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

DB_PATH = os.getenv('DATABASE_PATH', 'alphatown.db')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')

_use_supabase = HAS_SUPABASE and SUPABASE_URL and SUPABASE_KEY
_supabase_client = None

def get_supabase():
    global _supabase_client
    if _use_supabase and _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

def init_sqlite():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY, citizen TEXT NOT NULL, type TEXT NOT NULL,
            body TEXT NOT NULL, tags TEXT, confidence REAL, tier TEXT DEFAULT 'free',
            timestamp TEXT, reactions INTEGER DEFAULT 0, source_urls TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS seen_items (
            id TEXT PRIMARY KEY, agent TEXT NOT NULL, hash TEXT NOT NULL UNIQUE,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, status TEXT,
            items_found INTEGER DEFAULT 0, items_posted INTEGER DEFAULT 0, error TEXT,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS briefs (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
            agents_involved TEXT, confidence REAL, tier TEXT DEFAULT 'premium',
            timestamp TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT, location TEXT,
            source_agent TEXT, trigger_post_id TEXT, url TEXT,
            posted_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
            post_id TEXT NOT NULL, reaction_type TEXT DEFAULT 'save',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, post_id))''')
        conn.commit()

if not _use_supabase:
    init_sqlite()

@contextmanager
def get_db():
    if _use_supabase:
        yield get_supabase()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

def dict_from_row(row):
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}

class Database:
    @staticmethod
    def insert_post(post):
        post_id = post.get('id') or f"{post['citizen']}_{datetime.utcnow().timestamp()}"
        if _use_supabase:
            sb = get_supabase()
            try:
                sb.table('posts').insert({
                    'id': post_id, 'citizen': post['citizen'], 'type': post['type'],
                    'body': post['body'], 'tags': json.dumps(post.get('tags', [])),
                    'confidence': post.get('confidence', 0.5), 'tier': post.get('tier', 'free'),
                    'timestamp': post.get('timestamp', datetime.utcnow().isoformat()),
                    'reactions': 0, 'source_urls': json.dumps(post.get('source_urls', []))
                }).execute()
                return True
            except Exception as e:
                if 'duplicate' in str(e).lower():
                    return False
                raise
        else:
            with get_db() as conn:
                try:
                    conn.execute('''INSERT INTO posts (id, citizen, type, body, tags, confidence, tier, timestamp, source_urls)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (post_id, post['citizen'], post['type'], post['body'],
                         json.dumps(post.get('tags', [])), post.get('confidence', 0.5),
                         post.get('tier', 'free'), post.get('timestamp', datetime.utcnow().isoformat()),
                         json.dumps(post.get('source_urls', []))))
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False

    @staticmethod
    def get_posts(citizen=None, limit=50, offset=0):
        if _use_supabase:
            sb = get_supabase()
            query = sb.table('posts').select('*').order('timestamp', desc=True).limit(limit).offset(offset)
            if citizen:
                query = query.eq('citizen', citizen)
            return query.execute().data or []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                if citizen:
                    cursor.execute('SELECT * FROM posts WHERE citizen = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?',
                                   (citizen, limit, offset))
                else:
                    cursor.execute('SELECT * FROM posts ORDER BY timestamp DESC LIMIT ? OFFSET ?', (limit, offset))
                return [dict_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def get_recent_posts(hours=6, citizen=None):
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        if _use_supabase:
            sb = get_supabase()
            query = sb.table('posts').select('*').gte('timestamp', cutoff).order('timestamp', desc=True)
            if citizen:
                query = query.eq('citizen', citizen)
            return query.execute().data or []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                if citizen:
                    cursor.execute('SELECT * FROM posts WHERE citizen = ? AND timestamp > ? ORDER BY timestamp DESC',
                                   (citizen, cutoff))
                else:
                    cursor.execute('SELECT * FROM posts WHERE timestamp > ? ORDER BY timestamp DESC', (cutoff,))
                return [dict_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def check_seen(agent, item_hash):
        if _use_supabase:
            sb = get_supabase()
            result = sb.table('seen_items').select('id').eq('agent', agent).eq('hash', item_hash).execute()
            return len(result.data or []) > 0
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM seen_items WHERE agent = ? AND hash = ?', (agent, item_hash))
                return cursor.fetchone() is not None

    @staticmethod
    def mark_seen(agent, item_hash):
        if _use_supabase:
            sb = get_supabase()
            sb.table('seen_items').insert({
                'id': f"{agent}_{item_hash}", 'agent': agent, 'hash': item_hash
            }).execute()
        else:
            with get_db() as conn:
                conn.execute('INSERT OR IGNORE INTO seen_items (id, agent, hash) VALUES (?, ?, ?)',
                             (f"{agent}_{item_hash}", agent, item_hash))
                conn.commit()

    @staticmethod
    def log_agent_run(agent, status, items_found=0, items_posted=0, error=None):
        if _use_supabase:
            sb = get_supabase()
            sb.table('agent_runs').insert({
                'agent': agent, 'status': status, 'items_found': items_found,
                'items_posted': items_posted, 'error': error,
                'completed_at': datetime.utcnow().isoformat()
            }).execute()
        else:
            with get_db() as conn:
                conn.execute('''INSERT INTO agent_runs (agent, status, items_found, items_posted, error, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (agent, status, items_found, items_posted, error, datetime.utcnow().isoformat()))
                conn.commit()

    @staticmethod
    def insert_brief(brief):
        brief_id = brief.get('id') or f"brief_{datetime.utcnow().timestamp()}"
        if _use_supabase:
            sb = get_supabase()
            try:
                sb.table('briefs').insert({
                    'id': brief_id, 'title': brief['title'], 'body': brief['body'],
                    'agents_involved': json.dumps(brief.get('agents_involved', [])),
                    'confidence': brief.get('confidence', 0.5), 'tier': brief.get('tier', 'premium'),
                    'timestamp': brief.get('timestamp', datetime.utcnow().isoformat())
                }).execute()
                return True
            except Exception:
                return False
        else:
            with get_db() as conn:
                try:
                    conn.execute('''INSERT INTO briefs (id, title, body, agents_involved, confidence, tier, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (brief_id, brief['title'], brief['body'], json.dumps(brief.get('agents_involved', [])),
                         brief.get('confidence', 0.5), brief.get('tier', 'premium'),
                         brief.get('timestamp', datetime.utcnow().isoformat())))
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False

    @staticmethod
    def get_briefs(limit=20):
        if _use_supabase:
            sb = get_supabase()
            return sb.table('briefs').select('*').order('timestamp', desc=True).limit(limit).execute().data or []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM briefs ORDER BY timestamp DESC LIMIT ?', (limit,))
                return [dict_from_row(row) for row in cursor.fetchall()]

    @staticmethod
    def insert_job(job):
        job_id = job.get('id') or f"job_{datetime.utcnow().timestamp()}"
        if _use_supabase:
            sb = get_supabase()
            try:
                sb.table('jobs').insert({
                    'id': job_id, 'title': job['title'], 'company': job.get('company'),
                    'location': job.get('location'), 'source_agent': job.get('source_agent'),
                    'trigger_post_id': job.get('trigger_post_id'), 'url': job.get('url'),
                    'posted_at': job.get('posted_at', datetime.utcnow().isoformat())
                }).execute()
                return True
            except Exception:
                return False
        else:
            with get_db() as conn:
                try:
                    conn.execute('''INSERT INTO jobs (id, title, company, location, source_agent, trigger_post_id, url, posted_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (job_id, job['title'], job.get('company'), job.get('location'),
                         job.get('source_agent'), job.get('trigger_post_id'), job.get('url'),
                         job.get('posted_at', datetime.utcnow().isoformat())))
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False

    @staticmethod
    def get_jobs(limit=50):
        if _use_supabase:
            sb = get_supabase()
            return sb.table('jobs').select('*').order('posted_at', desc=True).limit(limit).execute().data or []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs ORDER BY posted_at DESC LIMIT ?', (limit,))
                return [dict_from_row(row) for row in cursor.fetchall()]
