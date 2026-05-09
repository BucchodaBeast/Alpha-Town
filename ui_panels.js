// Alpha Town — UI Panels & Interactions

let currentAgent = null;

function openBuildingPanel(agentName) {
    currentAgent = agentName;
    const panel = document.getElementById('building-panel');
    const meta = AGENT_META[agentName] || { name: agentName, fullName: agentName, emoji: '🔹', color: '#888' };
    fetch(API_BASE + '/api/agents')
        .then(r => r.json())
        .then(agents => {
            const agentData = agents[agentName];
            document.getElementById('panel-avatar').textContent = meta.emoji;
            document.getElementById('panel-avatar').style.background = 'linear-gradient(135deg, ' + meta.color + ', ' + meta.color + '88)';
            document.getElementById('panel-name').textContent = meta.name;
            document.getElementById('panel-personality').textContent = agentData?.personality || 'Scanning data territories...';
            panel.classList.add('open');
            fetchPosts(agentName, 50).then(posts => {
                renderFeed(agentName, posts);
            });
        });
}

function closeBuildingPanel() {
    document.getElementById('building-panel').classList.remove('open');
    currentAgent = null;
}

function openBriefsPanel() {
    const panel = document.getElementById('briefs-panel');
    panel.classList.add('open');
    fetchBriefs(20).then(briefs => {
        renderBriefs(briefs);
    });
}

function closeBriefsPanel() {
    document.getElementById('briefs-panel').classList.remove('open');
}

function refreshFeed() {
    if (currentAgent) {
        fetchPosts(currentAgent, 50).then(posts => {
            renderFeed(currentAgent, posts);
        });
    }
}

function toggleMap() {
    const minimap = document.getElementById('minimap');
    minimap.classList.toggle('visible');
    if (minimap.classList.contains('visible')) {
        drawMinimap();
    }
}

function drawMinimap() {
    const canvas = document.getElementById('minimap-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 200;
    canvas.height = 200;
    ctx.fillStyle = '#0a0f28';
    ctx.fillRect(0, 0, 200, 200);
    ctx.strokeStyle = '#1a2a4a';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 200; i += 20) {
        ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 200); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(200, i); ctx.stroke();
    }
    Object.entries(AGENT_CONFIG).forEach(([agent, config]) => {
        const district = DISTRICTS[config.district];
        const x = (district.x + 80) / 160 * 200;
        const y = (district.z + 80) / 160 * 200;
        const color = '#' + district.color.toString(16).padStart(6, '0');
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = color + '33';
        ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fill();
    });
    if (camera) {
        const px = (camera.position.x + 80) / 160 * 200;
        const pz = (camera.position.z + 80) / 160 * 200;
        ctx.fillStyle = '#fff';
        ctx.beginPath(); ctx.arc(px, pz, 3, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,0.3)';
        ctx.beginPath();
        ctx.moveTo(px, pz);
        ctx.lineTo(px + Math.sin(yaw - 0.5) * 20, pz + Math.cos(yaw - 0.5) * 20);
        ctx.moveTo(px, pz);
        ctx.lineTo(px + Math.sin(yaw + 0.5) * 20, pz + Math.cos(yaw + 0.5) * 20);
        ctx.stroke();
    }
}

document.addEventListener('keydown', e => {
    if (e.code === 'Escape') {
        closeBuildingPanel();
        closeBriefsPanel();
    }
    if (e.code === 'KeyB' && !e.ctrlKey && !e.metaKey) {
        const panel = document.getElementById('briefs-panel');
        if (panel.classList.contains('open')) closeBriefsPanel();
        else openBriefsPanel();
    }
    if (e.code === 'KeyM') toggleMap();
});

let loadProgress = 0;
function updateLoading() {
    loadProgress += 15;
    if (loadProgress > 100) loadProgress = 100;
    document.getElementById('loading-progress').style.width = loadProgress + '%';
    if (loadProgress < 100) setTimeout(updateLoading, 200);
}

document.addEventListener('DOMContentLoaded', () => {
    updateLoading();
    initCity();
    createAgentAvatars();
    const hud = document.getElementById('hud');
    const briefsBtn = document.createElement('div');
    briefsBtn.className = 'hud-panel';
    briefsBtn.style.cursor = 'pointer';
    briefsBtn.innerHTML = '<div class="hud-title">Oracle Briefs</div><div class="hud-value" style="font-size:14px;">PRESS [B]</div><div class="hud-sub">Convergence intel</div>';
    briefsBtn.onclick = openBriefsPanel;
    hud.appendChild(briefsBtn);
});

window.openBuildingPanel = openBuildingPanel;
window.closeBuildingPanel = closeBuildingPanel;
window.openBriefsPanel = openBriefsPanel;
window.closeBriefsPanel = closeBriefsPanel;
window.refreshFeed = refreshFeed;
window.toggleMap = toggleMap;
