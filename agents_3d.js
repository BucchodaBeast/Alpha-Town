// Alpha Town — Agent Avatars & City Life

const AVATARS = {};
let avatarMeshes = [];

function createAgentAvatars() {
    // Create small floating avatars that move between buildings
    const avatarGeo = new THREE.IcosahedronGeometry(0.3, 1);

    Object.keys(AGENT_CONFIG).forEach((agent, i) => {
        const config = AGENT_CONFIG[agent];
        const district = DISTRICTS[config.district];
        const color = new THREE.Color(district.color);

        const mat = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.5,
            roughness: 0.2,
            metalness: 0.8,
        });

        const mesh = new THREE.Mesh(avatarGeo, mat);

        // Start near their building
        mesh.position.set(
            district.x + (Math.random() - 0.5) * 8,
            1.5 + Math.random() * 2,
            district.z + (Math.random() - 0.5) * 8
        );

        mesh.userData = {
            agent: agent,
            homeX: district.x,
            homeZ: district.z,
            targetX: district.x,
            targetZ: district.z,
            speed: 0.02 + Math.random() * 0.03,
            bobOffset: Math.random() * Math.PI * 2,
            state: 'idle',
            idleTime: 0,
        };

        // Trail
        const trailGeo = new THREE.BufferGeometry();
        const trailCount = 20;
        const trailPos = new Float32Array(trailCount * 3);
        for (let j = 0; j < trailCount; j++) {
            trailPos[j * 3] = mesh.position.x;
            trailPos[j * 3 + 1] = mesh.position.y;
            trailPos[j * 3 + 2] = mesh.position.z;
        }
        trailGeo.setAttribute('position', new THREE.BufferAttribute(trailPos, 3));

        const trailMat = new THREE.PointsMaterial({
            color: color,
            size: 0.08,
            transparent: true,
            opacity: 0.4,
        });

        const trail = new THREE.Points(trailGeo, trailMat);
        scene.add(trail);

        AVATARS[agent] = { mesh, trail, trailPositions: [] };
        avatarMeshes.push(mesh);
        scene.add(mesh);
    });
}

function updateAvatars(time) {
    Object.entries(AVATARS).forEach(([agent, data]) => {
        const mesh = data.mesh;
        const ud = mesh.userData;

        // Bobbing motion
        mesh.position.y = 1.5 + Math.sin(time * 2 + ud.bobOffset) * 0.3;
        mesh.rotation.x = time * 0.5 + ud.bobOffset;
        mesh.rotation.y = time * 0.3;

        // Movement AI
        if (ud.state === 'idle') {
            ud.idleTime -= 0.016;
            if (ud.idleTime <= 0) {
                // Pick new target — either home district or random nearby
                if (Math.random() > 0.3) {
                    ud.targetX = ud.homeX + (Math.random() - 0.5) * 15;
                    ud.targetZ = ud.homeZ + (Math.random() - 0.5) * 15;
                } else {
                    // Visit another district
                    const otherAgents = Object.keys(AGENT_CONFIG).filter(a => a !== agent);
                    const target = otherAgents[Math.floor(Math.random() * otherAgents.length)];
                    const targetDistrict = DISTRICTS[AGENT_CONFIG[target].district];
                    ud.targetX = targetDistrict.x + (Math.random() - 0.5) * 5;
                    ud.targetZ = targetDistrict.z + (Math.random() - 0.5) * 5;
                }
                ud.state = 'moving';
            }
        } else if (ud.state === 'moving') {
            const dx = ud.targetX - mesh.position.x;
            const dz = ud.targetZ - mesh.position.z;
            const dist = Math.sqrt(dx * dx + dz * dz);

            if (dist < 0.5) {
                ud.state = 'idle';
                ud.idleTime = 2 + Math.random() * 4;
            } else {
                mesh.position.x += (dx / dist) * ud.speed;
                mesh.position.z += (dz / dist) * ud.speed;
            }
        }

        // Update trail
        data.trailPositions.unshift(mesh.position.clone());
        if (data.trailPositions.length > 20) data.trailPositions.pop();

        const positions = data.trail.geometry.attributes.position.array;
        for (let i = 0; i < data.trailPositions.length; i++) {
            positions[i * 3] = data.trailPositions[i].x;
            positions[i * 3 + 1] = data.trailPositions[i].y - 0.2;
            positions[i * 3 + 2] = data.trailPositions[i].z;
        }
        data.trail.geometry.attributes.position.needsUpdate = true;
    });
}

// Override animate to include avatars
const _districtsAnimate = animate;
animate = function() {
    const time = clock.getElapsedTime();
    updateAvatars(time);
    _districtsAnimate();
};

window.createAgentAvatars = createAgentAvatars;
window.updateAvatars = updateAvatars;
