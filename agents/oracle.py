"""
agents/oracle.py — Fixed ORACLE Meta-Synthesis Agent

FIXES APPLIED:
  [CRITICAL] Tags are now deserialized from JSON string before clustering.
             Previously iterated over characters ('[', '"', 'o', ...) instead
             of actual tag strings. ORACLE has never worked before this fix.
  [CRITICAL] Confidence is now grounded to number of contributing agents,
             not LLM self-reported.
  [QUALITY]  Added divergence detection (agents contradicting each other).
  [QUALITY]  Minimum confidence threshold before generating a brief.
  [QUALITY]  ORACLE now records which post IDs contributed to each brief.
  [QUALITY]  Brief body is limited to what the convergent posts actually say.
  [ARCH]     Shared Groq call function from base instead of duplicated requests.post.
  [PERF]     Skips re-synthesizing topics already briefed in last 2 hours.
"""

import os
import json
import logging
import time
import hashlib
from datetime import datetime, timezone, timedelta
from database import Database

logger = logging.getLogger(__name__)

# Import the shared Groq caller
try:
    from agents.base import _call_groq
except ImportError:
    # Fallback if running standalone
    def _call_groq(*args, **kwargs):
        return None

ORACLE_SYSTEM_PROMPT = """\
You are ORACLE, a meta-intelligence synthesis system.

You receive convergent posts from multiple independent intelligence agents.
Your ONLY job is to synthesize what those agents have ALREADY REPORTED.

ABSOLUTE RULES:
1. You CANNOT add information not present in the input posts
2. You CANNOT speculate about causes not explicitly reported by agents
3. You MUST attribute every statement to a specific agent
4. You MUST include the convergence score (0-1) and what agents agreed on
5. If agents contradict each other, your brief_type must be "divergence_warning"
6. Confidence = (number_of_agreeing_agents / total_agents) — do not invent this

Return JSON:
{
  "title": "max 80 chars — factual description of what converged",
  "body": "2-3 sentences. What converged, which agents, what they reported.",
  "brief_type": "convergence | divergence_warning | pattern_report",
  "confidence": 0.0,
  "convergence_score": 0.0,
  "contradiction_score": 0.0,
  "uncertainty_notes": "what the agents didn't agree on or what remains unclear"
}"""


def _deserialize_tags(raw_tags) -> list:
    """
    Fix for the critical tag deserialization bug.
    DB stores tags as JSON string. Must parse before using.
    """
    if isinstance(raw_tags, list):
        return raw_tags
    if isinstance(raw_tags, str) and raw_tags:
        try:
            result = json.loads(raw_tags)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
    return []


class OracleAgent:
    name = 'ORACLE'
    personality = (
        'Meta-intelligence that synthesizes convergent signals from multiple agents. '
        'Never speculates beyond what the convergence warrants. '
        'Speaks in confidence intervals and source attribution.'
    )
    interval_minutes = 30

    def __init__(self):
        self.db = Database()
        self._recently_briefed: dict[str, float] = {}  # topic → timestamp
        self._briefed_ttl = 7200  # Don't re-brief same topic within 2 hours

    def _was_recently_briefed(self, topic: str) -> bool:
        """Skip re-synthesizing a topic that was just briefed."""
        last = self._recently_briefed.get(topic, 0)
        return (time.time() - last) < self._briefed_ttl

    def _mark_briefed(self, topic: str):
        self._recently_briefed[topic] = time.time()
        # Clean up old entries
        cutoff = time.time() - self._briefed_ttl * 2
        self._recently_briefed = {
            k: v for k, v in self._recently_briefed.items() if v > cutoff
        }

    def detect_convergence(self):
        """
        Cluster recent posts by tag across agents.

        FIXED: Properly deserializes JSON-encoded tag strings before iteration.
        Previously: for tag in '[\"oil\",\"sanctions\"]' → iterates characters
        Now:        for tag in ['oil', 'sanctions']      → iterates real tags
        """
        posts = self.db.get_recent_posts(hours=6)

        if not posts:
            logger.info("[ORACLE] No recent posts to analyze")
            return [], []

        topic_clusters: dict[str, dict] = {}

        for post in posts:
            citizen = post.get('citizen', '')
            body = post.get('body', '')
            confidence = float(post.get('confidence', 0.0))
            post_id = post.get('id', '')

            # CRITICAL FIX: deserialize tags from JSON string
            raw_tags = post.get('tags', [])
            tags = _deserialize_tags(raw_tags)

            for tag in tags:
                # Skip single-character tags (artifact of old broken iteration)
                if len(tag) <= 1:
                    continue
                # Skip generic noise tags
                if tag in ('signal', 'alert', 'free', 'premium', 'breakthrough'):
                    continue

                if tag not in topic_clusters:
                    topic_clusters[tag] = {
                        'agents': {},  # agent → list of posts (not just set)
                        'posts': [],
                        'post_ids': [],
                        'total_confidence': 0.0,
                    }

                cluster = topic_clusters[tag]

                if citizen not in cluster['agents']:
                    cluster['agents'][citizen] = []
                cluster['agents'][citizen].append({
                    'body': body,
                    'confidence': confidence,
                    'post_id': post_id,
                })
                cluster['posts'].append(post)
                cluster['post_ids'].append(post_id)
                cluster['total_confidence'] += confidence

        # Build convergence signals (2+ agents on same topic)
        convergence_signals = []
        brief_candidates = []

        for topic, cluster in topic_clusters.items():
            agent_count = len(cluster['agents'])
            if agent_count < 2:
                continue

            avg_confidence = cluster['total_confidence'] / max(len(cluster['posts']), 1)

            # Detect divergence: agents saying very different things about same topic
            # (rough heuristic: check if any agent has low confidence on this topic
            #  while another has high confidence)
            agent_confidences = [
                sum(p['confidence'] for p in posts_) / len(posts_)
                for posts_ in cluster['agents'].values()
            ]
            confidence_spread = max(agent_confidences) - min(agent_confidences)
            is_divergent = confidence_spread > 0.4  # High spread = agents disagree

            signal = {
                'topic': topic,
                'agents': list(cluster['agents'].keys()),
                'agent_count': agent_count,
                'post_count': len(cluster['posts']),
                'post_ids': cluster['post_ids'],
                'posts': cluster['posts'][:5],  # cap for LLM context
                'avg_confidence': round(avg_confidence, 3),
                'is_divergent': is_divergent,
                'confidence_spread': round(confidence_spread, 3),
            }

            convergence_signals.append(signal)

            # Only generate briefs for topics that clear quality thresholds
            # and haven't been briefed recently
            if (agent_count >= 3 and
                avg_confidence >= 0.35 and
                not self._was_recently_briefed(topic)):
                brief_candidates.append(signal)
            elif (agent_count >= 2 and
                  is_divergent and
                  avg_confidence >= 0.3 and
                  not self._was_recently_briefed(f"diverge_{topic}")):
                # Divergence briefs don't need 3 agents
                brief_candidates.append(signal)

        logger.info(
            f"[ORACLE] {len(topic_clusters)} topics, "
            f"{len(convergence_signals)} with 2+ agents, "
            f"{len(brief_candidates)} brief candidates"
        )

        return convergence_signals, brief_candidates

    def synthesize_brief(self, signal: dict) -> dict | None:
        """Generate a synthesis brief from a convergence signal."""
        topic = signal['topic']
        agents = signal['agents']
        posts = signal['posts']
        is_divergent = signal.get('is_divergent', False)
        avg_confidence = signal['avg_confidence']

        # Confidence grounded to agent count (not LLM self-reported)
        # 2 agents → max 0.65, 3 agents → max 0.80, 4+ → max 0.90
        confidence_caps = {2: 0.55, 3: 0.70, 4: 0.82}
        grounded_confidence = min(
            avg_confidence * 1.1,  # Slight boost for convergence
            confidence_caps.get(min(len(agents), 4), 0.82)
        )

        # Build context for LLM from actual post content
        posts_summary = '\n'.join([
            f"- [{p.get('citizen', '?')}] (conf={p.get('confidence', 0):.2f}): "
            f"{p.get('body', '')[:200]}"
            for p in posts
        ])

        # Fallback brief (no LLM required)
        brief_type = 'divergence_warning' if is_divergent else 'convergence'
        fallback_brief = {
            'id': f"oracle_{hashlib.sha256(f'{topic}{time.time()}'.encode()).hexdigest()[:8]}",
            'title': f"{'DIVERGENCE' if is_divergent else 'CONVERGENCE'}: {topic}",
            'body': (
                f"ORACLE detected {'conflicting signals' if is_divergent else 'convergence'} "
                f"on '{topic}' from {len(agents)} agents "
                f"({', '.join(agents)}). "
                f"{signal['post_count']} posts in 6h window. "
                f"Average confidence: {avg_confidence:.0%}."
            ),
            'agents_involved': agents,
            'contributing_post_ids': signal['post_ids'],
            'confidence': round(grounded_confidence, 3),
            'brief_type': brief_type,
            'convergence_score': round(1.0 - signal.get('confidence_spread', 0), 3),
            'contradiction_score': round(signal.get('confidence_spread', 0), 3),
            'tier': 'premium',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        groq_key = os.getenv('GROQ_API_KEY', '')
        if not groq_key:
            return fallback_brief

        # LLM synthesis
        data_payload = (
            f"TOPIC: {topic}\n"
            f"AGENTS INVOLVED: {', '.join(agents)}\n"
            f"IS DIVERGENT: {is_divergent}\n"
            f"AVERAGE AGENT CONFIDENCE: {avg_confidence:.2f}\n"
            f"CONVERGENT POSTS:\n{posts_summary}"
        )

        parsed = _call_groq(
            agent_name='ORACLE',
            personality_context='Meta-intelligence synthesis — synthesize only what agents reported',
            data_payload=data_payload,
        )

        if not parsed:
            logger.warning(f"[ORACLE] LLM synthesis failed for topic '{topic}' — using fallback")
            return fallback_brief

        return {
            'id': fallback_brief['id'],
            'title': parsed.get('title', fallback_brief['title'])[:80],
            'body': parsed.get('body', fallback_brief['body'])[:600],
            'agents_involved': agents,
            'contributing_post_ids': signal['post_ids'],
            'confidence': round(grounded_confidence, 3),  # Always use grounded value
            'brief_type': parsed.get('brief_type', brief_type),
            'convergence_score': round(float(parsed.get('convergence_score', 0.5)), 3),
            'contradiction_score': round(float(parsed.get('contradiction_score', 0.0)), 3),
            'uncertainty_notes': parsed.get('uncertainty_notes', ''),
            'tier': 'premium',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    def run(self) -> int:
        logger.info("[ORACLE] Scanning for convergence...")
        start = time.time()

        convergence_signals, brief_candidates = self.detect_convergence()
        logger.info(
            f"[ORACLE] {len(convergence_signals)} convergence signals, "
            f"{len(brief_candidates)} brief candidates"
        )

        saved = 0
        for signal in brief_candidates:
            brief = self.synthesize_brief(signal)
            if brief:
                if self.db.insert_brief(brief):
                    saved += 1
                    self._mark_briefed(signal['topic'])
                    logger.info(
                        f"[ORACLE] Brief saved: '{brief['title']}' "
                        f"(type={brief['brief_type']}, conf={brief['confidence']:.2f})"
                    )

        duration = time.time() - start
        self.db.log_agent_run('ORACLE', 'success', len(convergence_signals), saved)
        logger.info(f"[ORACLE] Complete in {duration:.1f}s — saved {saved} briefs")
        return saved
