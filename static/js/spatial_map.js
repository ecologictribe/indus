// Leaflet Spatial GIS Map for Gujarat Industrial Parks
// Features: Multiple Basemaps, Marker Clustering, Buffer Rings, Hover Coordinates

let map = null;
let markersLayer = null;
let clusterGroup = null;
let bufferCirclesLayer = null;
let allParksData = [];
let isClusteringEnabled = true;

function initGujaratMap(containerId = 'leaflet-map', initialParks = []) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Center on Gujarat
    map = L.map(containerId).setView([22.5, 71.8], 7);

    // Basemap Layers (No API Key Required - Resolves Carto Watermark Error)
    const osmStandard = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    });

    const cartoPositron = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    });

    const esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 18
    });

    const openTopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)',
        maxZoom: 17
    });

    // Default to clean Carto Positron / OSM
    cartoPositron.addTo(map);

    // Layer Switcher Control in Top-Right
    const baseMaps = {
        "Light Canvas (Clean)": cartoPositron,
        "OpenStreetMap (Standard)": osmStandard,
        "Satellite Imagery (Esri)": esriSatellite,
        "Topographic / Terrain": openTopo
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

    // Feature Layers
    bufferCirclesLayer = L.layerGroup().addTo(map);
    markersLayer = L.layerGroup();
    
    if (typeof L.markerClusterGroup === 'function') {
        clusterGroup = L.markerClusterGroup({
            chunkedLoading: true,
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false
        });
        clusterGroup.addTo(map);
    } else {
        markersLayer.addTo(map);
    }

    // Coordinates Display on Mouse Move
    const coordsBar = document.getElementById('map-coords-bar');
    map.on('mousemove', function(e) {
        if (coordsBar) {
            coordsBar.innerHTML = `<strong>Coordinates:</strong> Lat: ${e.latlng.lat.toFixed(4)}°, Lng: ${e.latlng.lng.toFixed(4)}° &nbsp;|&nbsp; <strong>Zoom:</strong> ${map.getZoom()}`;
        }
    });

    if (initialParks && initialParks.length > 0) {
        allParksData = initialParks;
        renderParkMarkers(allParksData);
    } else {
        fetch('/api/parks')
            .then(res => res.json())
            .then(data => {
                allParksData = data;
                renderParkMarkers(allParksData);
            })
            .catch(err => console.error("Error loading parks:", err));
    }
}

function getParkMarkerColor(park) {
    if (park.authority_type === 'Private SEZ/Park') {
        return '#8b5cf6'; // Purple
    }
    const cat = (park.sector_category || '').toLowerCase();
    if (cat.includes('chemical') || cat.includes('petro')) return '#ef4444'; // Red
    if (cat.includes('auto')) return '#f59e0b'; // Amber
    if (cat.includes('textile') || cat.includes('apparel')) return '#06b6d4'; // Cyan
    if (cat.includes('tech') || cat.includes('electronic')) return '#10b981'; // Green
    return '#1e3a8a'; // Deep Blue default for GIDC
}

function renderParkMarkers(parks) {
    if (clusterGroup) {
        clusterGroup.clearLayers();
    }
    if (markersLayer) {
        markersLayer.clearLayers();
    }
    if (bufferCirclesLayer) {
        bufferCirclesLayer.clearLayers();
    }

    let count = 0;
    parks.forEach(park => {
        if (!park.latitude || !park.longitude) return;
        count++;

        const color = getParkMarkerColor(park);
        const marker = L.circleMarker([park.latitude, park.longitude], {
            radius: 7,
            fillColor: color,
            color: '#ffffff',
            weight: 1.5,
            opacity: 1,
            fillOpacity: 0.85
        });

        const popupContent = `
            <div style="min-width: 240px; font-family: sans-serif;">
                <div style="font-weight: 700; font-size: 1rem; color: #0f172a; margin-bottom: 4px;">
                    ${park.park_name}
                </div>
                <div style="font-size: 0.8rem; color: #475569; margin-bottom: 8px;">
                    <span class="badge" style="background-color: ${color}; color: white; padding: 2px 6px; border-radius: 4px;">
                        ${park.authority_type || 'GIDC'}
                    </span>
                    <span style="margin-left: 4px;">${park.sector_category || 'Industrial Estate'}</span>
                </div>
                <div style="font-size: 0.82rem; margin-bottom: 4px;">
                    <strong>District:</strong> ${park.district_name || 'N/A'} | <strong>Taluka:</strong> ${park.taluka_name || 'N/A'}
                </div>
                <div style="font-size: 0.82rem; margin-bottom: 4px;">
                    <strong>Area:</strong> ${park.total_area_acres ? park.total_area_acres + ' Acres' : 'N/A'} | 
                    <strong>Year:</strong> ${park.notification_year || 'N/A'}
                </div>
                <div style="font-size: 0.82rem; margin-bottom: 8px;">
                    <strong>CETP Active:</strong> ${park.has_cetp ? '<span style="color:#10b981;font-weight:bold;">Yes</span>' : '<span style="color:#64748b;">No</span>'}
                </div>
                <div style="display: flex; gap: 6px; margin-top: 8px;">
                    <a href="/parks/${park.park_id}" class="btn btn-sm btn-primary" style="font-size: 0.75rem; padding: 3px 8px; color: white; text-decoration: none; background: #1e3a8a; border-radius: 4px;">
                        Profile & Timeline
                    </a>
                    <button onclick="drawSpatialBuffers(${park.latitude}, ${park.longitude}, '${escapeHtml(park.park_name)}')" class="btn btn-sm" style="font-size: 0.75rem; padding: 3px 8px; background: #e2e8f0; border: none; border-radius: 4px; cursor: pointer;">
                        Show Buffers
                    </button>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent);

        if (isClusteringEnabled && clusterGroup) {
            clusterGroup.addLayer(marker);
        } else if (markersLayer) {
            markersLayer.addLayer(marker);
        }
    });

    const counterEl = document.getElementById('map-filtered-count');
    if (counterEl) {
        counterEl.innerText = count;
    }
}

function toggleMarkerClustering() {
    isClusteringEnabled = !isClusteringEnabled;
    const btn = document.getElementById('btnClusterToggle');
    if (btn) {
        btn.innerHTML = `<i class="bi bi-diagram-3 me-1"></i> Clustering: ${isClusteringEnabled ? 'ON' : 'OFF'}`;
        btn.classList.toggle('btn-primary', isClusteringEnabled);
        btn.classList.toggle('btn-outline-secondary', !isClusteringEnabled);
    }

    if (isClusteringEnabled) {
        if (markersLayer) map.removeLayer(markersLayer);
        if (clusterGroup) map.addLayer(clusterGroup);
    } else {
        if (clusterGroup) map.removeLayer(clusterGroup);
        if (markersLayer) map.addLayer(markersLayer);
    }

    filterMapParks();
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/'/g, "\\'");
}

function drawSpatialBuffers(lat, lng, parkName) {
    if (!bufferCirclesLayer) return;
    bufferCirclesLayer.clearLayers();

    // 0.5km Negative Externality Buffer (Red)
    L.circle([lat, lng], {
        radius: 500,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.25,
        weight: 1.5
    }).bindTooltip(`${parkName} (0 - 0.5km Proximity Drag)`).addTo(bufferCirclesLayer);

    // 1.5km Intermediate Transition Buffer (Green)
    L.circle([lat, lng], {
        radius: 1500,
        color: '#10b981',
        fillColor: '#10b981',
        fillOpacity: 0.15,
        weight: 1.5
    }).bindTooltip(`${parkName} (0.5 - 1.5km Intermediate Zone)`).addTo(bufferCirclesLayer);

    // 8.0km Sweet Spot Buffer (Purple)
    L.circle([lat, lng], {
        radius: 8000,
        color: '#8b5cf6',
        fillColor: '#8b5cf6',
        fillOpacity: 0.08,
        weight: 1.5,
        dashArray: '4, 4'
    }).bindTooltip(`${parkName} (3 - 8km Residential Sweet Spot)`).addTo(bufferCirclesLayer);

    map.flyTo([lat, lng], 12);
}

function resetAllMapFilters() {
    const districtEl = document.getElementById('filter-district');
    const categoryEl = document.getElementById('filter-category');
    const searchEl = document.getElementById('filter-search');

    if (districtEl) districtEl.value = 'ALL';
    if (categoryEl) categoryEl.value = 'ALL';
    if (searchEl) searchEl.value = '';

    renderParkMarkers(allParksData);
}

function filterMapParks() {
    const districtVal = document.getElementById('filter-district')?.value || 'ALL';
    const categoryVal = document.getElementById('filter-category')?.value || 'ALL';
    const searchVal = (document.getElementById('filter-search')?.value || '').toLowerCase().trim();

    const filtered = allParksData.filter(p => {
        if (districtVal !== 'ALL' && p.district_name !== districtVal) return false;
        if (categoryVal !== 'ALL') {
            if (categoryVal === 'GIDC' && p.authority_type !== 'GIDC') return false;
            if (categoryVal === 'Private' && p.authority_type !== 'Private SEZ/Park') return false;
            if (categoryVal === 'Chemical' && !(p.sector_category || '').toLowerCase().includes('chemical')) return false;
            if (categoryVal === 'Auto' && !(p.sector_category || '').toLowerCase().includes('auto')) return false;
        }
        if (searchVal) {
            const matchName = (p.park_name || '').toLowerCase().includes(searchVal);
            const matchTaluka = (p.taluka_name || '').toLowerCase().includes(searchVal);
            const matchDist = (p.district_name || '').toLowerCase().includes(searchVal);
            if (!matchName && !matchTaluka && !matchDist) return false;
        }
        return true;
    });

    renderParkMarkers(filtered);
}
