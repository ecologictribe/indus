/**
 * Plot Cadastral Intelligence & Synchronized Spatial Split-View Engine (Task T6)
 * Handles:
 * 1. Synchronized Leaflet Vector Map with Parcel Polygons & Selection Highlighting
 *    - Dual-Mode: Standard Allotment Inventory vs Brownfield Lifecycle Decay & Risk
 * 2. Smart Autocomplete Search (Estate, Plot, Survey #, DILR Cadastral ID)
 * 3. Dual Radar Scorecards:
 *    - 5-Axis Micro-Location Radar Scorecard (Chart.js)
 *    - 6-Axis Senescence & Obsolescence Resilience Radar (Chart.js)
 * 4. In-Estate Price Dispersion Scatterplot with Target Callout Marker
 * 5. In-Estate Distance Decay Spline (Gate to Deep Interior Cul-de-sac)
 * 6. Brownfield Lifecycle Decay Audit & Cadastral Risk Scoring
 * 7. Valuation Waterfall Deconstruction (Step-by-Step Price Formation)
 * 8. Interactive "What-If" Policy Simulator (Road widening, CETP, Estate maturity)
 * 9. Dynamic Drawer Updates and CAD/GIS Exports (GeoJSON, KML, DXF)
 */

let parcelMap = null;
let parcelGeoJsonLayer = null;
let selectedParcelLayer = null;
let radarChartInstance = null;
let dispersionChartInstance = null;
let decaySplineChartInstance = null;

let currentPlotData = null;
let currentTargetPlotId = null;
let currentParcelViewMode = 'standard'; // 'standard' or 'decay'
let currentRadarMode = 'micro'; // 'micro' or 'decay'

// Baseline simulator parameters
let simBaselineValue = 3500;
let simCircleRate = 2500;

// ----------------------------------------------------------------------------
// 1. Synchronized Split View Leaflet Parcel Map
// ----------------------------------------------------------------------------
function initParcelMap(mapContainerId, initialGeoJson, targetPlotId) {
    const mapEl = document.getElementById(mapContainerId);
    if (!mapEl) return;

    currentTargetPlotId = targetPlotId;

    if (parcelMap) {
        parcelMap.remove();
        parcelMap = null;
    }

    // Default center Gujarat
    let centerLat = 22.98;
    let centerLng = 72.38;

    if (initialGeoJson && initialGeoJson.features && initialGeoJson.features.length > 0) {
        const firstCoords = initialGeoJson.features[0].geometry.coordinates[0][0];
        centerLng = firstCoords[0];
        centerLat = firstCoords[1];
    }

    parcelMap = L.map(mapContainerId, {
        center: [centerLat, centerLng],
        zoom: 15,
        zoomControl: true
    });

    // Basemap: CartoDB Positron
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        attribution: '&copy; CartoDB & OpenStreetMap'
    }).addTo(parcelMap);

    renderParcelGeoJson(initialGeoJson, targetPlotId);
}

function getParcelStyle(feature, targetPlotId) {
    const p = feature.properties;
    const isTarget = (p.plot_id === targetPlotId);

    if (currentParcelViewMode === 'decay') {
        const decayFill = p.decay_fill_color || '#64748b';
        const strokeCol = isTarget ? '#b45309' : (p.stroke_color || '#1e293b');
        const strokeW = isTarget ? 3.5 : (p.stroke_width || 1.5);
        return {
            fillColor: isTarget ? '#f59e0b' : decayFill,
            weight: strokeW,
            opacity: 1,
            color: strokeCol,
            fillOpacity: isTarget ? 0.85 : 0.65
        };
    } else {
        const standardFill = p.fill_color || '#3b82f6';
        return {
            fillColor: isTarget ? '#f59e0b' : standardFill,
            weight: isTarget ? 3 : 1.5,
            opacity: 1,
            color: isTarget ? '#b45309' : '#1e293b',
            fillOpacity: isTarget ? 0.75 : 0.45
        };
    }
}

function getParcelTooltipContent(p) {
    if (currentParcelViewMode === 'decay') {
        return `<strong>${p.plot_id}</strong> (Plot #${p.plot_number})<br>` +
               `Lifecycle: <span class="badge bg-dark">${p.lifecycle_state || 'Stable Mature'}</span><br>` +
               `Decay Risk: <strong>${p.decay_score !== undefined ? p.decay_score : 35}/100</strong><br>` +
               `Ingress (LIF): <strong>${p.lif || 1.15}</strong><br>` +
               `Rate: ₹${Number(p.price_sqm).toLocaleString()}/sqm`;
    } else {
        return `<strong>${p.plot_id}</strong> (Plot #${p.plot_number})<br>` +
               `Status: <strong>${p.status}</strong><br>` +
               `Area: ${Number(p.area_sqm).toLocaleString()} sqm<br>` +
               `Rate: ₹${Number(p.price_sqm).toLocaleString()}/sqm`;
    }
}

function renderParcelGeoJson(geoJsonData, targetPlotId) {
    if (!parcelMap || !geoJsonData) return;
    currentTargetPlotId = targetPlotId;

    if (parcelGeoJsonLayer) {
        parcelMap.removeLayer(parcelGeoJsonLayer);
    }

    parcelGeoJsonLayer = L.geoJSON(geoJsonData, {
        style: function(feature) {
            return getParcelStyle(feature, targetPlotId);
        },
        onEachFeature: function(feature, layer) {
            const p = feature.properties;
            layer.bindTooltip(getParcelTooltipContent(p), { sticky: true });

            layer.on('click', function() {
                selectPlotById(p.plot_id);
            });

            if (p.plot_id === targetPlotId) {
                selectedParcelLayer = layer;
            }
        }
    }).addTo(parcelMap);

    // Zoom to fit bounds
    if (parcelGeoJsonLayer.getBounds().isValid()) {
        parcelMap.fitBounds(parcelGeoJsonLayer.getBounds(), { padding: [25, 25] });
    }
}

// Switch between Standard Allotment View and Brownfield Decay & Risk View
function setParcelViewMode(mode) {
    currentParcelViewMode = mode;
    const btnStd = document.getElementById('btnModeStandard');
    const btnDec = document.getElementById('btnModeDecay');
    const legStd = document.getElementById('standardLegendItems');
    const legDec = document.getElementById('decayLegendItems');

    if (mode === 'decay') {
        if (btnStd) { btnStd.className = 'btn btn-outline-primary'; }
        if (btnDec) { btnDec.className = 'btn btn-danger'; }
        if (legStd) { legStd.classList.add('d-none'); legStd.classList.remove('d-flex'); }
        if (legDec) { legDec.classList.remove('d-none'); legDec.classList.add('d-flex'); }
    } else {
        if (btnStd) { btnStd.className = 'btn btn-primary'; }
        if (btnDec) { btnDec.className = 'btn btn-outline-danger'; }
        if (legStd) { legStd.classList.remove('d-none'); legStd.classList.add('d-flex'); }
        if (legDec) { legDec.classList.add('d-none'); legDec.classList.remove('d-flex'); }
    }

    if (parcelGeoJsonLayer) {
        parcelGeoJsonLayer.eachLayer(layer => {
            const style = getParcelStyle(layer.feature, currentTargetPlotId);
            layer.setStyle(style);
            layer.setTooltipContent(getParcelTooltipContent(layer.feature.properties));
        });
    }
}

// ----------------------------------------------------------------------------
// 2. Select Plot by ID (Asynchronous Drawer & Map Sync)
// ----------------------------------------------------------------------------
function selectPlotById(plotId) {
    fetch(`/api/plot/detail/${plotId}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                return;
            }
            updatePlotDrawer(data);
            highlightMapParcel(plotId);
        })
        .catch(err => console.error('Failed to fetch plot details:', err));
}

function highlightMapParcel(plotId) {
    currentTargetPlotId = plotId;
    if (!parcelGeoJsonLayer) return;

    parcelGeoJsonLayer.eachLayer(layer => {
        const featPlotId = layer.feature.properties.plot_id;
        const style = getParcelStyle(layer.feature, plotId);
        layer.setStyle(style);
        layer.setTooltipContent(getParcelTooltipContent(layer.feature.properties));

        if (featPlotId === plotId) {
            layer.bringToFront();
            if (parcelMap) {
                parcelMap.panTo(layer.getBounds().getCenter());
            }
        }
    });
}

// ----------------------------------------------------------------------------
// 3. Update Intelligence Drawer UI Components
// ----------------------------------------------------------------------------
function updatePlotDrawer(data) {
    currentPlotData = data;
    currentTargetPlotId = data.plot_id;
    simBaselineValue = data.valuation_gauge.model_fair_value;
    simCircleRate = data.valuation_gauge.jantar_circle_rate;

    // 1. Badges and Text
    const idEl = document.getElementById('drawerPlotId');
    if (idEl) idEl.innerText = data.plot_id;

    const noEl = document.getElementById('drawerPlotNumber');
    if (noEl) noEl.innerText = 'Plot #' + data.plot_number;

    const nameEl = document.getElementById('drawerParkName');
    if (nameEl) nameEl.innerText = data.park_name;

    const locEl = document.getElementById('drawerLocation');
    if (locEl) locEl.innerText = `${data.taluka}, ${data.district}`;

    const survEl = document.getElementById('drawerSurveyNo');
    if (survEl) survEl.innerText = data.survey_number;

    const dilrEl = document.getElementById('drawerDilrId');
    if (dilrEl) dilrEl.innerText = data.dilr_cadastral_id;
    
    // Status Badge
    const statusEl = document.getElementById('drawerStatusBadge');
    if (statusEl) {
        statusEl.innerText = data.status;
        statusEl.className = 'badge ' + (data.status === 'Available' ? 'bg-success' : (data.status === 'Occupied' ? 'bg-primary' : 'bg-warning text-dark'));
    }

    // Physical Specs
    const areaSqmEl = document.getElementById('drawerAreaSqm');
    if (areaSqmEl) areaSqmEl.innerText = Number(data.plot_area_sqm).toLocaleString() + ' sqm';

    const areaSqftEl = document.getElementById('drawerAreaSqft');
    if (areaSqftEl) areaSqftEl.innerText = Number(data.plot_area_sqft).toLocaleString() + ' sqft';

    const catEl = document.getElementById('drawerCategory');
    if (catEl) catEl.innerText = data.category;

    const roadEl = document.getElementById('drawerRoadWidth');
    if (roadEl) roadEl.innerText = `${data.road_width_m}m (${data.frontage_m}m Front)`;

    const cornerEl = document.getElementById('drawerCornerBadge');
    if (cornerEl) {
        cornerEl.innerHTML = data.is_corner_plot 
            ? '<span class="badge bg-success-subtle text-success border">Yes (Corner Lot)</span>' 
            : '<span class="text-muted">Standard</span>';
    }

    // 2. Brownfield Decay & Lifecycle Vulnerability Audit
    if (data.decay_metrics) {
        const dm = data.decay_metrics;
        const lifeEl = document.getElementById('drawerLifecycleBadge');
        if (lifeEl) {
            lifeEl.innerText = dm.lifecycle_state.replace('_', ' ');
            const badgeClasses = {
                'Active_Production': 'badge bg-success',
                'Stable_Mature': 'badge bg-primary',
                'Underutilized_Speculative': 'badge bg-warning text-dark',
                'Distressed_Auction': 'badge bg-danger',
                'Environmental_Brownfield': 'badge text-white',
                'At_Risk_Stagnant': 'badge bg-danger text-white'
            };
            lifeEl.className = badgeClasses[dm.lifecycle_state] || 'badge bg-secondary';
            if (dm.lifecycle_state === 'Environmental_Brownfield') {
                lifeEl.style.backgroundColor = '#8b5cf6';
            } else {
                lifeEl.style.backgroundColor = '';
            }
        }

        const scoreEl = document.getElementById('drawerDecayScore');
        if (scoreEl) scoreEl.innerText = `${dm.decay_vulnerability_score} / 100`;

        const barEl = document.getElementById('drawerDecayBar');
        if (barEl) {
            barEl.style.width = `${dm.decay_vulnerability_score}%`;
            barEl.className = 'progress-bar ' + (dm.decay_vulnerability_score > 65 ? 'bg-danger' : (dm.decay_vulnerability_score > 40 ? 'bg-warning' : 'bg-success'));
        }

        const feiEl = document.getElementById('drawerFEI');
        if (feiEl) feiEl.innerText = dm.frontage_efficiency_index;

        const lifEl = document.getElementById('drawerLIF');
        if (lifEl) lifEl.innerText = dm.logistical_ingress_factor;

        const samEl = document.getElementById('drawerSAM');
        if (samEl) samEl.innerText = `${dm.speculation_arbitrage_multiple}x`;

        const sfrEl = document.getElementById('drawerSFR');
        if (sfrEl) sfrEl.innerText = `${(dm.stranded_footprint_ratio * 100).toFixed(1)}%`;

        const ediEl = document.getElementById('drawerEDI');
        if (ediEl) ediEl.innerText = `${dm.estate_decay_index} EDI`;

        const bmrEl = document.getElementById('drawerBMR');
        if (bmrEl) bmrEl.innerText = `${dm.brownfield_morbidity_ratio_pct}%`;

        const curfewEl = document.getElementById('drawerCurfewBadge');
        if (curfewEl) {
            curfewEl.innerHTML = `<i class="bi bi-clock-history me-1"></i>Curfew: ${dm.freight_curfew_hours_per_day}h/day`;
        }

        const chokeEl = document.getElementById('drawerChokeAlert');
        if (chokeEl) {
            if (dm.is_truck_choked || dm.is_pencil_plot) {
                chokeEl.classList.remove('d-none');
            } else {
                chokeEl.classList.add('d-none');
            }
        }
    }

    // 3. Valuation Benchmark Gauge
    const vg = data.valuation_gauge;
    if (vg) {
        const valCircle = document.getElementById('valCircleRate');
        if (valCircle) valCircle.innerText = '₹' + Number(vg.jantar_circle_rate).toLocaleString();

        const valFair = document.getElementById('valModelFair');
        if (valFair) valFair.innerText = '₹' + Number(vg.model_fair_value).toLocaleString();

        const valCi = document.getElementById('valCiBand');
        if (valCi) valCi.innerText = `[₹${Number(vg.fair_val_ci_low).toLocaleString()} – ₹${Number(vg.fair_val_ci_high).toLocaleString()}]`;

        const valCurr = document.getElementById('valCurrent');
        if (valCurr) valCurr.innerText = '₹' + Number(vg.current_price).toLocaleString();
        
        const deltaEl = document.getElementById('valDeltaBadge');
        if (deltaEl) {
            deltaEl.innerText = `${vg.delta_pct >= 0 ? '+' : ''}${vg.delta_pct}% (${vg.valuation_status})`;
            deltaEl.className = 'badge ' + (vg.delta_pct > 5 ? 'bg-warning-subtle text-dark border' : 'bg-success-subtle text-success border');
        }
    }

    // 4. Valuation Waterfall Deconstruction Breakdown
    if (data.valuation_waterfall) {
        const wf = data.valuation_waterfall;
        const setVal = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        };

        setVal('drawerWfBase', `₹${Number(wf.base_gidc_price_sqm || wf.base_allotment_price || 3500).toLocaleString()}/sqm`);
        setVal('drawerWfRoad', `+₹${Number(wf.road_width_premium_sqm || 0).toLocaleString()}`);
        setVal('drawerWfCorner', `+₹${Number(wf.corner_premium_sqm || 0).toLocaleString()}`);
        setVal('drawerWfDist', `-₹${Number(wf.distance_decay_drag_sqm || 0).toLocaleString()}`);
        setVal('drawerWfChoke', `-₹${Number(wf.truck_choke_penalty_sqm || 0).toLocaleString()}`);
        setVal('drawerWfCepi', `-₹${Number(wf.cepi_pollution_discount_sqm || 0).toLocaleString()}`);
        setVal('drawerWfCurfew', `-₹${Number(wf.urban_curfew_discount_sqm || 0).toLocaleString()}`);
        setVal('drawerWfNet', `₹${Number(wf.net_model_fair_value_sqm || wf.net_appraised_fair_value || 3500).toLocaleString()}/sqm`);
    }

    // Reset Policy Simulator Sliders
    const roadSlider = document.getElementById('simRoadSlider');
    if (roadSlider) {
        roadSlider.value = data.road_width_m || 18;
        document.getElementById('simRoadVal').innerText = (data.road_width_m || 18) + 'm';
        document.getElementById('simCetpCheck').checked = false;
        document.getElementById('simMaturitySlider').value = 5;
        document.getElementById('simMaturityVal').innerText = '5 yrs';
        recalculatePolicySimulator();
    }

    // 5. Multimodal Radial Distances Inset
    const radialContainer = document.getElementById('drawerRadialContainer');
    if (radialContainer && data.radial_infrastructure) {
        radialContainer.innerHTML = data.radial_infrastructure.map(r => `
            <div class="col-6 col-sm-4 col-md">
                <div class="p-2 bg-white rounded border text-center shadow-sm h-100">
                    <i class="bi ${r.icon} text-primary fs-5"></i>
                    <div class="fw-bold text-dark mt-1" style="font-size: 0.88rem;">${r.distance_km} km</div>
                    <div class="text-muted small text-truncate" style="font-size: 0.72rem;" title="${r.name}">${r.name}</div>
                </div>
            </div>
        `).join('');
    }

    // 6. Comps Matrix
    const compsBody = document.getElementById('drawerCompsBody');
    if (compsBody && data.comps_matrix) {
        compsBody.innerHTML = data.comps_matrix.map(c => `
            <tr>
                <td class="font-monospace fw-semibold"><a href="javascript:void(0)" onclick="selectPlotById('${c.plot_id}')">${c.plot_id}</a></td>
                <td>${Number(c.plot_area_sqm).toLocaleString()} sqm</td>
                <td>${c.road_width_m}m</td>
                <td><span class="badge ${c.status === 'Available' ? 'bg-success-subtle text-success' : 'bg-light text-dark border'}">${c.status}</span></td>
                <td class="fw-bold">₹${Number(c.price_sqm).toLocaleString()}</td>
                <td>${c.dist_to_gate_m}m</td>
            </tr>
        `).join('');
    }

    // 7. Update Action Links (Dossier & Exports)
    const dosLink = document.getElementById('drawerDossierLink');
    if (dosLink) dosLink.href = `/plot-dossier/${data.plot_id}`;

    const geoLink = document.getElementById('exportGeoJsonLink');
    if (geoLink) geoLink.href = `/api/plot/export/geojson/${data.plot_id}`;

    const kmlLink = document.getElementById('exportKmlLink');
    if (kmlLink) kmlLink.href = `/api/plot/export/kml/${data.plot_id}`;

    const dxfLink = document.getElementById('exportDxfLink');
    if (dxfLink) dxfLink.href = `/api/plot/export/dxf/${data.plot_id}`;

    // 8. Update Dual Radar Chart
    switchRadarMode(currentRadarMode);

    // 9. Update Dispersion Scatterplot
    updateDispersionChart(data.dispersion_points, data.plot_id);

    // 10. Update In-Estate Distance Decay Spline
    const gateDist = (data.comps_matrix && data.comps_matrix.length > 0) ? data.comps_matrix[0].dist_to_gate_m : 280;
    updateDecaySplineChart(data.park_id, data.plot_id, gateDist, data.allotment_price_sqm);
}

// ----------------------------------------------------------------------------
// 4. Dual Radar Scorecards (Micro-Location vs Senescence)
// ----------------------------------------------------------------------------
function switchRadarMode(mode) {
    currentRadarMode = mode;
    const btnMicro = document.getElementById('btnRadarMicro');
    const btnDecay = document.getElementById('btnRadarDecay');
    const subBadge = document.getElementById('radarSubBadge');

    if (mode === 'decay') {
        if (btnMicro) btnMicro.classList.remove('active');
        if (btnDecay) btnDecay.classList.add('active');
        if (subBadge) {
            subBadge.innerText = 'Senescence Resilience (0=Vulnerable, 100=Robust)';
            subBadge.className = 'badge bg-danger-subtle text-danger border';
        }
        if (currentPlotData && currentPlotData.vulnerability_radar) {
            renderRadarChart(currentPlotData.vulnerability_radar, 'Senescence & Obsolescence Resilience', '#ef4444', 'rgba(239, 68, 68, 0.25)');
        }
    } else {
        if (btnMicro) btnMicro.classList.add('active');
        if (btnDecay) btnDecay.classList.remove('active');
        if (subBadge) {
            subBadge.innerText = 'Normalized Index 0–100';
            subBadge.className = 'badge bg-primary-subtle text-primary border';
        }
        if (currentPlotData && currentPlotData.radar_scores) {
            renderRadarChart(currentPlotData.radar_scores, 'Plot Micro-Location Suitability', '#3b82f6', 'rgba(59, 130, 246, 0.25)');
        }
    }
}

function renderRadarChart(radarData, datasetLabel, borderColor, bgColor) {
    const ctx = document.getElementById('drawerRadarCanvas');
    if (!ctx || !radarData) return;

    if (radarChartInstance) {
        radarChartInstance.destroy();
    }

    const labels = radarData.labels;
    const scores = radarData.scores || radarData.values;

    radarChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: datasetLabel,
                data: scores,
                backgroundColor: bgColor,
                borderColor: borderColor,
                borderWidth: 2,
                pointBackgroundColor: borderColor,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: { stepSize: 20, display: false },
                    pointLabels: { font: { size: 10, weight: 'bold' } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: context => `${context.label}: ${context.raw} / 100`
                    }
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// 5. In-Estate Distance Decay Spline Chart
// ----------------------------------------------------------------------------
function updateDecaySplineChart(parkId, targetPlotId, targetGateDist, targetPrice) {
    const ctx = document.getElementById('estateDecaySplineCanvas');
    if (!ctx) return;

    fetch(`/api/estate/obsolescence-profile/${parkId}`)
        .then(res => res.json())
        .then(profile => {
            if (!profile || !profile.internal_decay_curve) return;

            if (decaySplineChartInstance) {
                decaySplineChartInstance.destroy();
            }

            const curvePoints = profile.internal_decay_curve.map(pt => ({
                x: pt.distance_from_gate_m,
                y: pt.realized_price_sqm
            }));

            // Target parcel point on the spline
            const targetDist = targetGateDist || 280;
            const targetRealized = targetPrice || (curvePoints[0].y * 0.94);
            const targetPoint = [{ x: targetDist, y: targetRealized }];

            const noteEl = document.getElementById('targetDecayPlotNote');
            if (noteEl) {
                noteEl.innerHTML = `<i class="bi bi-pin-map-fill text-warning me-1"></i>Target Plot: ${targetDist}m from Gate (₹${Number(targetRealized).toLocaleString()}/sqm)`;
            }

            const badgeEl = document.getElementById('estateDecayRateBadge');
            if (badgeEl) {
                badgeEl.innerText = `EDI: ${profile.estate_decay_index} | Morbidity: ${profile.brownfield_morbidity_ratio_pct}%`;
            }

            decaySplineChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [
                        {
                            label: 'Gate-to-Cul-de-sac Price Decay Spline',
                            data: curvePoints,
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.08)',
                            fill: true,
                            tension: 0.35,
                            borderWidth: 2.5,
                            pointRadius: 3,
                            pointHoverRadius: 5
                        },
                        {
                            label: 'Selected Target Plot',
                            data: targetPoint,
                            borderColor: '#b45309',
                            backgroundColor: '#f59e0b',
                            pointRadius: 9,
                            pointHoverRadius: 11,
                            pointStyle: 'star',
                            showLine: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'linear',
                            title: { display: true, text: 'Distance from Estate Gate (meters)' },
                            grid: { color: '#f1f5f9' },
                            ticks: { callback: v => v + 'm' }
                        },
                        y: {
                            title: { display: true, text: 'Realized Rate (₹/sqm)' },
                            ticks: { callback: v => '₹' + Number(v).toLocaleString() },
                            grid: { color: '#f1f5f9' }
                        }
                    },
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10 } } },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const pt = context.raw;
                                    return `${context.dataset.label}: ${pt.x}m @ ₹${Number(pt.y).toLocaleString()}/sqm`;
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(err => console.error('Failed to load estate decay spline:', err));
}

// ----------------------------------------------------------------------------
// 6. In-Estate Price Dispersion Scatterplot
// ----------------------------------------------------------------------------
function updateDispersionChart(dispPoints, targetPlotId) {
    const ctx = document.getElementById('drawerDispersionCanvas');
    if (!ctx || !dispPoints) return;

    if (dispersionChartInstance) {
        dispersionChartInstance.destroy();
    }

    const standardPoints = [];
    const targetPoint = [];

    dispPoints.forEach(p => {
        const item = { x: p.area_sqm, y: p.price_sqm, plot_id: p.plot_id, plot_no: p.plot_number };
        if (p.is_target) {
            targetPoint.push(item);
        } else {
            standardPoints.push(item);
        }
    });

    dispersionChartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Estate Parcel Comps',
                    data: standardPoints,
                    backgroundColor: '#64748b',
                    borderColor: '#334155',
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Target Parcel (Selected)',
                    data: targetPoint,
                    backgroundColor: '#f59e0b',
                    borderColor: '#b45309',
                    pointRadius: 9,
                    pointHoverRadius: 11,
                    pointStyle: 'star'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10 } } },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const raw = context.raw;
                            return `${raw.plot_id} (#${raw.plot_no}): ${Number(raw.x).toLocaleString()} sqm @ ₹${Number(raw.y).toLocaleString()}/sqm`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Plot Area (sqm)' },
                    grid: { color: '#f1f5f9' }
                },
                y: {
                    title: { display: true, text: 'Price (₹/sqm)' },
                    ticks: { callback: v => '₹' + Number(v).toLocaleString() },
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// 7. Interactive "What-If" Policy Simulator Calculator
// ----------------------------------------------------------------------------
function recalculatePolicySimulator() {
    const roadSlider = document.getElementById('simRoadSlider');
    if (!roadSlider) return;

    const roadWidth = parseFloat(roadSlider.value);
    const hasCetpUpgrade = document.getElementById('simCetpCheck').checked;
    const maturityYears = parseInt(document.getElementById('simMaturitySlider').value);

    document.getElementById('simRoadVal').innerText = roadWidth + 'm';
    document.getElementById('simMaturityVal').innerText = maturityYears + ' yrs';

    // Model coefficients:
    // Road: +0.85% per meter above 18m
    const roadDeltaPct = (roadWidth - 18.0) * 0.85;
    // CETP: +12.4% capitalization impact if upgraded to Zero Liquid Discharge
    const cetpDeltaPct = hasCetpUpgrade ? 12.4 : 0.0;
    // Maturity: +1.2% per year of estate maturation
    const maturityDeltaPct = (maturityYears - 5) * 1.2;

    const totalSimImpactPct = roadDeltaPct + cetpDeltaPct + maturityDeltaPct;
    const projectedFairVal = Math.round(simBaselineValue * (1 + totalSimImpactPct / 100.0));
    const deltaRupees = projectedFairVal - Math.round(simBaselineValue);

    document.getElementById('simProjectedPrice').innerText = '₹' + projectedFairVal.toLocaleString() + ' / sqm';
    
    const impactEl = document.getElementById('simImpactDelta');
    impactEl.innerText = `${totalSimImpactPct >= 0 ? '+' : ''}${totalSimImpactPct.toFixed(1)}% (₹${deltaRupees >= 0 ? '+' : ''}${deltaRupees.toLocaleString()})`;
    impactEl.className = 'badge ' + (totalSimImpactPct >= 0 ? 'bg-success text-white' : 'bg-danger text-white');
}

// ----------------------------------------------------------------------------
// 8. Smart Autocomplete Search Bar
// ----------------------------------------------------------------------------
function initPlotAutocompleteSearch(inputId, resultsDropdownId) {
    const inputEl = document.getElementById(inputId);
    const dropdownEl = document.getElementById(resultsDropdownId);
    if (!inputEl || !dropdownEl) return;

    let debounceTimer = null;

    inputEl.addEventListener('input', function() {
        const query = this.value.trim();
        clearTimeout(debounceTimer);
        if (query.length < 2) {
            dropdownEl.classList.add('d-none');
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/plot/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(items => {
                    if (!items || items.length === 0) {
                        dropdownEl.innerHTML = '<div class="p-2 text-muted small">No parcels found.</div>';
                    } else {
                        dropdownEl.innerHTML = items.map(item => `
                            <a href="javascript:void(0)" class="dropdown-item p-2 border-bottom" onclick="selectFromSearch('${item.plot_id}')">
                                <div class="d-flex justify-content-between align-items-center">
                                    <strong class="text-primary font-monospace">${item.plot_id}</strong>
                                    <span class="badge ${item.status === 'Available' ? 'bg-success' : 'bg-secondary'}">${item.status}</span>
                                </div>
                                <div class="small text-dark mt-1">${item.park_name} &bull; ${item.district}</div>
                                <div class="small text-muted">${Number(item.area_sqm).toLocaleString()} sqm &bull; ₹${Number(item.price_sqm).toLocaleString()}/sqm</div>
                            </a>
                        `).join('');
                    }
                    dropdownEl.classList.remove('d-none');
                })
                .catch(err => console.error(err));
        }, 250);
    });

    // Close dropdown on outside click
    document.addEventListener('click', function(e) {
        if (!inputEl.contains(e.target) && !dropdownEl.contains(e.target)) {
            dropdownEl.classList.add('d-none');
        }
    });
}

function selectFromSearch(plotId) {
    const dropdownEl = document.getElementById('searchDropdownResults');
    if (dropdownEl) dropdownEl.classList.add('d-none');
    selectPlotById(plotId);
}
