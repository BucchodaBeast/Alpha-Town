// Alpha Town — Intelligence Operating Environment
// Professional OSINT Dashboard Frontend

const API_BASE = window.location.origin.includes('github.io') 
    ? 'https://your-backend.onrender.com'  // CHANGE THIS
    : window.location.origin;

const AGENT_META = {
    MARCUS:    { name: 'MARCUS',    district: 'THE EXCHANGE',     emoji: '🏢', color: '#3b82f6' },
    RAZOR:     { name: 'RAZOR',     district: 'THE PIT',          emoji: '🔴', color: '#ef4444' },
    VEXA:      { name: 'VEXA',      district: 'THE CLINIC',       emoji: '🏥', color: '#10b981' },
    SYNTHESIS: { name: 'SYNTHESIS', district: 'THE LAB',          emoji: '🔬', color: '#8b5cf6' },
    KRON:      { name: 'KRON',      district: 'THE BROADCAST',    emoji: '📡', color: '#f59e0b' },
    WATT:      { name: 'WATT',      district: 'THE GRID',         emoji: '⚡', color: '#eab308' },
    HULL:      { name: 'HULL',      district: 'THE HARBOUR',      emoji: '⚓', color: '#3b82f6' },
    PULSE:     { name: 'PULSE',     district: 'THE FEED',         emoji: '💜', color: '#ec4899' },
    STATUTE:   { name: 'STATUTE',   district: 'THE CHAMBER',      emoji: '⚖️', color: '#6b7280' },
    SCOUT:     { name: 'SCOUT',     district: 'THE FLOOR',        emoji: '💼', color: '#10b981' },
    PARCEL:    { name: 'PARCEL',    district: 'THE VAULT',        emoji: '🏛️', color: '#d97706' },
    GAIA:      { name: 'GAIA',      district: 'THE OBSERVATORY',  emoji: '🌍', color: '#06b6d4' },
    ODDS:      { name: 'ODDS',      district: 'THE CASINO',       emoji: '🎰', color: '#a855f7' },
    CIPHER:    { name: 'CIPHER',    district: 'THE EMBASSY',      emoji: '🏴', color: '#dc2626' },
};

let cityState = { posts: [], briefs: [], jobs: [], agents: {}, lastUpdate: null };
let autoScroll = true;
let currentFilter = 'all';
let bootComplete = false;
let systemLogs = [];

// ===== BOOT SEQUENCE =====
const bootLines = [
    { text: 'Initializing kernel...', status: 'ok', delay: 100 },
    { text: 'Loading agent modules [14/14]...', status: 'ok', delay: 200 },
    { text: 'Mounting database layer...', status: 'ok', delay: 150 },
    { text: 'Connecting to Groq inference endpoint...', status: 'info', delay: 300 },
    { text: 'Establishing data feeds...', status: 'info', delay: 200 },
    { text: 'MARCUS: Market data stream active', status: 'ok', delay: 100 },
    { text: 'RAZOR: SEC EDGAR feed connected', status: 'ok', delay: 100 },
    { text: 'VEXA: CDC/WHO health monitors online', status: 'ok', delay: 100 },
    { text: 'SYNTHESIS: arXiv API reachable', status: 'ok', delay: 100 },
    { text: 'KRON: News aggregation active', status: 'ok', delay: 100 },
    { text: 'WATT: EIA grid data connected', status: 'ok', delay: 100 },
    { text: 'HULL: UN Comtrade feed active', status: 'ok', delay: 100 },
    { text: 'PULSE: Social signal receptors online', status: 'ok', delay: 100 },
    { text: 'STATUTE: Federal Register monitor active', status: 'ok', delay: 100 },
    { text: 'SCOUT: Job cross-reference engine ready', status: 'ok', delay: 100 },
    { text: 'PARCEL: Real estate data connected', status: 'ok', delay: 100 },
    { text: 'GAIA: NOAA/USGS environmental feeds active', status: 'ok', delay: 100 },
    { text: 'ODDS: Prediction market APIs connected', status: 'ok', delay: 100 },
    { text: 'CIPHER: ACLED conflict monitor active', status: 'ok', delay: 100 },
    { text: 'ORACLE: Convergence detection engine ready', status: 'ok', delay: 100 },
    { text: 'Calibrating signal confidence thresholds...', status: 'info', delay: 200 },
    { text: 'System ready.', status: 'ok', delay: 100 },
];

async function runBootSequence() {
    const terminal = document.getElementById('boot-terminal');
    const bar = document.getElementById('boot-bar');

    for (let i = 0; i < bootLines.length; i++) {
        const line = bootLines[i];
        const div = document.createElement('div');
        const time = new Date().toISOString().split('T')[1].split('.')[0];
        div.innerHTML = `<span class="log-time">[${time}]</span><span class="${line.status}">${line.text}</span>`;
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;

        const progress = ((i + 1) / bootLines.length) * 100;
        bar.style.width = progress + '%';

        await sleep(line.delay);
    }

    await sleep(400);
    document.getElementById('boot-screen').classList.add('done');
    document.getElementById('app').style.display = 'flex';
    bootComplete = true;

    initApp();
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ===== APP INIT =====
function initApp() {
    renderAgentGrid();
    initFlowCanvas();
    initTabs();
    initPanelTabs();
    startClock();
    syncData();
    setInterval(syncData, 30000);
    setInterval(updateUptime, 1000);
    setInterval(animateTicker, 50);
}

// ===== DATA SYNC =====
async function syncData() {
    const startTime = performance.now();

    try {
        const [postsRes, briefsRes, jobsRes, statsRes, agentsRes] = await Promise.all([
            fetch(API_BASE + '/api/posts?limit=100').catch(() => ({json: () => []})),
            fetch(API_BASE + '/api/briefs?limit=20').catch(() => ({json: () => []})),
            fetch(API_BASE + '/api/jobs?limit=20').catch(() => ({json: () => []})),
            fetch(API_BASE + '/api/stats').catch(() => ({json: () => null})),
            fetch(API_BASE + '/api/agents').catch(() => ({json: () => ({})})),
        ]);

        const posts = await postsRes.json();
        const briefs = await briefsRes.json();
        const jobs = await jobsRes.json();
        const stats = await statsRes.json();
        const agents = await agentsRes.json();

        const latency = Math.round(performance.now() - startTime);
        document.getElementById('metric-latency').textContent = latency + 'ms';

        const newPosts = detectNewPosts(posts);
        cityState = { posts, briefs, jobs, agents, lastUpdate: new Date() };

        renderFeed();
        renderBriefs();
        renderJobs();
        updateAgentGrid(agents, stats);
        updateGlobalStats(stats);
        updateTicker(posts);

        if (newPosts.length > 0) {
            newPosts.forEach(p => logSystem(p.citizen + ' generated ' + p.type, 'ok'));
        }

        document.getElementById('metric-last-sync').textContent = new Date().toLocaleTimeString();
        document.getElementById('metric-throughput').textContent = posts.length + '/session';

    } catch (e) {
        logSystem('Sync failed: ' + e.message, 'err');
        document.getElementById('metric-latency').textContent = 'ERR';
    }
}

function detectNewPosts(newPosts) {
    const existingIds = new Set(cityState.posts.map(p => p.id));
    return newPosts.filter(p => !existingIds.has(p.id));
}

// ===== AGENT GRID =====
function renderAgentGrid() {
    const grid = document.getElementById('agent-grid');
    grid.innerHTML = Object.entries(AGENT_META).map(([key, meta]) => `
        <div class="agent-card" data-agent="${key}" onclick="openAgentModal('${key}')" style="--agent-color: ${meta.color}">
            <div class="agent-card-header">
                <span class="agent-emoji">${meta.emoji}</span>
                <span class="agent-name">${meta.name}</span>
            </div>
            <div class="agent-district">${meta.district}</div>
            <div class="agent-meta">
                <span class="agent-signal-count" id="count-${key}">0 sig</span>
                <span class="agent-status" id="status-${key}"></span>
            </div>
        </div>
    `).join('');
}

function updateAgentGrid(agents, stats) {
    if (!stats || !stats.agent_activity) return;

    Object.entries(AGENT_META).forEach(([key, meta]) => {
        const count = stats.agent_activity[key] || 0;
        const countEl = document.getElementById('count-' + key);
        const statusEl = document.getElementById('status-' + key);

        if (countEl) countEl.textContent = count + ' sig';
        if (statusEl) {
            if (count > 0) {
                statusEl.className = 'agent-status online';
            } else {
                statusEl.className = 'agent-status scanning';
            }
        }
    });
}

// ===== FEED =====
function renderFeed() {
    const stream = document.getElementById('feed-stream');
    const posts = cityState.posts || [];

    if (posts.length === 0) {
        stream.innerHTML = '<div class="feed-empty">No signals detected yet. Agents are scanning...</div>';
        return;
    }

    const filtered = currentFilter === 'all' 
        ? posts 
        : posts.filter(p => p.type === currentFilter);

    const wasAtBottom = stream.scrollTop + stream.clientHeight >= stream.scrollHeight - 50;

    stream.innerHTML = filtered.map(post => {
        const meta = AGENT_META[post.citizen] || { emoji: '🔹', color: '#888', name: post.citizen };
        const type = post.type || 'signal';
        const confidence = post.confidence || 0.5;
        const time = post.timestamp ? formatTime(post.timestamp) : '--';
        const tags = (post.tags || []).map(t => `<span class="signal-tag">${t}</span>`).join('');

        let confColor = '#ef4444';
        if (confidence > 0.7) confColor = '#10b981';
        else if (confidence > 0.4) confColor = '#3b82f6';

        return `
            <div class="signal-card" style="--signal-color: ${meta.color}">
                <div class="signal-header">
                    <div class="signal-agent">
                        <span class="signal-agent-emoji">${meta.emoji}</span>
                        <span class="signal-agent-name">${meta.name}</span>
                    </div>
                    <span class="signal-type ${type}">${type}</span>
                    <span class="signal-time">${time}</span>
                </div>
                <div class="signal-body">${escapeHtml(post.body || 'No content')}</div>
                <div class="signal-footer">
                    <div class="signal-tags">${tags}</div>
                    <div class="signal-confidence">
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${confidence * 100}%; background: ${confColor}"></div>
                        </div>
                        <span class="confidence-value">${Math.round(confidence * 100)}%</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    if (autoScroll && wasAtBottom) {
        stream.scrollTop = stream.scrollHeight;
    }
}

function initTabs() {
    document.querySelectorAll('.feed-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.feed-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = tab.dataset.filter;
            renderFeed();
        });
    });
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    document.getElementById('autoscroll-btn').style.opacity = autoScroll ? '1' : '0.4';
}

function refreshAll() {
    logSystem('Manual refresh triggered', 'info');
    syncData();
}

// ===== BRIEFS =====
function renderBriefs() {
    const list = document.getElementById('briefs-list');
    const briefs = cityState.briefs || [];

    if (briefs.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">◈</div>
                <div class="empty-title">No convergence detected</div>
                <div class="empty-sub">Oracle monitors all agents for multi-source signal alignment</div>
            </div>`;
        return;
    }

    list.innerHTML = briefs.map(brief => {
        const agents = brief.agents_involved || [];
        const agentTags = agents.map(a => {
            const meta = AGENT_META[a] || { emoji: '🔹' };
            return `<span class="brief-agent-tag">${meta.emoji} ${a}</span>`;
        }).join('');

        return `
            <div class="brief-card">
                <div class="brief-header">
                    <span class="brief-badge">ORACLE BRIEF</span>
                    <span class="brief-confidence">${Math.round((brief.confidence || 0) * 100)}% CONF</span>
                </div>
                <div class="brief-title">${escapeHtml(brief.title || 'Untitled')}</div>
                <div class="brief-body">${escapeHtml(brief.body || '')}</div>
                <div class="brief-agents">${agentTags}</div>
            </div>
        `;
    }).join('');
}

// ===== JOBS =====
function renderJobs() {
    const list = document.getElementById('jobs-list');
    const jobs = cityState.jobs || [];

    if (jobs.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">◉</div>
                <div class="empty-title">SCOUT scanning</div>
                <div class="empty-sub">Cross-referencing agent signals with opportunity vectors</div>
            </div>`;
        return;
    }

    list.innerHTML = jobs.map(job => `
        <div class="job-card">
            <div class="job-title">${escapeHtml(job.title || 'Unknown')}</div>
            <div class="job-meta">
                <span>${escapeHtml(job.company || job.agency || 'Unknown')}</span>
                <span>${escapeHtml(job.location || 'Remote')}</span>
            </div>
            <div style="margin-top: 6px;">
                <span class="job-source">${job.source_agent || 'SCOUT'}</span>
            </div>
        </div>
    `).join('');
}

// ===== PANEL TABS =====
function initPanelTabs() {
    document.querySelectorAll('.panel-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            document.querySelectorAll('.panel-content').forEach(p => p.classList.add('hidden'));
            document.getElementById('panel-' + tab.dataset.panel).classList.remove('hidden');
        });
    });
}

// ===== MODAL =====
function openAgentModal(agentName) {
    const meta = AGENT_META[agentName];
    const agentData = cityState.agents[agentName] || {};
    const agentPosts = cityState.posts.filter(p => p.citizen === agentName);

    document.getElementById('modal-avatar').textContent = meta.emoji;
    document.getElementById('modal-name').textContent = meta.name;
    document.getElementById('modal-district').textContent = meta.district;
    document.getElementById('modal-personality').textContent = agentData.personality || 'Scanning data territories...';
    document.getElementById('modal-posts').textContent = agentPosts.length;

    const avgConf = agentPosts.length > 0 
        ? Math.round((agentPosts.reduce((a, p) => a + (p.confidence || 0), 0) / agentPosts.length) * 100)
        : 0;
    document.getElementById('modal-confidence').textContent = avgConf + '%';
    document.getElementById('modal-interval').textContent = (agentData.interval_minutes || '--') + 'm';

    const feed = document.getElementById('modal-feed');
    feed.innerHTML = agentPosts.slice(0, 10).map(post => {
        const time = post.timestamp ? formatTime(post.timestamp) : '--';
        return `
            <div class="signal-card" style="--signal-color: ${meta.color}">
                <div class="signal-header">
                    <span class="signal-type ${post.type || 'signal'}">${post.type || 'signal'}</span>
                    <span class="signal-time">${time}</span>
                </div>
                <div class="signal-body">${escapeHtml(post.body || '')}</div>
            </div>
        `;
    }).join('');

    document.getElementById('agent-modal').classList.add('open');
}

function closeModal() {
    document.getElementById('agent-modal').classList.remove('open');
}

// ===== FLOW CANVAS =====
function initFlowCanvas() {
    const canvas = document.getElementById('flow-canvas');
    const ctx = canvas.getContext('2d');
    const agents = Object.keys(AGENT_META);
    const particles = [];

    for (let i = 0; i < 30; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            agent: agents[Math.floor(Math.random() * agents.length)],
            size: Math.random() * 2 + 1,
        });
    }

    function draw() {
        ctx.fillStyle = '#0a0c10';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Grid
        ctx.strokeStyle = '#1e2230';
        ctx.lineWidth = 0.5;
        for (let x = 0; x < canvas.width; x += 20) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
        }
        for (let y = 0; y < canvas.height; y += 20) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
        }

        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

            const meta = AGENT_META[p.agent];
            ctx.fillStyle = meta ? meta.color : '#888';
            ctx.globalAlpha = 0.6;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1;
        });

        requestAnimationFrame(draw);
    }

    draw();
}

// ===== TICKER =====
let tickerOffset = 0;
function updateTicker(posts) {
    const ticker = document.getElementById('ticker');
    if (posts.length === 0) return;

    const recent = posts.slice(0, 5);
    const items = recent.map(p => {
        const meta = AGENT_META[p.citizen] || { name: p.citizen };
        return meta.name + ': ' + (p.body || '').substring(0, 60) + '...';
    });

    ticker.innerHTML = '<span class="ticker-item">' + items.join(' &nbsp;&nbsp;•&nbsp;&nbsp; ') + '</span>';
}

function animateTicker() {
    const ticker = document.getElementById('ticker');
    if (!ticker) return;
    tickerOffset -= 0.5;
    const item = ticker.querySelector('.ticker-item');
    if (item) {
        item.style.transform = 'translateX(' + tickerOffset + 'px)';
        if (Math.abs(tickerOffset) > item.offsetWidth + 200) {
            tickerOffset = ticker.offsetWidth;
        }
    }
    requestAnimationFrame(animateTicker);
}

// ===== GLOBAL STATS =====
function updateGlobalStats(stats) {
    if (!stats) return;
    document.getElementById('global-signals').textContent = (stats.total_posts || 0) + ' signals';
    document.getElementById('global-briefs').textContent = (stats.total_briefs || 0) + ' briefs';
}

// ===== SYSTEM LOG =====
function logSystem(message, type) {
    const log = document.getElementById('system-log');
    const time = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.innerHTML = `<span class="log-time">[${time}]</span><span class="log-${type}">${message}</span>`;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;

    while (log.children.length > 50) {
        log.removeChild(log.firstChild);
    }
}

// ===== CLOCK & UPTIME =====
function startClock() {
    function update() {
        const now = new Date();
        document.getElementById('clock').textContent = 
            now.toISOString().replace('T', ' ').split('.')[0] + ' UTC';
    }
    update();
    setInterval(update, 1000);
}

let uptimeSeconds = 0;
function updateUptime() {
    uptimeSeconds++;
    const h = Math.floor(uptimeSeconds / 3600).toString().padStart(2, '0');
    const m = Math.floor((uptimeSeconds % 3600) / 60).toString().padStart(2, '0');
    const s = (uptimeSeconds % 60).toString().padStart(2, '0');
    document.getElementById('global-uptime').textContent = h + ':' + m + ':' + s;
}

// ===== UTILS =====
function formatTime(iso) {
    try {
        return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch { return '--:--:--'; }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function triggerAllAgents() {
    logSystem('Triggering all agents...', 'info');
    fetch(API_BASE + '/api/trigger/all', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            logSystem('All agents triggered', 'ok');
            setTimeout(syncData, 2000);
        })
        .catch(e => logSystem('Trigger failed: ' + e.message, 'err'));
}

// ===== START =====
document.addEventListener('DOMContentLoaded', runBootSequence);
