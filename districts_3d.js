// Alpha Town — Districts & Building Geometry
// Three.js r128 — no build step

const DISTRICTS = {
    EXCHANGE: { color: 0x00a8ff, x: -60, z: -60, label: 'THE EXCHANGE' },
    PIT:      { color: 0xff3333, x: -20, z: -60, label: 'THE PIT' },
    CLINIC:   { color: 0x00d4aa, x: 20,  z: -60, label: 'THE CLINIC' },
    LAB:      { color: 0xaa66ff, x: 60,  z: -60, label: 'THE LAB' },
    BROADCAST:{ color: 0xffaa00, x: -60, z: -20, label: 'THE BROADCAST' },
    GRID:     { color: 0xffdd00, x: -20, z: -20, label: 'THE GRID' },
    HARBOUR:  { color: 0x4488ff, x: 20,  z: -20, label: 'THE HARBOUR' },
    FEED:     { color: 0xff44aa, x: 60,  z: -20, label: 'THE FEED' },
    CHAMBER:  { color: 0x888888, x: -60, z: 20,  label: 'THE CHAMBER' },
    FLOOR:    { color: 0x44ff88, x: -20, z: 20,  label: 'THE FLOOR' },
    VAULT:    { color: 0xcc8844, x: 20,  z: 20,  label: 'THE VAULT' },
    OBS:      { color: 0x44ccff, x: 60,  z: 20,  label: 'THE OBSERVATORY' },
    CASINO:   { color: 0xff00ff, x: -40, z: 60,  label: 'THE CASINO' },
    EMBASSY:  { color: 0xcc2222, x: 40,  z: 60,  label: 'THE EMBASSY' },
};

const AGENT_CONFIG = {
    MARCUS:    { district: 'EXCHANGE', height: 25, shape: 'tower',  windows: 40, emissive: 0x0066aa },
    RAZOR:     { district: 'PIT',      height: 12, shape: 'cube',   windows: 20, emissive: 0xaa0000 },
    VEXA:      { district: 'CLINIC',   height: 22, shape: 'tower',  windows: 35, emissive: 0x00aa66 },
    SYNTHESIS: { district: 'LAB',      height: 18, shape: 'pyramid',windows: 0,  emissive: 0x6600aa },
    KRON:      { district: 'BROADCAST',height: 30, shape: 'antenna',windows: 10, emissive: 0xaa6600 },
    WATT:      { district: 'GRID',     height: 15, shape: 'plant',  windows: 15, emissive: 0xaaaa00 },
    HULL:      { district: 'HARBOUR',  height: 14, shape: 'warehouse',windows:25, emissive: 0x0044aa },
    PULSE:     { district: 'FEED',     height: 28, shape: 'tower',  windows: 50, emissive: 0xaa0044 },
    STATUTE:   { district: 'CHAMBER',  height: 20, shape: 'columns',windows: 30, emissive: 0x444444 },
    SCOUT:     { district: 'FLOOR',    height: 16, shape: 'block',  windows: 30, emissive: 0x00aa44 },
    PARCEL:    { district: 'VAULT',    height: 19, shape: 'mixed',  windows: 28, emissive: 0xaa6622 },
    GAIA:      { district: 'OBS',      height: 12, shape: 'dome',   windows: 0,  emissive: 0x0088aa },
    ODDS:      { district: 'CASINO',   height: 17, shape: 'casino', windows: 35, emissive: 0xaa00aa },
    CIPHER:    { district: 'EMBASSY',  height: 21, shape: 'embassy',windows: 32, emissive: 0xaa1111 },
};

let scene, camera, renderer, raycaster, mouse;
let buildings = [];
let buildingMeshes = [];
let windowMaterials = [];
let streetLights = [];
let dataParticles = [];
let clock = new THREE.Clock();

function initCity() {
    const canvas = document.getElementById('city-canvas');

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050510);
    scene.fog = new THREE.FogExp2(0x050510, 0.008);

    // Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 8, 50);

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Raycaster
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    // Lighting
    const ambient = new THREE.AmbientLight(0x1a1a3a, 0.4);
    scene.add(ambient);

    const moon = new THREE.DirectionalLight(0x4466aa, 0.5);
    moon.position.set(50, 100, 50);
    moon.castShadow = true;
    scene.add(moon);

    // Ground
    createGround();

    // Buildings
    createBuildings();

    // Streets
    createStreets();

    // Particles
    createDataFlow();

    // Event listeners
    window.addEventListener('resize', onWindowResize);
    canvas.addEventListener('click', onCanvasClick);
    canvas.addEventListener('mousemove', onMouseMove);

    // Start loop
    animate();

    // Hide loading
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 1500);
}

function createGround() {
    const geo = new THREE.PlaneGeometry(300, 300, 60, 60);

    // Grid shader-like effect via vertex colors
    const colors = [];
    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i);
        const z = pos.getZ(i);
        const dist = Math.sqrt(x*x + z*z);
        const intensity = Math.max(0, 1 - dist / 150);
        colors.push(0.02 * intensity, 0.03 * intensity, 0.08 * intensity);
    }
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const mat = new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.9,
        metalness: 0.1,
    });

    const ground = new THREE.Mesh(geo, mat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // Grid lines
    const gridHelper = new THREE.GridHelper(300, 60, 0x1a2a4a, 0x0a1525);
    gridHelper.position.y = 0.05;
    scene.add(gridHelper);
}

function createBuildings() {
    Object.entries(AGENT_CONFIG).forEach(([agent, config]) => {
        const district = DISTRICTS[config.district];
        const group = new THREE.Group();
        group.position.set(district.x, 0, district.z);

        const color = new THREE.Color(district.color);
        const emissive = new THREE.Color(config.emissive);

        // Main building body
        let bodyGeo, bodyMesh;
        const w = 6, d = 6;

        switch(config.shape) {
            case 'tower':
                bodyGeo = new THREE.BoxGeometry(w, config.height, d);
                break;
            case 'cube':
                bodyGeo = new THREE.BoxGeometry(w + 2, config.height, d + 2);
                break;
            case 'pyramid':
                bodyGeo = new THREE.ConeGeometry(w * 0.8, config.height, 4);
                break;
            case 'dome':
                bodyGeo = new THREE.SphereGeometry(config.height * 0.5, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2);
                break;
            case 'antenna':
                bodyGeo = new THREE.CylinderGeometry(0.5, 1.5, config.height, 8);
                break;
            case 'plant':
                bodyGeo = new THREE.BoxGeometry(w + 4, config.height, d + 4);
                break;
            case 'warehouse':
                bodyGeo = new THREE.BoxGeometry(w + 6, config.height * 0.6, d + 10);
                break;
            case 'casino':
                bodyGeo = new THREE.CylinderGeometry(w, w, config.height, 8);
                break;
            case 'embassy':
                bodyGeo = new THREE.BoxGeometry(w + 3, config.height, d + 3);
                break;
            default:
                bodyGeo = new THREE.BoxGeometry(w, config.height, d);
        }

        const bodyMat = new THREE.MeshStandardMaterial({
            color: color,
            roughness: 0.3,
            metalness: 0.7,
            emissive: emissive,
            emissiveIntensity: 0.1,
        });

        bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
        bodyMesh.position.y = config.height / 2;
        bodyMesh.castShadow = true;
        bodyMesh.receiveShadow = true;
        bodyMesh.userData = { agent: agent, type: 'building' };
        group.add(bodyMesh);
        buildingMeshes.push(bodyMesh);

        // Windows
        if (config.windows > 0 && config.shape !== 'dome' && config.shape !== 'pyramid') {
            const winGeo = new THREE.PlaneGeometry(0.4, 0.6);
            const winMat = new THREE.MeshBasicMaterial({
                color: 0x88ccff,
                transparent: true,
                opacity: 0.6,
            });
            windowMaterials.push({ material: winMat, agent: agent });

            const cols = 4;
            const rows = Math.floor(config.windows / cols);
            for (let r = 0; r < rows; r++) {
                for (let c = 0; c < cols; c++) {
                    const win = new THREE.Mesh(winGeo, winMat.clone());
                    win.position.set(
                        (c - cols/2 + 0.5) * 1.2,
                        2 + r * 2.5,
                        (config.shape === 'warehouse' ? d/2 + 5.1 : d/2 + 0.1)
                    );
                    group.add(win);
                }
            }
        }

        // Glow ring at base
        const ringGeo = new THREE.RingGeometry(w * 0.8, w * 1.2, 32);
        const ringMat = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.3,
            side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 0.1;
        group.add(ring);

        // Label
        const labelDiv = document.createElement('div');
        // (Labels would need CSS2DRenderer; skip for pure canvas)

        buildings.push({
            agent: agent,
            group: group,
            mesh: bodyMesh,
            config: config,
            district: district,
            lastActivity: 0,
        });

        scene.add(group);
    });
}

function createStreets() {
    // Street lights
    const positions = [
        [-40, -40], [-40, 0], [-40, 40],
        [0, -40], [0, 0], [0, 40],
        [40, -40], [40, 0], [40, 40],
    ];

    positions.forEach(([x, z]) => {
        const poleGeo = new THREE.CylinderGeometry(0.05, 0.05, 4, 8);
        const poleMat = new THREE.MeshStandardMaterial({ color: 0x333344 });
        const pole = new THREE.Mesh(poleGeo, poleMat);
        pole.position.set(x, 2, z);
        scene.add(pole);

        const lightGeo = new THREE.SphereGeometry(0.15, 8, 8);
        const lightMat = new THREE.MeshBasicMaterial({ color: 0xffaa44 });
        const lightMesh = new THREE.Mesh(lightGeo, lightMat);
        lightMesh.position.set(x, 4, z);
        scene.add(lightMesh);

        const pointLight = new THREE.PointLight(0xffaa44, 0.5, 15);
        pointLight.position.set(x, 4, z);
        scene.add(pointLight);
        streetLights.push({ mesh: lightMesh, light: pointLight, baseInt: 0.5 });
    });
}

function createDataFlow() {
    // Floating data particles between buildings
    const particleGeo = new THREE.BufferGeometry();
    const count = 200;
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 200;
        positions[i * 3 + 1] = Math.random() * 30 + 2;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 200;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const particleMat = new THREE.PointsMaterial({
        color: 0x00a8ff,
        size: 0.15,
        transparent: true,
        opacity: 0.6,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);
    dataParticles.push(particles);
}

function animate() {
    requestAnimationFrame(animate);

    const time = clock.getElapsedTime();
    const delta = clock.getDelta();

    // Pulse windows
    windowMaterials.forEach((wm, i) => {
        const pulse = Math.sin(time * 2 + i) * 0.3 + 0.5;
        wm.material.opacity = 0.3 + pulse * 0.4;
    });

    // Street light flicker
    streetLights.forEach((sl, i) => {
        const flicker = Math.sin(time * 3 + i * 1.5) * 0.1 + 1;
        sl.light.intensity = sl.baseInt * flicker;
    });

    // Data particles drift
    dataParticles.forEach(p => {
        p.rotation.y = time * 0.02;
        const pos = p.geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) {
            pos.setY(i, pos.getY(i) + Math.sin(time + i) * 0.005);
        }
        pos.needsUpdate = true;
    });

    // Building emissive pulse on activity
    buildings.forEach(b => {
        const activity = b.lastActivity > 0 ? Math.min((Date.now() - b.lastActivity) / 10000, 1) : 1;
        b.mesh.material.emissiveIntensity = 0.1 + (1 - activity) * 0.4;
    });

    renderer.render(scene, camera);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onCanvasClick(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(buildingMeshes);

    if (intersects.length > 0) {
        const building = intersects[0].object;
        const agent = building.userData.agent;
        if (agent) {
            openBuildingPanel(agent);
        }
    }
}

function onMouseMove(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(buildingMeshes);

    document.body.style.cursor = intersects.length > 0 ? 'pointer' : 'default';
}

function pulseBuilding(agentName) {
    const building = buildings.find(b => b.agent === agentName);
    if (building) {
        building.lastActivity = Date.now();
    }
}

// Camera controls (simple WASD + mouse)
let keys = {};
let yaw = 0, pitch = 0;
let isPointerLocked = false;

document.addEventListener('keydown', e => keys[e.code] = true);
document.addEventListener('keyup', e => keys[e.code] = false);

document.addEventListener('mousemove', e => {
    if (!isPointerLocked) return;
    yaw -= e.movementX * 0.002;
    pitch -= e.movementY * 0.002;
    pitch = Math.max(-Math.PI/2.5, Math.min(Math.PI/2.5, pitch));
});

document.addEventListener('dblclick', () => {
    document.body.requestPointerLock();
});

document.addEventListener('pointerlockchange', () => {
    isPointerLocked = document.pointerLockElement === document.body;
});

function updateCamera() {
    const speed = 0.15;
    const forward = new THREE.Vector3(Math.sin(yaw), 0, Math.cos(yaw));
    const right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));

    if (keys['KeyW']) camera.position.addScaledVector(forward, speed);
    if (keys['KeyS']) camera.position.addScaledVector(forward, -speed);
    if (keys['KeyA']) camera.position.addScaledVector(right, -speed);
    if (keys['KeyD']) camera.position.addScaledVector(right, speed);

    camera.rotation.order = 'YXZ';
    camera.rotation.y = yaw;
    camera.rotation.x = pitch;
}

// Override animate to include camera
const _origAnimate = animate;
animate = function() {
    updateCamera();
    _origAnimate();
};

// Expose
window.initCity = initCity;
window.pulseBuilding = pulseBuilding;
window.buildings = buildings;
window.scene = scene;
window.camera = camera;
