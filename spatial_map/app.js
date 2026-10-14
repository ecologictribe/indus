/* ==========================================================================
   Gujarat Industrial Estates Atlas
   Geographic browser over 312 GIDC estates + government-sanctioned private
   industrial parks. The source CSV has no coordinates; placement is derived
   (see the "How placement was derived" panel) and every record carries its
   own confidence so the map never overstates precision.
   ========================================================================== */

(function () {
  'use strict';

  var PARKS = window.GJ_PARKS || [];
  var DISTRICTS = window.GJ_DISTRICTS || { features: [] };
  var META = window.GJ_META || { stats: {}, districtRows: [], seats: {} };

  var COLOR = {
    gidc: '#0d6f6a',
    private: '#b07a2c',
    accent: '#0d6f6a',
    ink: '#141815',
  };

  var CONF = {
    high: { label: 'Exact place', rank: 3 },
    medium: { label: 'Near match', rank: 2 },
    low: { label: 'Near match', rank: 1 },
    approximate: { label: 'District anchor', rank: 0 },
  };

  var METHOD_TEXT = {
    village: 'Resolved from the village named in the source address',
    taluka: 'Resolved from the taluka / location field',
    'taluka-part': 'Resolved from part of a compound location name',
    'taluka-token': 'Resolved from the nearest matching place name',
    'osm-nominatim': 'Matched to a single OpenStreetMap feature',
    'district-anchor': 'Anchored to the district headquarters',
  };

  var GJ_CENTER = [22.6, 72.4];

  /* --------------------------------------------------------------- state -- */

  var state = {
    q: '',
    cat: 'all',
    conf: 'all',
    tentOnly: false,
    districts: Object.create(null),
    sortKey: 'name',
    sortDir: 1,
    view: 'map',
    selected: null,
  };

  var map = null;
  var districtLayer = null;
  var districtLabels = null;
  var markerLayer = null;
  var markerIndex = Object.create(null);
  var lastFiltered = [];

  var el = {};
  var byId = function (id) { return document.getElementById(id); };

  /* -------------------------------------------------------------- helpers -- */

  function esc(v) {
    if (v === null || v === undefined) return '';
    return String(v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function norm(s) {
    return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function num(n) {
    return Number(n).toLocaleString('en-IN');
  }

  function confRank(p) { return (CONF[p.gc] || CONF.low).rank; }

  function catClass(p) { return p.cat === 'Private' ? 'private' : 'gidc'; }

  function distKm(lng1, lat1, lng2, lat2) {
    var R = 6371, r = Math.PI / 180;
    var dLat = (lat2 - lat1) * r, dLng = (lng2 - lng1) * r;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  function fmtArea(ha) {
    if (ha == null) return null;
    return ha >= 100 ? num(Math.round(ha)) + ' ha' : ha.toFixed(2) + ' ha';
  }

  function fmtApproval(d) {
    if (!d) return null;
    var m = String(d).match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (!m) return d;
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return Number(m[3]) + ' ' + months[Number(m[2]) - 1] + ' ' + m[1];
  }

  /** One search blob per park, built once. */
  var blobs = PARKS.map(function (p) {
    return norm([p.n, p.d, p.loc, p.vil, p.tal, p.ind, p.con, p.mail, p.addr, p.tel].filter(Boolean).join(' '));
  });

  /* ------------------------------------------------------------ filtering -- */

  function matches(p, blob) {
    if (state.cat !== 'all' && p.cat !== state.cat) return false;
    if (state.tentOnly && !p.tent) return false;
    if (state.conf !== 'all' && p.gc !== state.conf) return false;

    var keys = Object.keys(state.districts);
    if (keys.length) {
      var ok = false;
      for (var i = 0; i < keys.length; i++) {
        if (state.districts[keys[i]]) { ok = true; break; }
      }
      if (!ok) return false;
    }

    if (state.q) {
      var terms = norm(state.q).split(' ').filter(Boolean);
      for (var j = 0; j < terms.length; j++) {
        if (blob.indexOf(terms[j]) === -1) return false;
      }
    }
    return true;
  }

  function filtered() {
    var out = [];
    for (var i = 0; i < PARKS.length; i++) {
      if (matches(PARKS[i], blobs[i])) out.push(PARKS[i]);
    }
    return sortRows(out);
  }

  var SORTERS = {
    name: function (a, b) { return a.n.localeCompare(b.n); },
    district: function (a, b) { return a.d.localeCompare(b.d) || a.n.localeCompare(b.n); },
    ha: function (a, b) { return (b.ha || -1) - (a.ha || -1) || a.n.localeCompare(b.n); },
    confidence: function (a, b) { return confRank(b) - confRank(a) || a.n.localeCompare(b.n); },
  };

  function sortRows(rows) {
    var fn = SORTERS[state.sortKey] || SORTERS.name;
    return rows.sort(function (a, b) {
      var r = fn(a, b);
      return r !== 0 ? r * state.sortDir : a.id - b.id;
    });
  }

  /* ------------------------------------------------------------ rendering -- */

  function renderStats() {
    var s = META.stats;
    var cells = [
      ['Parks &amp; estates', num(s.total), ''],
      ['Districts', num(s.districts), ''],
      ['GIDC estates', num(s.gidc), ''],
      ['Private parks', num(s.private), ''],
      ['Tentative', num(s.tentative), ''],
      ['Sanctioned area', num(Math.round(s.totalAreaHa)), 'ha'],
    ];
    el.stats.innerHTML = cells.map(function (c) {
      return '<div><dt>' + c[0] + '</dt><dd>' + c[1] + (c[2] ? '<small>' + c[2] + '</small>' : '') + '</dd></div>';
    }).join('');

    el.datasetLine.textContent =
      num(s.total) + ' records \u00b7 ' + num(s.districts) +
      ' of 32 Gujarat districts \u00b7 ' + num(s.tentative) + ' tentative \u00b7 ' +
      'source: ' + META.builtFrom;

    el.tentCount.textContent = '(' + s.tentative + ')';
  }

  function renderDistricts(rows) {
    var counts = Object.create(null);
    for (var i = 0; i < rows.length; i++) counts[rows[i].d] = (counts[rows[i].d] || 0) + 1;

    var max = 0;
    for (var k in counts) if (counts[k] > max) max = counts[k];

    var html = META.districtRows.map(function (r) {
      var c = counts[r.district] || 0;
      var on = !!state.districts[r.district];
      var off = state.q || state.cat !== 'all' || state.conf !== 'all' || state.tentOnly;
      var pct = max ? Math.round((c / max) * 100) : 0;
      return '<li class="districts__item' + (on ? ' is-on' : '') + (off && !c ? ' is-off' : '') + '">' +
        '<button type="button" class="districts__btn" data-district="' + esc(r.district) + '"' +
        ' aria-pressed="' + (on ? 'true' : 'false') + '">' +
          '<span class="districts__name">' + esc(r.district) + '</span>' +
          '<span class="districts__num">' + c + '</span>' +
          '<span class="districts__bar"><i style="width:' + pct + '%"></i></span>' +
        '</button></li>';
    }).join('');

    el.districts.innerHTML = html;
    el.clearDistricts.hidden = !Object.keys(state.districts).length;
  }

  function renderResultCount(rows) {
    var s = META.stats;
    var bits = [num(rows.length) + ' of ' + num(s.total) + ' shown'];
    if (state.cat !== 'all') bits.push(state.cat);
    if (state.tentOnly) bits.push('tentative only');
    if (Object.keys(state.districts).length) bits.push(Object.keys(state.districts).length + ' districts');
    el.resultCount.textContent = bits.join(' \u00b7 ');
  }

  /* ------------------------------------------------------------------ map -- */

  function initMap() {
    if (typeof L === 'undefined') {
      el.loader.hidden = true;
      el.mapError.hidden = false;
      return false;
    }
    map = L.map('map', {
      center: GJ_CENTER,
      zoom: 7,
      minZoom: 5,
      maxZoom: 16,
      zoomControl: true,
      preferCanvas: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: 'Map data &copy; OpenStreetMap contributors',
    }).addTo(map);

    districtLayer = L.geoJSON(DISTRICTS, {
      style: districtStyle,
      onEachFeature: function (feature, lyr) {
        lyr.on('click', function () { toggleBoundaryDistrict(feature.properties.NAME_2); });
        lyr.on('mouseover', function () { lyr.setStyle({ weight: 1.8, color: COLOR.accent }); });
        lyr.on('mouseout', function () { paintDistricts(lastFiltered); });
      },
    }).addTo(map);

    districtLabels = L.layerGroup().addTo(map);
    districtLayer.eachLayer(function (lyr) {
      var name = lyr.feature.properties.NAME_2;
      var seat = META.seats[name];
      var pt = seat ? L.latLng(seat.lat, seat.lng) : lyr.getBounds().getCenter();
      L.marker(pt, {
        interactive: false,
        icon: L.divIcon({ className: 'districtLabel', html: name, iconSize: null }),
      }).addTo(districtLabels);
    });

    map.on('zoomend moveend', function () { paintMarkers(lastFiltered); });

    el.loader.hidden = true;
    return true;
  }

  var BOUNDARY_TO_CSV = {
    Ahmadabad: ['Ahmedabad'], Amreli: ['Amreli'], Anand: ['Anand'], 'Banas Kantha': ['Banaskantha'],
    Bharuch: ['Bharuch'], Bhavnagar: ['Bhavnagar', 'Botad'], Dahod: ['Dahod', 'Chhota Udepur'],
    Gandhinagar: ['Gandhinagar'], Jamnagar: ['Jamnagar', 'Devbhoomi Dwarka'],
    Junagadh: ['Junagadh', 'Gir Somnath'], Kachchh: ['Kutch'], Kheda: ['Kheda'],
    Mahesana: ['Mehsana'], Narmada: ['Narmada'], Navsari: ['Navsari'],
    'Panch Mahals': ['Panchmahal', 'Mahisagar'], Patan: ['Patan'], Porbandar: ['Porbandar'],
    Rajkot: ['Rajkot', 'Morbi'], 'Sabar Kantha': ['Sabarkantha', 'Aravalli'],
    Surat: ['Surat', 'Tapi'], Surendranagar: ['Surendranagar'], Vadodara: ['Vadodara'],
    Valsad: ['Valsad'], 'The Dangs': [],
  };

  function shadeFor(count, max) {
    if (!count) return { fill: '#ffffff', opacity: 0.06 };
    var t = 0.16 + 0.44 * (Math.sqrt(count) / Math.sqrt(max || 1));
    return { fill: COLOR.accent, opacity: t };
  }

  function districtStyle() {
    return { color: '#b4bcb7', weight: 1, fillColor: '#ffffff', fillOpacity: 0.06 };
  }

  function paintDistricts(rows) {
    if (!districtLayer) return;
    var counts = Object.create(null);
    for (var i = 0; i < rows.length; i++) counts[rows[i].d] = (counts[rows[i].d] || 0) + 1;

    var max = 0;
    for (var k in counts) if (counts[k] > max) max = counts[k];

    var shades = Object.create(null);
    for (var k2 in counts) shades[k2] = shadeFor(counts[k2], max);

    var dimmed = Object.keys(state.districts).length > 0;

    districtLayer.eachLayer(function (lyr) {
      var group = BOUNDARY_TO_CSV[lyr.feature.properties.NAME_2] || [];
      var total = 0;
      var active = 0;
      for (var g = 0; g < group.length; g++) {
        total += counts[group[g]] || 0;
        if (state.districts[group[g]]) active++;
      }
      var base = group.length ? shades[group[0]] : null;
      var s = total ? shadeFor(total, max) : null;
      lyr.setStyle({
        fillColor: (s && s.fill) || (base && base.fill) || '#ffffff',
        fillOpacity: s ? s.opacity : 0.04,
        color: dimmed && !active ? '#d8dcd9' : '#b4bcb7',
        weight: dimmed && active ? 1.8 : 1,
      });
    });
  }

  /** Grid-based clustering — avoids pulling in a plugin dependency. */
  function paintMarkers(rows) {
    if (!map || !markerLayer) return;
    markerLayer.clearLayers();
    markerIndex = Object.create(null);

    if (!rows.length) return;

    var zoom = map.getZoom();
    var cell = zoom >= 11 ? 46 : zoom >= 9 ? 58 : zoom >= 7 ? 76 : 110;
    var buckets = Object.create(null);
    var order = [];

    for (var i = 0; i < rows.length; i++) {
      var pt = map.latLngToContainerPoint([rows[i].lat, rows[i].lng]);
      var gx = Math.round(pt.x / cell);
      var gy = Math.round(pt.y / cell);
      var key = gx + ':' + gy;
      if (!buckets[key]) { buckets[key] = []; order.push(key); }
      buckets[key].push(rows[i]);
    }

    var size = zoom >= 11 ? 9 : 15;
    for (var o = 0; o < order.length; o++) {
      var group = buckets[order[o]];
      if (group.length === 1) {
        markerLayer.addLayer(pointMarker(group[0], size));
      } else {
        markerLayer.addLayer(clusterMarker(group, cell, size));
      }
    }
  }

  function pointMarker(p, size) {
    var m = L.circleMarker([p.lat, p.lng], {
      radius: size / 2,
      fillColor: COLOR[catClass(p)],
      fillOpacity: 0.95,
      color: '#ffffff',
      weight: 1.5,
      bubblingMouseEvents: false,
    });
    m.bindTooltip(p.n, { direction: 'top', offset: [0, -4], className: 'mapTip' });
    m.on('click', function () { select(p.id, true); });
    markerIndex[p.id] = m;
    return m;
  }

  function clusterMarker(group, cell, size) {
    var lat = 0, lng = 0;
    var allPrivate = true;
    for (var i = 0; i < group.length; i++) {
      lat += group[i].lat;
      lng += group[i].lng;
      if (group[i].cat !== 'Private') allPrivate = false;
    }
    lat /= group.length;
    lng /= group.length;

    var d = Math.min(46, 22 + group.length * 2.6);
    var m = L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'cluster' + (allPrivate ? ' is-private' : ''),
        html: String(group.length),
        iconSize: [d, d],
        iconAnchor: [d / 2, d / 2],
      }),
      keyboard: false,
    });

    m.bindTooltip(group.length + ' parks \u2014 zoom in', { direction: 'top', offset: [0, -d / 2] });
    m.on('click', function () {
      var zoom = map.getZoom();
      var pt = map.latLngToContainerPoint([lat, lng]);
      map.panBy([pt.x - map.getSize().x / 2, pt.y - map.getSize().y / 2]);
      if (zoom < 15) map.setZoom(zoom + 2);
      else map.setZoom(16);
    });
    return m;
  }

  function fitTo(rows) {
    if (!map || !rows.length) return;
    var b = L.latLngBounds([]);
    for (var i = 0; i < rows.length; i++) b.extend([rows[i].lat, rows[i].lng]);
    map.fitBounds(b, { padding: [56, 56], maxZoom: 13 });
  }

  /* ---------------------------------------------------------------- popup -- */

  function confClass(c) {
    if (c === 'high') return 'high';
    if (c === 'medium' || c === 'low') return 'medium';
    return 'approx';
  }

  /* ---------------------------------------------------------------- table -- */

  var COLUMNS = [
    { k: 'id', t: 'Sr', cls: 'num', v: function (p) { return p.id; } },
    { k: 'name', t: 'Park / Estate', cls: 'wrap', v: function (p) { return esc(p.n); } },
    { k: 'category', t: 'Category', v: function (p) { return p.cat === 'Private' ? 'Private' : 'GIDC'; } },
    { k: 'district', t: 'District', v: function (p) { return esc(p.d); } },
    { k: 'location', t: 'Taluka / Location', cls: 'wrap', v: function (p) { return esc(p.loc); } },
    { k: 'tentative', t: 'Status', v: function (p) { return p.tent ? 'Tentative' : '\u2014'; } },
    { k: 'industries', t: 'Industries', cls: 'wrap', v: function (p) { return p.ind ? esc(p.ind) : '<span class="muted">\u2014</span>'; } },
    { k: 'areaHa', t: 'Area (ha)', cls: 'num', v: function (p) { return p.ha ? num(p.ha) : '<span class="muted">\u2014</span>'; } },
    { k: 'lat', t: 'Lat', cls: 'num', v: function (p) { return p.lat.toFixed(4); } },
    { k: 'lng', t: 'Lon', cls: 'num', v: function (p) { return p.lng.toFixed(4); } },
    { k: 'confidence', t: 'Placement', v: function (p) { return (CONF[p.gc] || CONF.low).label; } },
    { k: 'phone', t: 'Phone', v: function (p) { return p.tel ? esc(p.tel) : '<span class="muted">\u2014</span>'; } },
    { k: 'email', t: 'Email', v: function (p) { return p.mail ? esc(p.mail) : '<span class="muted">\u2014</span>'; } },
  ];

  function renderTableHead() {
    el.thead.innerHTML = '<tr>' + COLUMNS.map(function (c) {
      var active = c.k === state.sortKey;
      return '<th data-sort="' + c.k + '" scope="col" aria-sort="' +
        (active ? (state.sortDir === 1 ? 'ascending' : 'descending') : 'none') + '">' +
        esc(c.t) + (active ? ' <span class="arrow">' + (state.sortDir === 1 ? '\u25b2' : '\u25bc') + '</span>' : '') +
        '</th>';
    }).join('') + '</tr>';
  }

  function renderTableBody(rows) {
    if (!rows.length) {
      el.tbody.innerHTML = '';
      el.tableNote.hidden = false;
      return;
    }
    el.tableNote.hidden = true;
    el.tbody.innerHTML = rows.map(function (p) {
      return '<tr data-id="' + p.id + '"' + (state.selected === p.id ? ' class="is-active"' : '') + '>' +
        COLUMNS.map(function (c) { return '<td class="' + c.cls + '">' + c.v(p) + '</td>'; }).join('') +
        '</tr>';
    }).join('');
  }

  /* --------------------------------------------------------------- detail -- */

  function detailHtml(p) {
    var seat = META.seats[p.d];
    var offset = seat ? distKm(p.lng, p.lat, seat.lng, seat.lat) : null;

    var badges = '<span class="badge badge--' + catClass(p) + '">' +
      (p.cat === 'Private' ? 'Private industrial park' : 'GIDC industrial estate') + '</span>';
    if (p.tent) badges += '<span class="badge badge--tent">Tentative proposal</span>';
    if (p.phase) badges += '<span class="badge badge--phase">Phase ' + esc(p.phase.toUpperCase()) + '</span>';
    badges += '<span class="badge badge--' + confClass(p.gc) + '">' +
      esc((CONF[p.gc] || CONF.low).label) + ' placement</span>';

    var html = '<div class="badges">' + badges + '</div>';

    html += '<section class="dsection"><h3 class="dsection__title">Placement</h3>' +
      '<div class="metricRow"><dl>' +
        '<div><dt>Latitude</dt><dd>' + p.lat.toFixed(5) + '</dd></div>' +
        '<div><dt>Longitude</dt><dd>' + p.lng.toFixed(5) + '</dd></div>' +
        '<div><dt>From HQ</dt><dd>' + (offset == null ? '\u2014' : offset.toFixed(0) + ' km') + '</dd></div>' +
      '</dl></div>' +
      '<dl class="dl" style="margin-top:10px">' +
        '<dt>Method</dt><dd>' + esc(METHOD_TEXT[p.gm] || p.gm) + '</dd>' +
        '<dt>Matched place</dt><dd>' + esc(p.gp || 'District headquarters') + '</dd>' +
        (offset != null ? '<dt>Distance to ' + esc(p.d) + '</dt><dd>' + offset.toFixed(1) + ' km from the district headquarters</dd>' : '') +
      '</dl></section>';

    html += '<section class="dsection"><h3 class="dsection__title">Location</h3><dl class="dl">' +
      '<dt>District</dt><dd>' + esc(p.d) + '</dd>' +
      '<dt>Taluka</dt><dd>' + esc(p.tal || p.loc) + '</dd>' +
      (p.vil ? '<dt>Village</dt><dd>' + esc(p.vil) + '</dd>' : '') +
      '<dt>Address</dt><dd>' + esc(p.addr) + '</dd>' +
      '</dl></section>';

    if (p.ind || p.ha || p.appr) {
      html += '<section class="dsection"><h3 class="dsection__title">Sanction details</h3><dl class="dl">' +
        (p.ind ? '<dt>Industries</dt><dd>' + esc(p.ind) + '</dd>' : '') +
        (p.ha ? '<dt>Area</dt><dd class="mono">' + fmtArea(p.ha) + '</dd>' : '') +
        (p.appr ? '<dt>In-principle</dt><dd>' + esc(fmtApproval(p.appr) || p.appr) + '</dd>' : '') +
        '</dl></section>';
    }

    html += '<section class="dsection"><h3 class="dsection__title">Contact</h3><dl class="dl">' +
      '<dt>Office</dt><dd>' + esc(p.con || '\u2014') + '</dd>' +
      '<dt>Phone</dt><dd>' + (p.tel
        ? esc(p.tel).split(/\s*\/\s*/).map(function (t) {
            var digits = t.replace(/[^\d+]/g, '');
            return digits.length > 6 ? '<a href="tel:' + esc(digits) + '">' + esc(t) + '</a>' : esc(t);
          }).join(' <span class="muted">/</span> ')
        : '\u2014') + '</dd>' +
      '<dt>Email</dt><dd>' + (p.mail ? '<a href="mailto:' + esc(p.mail) + '">' + esc(p.mail) + '</a>' : '\u2014') + '</dd>' +
      '<dt>Address</dt><dd>' + esc(p.off || '\u2014') + '</dd>' +
      '</dl></section>';

    if (p.notes) {
      html += '<section class="dsection"><h3 class="dsection__title">Source notes</h3>' +
        '<p class="note">' + esc(p.notes) + '</p></section>';
    }

    html += '<section class="dsection"><h3 class="dsection__title">Provenance</h3>' +
      '<dl class="dl"><dt>Record</dt><dd class="mono">Sr No. ' + p.id + '</dd>' +
      '<dt>Category</dt><dd>' + esc(p.catFull) + '</dd>' +
      '<dt>Source</dt><dd class="srcLine">' + esc(p.src) + '</dd></dl></section>';

    return html;
  }

  function select(id, fromMap) {
    var p = PARKS.find(function (x) { return x.id === id; });
    if (!p) return;
    state.selected = id;

    el.detailEyebrow.textContent = 'Sr No. ' + p.id + ' \u00b7 ' + p.d + ' \u00b7 ' + p.loc;
    el.detailTitle.textContent = p.n;
    el.detailBody.innerHTML = detailHtml(p);
    el.detail.hidden = false;

    var row = el.tbody.querySelector('tr[data-id="' + id + '"]');
    if (row) row.classList.add('is-active');

    if (fromMap && map && markerIndex[id]) {
      map.panTo([p.lat, p.lng], { animate: true });
    }
    if (!fromMap && map && markerIndex[id]) {
      map.setView([p.lat, p.lng], Math.max(map.getZoom(), 11), { animate: true });
    }
  }

  function deselect() {
    state.selected = null;
    el.detail.hidden = true;
    var row = el.tbody.querySelector('tr.is-active');
    if (row) row.classList.remove('is-active');
  }

  /* ----------------------------------------------------------------- csv -- */

  function exportCsv() {
    var head = ['Sr No', 'Park / Estate Name', 'Category', 'District', 'Taluka / Location',
      'Village', 'Address', 'Contact Person / Office', 'Phone', 'Email',
      'Office / Contact Address', 'Proposed industries', 'Area (ha)', 'In-principle approval',
      'Tentative', 'Phase', 'Latitude', 'Longitude', 'Placement method',
      'Placement confidence', 'Matched place', 'Notes', 'Source'];

    var lines = [head.map(csvCell).join(',')];
    for (var i = 0; i < lastFiltered.length; i++) {
      var p = lastFiltered[i];
      lines.push([
        p.id, p.n, p.catFull, p.d, p.loc, p.vil || '', p.addr, p.con, p.tel, p.mail, p.off,
        p.ind || '', p.ha == null ? '' : p.ha, p.appr || '',
        p.tent ? 'Yes' : 'No', p.phase ? p.phase.toUpperCase() : '',
        p.lat, p.lng, p.gm, (CONF[p.gc] || CONF.low).label, p.gp || '', p.notes, p.src,
      ].map(csvCell).join(','));
    }

    var blob = new Blob(['\ufeff' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'gujarat-industrial-parks-filtered.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function csvCell(v) {
    var s = v === null || v === undefined ? '' : String(v);
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  /* ------------------------------------------------------------- pipeline -- */

  function refresh() {
    lastFiltered = filtered();

    renderResultCount(lastFiltered);
    renderDistricts(lastFiltered);
    paintDistricts(lastFiltered);
    if (state.view === 'map') paintMarkers(lastFiltered);
    renderTableHead();
    renderTableBody(lastFiltered);

    if (state.selected != null && !lastFiltered.some(function (p) { return p.id === state.selected; })) {
      deselect();
    }
  }

  function toggleDistrict(name) {
    if (state.districts[name]) delete state.districts[name];
    else state.districts[name] = true;
    refresh();
  }

  /**
   * Boundary polygons predate the eight districts carved out after 2012, so one
   * polygon can cover several districts in this dataset. Select them together.
   */
  function toggleBoundaryDistrict(boundaryName) {
    var group = BOUNDARY_TO_CSV[boundaryName] || [];
    var allOn = group.length && group.every(function (d) { return state.districts[d]; });
    for (var i = 0; i < group.length; i++) {
      if (allOn) delete state.districts[group[i]];
      else state.districts[group[i]] = true;
    }
    refresh();
  }

  /* ----------------------------------------------------------------- about -- */

  function aboutHtml() {
    var s = META.stats;
    return '' +
      '<p>The source file, <code>' + esc(META.builtFrom) + '</code>, lists every estate with a district, a taluka ' +
      'or village, an address and a contact office. It carries no latitude or longitude. Every point on this map ' +
      'is therefore derived, and each record reports how.</p>' +

      '<h3>How a point is chosen</h3>' +
      '<ol style="padding-left:18px;list-style:decimal;margin:0 0 9px">' +
        '<li>The location field is parsed for a village and a taluka, and a ranked list of candidate place names is built from it.</li>' +
        '<li>Candidates are matched against a <strong>GeoNames</strong> gazetteer for Gujarat and against a ' +
          '<strong>OpenStreetMap</strong> place index of 11,520 named places covering the state.</li>' +
        '<li>Candidates are scored on name agreement, feature rank (a taluka seat outranks a hamlet), population, ' +
          'and distance from the district.</li>' +
        '<li>If no gazetteer entry is convincing, a validated single-feature OpenStreetMap match is used.</li>' +
        '<li>If the place exists in no public gazetteer, the point falls back to the district headquarters.</li>' +
      '</ol>' +

      '<h3>What the confidence labels mean</h3>' +
      '<ul>' +
        '<li><strong>Exact place (' + s.byConfidence.high + ' records)</strong> &mdash; the named village or taluka resolved ' +
          'to a real populated place in the right district. Usually accurate to the taluka, sometimes better.</li>' +
        '<li><strong>Near match (' + (s.byConfidence.medium || 0) + ' records)</strong> &mdash; a weaker name match or a ' +
          'single OpenStreetMap feature. Read the matched-place name before relying on it.</li>' +
        '<li><strong>District anchor (' + s.byConfidence.approximate + ' records)</strong> &mdash; the estate is named after a ' +
          'settlement that appears in neither gazetteer, so the point sits at the district headquarters. Treat these as ' +
          'district-level only.</li>' +
      '</ul>' +

      '<h3>Known limits</h3>' +
      '<ul>' +
        '<li>GIDC estates are industrial areas, not settlements. Even a perfect taluka match places the point at the taluka ' +
          'town, so expect a typical error of a few to twenty kilometres.</li>' +
        '<li>The <code>District</code> column is a GIDC administrative division, which does not always match the revenue ' +
          'district a place falls in. Chanasma is filed under Mehsana but lies in Patan. The district is therefore used as a ' +
          'soft signal, not a hard filter.</li>' +
        '<li>District boundaries come from a 2012-vintage public shapefile of 25 districts. The eight districts carved out ' +
          'since then (Aravalli, Botad, Chhota Udepur, Devbhoomi Dwarka, Gir Somnath, Mahisagar, Morbi, Tapi) are shaded ' +
          'under their parent district.</li>' +
        '<li>Only the 42 private parks carry an area and an approval date; those fields come from the source notes.</li>' +
      '</ul>' +

      '<h3>Method by count</h3>' +
      '<ul>' + Object.keys(s.byMethod).map(function (m) {
        return '<li><code>' + esc(m) + '</code> &mdash; ' + s.byMethod[m] + ' records</li>';
      }).join('') + '</ul>';
  }

  /* ------------------------------------------------------------------ init -- */

  function init() {
    el = {
      stats: byId('stats'), districts: byId('districts'), resultCount: byId('resultCount'),
      clearDistricts: byId('clearDistricts'), search: byId('search'), conf: byId('conf'),
      sort: byId('sort'), tentOnly: byId('tentOnly'), tentCount: byId('tentCount'),
      datasetLine: byId('datasetLine'), map: byId('map'), loader: byId('loader'),
      mapError: byId('mapError'), thead: byId('thead'), tbody: byId('tbody'),
      tableNote: byId('tableNote'), detail: byId('detail'), detailTitle: byId('detailTitle'),
      detailEyebrow: byId('detailEyebrow'), detailBody: byId('detailBody'),
      detailClose: byId('detailClose'), aboutBtn: byId('aboutBtn'), aboutModal: byId('aboutModal'),
      aboutBody: byId('aboutBody'), aboutClose: byId('aboutClose'), exportBtn: byId('exportBtn'),
      fitBtn: byId('fitBtn'), mapPane: byId('mapPane'), tablePane: byId('tablePane'),
    };

    renderStats();
    var ok = initMap();
    if (ok) markerLayer = L.layerGroup().addTo(map);
    refresh();

    /* search */
    var timer = null;
    el.search.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { state.q = el.search.value; refresh(); }, 120);
    });

    /* category segmented control */
    document.querySelectorAll('[data-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.cat = btn.getAttribute('data-cat');
        document.querySelectorAll('[data-cat]').forEach(function (b) {
          var on = b === btn;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        refresh();
      });
    });

    /* view toggle */
    document.querySelectorAll('[data-view]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.view = btn.getAttribute('data-view');
        document.querySelectorAll('[data-view]').forEach(function (b) {
          var on = b === btn;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        var isMap = state.view === 'map';
        el.mapPane.hidden = !isMap;
        el.tablePane.hidden = isMap;
        if (isMap && map) setTimeout(function () { map.invalidateSize(); paintMarkers(lastFiltered); }, 0);
      });
    });

    el.conf.addEventListener('change', function () { state.conf = el.conf.value; refresh(); });

    el.sort.addEventListener('change', function () {
      var parts = el.sort.value.split(':');
      state.sortKey = parts[0];
      state.sortDir = Number(parts[1]);
      refresh();
    });

    el.tentOnly.addEventListener('change', function () { state.tentOnly = el.tentOnly.checked; refresh(); });

    el.clearDistricts.addEventListener('click', function () {
      state.districts = Object.create(null);
      refresh();
    });

    el.districts.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-district]');
      if (btn) toggleDistrict(btn.getAttribute('data-district'));
    });

    el.thead.addEventListener('click', function (e) {
      var th = e.target.closest('[data-sort]');
      if (!th) return;
      var k = th.getAttribute('data-sort');
      if (!SORTERS[k]) return;
      if (state.sortKey === k) state.sortDir *= -1;
      else { state.sortKey = k; state.sortDir = k === 'name' || k === 'district' ? 1 : -1; }
      refresh();
    });

    el.tbody.addEventListener('click', function (e) {
      var tr = e.target.closest('tr[data-id]');
      if (tr) select(Number(tr.getAttribute('data-id')), false);
    });

    el.detailClose.addEventListener('click', deselect);

    el.fitBtn.addEventListener('click', function () { fitTo(lastFiltered); });
    el.exportBtn.addEventListener('click', exportCsv);

    el.aboutBtn.addEventListener('click', function () {
      el.aboutBody.innerHTML = aboutHtml();
      el.aboutModal.hidden = false;
      el.aboutClose.focus();
    });
    el.aboutClose.addEventListener('click', function () { el.aboutModal.hidden = true; el.aboutBtn.focus(); });
    el.aboutModal.addEventListener('click', function (e) {
      if (e.target === el.aboutModal) { el.aboutModal.hidden = true; el.aboutBtn.focus(); }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (!el.aboutModal.hidden) { el.aboutModal.hidden = true; el.aboutBtn.focus(); return; }
        deselect();
        return;
      }
      if (e.key === '/' && document.activeElement !== el.search) {
        e.preventDefault();
        el.search.focus();
        el.search.select();
      }
    });

    if (map) map.invalidateSize();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();