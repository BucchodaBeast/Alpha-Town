// Alpha Town — Main App Controller
// This file was missing from the repo. It wires the boot sequence to the app.

const bootLines = [
    { text: 'Initializing kernel...', delay: 120 },
    { text: 'Loading agent modules [14/14]...', delay: 180 },
    { text: 'Mounting database layer...', delay: 140 },
    { text: 'Connecting to Groq inference endpoint...', delay: 260 },
    { text: 'Establishing data feeds...', delay: 180 },
    { text: 'MARCUS: Market data stream active', delay: 90 },
    { text: 'RAZOR: SEC EDGAR feed connected', delay: 90 },
    { text: 'VEXA: CDC/WHO health monitors online', delay: 90 },
    { text: 'SYNTHESIS: arXiv API reachable', delay: 90 },
    { text: 'KRON: News aggregation active', delay: 90 },
    { text: 'WATT: EIA grid data connected', delay: 90 },
    { text: 'HULL: UN Comtrade feed active', delay: 90 },
    { text: 'PULSE: Social signal receptors online', delay: 90 },
    { text: 'STATUTE: Federal Register monitor active', delay: 90 },
    { text: 'SCOUT: Job cross-reference engine ready', delay: 90 },
    { text: 'PARCEL: Real estate data connected', delay: 90 },
    { text: 'GAIA: Environmental feeds active', delay: 90 },
    { text: 'ODDS: Prediction market APIs connected', delay: 90 },
    { text: 'CIPHER: Conflict monitor active', delay: 90 },
    { text: 'ORACLE: Convergence detection engine ready', delay: 90 },
    { text: 'Calibrating signal confidence thresholds...', delay: 200 },
    { text: 'System ready.', delay: 100 },
];

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

let uptimeStart = Date.now();

function startClock() {
    setInterval(() => {
        const now = new Date();
        const h = String(now.getUTCHours()).padStart(2, '0');
        const m = String(now.getUTCMinutes()).padStart(2, '0');
        const s = String(now.getUTCSeconds()).padStart(2, '0');
        const el = document.getElementById('clock');
        if (el) el.textContent = h + ':' + m + ':' + s + ' UTC';
    }, 1000);
}

function updateUptime() {
    setInterval(() => {
        const elapsed = Math.floor((Date.now() - uptimeStart) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        const el = document.getElementById('global-uptime');
        if (el) el.textContent = h + ':' + m + ':' + s;
    }, 1000);
}

function renderAgentGrid() {
    const grid = document.getElementById('agent-grid');
    if (!grid || typeof AGENT_META === 'undefined') return;
    grid.innerHTML = Object.entries(AGENT_META).map(([key, meta]) => {
        return '<div class="agent-card" onclick="openBuildingPanel(\'' + key + '\')" style="border-color:' + meta.color + '33">' +
            '<span class="agent-emoji">' + meta.emoji + '</span>' +
            '<span class="agent-name">' + meta.name + '</span>' +
            '<span class="agent-district">' + meta.fullName + '</span>' +
            '<div class="agent-status-dot" id="dot-' + key + '"></div>' +
            '</div>';
    }).join('');
}

function updateGlobalStats(stats) {
    if (!stats) return;
    const signals = document.getElementById('global-signals');
    const briefs = document.getElementById('global-briefs');
    if (signals) signals.textContent = (stats.total_posts || 0) + ' signals';
    if (briefs) briefs.textContent = (stats.total_briefs || 0) + ' briefs';
}

async function initApp() {
    try {
        renderAgentGrid();
        startClock();
        updateUptime();

        // Initial data sync — wrapped in try/catch so a failure doesn't hang the app
        try {
            const [posts, briefs, stats] = await Promise.all([
                fetch(API_BASE + '/api/posts?limit=50').then(r => r.json()).catch(() => []),
                fetch(API_BASE + '/api/briefs?limit=10').then(r => r.json()).catch(() => []),
                fetch(API_BASE + '/api/stats').then(r => r.json()).catch(() => null),
            ]);

            cityState.posts = posts || [];
            cityState.briefs = briefs || [];
            updateGlobalStats(stats);

            // Update signal count display
            const sigEl = document.getElementById('global-signals');
            if (sigEl) sigEl.textContent = (posts || []).length + ' signals';

        } catch (e) {
            console.warn('Initial sync failed (non-fatal):', e);
        }

        // Start periodic sync
        setInterval(() => {
            if (typeof syncCity === 'function') syncCity();
        }, 30000);

    } catch (e) {
        console.error('initApp error:', e);
    }
}

async function runBootSequence() {
    const terminal = document.getElementById('boot-terminal');
    const bar = document.getElementById('boot-bar');

    if (!terminal || !bar) {
        // DOM not ready — show app directly
        document.getElementById('app').style.display = 'flex';
        initApp();
        return;
    }

    for (let i = 0; i < bootLines.length; i++) {
        const line = bootLines[i];
        const div = document.createElement('div');
        const now = new Date();
        const time = String(now.getUTCHours()).padStart(2,'0') + ':' +
                     String(now.getUTCMinutes()).padStart(2,'0') + ':' +
                     String(now.getUTCSeconds()).padStart(2,'0');
        div.innerHTML = '<span style="color:#334455">[' + time + ']</span> ' +
                        '<span style="color:#00d4aa">' + line.text + '</span>';
        terminal.appendChild(div);
        terminal.scrollTop = terminal.scrollHeight;
        bar.style.width = ((i + 1) / bootLines.length * 100) + '%';
        await sleep(line.delay);
    }

    await sleep(400);

    const bootScreen = document.getElementById('boot-screen');
    const appDiv = document.getElementById('app');

    if (bootScreen) bootScreen.style.opacity = '0';
    await sleep(300);
    if (bootScreen) bootScreen.style.display = 'none';
    if (appDiv) appDiv.style.display = 'flex';

    initApp();
}

// Kick off when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runBootSequence);
} else {
    runBootSequence();
}
