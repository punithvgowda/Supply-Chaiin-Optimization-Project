document.addEventListener('DOMContentLoaded', () => {
    // 1. Map Initialization
    const map = L.map('map').setView([20, 78], 3);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' }).addTo(map);

    const markers = {};
    let activeRoutes = [];
    let selectedTruck = null;

    const setupToggle = (id, dropId) => {
        const t = document.getElementById(id);
        const d = document.getElementById(dropId);
        if (t && d) t.onclick = () => { d.style.display = d.style.display === 'none' ? 'block' : 'none'; };
    };
    setupToggle('shipments-toggle', 'shipments-dropdown');
    setupToggle('fleet-health-toggle', 'fleet-health-dropdown');
    setupToggle('alerts-toggle', 'alerts-dropdown');

    async function sync() {
        try {
            const userRes = await fetch('/api/user');
            const userData = await userRes.json();
            if (document.getElementById('user-greeting')) {
                document.getElementById('user-greeting').innerHTML = `Welcome back, <span>${userData.username || 'Guest'}</span>`;
            }

            const [sRes, cRes] = await Promise.all([fetch('/api/shipments'), fetch('/api/control_tower')]);
            if (sRes.status === 401) { window.location.href = '/login'; return; }
            const shipments = (await sRes.json()) || [];
            const ct = (await cRes.json()) || {};

            if (document.getElementById('total-trucks')) document.getElementById('total-trucks').textContent = shipments.length;
            if (document.getElementById('total-hubs')) document.getElementById('total-hubs').textContent = (ct.hubs || []).length;

            // 2. Map Assets - Hubs
            (ct.hubs || []).forEach(h => {
                const k = `hub-${h.name}`;
                if (!markers[k]) {
                    markers[k] = L.marker([h.lat, h.lng], {
                        icon: L.divIcon({
                            className: '',
                            html: `<div style="width:16px;height:16px;background:#10b981;border:2px solid #fff;border-radius:2px;box-shadow:0 0 10px #10b981;"></div>`,
                            iconSize: [16, 16]
                        })
                    }).addTo(map).bindPopup(`<b>Hub:</b> ${h.name}<br>Mgr: ${h.manager || 'N/A'}<br>Status: ${h.status}`);
                }
            });

            // Checkpoints
            (ct.checkpoints || []).forEach(c => {
                const k = `cp-${c.name}`;
                if (!markers[k]) markers[k] = L.marker([c.lat, c.lng], {
                    icon: L.divIcon({
                        className: '',
                        html: `<div style="width:18px;height:18px;background:#f59e0b;clip-path:polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);border:2px solid #fff;box-shadow:0 0 10px #f59e0b;"></div>`,
                        iconSize: [18, 18]
                    })
                }).addTo(map).bindPopup(`<b>Checkpoint:</b> ${c.name}`);
            });

            // Truck markers
            shipments.forEach(s => {
                if (!s.location) return;
                const statusColor = (s.status || '').toLowerCase() === 'delayed' ? '#ef4444' :
                    (s.status || '').toLowerCase() === 'rerouted' ? '#f59e0b' : '#06b6d4';
                const truckHtml = `<div style="display:flex; align-items:center; transform: translate(-8px, -8px);">
                    <div style="width:18px;height:10px;background:${statusColor};border:1px solid #fff;box-shadow:0 0 8px ${statusColor};"></div>
                    <div style="margin-left:4px;background:rgba(3,7,18,0.9);color:#fff;font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px;border:1px solid ${statusColor};white-space:nowrap;">${s.truck_id} · ${s.risk || 0}%</div>
                </div>`;
                if (markers[s.truck_id]) {
                    markers[s.truck_id].setLatLng([s.location.lat, s.location.lng]);
                    markers[s.truck_id].setIcon(L.divIcon({ className: '', html: truckHtml, iconSize: [20, 20], iconAnchor: [10, 10] }));
                } else {
                    markers[s.truck_id] = L.marker([s.location.lat, s.location.lng], {
                        icon: L.divIcon({ className: '', html: truckHtml, iconSize: [20, 20], iconAnchor: [10, 10] })
                    }).addTo(map).bindPopup(`<b>${s.truck_id}</b>`);
                }
            });

            // 3. Feature Cards
            if (document.getElementById('safety-list')) {
                document.getElementById('safety-list').innerHTML = (ct.safety_logs || []).map(l =>
                    `<li style="flex-direction:column; align-items:start; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.03);">
                        <strong>${l.id}</strong><small>Cargo: ${l.cargo} | Seal: ${l.seal}</small>
                    </li>`).join('');
            }
            if (document.getElementById('reviews-list')) {
                document.getElementById('reviews-list').innerHTML = (ct.reviews || []).map(r =>
                    `<li style="flex-direction:column; align-items:start; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.03);">
                        <strong>${r.name}</strong><small>${'★'.repeat(r.rating || 0)} "${r.comment || ''}"</small>
                    </li>`).join('');
            }
            if (document.getElementById('swaps-list')) {
                document.getElementById('swaps-list').innerHTML = (ct.recent_swaps || []).map(s =>
                    `<li style="font-size:0.7rem; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.03);">
                        <div style="display:flex; justify-content:space-between;"><strong>${s.truck}</strong><span style="color:#10b981">${s.status}</span></div>
                        <small style="opacity:0.6">${(s.hash || '').substring(0, 8)} | ${s.gas || 0} ETH</small>
                    </li>`).join('');
            }
            if (document.getElementById('hubs-list')) {
                document.getElementById('hubs-list').innerHTML = (ct.hubs || []).map(h =>
                    `<li style="font-size:0.7rem; padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.03);">
                        <strong>${h.name}</strong><small style="opacity:0.6">Mgr: ${h.manager || 'N/A'}</small>
                    </li>`).join('');
            }

            // Alerts section — TRK-022 always injected
            const alertCont = document.getElementById('alerts-container');
            let alerts = ct.alerts || [];

            // 🔥 Force TRK-022 to always appear in disruptions panel
            const has022 = alerts.some(a => a.truck_id === 'TRK-022');
            if (!has022) {
                alerts = [{
                    truck_id: 'TRK-022',
                    type: 'Heavy Rain',
                    desc: 'TRK-022 main route flooded — heavy rainfall blocking highway',
                    cause: 'Heavy Rain & Flooding on Highway',
                    rec: '🌧️ Take alternate inland bypass — avoids flood zone completely',
                    sev: 'Critical'
                }, ...alerts];
            }

            // Only show trucks with delay > 50% (plus TRK-022 always)
            alerts = alerts.filter(a => a.truck_id === 'TRK-022' || (a.delay > 50 || a.sev === 'Critical' || a.sev === 'High'));

            if (alertCont) {
                alertCont.innerHTML = alerts.length ? alerts.map(a => {
                    const sevColor = a.sev === 'Critical' ? '#ef4444' : (a.sev === 'High' ? '#f59e0b' : '#3b82f6');
                    const icon = a.sev === 'Critical' ? '🌧️' : '⚠️';
                    return `<div class="alert-item" style="background:rgba(239,68,68,0.1); padding:12px; border-radius:12px; margin-bottom:12px; border:1px solid ${sevColor}; cursor:pointer;" onclick="plotRoute('${a.truck_id}')">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong style="color:#fff;">${icon} ${a.truck_id}</strong>
                            <span style="font-size:0.6rem; background:${sevColor}; padding:2px 6px; border-radius:3px; color:#fff;">${a.sev}</span>
                        </div>
                        <p style="font-size:0.8rem; margin:6px 0; color:#fca5a5;">Cause: ${a.cause || 'Unknown'}</p>
                        <p style="font-size:0.75rem; color:#f59e0b;">AI Rec: ${a.rec || 'Analyze'}</p>
                        <p style="font-size:0.65rem; color:#6b7280; margin-top:4px;">Click to analyze route →</p>
                    </div>`;
                }).join('') : '<div style="text-align:center; padding:20px; opacity:0.5;">No active threats</div>';

                if (document.getElementById('alert-badge')) {
                    document.getElementById('alert-badge').textContent = alerts.length;
                }
            }

            // 4. Main Table
            const tbody = document.getElementById('shipments-body');
            if (tbody) {
                tbody.innerHTML = shipments.map(s => `
                <tr>
                    <td><strong>${s.truck_id}</strong><br><small style="color:var(--primary-color)">${s.carbon || 0}kg CO₂</small></td>
                    <td>${(s.origin || 'N/A').split(' ')[0]} ➔ ${(s.destination || 'N/A').split(' ')[0]}<br><small style="opacity:0.6">${(s.dev || 0) > 0 ? '+' + s.dev : s.dev}h ETA dev</small></td>
                    <td><span class="status-badge ${(s.status || '').toLowerCase()}">${s.status || 'Active'}</span><br><small style="color:${(s.prob || 0) > 60 ? '#ef4444' : '#f59e0b'}">${s.prob || 0}% Delay</small></td>
                    <td>${(s.driver || {}).name || 'Unknown'}<br><small>Risk: ${s.risk || 0}</small></td>
                    <td>
                        ${(s.speed || 0).toFixed(0)} km/h<br>
                        <small style="color:#06b6d4;">${s.weather || 'Clear'}</small>
                    </td>
                    <td><small style="font-size:0.65rem; color:#10b981;">AI: ${(s.reason || 'Optimal').substring(0, 25)}...</small></td>
                    <td><button class="action-btn" onclick="plotRoute('${s.truck_id}')">Analyze</button></td>
                </tr>`).join('');
            }

            // 5. Sidebar dropdowns
            const shipDrop = document.getElementById('shipments-dropdown');
            if (shipDrop) shipDrop.innerHTML = shipments.map(s =>
                `<div class="dropdown-item" onclick="plotRoute('${s.truck_id}')"><strong>${s.truck_id}</strong><small>${s.risk || 0}% Risk | ${s.prob || 0}% Prob</small></div>`
            ).join('');

            const healthDrop = document.getElementById('fleet-health-dropdown');
            if (healthDrop) healthDrop.innerHTML = (ct.fleet_health || []).map(f =>
                `<div class="dropdown-item"><strong>${f.id}</strong><small>Next: ${f.service || 'TBD'}</small></div>`
            ).join('');

            const alertsDrop = document.getElementById('alerts-dropdown');
            if (alertsDrop) alertsDrop.innerHTML = alerts.length ? alerts.map(a =>
                `<div class="dropdown-item" onclick="plotRoute('${a.truck_id}')" style="border-left: 2px solid #ef4444;">
                    <strong>${a.truck_id}</strong><small>${a.desc}</small>
                </div>`
            ).join('') : '<div class="dropdown-item" style="opacity:0.5;">No alerts</div>';

            if (document.getElementById('carbon-credits')) {
                document.getElementById('carbon-credits').textContent = Math.round(ct.carbon_credits || 0);
            }

            // Truck selector
            const selector = document.getElementById('truck-selector');
            if (selector) {
                selector.innerHTML = '<option value="">-- Select Asset to Analyze --</option>' +
                    shipments.map(s =>
                        `<option value="${s.truck_id}" ${s.truck_id === selectedTruck ? 'selected' : ''}>${s.truck_id} (${s.status})</option>`
                    ).join('');
            }

        } catch (e) { console.error("Sync Error", e); }
    }

    // ---- ANALYZE / PLOT ROUTE (SINGLE DEFINITION) ----
    window.plotRoute = async function (id) {
        if (!id) return;
        selectedTruck = id;

        const simLabel = document.getElementById('sim-target-label');
        if (simLabel) {
            simLabel.textContent = `Target: ${id}`;
            simLabel.style.color = 'var(--primary-color)';
        }

        const selector = document.getElementById('truck-selector');
        if (selector) selector.value = id;

        try {
            // Step 1: trigger analyze for THIS truck
            await fetch(`/api/analyze/${id}`);

            // Step 2: get route data
            const res = await fetch(`/api/route/${id}`);
            const data = await res.json();

            // Step 3: clear old routes
            activeRoutes.forEach(r => map.removeLayer(r));
            activeRoutes = [];

            document.getElementById('map').scrollIntoView({ behavior: 'smooth', block: 'center' });

            if (!data.current || !data.origin || !data.destination) {
                console.warn("Missing route data for", id);
                return;
            }

            // Step 4: draw main route (cyan dashed)
            const mainRoute = L.polyline([
                [data.origin.lat, data.origin.lng],
                [data.current.lat, data.current.lng],
                [data.destination.lat, data.destination.lng]
            ], {
                color: '#06b6d4',
                weight: 4,
                dashArray: '10, 5'
            }).addTo(map);
            activeRoutes.push(mainRoute);

            // Step 5: draw alt route if present
            if (data.alt_route) {
                const altLayer = L.geoJSON(data.alt_route, {
                    style: {
                        color: '#f59e0b',
                        weight: 6,
                        opacity: 0.85,
                        dashArray: '5, 10'
                    }
                }).addTo(map);
                activeRoutes.push(altLayer);

                // Popup on truck marker
                const truckM = markers[id];
                if (truckM) {
                    truckM.bindPopup(`
                        <b>${id} — High Risk Detected</b><br>
                        <span style="color:#f59e0b;">⚠️ ${data.recommendation || 'Alternate route suggested'}</span><br><br>
                        <button onclick="acceptRoute('${id}')"
                            style="margin-top:5px;background:#10b981;border:none;color:white;padding:4px 10px;border-radius:4px;cursor:pointer;">
                            ✅ Accept Alternate Route
                        </button>
                    `).openPopup();
                }

                showNotification(`⚠️ High risk on ${id}! Alternate route shown in orange.`, 'error');
            } else {
                const truckM = markers[id];
                if (truckM) {
                    truckM.bindPopup(`<b>${id}</b><br>Status: ${data.status || 'In Transit'}<br>Route looks clear ✅`).openPopup();
                }
                showNotification(`✅ ${id} route analyzed — No issues detected.`, 'success');
            }

            map.fitBounds(mainRoute.getBounds(), { padding: [80, 80] });

            // Step 6: refresh UI
            setTimeout(sync, 500);

        } catch (err) {
            console.error("Analyze error:", err);
            showNotification("Failed to analyze route. Check server.", "error");
        }
    };

    window.acceptRoute = (id) => {
        // Close any open popups
        map.closePopup();

        // Clear all existing routes
        activeRoutes.forEach(r => map.removeLayer(r));
        activeRoutes = [];

        // Re-fetch route and draw ONLY the alternate (orange) as the new confirmed route
        fetch(`/api/route/${id}`)
            .then(r => r.json())
            .then(data => {
                if (!data.current || !data.origin || !data.destination) return;

                const cur = data.current;
                const dst = data.destination;

                // Same perpendicular math as backend for consistency
                const mid_lat = (cur.lat + dst.lat) / 2;
                const mid_lng = (cur.lng + dst.lng) / 2;
                const dlat = dst.lat - cur.lat;
                const dlng = dst.lng - cur.lng;
                const length = Math.sqrt(dlat * dlat + dlng * dlng) || 1;
                const perp_lat = -dlng / length;
                const perp_lng = dlat / length;
                const offset_amount = length * 0.25;
                const offset_lat = mid_lat + perp_lat * offset_amount;
                const offset_lng = mid_lng + perp_lng * offset_amount;

                // Draw the accepted alternate route in GREEN (confirmed)
                const acceptedRoute = L.polyline([
                    [cur.lat, cur.lng],
                    [offset_lat, offset_lng],
                    [dst.lat, dst.lng]
                ], {
                    color: '#10b981',   // green = accepted/safe
                    weight: 5,
                    dashArray: null,    // solid line = confirmed route
                    opacity: 1
                }).addTo(map);

                activeRoutes.push(acceptedRoute);

                // Add destination marker
                const destMarker = L.circleMarker([data.destination.lat, data.destination.lng], {
                    color: '#10b981',
                    fillColor: '#10b981',
                    fillOpacity: 0.8,
                    radius: 10
                }).addTo(map).bindPopup(`<b>${id}</b><br>✅ Rerouted successfully!<br>New safe route confirmed.`).openPopup();
                activeRoutes.push(destMarker);

                map.fitBounds(acceptedRoute.getBounds(), { padding: [80, 80] });

                // Update truck marker to green (rerouted)
                const truckM = markers[id];
                if (truckM) {
                    const newHtml = `<div style="display:flex; align-items:center; transform:translate(-8px,-8px);">
                        <div style="width:18px;height:10px;background:#10b981;border:1px solid #fff;box-shadow:0 0 8px #10b981;"></div>
                        <div style="margin-left:4px;background:rgba(3,7,18,0.9);color:#10b981;font-size:9px;font-weight:800;padding:1px 5px;border-radius:3px;border:1px solid #10b981;white-space:nowrap;">${id} · REROUTED</div>
                    </div>`;
                    truckM.setIcon(L.divIcon({ className: '', html: newHtml, iconSize: [20, 20], iconAnchor: [10, 10] }));
                }

                showNotification(`✅ ${id} rerouted successfully! New safe route confirmed.`, 'success');
            })
            .catch(err => console.error("Accept route error:", err));
    };

    window.showNotification = (message, type = 'info') => {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        const color = type === 'success' ? '#10b981' : (type === 'error' ? '#ef4444' : '#00f2ff');
        const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');

        toast.style.cssText = `
            background: rgba(15,23,42,0.95);
            backdrop-filter: blur(10px);
            border-left: 4px solid ${color};
            color: #fff;
            padding: 15px 20px;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            min-width: 300px;
            margin-bottom: 10px;
        `;
        toast.innerHTML = `<div style="display:flex; align-items:center; gap:12px;">
            <span style="font-size:1.2rem;">${icon}</span>
            <span>${message}</span>
        </div>`;
        container.appendChild(toast);

        const logs = document.getElementById('logs-container');
        if (logs) {
            const entry = document.createElement('div');
            entry.style.cssText = `padding:10px; border-bottom:1px solid rgba(255,255,255,0.02); display:flex; justify-content:space-between; align-items:center;`;
            const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            entry.innerHTML = `<span style="color:${color}">${icon} ${message}</span><span style="opacity:0.4; font-size:0.6rem;">${time}</span>`;
            logs.prepend(entry);
        }

        setTimeout(() => toast.remove(), 5000);
    };

    window.runWhatIf = (type) => {
        if (!selectedTruck) {
            showNotification("Please select a truck first by clicking 'Analyze'.", "error");
            return;
        }
        const modal = document.getElementById('sim-modal');
        const body = document.getElementById('modal-body');
        modal.style.display = 'block';

        let html = '';
        if (type === 'courier') {
            showNotification(`Comparing courier options for ${selectedTruck}...`, "info");
            html = `
                <div style="text-align:center; margin-bottom:25px;">
                    <span style="font-size:3rem;">🚚</span>
                    <h2 style="color:var(--primary-color); margin-top:10px;">Change Courier for ${selectedTruck}</h2>
                    <p style="color:var(--text-dim);">We analyzed 15 alternative carriers for this route.</p>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
                    <div class="card" style="background:rgba(255,255,255,0.03); padding:20px; border:1px solid rgba(255,255,255,0.1);">
                        <h4 style="color:var(--text-dim); margin-bottom:15px;">CURRENT OPTION</h4>
                        <p style="font-size:1.1rem; font-weight:700;">TRANZITS</p>
                        <hr style="opacity:0.1; margin:10px 0;">
                        <p>💰 Cost: $450</p><p>⏱ Arrival: 48 hours</p><p>🌿 Carbon: 120kg</p>
                    </div>
                    <div class="card" style="background:rgba(16,185,129,0.05); padding:20px; border:1px solid #10b981;">
                        <h4 style="color:#10b981; margin-bottom:15px;">BETTER OPTION</h4>
                        <p style="font-size:1.1rem; font-weight:700;">BlueDart Express</p>
                        <hr style="opacity:0.1; margin:10px 0;">
                        <p>💰 Cost: <span style="color:#10b981;">$420</span></p>
                        <p>⏱ Arrival: <span style="color:#10b981;">42 hours</span></p>
                        <p>🌿 Carbon: <span style="color:#10b981;">95kg</span></p>
                    </div>
                </div>
                <div style="margin-top:25px; padding:15px; background:rgba(0,242,255,0.05); border-radius:12px; border:1px solid rgba(0,242,255,0.2);">
                    <p style="font-size:0.9rem;"><b>AI Suggestion:</b> Switch to BlueDart. Save <b>$30</b> and arrive <b>6 hours earlier</b>.</p>
                </div>
                <button class="action-btn" style="margin-top:25px; width:100%; height:50px; font-size:1rem;" onclick="closeModal('Courier Update')">Apply This Change</button>`;
        } else if (type === 'tomorrow') {
            showNotification(`Checking tomorrow's weather for ${selectedTruck}...`, "info");
            html = `
                <div style="text-align:center; margin-bottom:25px;">
                    <span style="font-size:3rem;">⏳</span>
                    <h2 style="color:var(--primary-color); margin-top:10px;">Ship Tomorrow? (${selectedTruck})</h2>
                </div>
                <div class="card" style="background:rgba(245,158,11,0.05); border:1px solid #f59e0b; padding:25px; text-align:center;">
                    <h4 style="color:#f59e0b; margin-bottom:10px;">SAFETY PREDICTION</h4>
                    <p style="font-size:1.4rem; font-weight:800;">Risk Drops by 50%</p>
                    <p style="margin-top:10px; color:var(--text-dim);">A storm is passing through. Wait 12 hours for clear conditions.</p>
                </div>
                <div style="margin-top:25px; display:grid; grid-template-columns:1fr 1fr; gap:15px;">
                    <div style="text-align:center; padding:15px; background:rgba(255,255,255,0.03); border-radius:12px;">
                        <small>NOW</small><p style="color:#ef4444; font-weight:700;">65% Risk</p>
                    </div>
                    <div style="text-align:center; padding:15px; background:rgba(16,185,129,0.1); border-radius:12px;">
                        <small>TOMORROW</small><p style="color:#10b981; font-weight:700;">15% Risk</p>
                    </div>
                </div>
                <button class="action-btn" style="margin-top:25px; width:100%; height:50px; font-size:1rem;" onclick="closeModal('Schedule Shift')">Wait Until Tomorrow</button>`;
        } else if (type === 'split') {
            showNotification(`Finding best split for this order...`, "info");
            html = `
                <div style="text-align:center; margin-bottom:25px;">
                    <span style="font-size:3rem;">📦📦</span>
                    <h2 style="color:var(--primary-color); margin-top:10px;">Split This Order? (${selectedTruck})</h2>
                </div>
                <div class="card" style="background:rgba(255,255,255,0.03); border:1px solid var(--primary-color); padding:20px;">
                    <p style="font-weight:700; color:var(--primary-color);">📦 Part 1: URGENT (30%)</p>
                    <p style="font-size:0.85rem; color:var(--text-dim);">Ship via Air. Arrives in 12 hours.</p>
                    <br>
                    <p style="font-weight:700; color:#10b981;">📦 Part 2: STANDARD (70%)</p>
                    <p style="font-size:0.85rem; color:var(--text-dim);">Keep on Truck. Saves $200.</p>
                </div>
                <button class="action-btn" style="margin-top:25px; width:100%; height:50px; font-size:1rem;" onclick="closeModal('Order Split')">Split Order Now</button>`;
        }
        body.innerHTML = html;
    };

    window.closeModal = (actionName) => {
        document.getElementById('sim-modal').style.display = 'none';
        if (actionName) showNotification(`Success! ${actionName} implemented for ${selectedTruck}.`, "success");
    };

    sync();
    setInterval(sync, 5000); // refresh every 5s so velocity/delay updates feel live
});