import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const GEONAMES = process.argv[2];
const BOUNDARIES = path.join(__dirname, '..', 'data', 'gujarat-districts.geojson');

/* ------------------------------------------------------------------ utils */

function deaccent(s) {
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[\u0951-\u0954]/g, '')
    .replace(/[\u0964\u0965]/g, '')
    .replace(/[&\u00b7\u2022]/g, ' and ')
    .replace(/\u2019|'/g, '')
    .toLowerCase();
}

function normKey(s) {
  return deaccent(s)
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

const GENERIC = new Set([
  'gidc', 'industrial', 'estate', 'park', 'parks', 'msme', 'non', 'women', 'woman', 'development',
  'agro', 'food', 'it', 'se', 'sez', 'zone', 'zones', 'area', 'speciality', 'fine', 'chemicals',
  'new', 'old', 'expansion', 'phase', 'japan', 'japanese', 'housing', 'apparel', 'logistics',
  'mixed', 'general', 'engineering', 'textiles', 'textile', 'auto', 'component', 'components',
  'multi', 'product', 'products', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
  'and', 'of', 'at', 'in', 'the', 'project', 'projects', 'limited', 'ltd', 'llp', 'pvt',
]);

const ROMAN = new Set(['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii']);

function tokens(s) {
  return normKey(s).split(' ').filter(Boolean);
}

function significantTokens(s) {
  return tokens(s).filter((t) => t.length >= 4 && !GENERIC.has(t) && !ROMAN.has(t));
}

/** Strip phase/roman/generic decoration from a place label. */
function cleanPlace(s) {
  let out = tokens(s).filter((t) => !ROMAN.has(t) && t !== 'phase');
  return out.join(' ').trim();
}

/* ------------------------------------------------- point in polygon (ray) */

function pointInRing(lng, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect = yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function pointInPolygon(lng, lat, geom) {
  if (!geom) return false;
  if (geom.type === 'Polygon') {
    if (!pointInRing(lng, lat, geom.coordinates[0])) return false;
    for (let k = 1; k < geom.coordinates.length; k++) {
      if (pointInRing(lng, lat, geom.coordinates[k])) return false;
    }
    return true;
  }
  if (geom.type === 'MultiPolygon') {
    for (const poly of geom.coordinates) {
      if (pointInPolygon(lng, lat, { type: 'Polygon', coordinates: poly })) return true;
    }
  }
  return false;
}

function polygonCentroid(geom) {
  const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
  let x = 0;
  let y = 0;
  let n = 0;
  for (const poly of polys) {
    for (const ring of poly) {
      for (const [px, py] of ring) {
        x += px;
        y += py;
        n++;
      }
    }
  }
  return n ? [x / n, y / n] : [72.6, 22.3];
}

/* ------------------------------------------------------------- boundaries */

const boundaryRaw = JSON.parse(fs.readFileSync(BOUNDARIES, 'utf8'));
const boundaryPolys = boundaryRaw.features.map((f) => ({
  name: f.properties.NAME_2,
  varname: f.properties.VARNAME_2 || '',
  geom: f.geometry,
  centroid: polygonCentroid(f.geometry),
}));

function locateDistrict(lng, lat) {
  const hits = boundaryPolys.filter((b) => pointInPolygon(lng, lat, b.geom));
  if (!hits.length) return null;
  // Smallest containing polygon wins (handles enclaves / overlaps).
  hits.sort((a, b) => {
    const area = (p) => {
      let s = 0;
      const polys = p.geom.type === 'Polygon' ? [p.geom.coordinates] : p.geom.coordinates;
      for (const poly of polys) {
        const ring = poly[0];
        let a2 = 0;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          a2 += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1];
        }
        s += Math.abs(a2 / 2);
      }
      return s;
    };
    return area(a) - area(b);
  });
  return hits[0].name;
}

/* ------------------------------------------------------------- gazetteer */

console.log('reading geonames…');
const raw = fs.readFileSync(GEONAMES, 'utf8');
const lines = raw.split('\n');

const byName = new Map();
let gjCount = 0;
let adminMismatch = 0;

const WANTED_CLASS = new Set(['P', 'A']);

// Gujarat bounding box, used as a cheap pre-filter before the exact polygon test.
const BBOX = { minLng: 67.5, maxLng: 74.8, minLat: 19.5, maxLat: 25.0 };

for (const line of lines) {
  if (!line) continue;
  const f = line.split('\t');
  if (f.length < 14) continue;
  if (f[8] !== 'IN') continue;
  const fclass = f[6];
  const fcode = f[7];
  if (!WANTED_CLASS.has(fclass)) continue;
  if (fclass === 'A' && !fcode.startsWith('ADM')) continue;

  const lat = Number(f[4]);
  const lng = Number(f[5]);
  if (!(lng >= BBOX.minLng && lng <= BBOX.maxLng && lat >= BBOX.minLat && lat <= BBOX.maxLat)) continue;

  const district = locateDistrict(lng, lat);
  if (!district) continue;

  gjCount++;
  if (f[10] !== '09') adminMismatch++;

  const rec = {
    name: f[1],
    ascii: f[2],
    lat,
    lng,
    fclass,
    fcode,
    pop: Number(f[14] || 0),
    admin2: f[11] || '',
    admin3: f[12] || '',
    admin4: f[13] || '',
    district,
  };

  const keys = new Set([f[1], f[2]]);
  if (f[3]) {
    for (const alt of f[3].split(',')) {
      const a = alt.trim();
      if (a && a.length <= 60 && /^[A-Za-z\u0900-\u097F ]+$/.test(a)) keys.add(a);
    }
  }
  for (const k of keys) {
    const key = normKey(k);
    if (!key) continue;
    if (!byName.has(key)) byName.set(key, []);
    byName.get(key).push(rec);
  }
}

console.log(`gujarat gazetteer records: ${gjCount} (admin1!=09: ${adminMismatch})`);
console.log(`distinct name keys: ${byName.size}`);

/* ------------------------------------------------- OSM place index (tier 2) */

const OSM_PLACES = path.join(__dirname, '..', 'data', 'osm-gujarat-places.json');
const osmByName = new Map();
let osmCount = 0;

if (fs.existsSync(OSM_PLACES)) {
  const OSM_RANK = {
    city: 22, town: 20, municipality: 16, borough: 16, suburb: 15, village: 12,
    neighbourhood: 12, quarter: 10, hamlet: 8, isolated_dwelling: 4,
  };
  for (const rec of JSON.parse(fs.readFileSync(OSM_PLACES, 'utf8'))) {
    if (!(rec.lat >= BBOX.minLat && rec.lat <= BBOX.maxLat && rec.lng >= BBOX.minLng && rec.lng <= BBOX.maxLng)) continue;
    const district = locateDistrict(rec.lng, rec.lat);
    if (!district) continue;
    const rec2 = {
      source: 'osm',
      name: rec.names[0],
      ascii: rec.names[0],
      lat: rec.lat,
      lng: rec.lng,
      fclass: 'P',
      fcode: `OSM_${rec.place}`,
      pop: rec.pop || 0,
      osmRank: OSM_RANK[rec.place] ?? 8,
      district,
    };
    osmCount++;
    for (const n of rec.names) {
      const key = normKey(n);
      if (!key || key.length < 3) continue;
      if (!osmByName.has(key)) osmByName.set(key, []);
      osmByName.get(key).push(rec2);
    }
  }
}
console.log(`osm place records: ${osmCount} (distinct keys: ${osmByName.size})`);

/* -------------------------------------------------------- district seats */

/**
 * The centroid of a district polygon is a poor proxy for "where is this
 * district" (Kutch's centroid lands in the Rann). Resolve the real district
 * headquarters and use that as the geographic reference instead.
 */
// ADM features carry a representative point for the whole unit, not the town
// seat, so they are excluded here — only populated places qualify as a seat.
const SEAT_RANK = { PPLA2: 26, PPLA3: 22, PPLA: 20, PPLA4: 10, PPL: 10, PPLL: 6 };
const DISTRICT_ALIAS = {
  kutch: ['bhuj'],
  'devbhoomi dwarka': ['khambhalia', 'jamnagar'],
  mehsana: ['mahesana', 'mehsana'],
  banaskantha: ['palanpur', 'deesa'],
  aravalli: ['modasa'],
  mahisagar: ['balasinor', 'godhra'],
  'gir somnath': ['veraval', 'kodinar'],
  morbi: ['morbi'],
  bhavnagar: ['bhavnagar'],
  navsari: ['navsari'],
  valsad: ['valsad', 'bulsar'],
  narmada: ['rajpipla'],
  'chhota ude pur': ['chhotaudepur'],
  chhotaudepur: ['chhotaudepur'],
  botad: ['botad'],
  kheda: ['nadiad'],
  anand: ['anand'],
  dahod: ['dahod'],
  panchmahal: ['godhra'],
};

function findSeat(districtName) {
  const key = districtKey(districtName);
  const target = DISTRICT_TO_BOUNDARY[key];
  const names = [districtName, ...(DISTRICT_ALIAS[key] ?? [])];

  const pool = [];
  for (const nm of names) {
    for (const rec of [...(byName.get(normKey(nm)) ?? []), ...(osmByName.get(normKey(nm)) ?? [])]) {
      pool.push(rec);
    }
  }

  const scored = pool
    .filter((r) => (SEAT_RANK[r.fcode] ?? 8) > 0)
    .map((r) => {
      const [clng, clat] = polygonCentroidOf(target);
      const d = km(r.lng, r.lat, clng, clat);
      const inDistrict = r.district === target ? 1 : 0;
      return { ...r, seatScore: (SEAT_RANK[r.fcode] ?? 8) * 3 + Math.min(28, Math.log10((r.pop || 1) + 1) * 8) + inDistrict * 40 - Math.min(50, d * 0.25) };
    })
    .sort((a, b) => b.seatScore - a.seatScore);

  return scored[0] ?? null;
}

function polygonCentroidOf(boundaryName) {
  if (!boundaryName) return [72.6, 22.6];
  const poly = boundaryPolys.find((b) => b.name === boundaryName);
  return poly ? poly.centroid : [72.6, 22.6];
}

const districtSeats = new Map();
const SEAT_OUT = {};

/* ---------------------------------------------------------- district alias */

const DISTRICT_TO_BOUNDARY = {
  ahmedabad: 'Ahmadabad',
  bharuch: 'Bharuch',
  rajkot: 'Rajkot',
  morbi: 'Rajkot',
  mehsana: 'Mahesana',
  kutch: 'Kachchh',
  vadodara: 'Vadodara',
  surat: 'Surat',
  tapi: 'Surat',
  bhavnagar: 'Bhavnagar',
  botad: 'Bhavnagar',
  surendranagar: 'Surendranagar',
  jamnagar: 'Jamnagar',
  'devbhoomi dwarka': 'Jamnagar',
  valsad: 'Valsad',
  amreli: 'Amreli',
  anand: 'Anand',
  banaskantha: 'Banas Kantha',
  gandhinagar: 'Gandhinagar',
  patan: 'Patan',
  aravalli: 'Sabar Kantha',
  sabarkantha: 'Sabar Kantha',
  kheda: 'Kheda',
  panchmahal: 'Panch Mahals',
  mahisagar: 'Panch Mahals',
  junagadh: 'Junagadh',
  'gir somnath': 'Junagadh',
  dahod: 'Dahod',
  'chhota ude pur': 'Dahod',
  chhotaudepur: 'Dahod',
  porbandar: 'Porbandar',
  narmada: 'Narmada',
  navsari: 'Navsari',
};

function districtKey(name) {
  return normKey(name).replace(/\s*district\s*/, '').trim();
}

const centroidCache = new Map();
function districtCentroid(districtName) {
  const k = districtKey(districtName);
  if (centroidCache.has(k)) return centroidCache.get(k);
  let c = [72.6, 22.6];
  const seat = districtSeats.get(k);
  if (seat) c = [seat.lng, seat.lat];
  else {
    const target = DISTRICT_TO_BOUNDARY[k];
    const poly = boundaryPolys.find((b) => b.name === target);
    if (poly) c = poly.centroid;
  }
  centroidCache.set(k, c);
  return c;
}

function km(lng1, lat1, lng2, lat2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
}

/* ------------------------------------------------------------- resolution */

const PLACE_FCODE_RANK = {
  PPLA: 22, PPLA2: 20, PPLA3: 16, PPLA4: 13, ADM2: 16, ADM3: 14, ADM4: 10,
  PPL: 12, PPLL: 8, PPLS: 8, PPLW: 6, PPLX: 4,
};
const EXCLUDE_FCODE = new Set([
  'WTRF', 'WTRS', 'LK', 'RSV', 'BAY', 'CAPE', 'ISL', 'BCHR', 'RST', 'HTL', 'PRK',
  'STDM', 'STM', 'MSQE', 'MNMT', 'BLDG', 'RD', 'RDINTE', 'RR', 'MT', 'PK', 'HTL',
]);

function editDistanceWithin(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  const prev = new Array(b.length + 1);
  const cur = new Array(b.length + 1);
  for (let j = 0; j <= b.length; j++) prev[j] = j;
  for (let i = 1; i <= a.length; i++) {
    cur[0] = i;
    let rowMin = cur[0];
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(
        prev[j] + 1,
        cur[j - 1] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      );
      if (cur[j] < rowMin) rowMin = cur[j];
    }
    if (rowMin > max) return max + 1;
    for (let j = 0; j <= b.length; j++) prev[j] = cur[j];
  }
  return prev[b.length];
}

/**
 * The CSV `District` column is a GIDC administrative division, which does not
 * always match the revenue district a place actually falls in (Chanasma is
 * filed under Mehsana but sits in Patan). So the district is a soft signal only.
 */
function scoreCandidate(rec, districtName, queryKey, weight) {
  if (EXCLUDE_FCODE.has(rec.fcode)) return null;

  const qParts = queryKey.split(' ').filter(Boolean);
  const nName = normKey(rec.name);
  const nAscii = normKey(rec.ascii);
  const nParts = nName.split(' ').filter(Boolean);

  let s;
  if (queryKey === nName || queryKey === nAscii) s = 50;
  else if (queryKey === nName.replace(/\s+/g, '')) s = 46;
  else if (nName.includes(queryKey) && qParts.length >= 2) s = 34;
  else if (qParts.length === 1 && nParts.length === 1 && nParts[0].length >= 5) {
    s = editDistanceWithin(qParts[0], nParts[0], 1) <= 1 ? 30 : 12;
  } else if (qParts.filter((t) => nParts.includes(t)).length === qParts.length) s = 30;
  else s = 16;

  s += rec.osmRank ?? (PLACE_FCODE_RANK[rec.fcode] ?? 8);
  s += Math.min(34, Math.log10((rec.pop || 1) + 1) * 8);

  if (qParts.length > 1) s += 8 * (qParts.filter((t) => nParts.includes(t)).length / qParts.length);

  const target = DISTRICT_TO_BOUNDARY[districtKey(districtName)];
  if (target) s += rec.district === target ? 18 : -22;

  const [clng, clat] = districtCentroid(districtName);
  s -= Math.min(60, km(rec.lng, rec.lat, clng, clat) * 0.3);

  return s * weight;
}

function lookup(query, districtName, weight) {
  const key = normKey(query);
  if (!key || key.length < 3) return null;
  const pools = [byName.get(key), osmByName.get(key)];
  let best = null;
  for (const pool of pools) {
    if (!pool || !pool.length) continue;
    for (const rec of pool) {
      const sc = scoreCandidate(rec, districtName, key, weight);
      if (sc === null) continue;
      if (!best || sc > best.score) best = { ...rec, score: sc };
    }
  }
  if (!best) return null;
  const [clng, clat] = districtCentroid(districtName);
  best.distanceKm = +km(best.lng, best.lat, clng, clat).toFixed(1);
  return best;
}

/* ---------------------------------------------------------- query ladders */

function parseLocation(location, parkName) {
  const raw = location.trim();
  let village = null;
  let taluka = raw;

  const vm = raw.match(/^Village:\s*(.*)$/i);
  if (vm) {
    const rest = vm[1];
    const tm = rest.match(/Taluka:\s*([^,]+)\s*$/i);
    if (tm) {
      taluka = tm[1].trim();
      village = rest.slice(0, rest.length - tm[0].length).replace(/,\s*$/, '').trim();
    } else {
      village = rest;
      taluka = parkName;
    }
  }

  const villageParts = village ? village.split(/\s*(?:,|&|\band\b)\s*/i).map((s) => s.trim()).filter(Boolean) : [];
  const talukaParts = taluka.split(/\s*(?:,|\/)\s*/).map((s) => s.trim()).filter(Boolean);

  return { villageParts, talukaParts, taluka: cleanPlace(taluka) };
}

function queryLadder({ villageParts, talukaParts }, parkName) {
  const q = [];
  const push = (s, w, label) => {
    const c = cleanPlace(s);
    if (c && c.length >= 3) q.push({ query: c, weight: w, label });
  };

  villageParts.forEach((v, i) => push(v, 1.0 - i * 0.06, 'village'));

  talukaParts.forEach((t, i) => push(t, 0.98 - i * 0.06, 'taluka'));
  talukaParts.forEach((t) => t.split(/\s*-\s*/).forEach((p, i) => push(p, 0.9 - i * 0.04, 'taluka-part')));
  talukaParts.forEach((t) =>
    significantTokens(t).forEach((tok, i) => q.push({ query: tok, weight: 0.82 - i * 0.03, label: 'taluka-token' })),
  );

  // Park name, with the authority prefix and decoration removed.
  const pn = parkName.replace(/^\s*GIDC\s+/i, '').replace(/\s*\(.*?\)\s*/g, ' ').trim();
  push(pn, 0.8, 'park-name');
  pn.split(/\s*(?:,|\/)\s*/).forEach((p, i) => push(p, 0.74 - i * 0.04, 'park-part'));
  significantTokens(pn).forEach((tok, i) => q.push({ query: tok, weight: 0.62 - i * 0.03, label: 'park-token' }));

  // De-duplicate, preserving order and keeping the strongest weight.
  const seen = new Map();
  for (const item of q) {
    const key = normKey(item.query);
    if (!key) continue;
    if (!seen.has(key) || seen.get(key).weight < item.weight) seen.set(key, { ...item, query: key });
  }
  return [...seen.values()];
}

/* ------------------------------------------------------------------- CSV */

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i++;
        } else inQuotes = false;
      } else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ',') {
      row.push(field);
      field = '';
    } else if (c === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (c !== '\r') field += c;
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const header = rows[0].map((h) => h.trim());
  return rows
    .slice(1)
    .filter((r) => r.length > 1 && r[0] && r[0].trim())
    .map((r) => Object.fromEntries(header.map((h, i) => [h, (r[i] ?? '').trim()])));
}

/* --------------------------------------------------------------- run build */

const csvPath = process.argv[3];
const outPath = process.argv[4];

const records = parseCsv(fs.readFileSync(csvPath, 'utf8'));
console.log('csv rows:', records.length);

// Resolve every district headquarters once; the rest of the pipeline uses it
// as the geographic reference for that district.
for (const d of [...new Set(records.map((r) => r['District']))].sort()) {
  const seat = findSeat(d);
  if (seat) {
    districtSeats.set(districtKey(d), seat);
    SEAT_OUT[d] = { lat: seat.lat, lng: seat.lng, place: seat.name, source: seat.source ?? 'geonames', fcode: seat.fcode };
  } else {
    const [clng, clat] = polygonCentroidOf(DISTRICT_TO_BOUNDARY[districtKey(d)]);
    SEAT_OUT[d] = { lat: +clat.toFixed(5), lng: +clng.toFixed(5), place: `${d} (polygon centroid)`, source: 'polygon-centroid' };
  }
}
console.log('\ndistrict seats:');
for (const [d, s] of Object.entries(SEAT_OUT)) {
  console.log(`  ${d.padEnd(20)} ${s.lat},${s.lng}  (${s.place})`);
}
fs.writeFileSync(path.join(__dirname, '..', 'data', 'district-seats.json'), JSON.stringify(SEAT_OUT, null, 1));

const H = {
  sr: 'Sr No',
  name: 'Park / Estate Name',
  category: 'Category',
  district: 'District',
  location: 'Taluka / Location',
  address: 'Address',
  contact: 'Contact Person / Office',
  phone: 'Phone',
  email: 'Email',
  office: 'Office / Contact Address',
  notes: 'Notes',
  source: 'Source',
};

const PARSE_NOTE = {
  industries: /Proposed industries:\s*([^;]+)/i,
  area: /Area:\s*([\d.]+)\s*ha/i,
  approval: /In-principle approval:\s*([\d.]+)/i,
};

const out = [];
const unresolved = [];
const usedKeys = new Map();

for (const r of records) {
  const district = r[H.district];
  const name = r[H.name];
  const parsedLoc = parseLocation(r[H.location], name);
  const ladder = queryLadder(parsedLoc, name);

  let hit = null;
  let usedStep = null;
  for (const step of ladder) {
    const cand = lookup(step.query, district, step.weight);
    if (cand && (!hit || cand.score > hit.score)) {
      hit = cand;
      usedStep = step;
      if (cand.score >= 75) break;
    }
  }

  let lat;
  let lng;
  let method;
  let confidence;
  let matchedName = null;
  let placeDistanceKm = null;

  if (hit && hit.score >= 45) {
    lat = +hit.lat.toFixed(5);
    lng = +hit.lng.toFixed(5);
    matchedName = hit.name;
    placeDistanceKm = hit.distanceKm;
    method = usedStep.label;
    if (hit.score >= 75) confidence = 'high';
    else if (hit.score >= 55) confidence = 'medium';
    else confidence = 'low';
    const k = normKey(usedStep.query);
    usedKeys.set(k, (usedKeys.get(k) || 0) + 1);
  } else {
    const [clng, clat] = districtCentroid(district);
    lng = +clng.toFixed(5);
    lat = +clat.toFixed(5);
    method = 'district-centroid';
    confidence = 'district';
    if (hit) {
      matchedName = hit.name;
    }
    unresolved.push({
      sr: Number(r[H.sr]),
      name,
      district,
      location: r[H.location],
      ladder: ladder.slice(0, 8).map((s) => `${s.label}:${s.query}`),
      bestHit: hit ? `${hit.name} (${hit.score.toFixed(1)})` : 'none',
    });
  }

  const noteRaw = r[H.notes] || '';
  const mInd = noteRaw.match(PARSE_NOTE.industries);
  const mArea = noteRaw.match(PARSE_NOTE.area);
  const mApp = noteRaw.match(PARSE_NOTE.approval);

  out.push({
    id: Number(r[H.sr]),
    name,
    category: r[H.category],
    categoryShort: /private/i.test(r[H.category]) ? 'Private' : 'GIDC',
    district,
    location: r[H.location],
    village: parsedLoc.villageParts[0] ?? null,
    taluka: parsedLoc.taluka,
    address: r[H.address],
    contact: r[H.contact],
    phone: r[H.phone],
    email: r[H.email],
    office: r[H.office],
    notes: noteRaw,
    source: r[H.source],
    tentative: /\(tentative\)/i.test(name),
    phaseMatch: (name.match(/phase[- ]?(i{1,3}|iv|v|vi{1,3})/i) || [])[1] || null,
    industries: mInd ? mInd[1].trim() : null,
    areaHa: mArea ? Number(mArea[1]) : null,
    approval: mApp ? mApp[1] : null,
    lat,
    lng,
    geo: {
      method,
      confidence,
      matchedPlace: matchedName,
      placeDistanceKm,
    },
  });
}

/* ---------------------------------------------------------------- reports */

const dist = {};
for (const p of out) dist[p.geo.confidence] = (dist[p.geo.confidence] || 0) + 1;
console.log('\nconfidence distribution:', dist);

const methodDist = {};
for (const p of out) {
  const m = p.geo.method.split(' (')[0];
  methodDist[m] = (methodDist[m] || 0) + 1;
}
console.log('method distribution:', methodDist);

console.log(`\nunresolved (${unresolved.length}):`);
for (const u of unresolved) {
  console.log(`  [${u.sr}] ${u.name} | ${u.district} | ${u.location}`);
  console.log(`      ladder: ${u.ladder.join(' , ')}`);
  console.log(`      best:   ${u.bestHit}`);
}

const lowConf = out.filter((p) => p.geo.confidence === 'low');
console.log(`\nlow confidence (${lowConf.length}):`);
for (const p of lowConf) {
  console.log(`  [${p.id}] ${p.name} | ${p.district} | ${p.location} -> ${p.geo.matchedPlace} (${p.geo.method})`);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(out));
console.log(`\nwrote ${outPath} (${out.length} features, ${fs.statSync(outPath).size} bytes)`);