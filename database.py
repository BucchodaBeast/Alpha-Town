"""
database.py — Alpha Town Database Layer

FIXES IN THIS VERSION:
  [CRITICAL] check_seen() — wraps Supabase call in try/except, returns False
             on connection error so agents continue instead of crashing.
  [CRITICAL] mark_seen() — try/except, silently ignores connection errors.
  [CRITICAL] insert_post() — try/except on Supabase, falls back gracefully.
  [CRITICAL] get_posts() / get_recent_posts() — try/except, returns [] on error.
  [CRITICAL] get_supabase() — resets cached client on connection failure so
             next call gets a fresh connection instead of reusing a broken one.
  [FIX]     insert_post() no longer raises on non-duplicate errors — logs and
             returns False instead of crashing the agent thread.
  [FIX]     get_stats() Supabase path returns safe defaults on any error.
  [FIX]     All Supabase methods now log warnings instead of propagating
             exceptions that kill background agent threads.
"""

import os
import sqlite3
import json
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

DB_PATH = os.getenv('DATABASE_PATH', 'alphatown.db')
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY', '')

_use_supabase = HAS_SUPABASE and bool(SUPABASE_URL) and bool(SUPABASE_KEY)
_supabase_client = None


def get_supabase():
    """
    Returns Supabase client. Resets cached client if it appears broken
    so the next call gets a fresh connection.
    """
    global _supabase_client
    if _use_supabase and _supabase_client is None:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            return None
    return _supabase_client


def _reset_supabase_client():
    """Reset cached client so next call gets a fresh one."""
    global _supabase_client
    _supabase_client = None


def init_sqlite():
    """Initialize SQLite schema with proper indexes."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            citizen TEXT NOT NULL,
            type TEXT NOT NULL,
            body TEXT NOT NULL,
            facts TEXT DEFAULT '[]',
            inferences TEXT DEFAULT '[]',
            uncertainty_notes TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.3,
            source_count INTEGER DEFAULT 1,
            tier TEXT DEFAULT 'free',
            timestamp TEXT,
            source_urls TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS seen_items (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            hash TEXT NOT NULL,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            status TEXT,
            items_found INTEGER DEFAULT 0,
            items_posted INTEGER DEFAULT 0,
            error TEXT,
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS briefs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            agents_involved TEXT DEFAULT '[]',
            contributing_post_ids TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            brief_type TEXT DEFAULT 'convergence',
            convergence_score REAL DEFAULT 0.5,
            contradiction_score REAL DEFAULT 0.0,
            uncertainty_notes TEXT DEFAULT '',
            tier TEXT DEFAULT 'premium',
            timestamp TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            source_agent TEXT,
            trigger_post_id TEXT,
            url TEXT,
            posted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS user_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            post_id TEXT NOT NULL,
            reaction_type TEXT DEFAULT 'save',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id)
        )''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_citizen ON posts(citizen)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_seen_agent_hash ON seen_items(agent, hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_runs_agent ON agent_runs(agent)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_runs_started ON agent_runs(started_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_briefs_timestamp ON briefs(timestamp DESC)')

        conn.commit()
        logger.info(f"SQLite initialized at {DB_PATH}")


if not _use_supabase:
    init_sqlite()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row) -> dict:
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}


class Database:

    @staticmethod
    def insert_post(post: dict) -> bool:
        import hashlib

        citizen = post.get('citizen', 'unknown')
        body = post.get('body', '')
        ts = post.get('timestamp', datetime.now(timezone.utc).isoformat())
        content_hash = hashlib.sha256(f"{citizen}|{body[:100]}|{ts[:16]}".encode()).hexdigest()[:12]
        post_id = post.get('id') or f"{citizen}_{content_hash}"

        facts = json.dumps(post.get('facts', []))
        inferences = json.dumps(post.get('inferences', []))
        tags = json.dumps(post.get('tags', []))
        source_urls = json.dumps(post.get('source_urls', []))
        uncertainty_notes = post.get('uncertainty_notes', '')
        source_count = int(post.get('source_count', 1))

        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    raise Exception("Supabase client unavailable")
                sb.table('posts').insert({
                    'id': post_id,
                    'citizen': citizen,
                    'type': post.get('type', 'signal'),
                    'body': body,
                    'facts': facts,
                    'inferences': inferences,
                    'uncertainty_notes': uncertainty_notes,
                    'tags': tags,
                    'confidence': float(post.get('confidence', 0.3)),
                    'source_count': source_count,
                    'tier': post.get('tier', 'free'),
                    'timestamp': ts,
                    'source_urls': source_urls,
                }).execute()
                return True
            except Exception as e:
                err = str(e).lower()
                if 'duplicate' in err or '23505' in err or 'unique' in err:
                    return False
                # Connection error — reset client so next call retries fresh
                if 'resource temporarily unavailable' in err or 'read error' in err or 'connection' in err:
                    logger.warning(f"Supabase connection error on insert_post — resetting client: {e}")
                    _reset_supabase_client()
                else:
                    logger.error(f"insert_post failed: {e}")
                return False
        else:
            with get_db() as conn:
                try:
                    conn.execute(
                        '''INSERT INTO posts
                           (id, citizen, type, body, facts, inferences,
                            uncertainty_notes, tags, confidence, source_count,
                            tier, timestamp, source_urls)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (post_id, citizen, post.get('type', 'signal'), body,
                         facts, inferences, uncertainty_notes, tags,
                         float(post.get('confidence', 0.3)), source_count,
                         post.get('tier', 'free'), ts, source_urls)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False

    @staticmethod
    def get_posts(citizen=None, limit=50, offset=0) -> list:
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return []
                query = (sb.table('posts')
                         .select('*')
                         .order('timestamp', desc=True)
                         .limit(limit)
                         .offset(offset))
                if citizen:
                    query = query.eq('citizen', citizen)
                return query.execute().data or []
            except Exception as e:
                logger.warning(f"get_posts Supabase error: {e}")
                _reset_supabase_client()
                return []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                if citizen:
                    cursor.execute(
                        'SELECT * FROM posts WHERE citizen = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?',
                        (citizen, limit, offset)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM posts ORDER BY timestamp DESC LIMIT ? OFFSET ?',
                        (limit, offset)
                    )
                return [dict_from_row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_recent_posts(hours=6, citizen=None) -> list:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return []
                query = (sb.table('posts')
                         .select('*')
                         .gte('timestamp', cutoff)
                         .order('timestamp', desc=True))
                if citizen:
                    query = query.eq('citizen', citizen)
                return query.execute().data or []
            except Exception as e:
                logger.warning(f"get_recent_posts Supabase error: {e}")
                _reset_supabase_client()
                return []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                if citizen:
                    cursor.execute(
                        'SELECT * FROM posts WHERE citizen = ? AND timestamp > ? ORDER BY timestamp DESC',
                        (citizen, cutoff)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM posts WHERE timestamp > ? ORDER BY timestamp DESC',
                        (cutoff,)
                    )
                return [dict_from_row(r) for r in cursor.fetchall()]

    @staticmethod
    def check_seen(agent: str, item_hash: str) -> bool:
        """
        FIXED: Returns False on any connection error so agents continue
        processing instead of crashing. Treats connection failure as
        'not seen' — worst case is a duplicate post, not a dead agent.
        """
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return False
                result = sb.table('seen_items').select('id').eq('agent', agent).eq('hash', item_hash).execute()
                return len(result.data or []) > 0
            except Exception as e:
                logger.warning(f"check_seen connection error (treating as unseen): {e}")
                _reset_supabase_client()
                return False  # Fail open: let the item through
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM seen_items WHERE agent = ? AND hash = ?', (agent, item_hash))
                return cursor.fetchone() is not None

    @staticmethod
    def mark_seen(agent: str, item_hash: str):
        """FIXED: Silently ignores connection errors — non-critical operation."""
        seen_id = f"{agent}_{item_hash}"
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return
                sb.table('seen_items').insert({
                    'id': seen_id, 'agent': agent, 'hash': item_hash
                }).execute()
            except Exception as e:
                err = str(e).lower()
                if 'duplicate' in err or '23505' in err or 'unique' in err:
                    pass  # Already seen, fine
                elif 'resource temporarily unavailable' in err or 'read error' in err:
                    logger.warning(f"mark_seen connection error (non-fatal): {e}")
                    _reset_supabase_client()
                else:
                    logger.debug(f"mark_seen error (non-fatal): {e}")
        else:
            with get_db() as conn:
                conn.execute(
                    'INSERT OR IGNORE INTO seen_items (id, agent, hash) VALUES (?, ?, ?)',
                    (seen_id, agent, item_hash)
                )
                conn.commit()

    @staticmethod
    def log_agent_run(agent: str, status: str, items_found=0, items_posted=0, error=None):
        completed = datetime.now(timezone.utc).isoformat()
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return
                sb.table('agent_runs').insert({
                    'agent': agent, 'status': status,
                    'items_found': items_found, 'items_posted': items_posted,
                    'error': error, 'completed_at': completed,
                }).execute()
            except Exception as e:
                logger.warning(f"log_agent_run failed (non-fatal): {e}")
        else:
            with get_db() as conn:
                conn.execute(
                    '''INSERT INTO agent_runs
                       (agent, status, items_found, items_posted, error, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (agent, status, items_found, items_posted, error, completed)
                )
                conn.commit()

    @staticmethod
    def get_agent_runs(limit=50) -> list:
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return []
                result = (sb.table('agent_runs')
                          .select('*')
                          .order('started_at', desc=True)
                          .limit(limit)
                          .execute())
                return result.data or []
            except Exception as e:
                logger.warning(f"get_agent_runs error: {e}")
                return []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM agent_runs ORDER BY started_at DESC LIMIT ?', (limit,))
                return [dict_from_row(r) for r in cursor.fetchall()]

    @staticmethod
    def get_stats() -> dict:
        """Efficient stats using COUNT queries."""
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return {'total_posts': 0, 'total_briefs': 0, 'agent_activity': {}}
                posts_result = sb.table('posts').select('citizen', count='exact').execute()
                briefs_result = sb.table('briefs').select('id', count='exact').execute()
                total_posts = posts_result.count or 0
                total_briefs = briefs_result.count or 0

                agent_rows = sb.table('posts').select('citizen').execute().data or []
                agent_counts = {}
                for row in agent_rows:
                    c = row.get('citizen', 'UNKNOWN')
                    agent_counts[c] = agent_counts.get(c, 0) + 1

                return {
                    'total_posts': total_posts,
                    'total_briefs': total_briefs,
                    'agent_activity': agent_counts,
                }
            except Exception as e:
                logger.error(f"get_stats error: {e}")
                return {'total_posts': 0, 'total_briefs': 0, 'agent_activity': {}}
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM posts')
                total_posts = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM briefs')
                total_briefs = cursor.fetchone()[0]
                cursor.execute('SELECT citizen, COUNT(*) as cnt FROM posts GROUP BY citizen')
                agent_counts = {row[0]: row[1] for row in cursor.fetchall()}
                return {
                    'total_posts': total_posts,
                    'total_briefs': total_briefs,
                    'agent_activity': agent_counts,
                }

    @staticmethod
    def insert_brief(brief: dict) -> bool:
        import hashlib
        brief_id = brief.get('id') or f"oracle_{hashlib.sha256(brief.get('title', '').encode()).hexdigest()[:8]}"
        ts = brief.get('timestamp', datetime.now(timezone.utc).isoformat())
        agents = json.dumps(brief.get('agents_involved', []))
        post_ids = json.dumps(brief.get('contributing_post_ids', []))

        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return False
                sb.table('briefs').insert({
                    'id': brief_id,
                    'title': brief.get('title', '')[:80],
                    'body': brief.get('body', ''),
                    'agents_involved': agents,
                    'contributing_post_ids': post_ids,
                    'confidence': float(brief.get('confidence', 0.5)),
                    'brief_type': brief.get('brief_type', 'convergence'),
                    'convergence_score': float(brief.get('convergence_score', 0.5)),
                    'contradiction_score': float(brief.get('contradiction_score', 0.0)),
                    'uncertainty_notes': brief.get('uncertainty_notes', ''),
                    'tier': brief.get('tier', 'premium'),
                    'timestamp': ts,
                }).execute()
                return True
            except Exception as e:
                err = str(e).lower()
                if 'duplicate' in err or '23505' in err:
                    return False
                logger.warning(f"insert_brief failed: {e}")
                return False
        else:
            with get_db() as conn:
                try:
                    conn.execute(
                        '''INSERT INTO briefs
                           (id, title, body, agents_involved, contributing_post_ids,
                            confidence, brief_type, convergence_score, contradiction_score,
                            uncertainty_notes, tier, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (brief_id, brief.get('title', '')[:80], brief.get('body', ''),
                         agents, post_ids,
                         float(brief.get('confidence', 0.5)),
                         brief.get('brief_type', 'convergence'),
                         float(brief.get('convergence_score', 0.5)),
                         float(brief.get('contradiction_score', 0.0)),
                         brief.get('uncertainty_notes', ''),
                         brief.get('tier', 'premium'), ts)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False

    @staticmethod
    def get_briefs(limit=20) -> list:
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return []
                return (sb.table('briefs')
                        .select('*')
                        .order('timestamp', desc=True)
                        .limit(limit)
                        .execute().data or [])
            except Exception as e:
                logger.warning(f"get_briefs error: {e}")
                return []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM briefs ORDER BY timestamp DESC LIMIT ?', (limit,))
                return [dict_from_row(r) for r in cursor.fetchall()]

    @staticmethod
    def insert_job(job: dict) -> bool:
        import hashlib
        job_id = job.get('id') or f"job_{hashlib.sha256((job.get('title','') + job.get('url','')).encode()).hexdigest()[:10]}"
        posted = job.get('posted_at', datetime.now(timezone.utc).isoformat())

        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return False
                sb.table('jobs').insert({
                    'id': job_id, 'title': job.get('title', ''),
                    'company': job.get('company'), 'location': job.get('location'),
                    'source_agent': job.get('source_agent'),
                    'trigger_post_id': job.get('trigger_post_id'),
                    'url': job.get('url'), 'posted_at': posted,
                }).execute()
                return True
            except Exception as e:
                logger.warning(f"insert_job failed: {e}")
                return False
        else:
            with get_db() as conn:
                try:
                    conn.execute(
                        '''INSERT INTO jobs
                           (id, title, company, location, source_agent,
                            trigger_post_id, url, posted_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (job_id, job.get('title', ''), job.get('company'),
                         job.get('location'), job.get('source_agent'),
                         job.get('trigger_post_id'), job.get('url'), posted)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False

    @staticmethod
    def get_jobs(limit=50) -> list:
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return []
                return (sb.table('jobs')
                        .select('*')
                        .order('posted_at', desc=True)
                        .limit(limit)
                        .execute().data or [])
            except Exception as e:
                logger.warning(f"get_jobs error: {e}")
                return []
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs ORDER BY posted_at DESC LIMIT ?', (limit,))
                return [dict_from_row(r) for r in cursor.fetchall()]

    @staticmethod
    def cleanup_seen_items(days_old=7):
        """Purge old dedup hashes to prevent unbounded growth."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
        if _use_supabase:
            try:
                sb = get_supabase()
                if sb is None:
                    return
                sb.table('seen_items').delete().lt('seen_at', cutoff).execute()
            except Exception as e:
                logger.warning(f"cleanup_seen_items failed: {e}")
        else:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM seen_items WHERE seen_at < ?', (cutoff,))
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted} stale seen_items")
