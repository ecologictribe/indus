import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(__dirname, '..', 'data');

const PARKS = process.argv[2] || path.join(DATA, 'parks.json');
const CACHE = path.join(DATA, 'osm-nominatim-cache.json');

const UA = 'GujaratIndustrialEstatesAtlas/1.0 (offline research dataset build)';
const VIEWBOX = [68.0, 24.8, 74.6, 20.0];
const BBOX = { minLng: 67.8, maxLng: 74.8, minLat: 19.8, maxLat: 25.0 };
const MAX_DISTRICT_OFFSET_KM = 70;

const cache = fs.existsSync(CACHE) ? JSON.parse(fs.readFileSync(CACHE, 'utf8')) : {};
let dirty = false;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function normKey(s) {
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function km(lng1, lat1, lng2, lat2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
}

const GENERIC = new Set([
  'gidc', 'industrial', 'estate', 'estates', 'park', 'parks', 'msme', 'non', 'women', 'woman',
  'development', 'agro', 'food', 'sez', 'zone', 'mini', 'new', 'phase', 'japanese', 'housing',
  'apparel', 'v', 'u', 'n', 'g', 'r', 'idc', 'ashray', 'infrastructure', 'project', 'private',
  'limited', 'pvt', 'llp', 'and', 'company', 'india', 'the', 'of', 'general', 'special',
  'expansion', 'nanak', 'ujjain', 'narsingh', 'gorakh', 'pratap',
]);

/** Reduce a park/location label to the bare place name Nominatim can match. */
function placeKey(s) {
  return s
    .replace(/\s*\(.*?\)\s*/g, ' ')
    .split(/[,;/]/)
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) =>
      x
        .split(/\s+/)
        .filter((t) => !GENERIC.has(t.toLowerCase()))
        .join(' ')
        .trim(),
    )
    .filter((x) => x.length >= 4)
    .sort((a, b) => b.length - a.length)[0] ?? null;
}

async function search(q) {
  if (Object.prototype.hasOwnProperty.call(cache, q)) return cache[q];
  const url = new URL('https://nominatim.openstreetmap.org/search');
  for (const [k, v] of Object.entries({
    q,
    format: 'jsonv2',
    limit: '10',
    countrycodes: 'in',
    viewbox: VIEWBOX.join(','),
    bounded: '1',
    'accept-language': 'en',
  })) {
    url.searchParams.set(k, v);
  }

  let result = null;
  for (let attempt = 0; attempt < 3 && result === null; attempt++) {
    try {
      const res = await fetch(url, { headers: { 'User-Agent': UA, 'Accept-Language': 'en' } });
      if (res.status === 429 || res.status >= 500) {
        await sleep(3000 * (attempt + 1));
        continue;
      }
      if (!res.ok) break;
      const body = await res.json();
      result = body
        .filter((r) => +r.lat >= BBOX.minLat && +r.lat <= BBOX.maxLat && +r.lon >= BBOX.minLng && +r.lon <= BBOX.maxLng)
        .map((r) => ({
          lat: +(+r.lat).toFixed(5),
          lon: +(+r.lon).toFixed(5),
          name: r.name,
          norm: normKey(r.name),
          type: r.type,
          cls: r.class,
          importance: r.importance ?? 0,
          osm: `${r.osm_type}/${r.osm_id}`,
          display: r.display_name,
        }));
    } catch {
      await sleep(2000 * (attempt + 1));
    }
  }
  if (result === null) result = [];
  cache[q] = result;
  dirty = true;
  await sleep(1150);
  return result;
}

const parks = JSON.parse(fs.readFileSync(PARKS, 'utf8'));
const targets = parks.filter((p) => p.geo.confidence === 'district' || p.geo.confidence === 'low');
console.log(`resolving ${targets.length} of ${parks.length} parks\n`);

// Anchor on the real district headquarters, resolved from the gazetteer.
const SEATS = JSON.parse(fs.readFileSync(path.join(DATA, 'district-seats.json'), 'utf8'));
const districtAnchors = new Map();
for (const [d, s] of Object.entries(SEATS)) districtAnchors.set(d, { lat: s.lat, lng: s.lng, name: s.place });
console.log('district anchors:', [...districtAnchors].map(([d, s]) => `${d}->${s.lat},${s.lng}`).join(' | '));

function validate(cands, wanted, anchorLat, anchorLng) {
  const key = normKey(wanted);
  const scored = [];
  for (const c of cands) {
    // Require the result to *be* the place we asked for: either an exact name
    // match, or the place name followed by a qualifier ("Odhav Lake").
    const exact = c.norm === key;
    const qualified = c.norm.startsWith(`${key} `);
    if (!exact && !qualified) continue;
    const dist = km(c.lon, c.lat, anchorLng, anchorLat);
    if (dist > MAX_DISTRICT_OFFSET_KM) continue;
    const placeLike = ['place', 'boundary'].includes(c.cls) ? 1.2 : 1;
    scored.push({ ...c, dist, score: c.importance * placeLike * (exact ? 1.5 : 1) });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored[0] ?? null;
}

let n = 0;
const report = [];
for (const p of targets) {
  const anchor = districtAnchors.get(p.district);
  const aLat = anchor?.lat ?? p.lat;
  const aLng = anchor?.lng ?? p.lng;

  const wanted = [placeKey(p.location), placeKey(p.name)].filter(Boolean);
  let hit = null;
  let usedKey = null;
  for (const w of wanted) {
    const q = `${w}, ${p.district}, Gujarat, India`;
    const cands = await search(q);
    const v = validate(cands, w, aLat, aLng);
    if (v) {
      hit = v;
      usedKey = w;
      break;
    }
  }

  if (hit) {
    p.lat = hit.lat;
    p.lng = hit.lon;
    p.geo = {
      method: 'osm-nominatim',
      confidence: 'medium',
      matchedPlace: hit.name,
      display: hit.display,
      osmType: hit.type,
      osmId: hit.osm,
      placeDistanceKm: +hit.dist.toFixed(1),
      geoId: p.geo.geoId ?? null,
    };
    report.push({ id: p.id, name: p.name, district: p.district, resolved: `osm:${hit.name}`, at: `${hit.lat},${hit.lon}`, kmFromAnchor: +hit.dist.toFixed(1) });
  } else {
    if (anchor) {
      p.lat = anchor.lat;
      p.lng = anchor.lng;
      p.geo = {
        method: 'district-anchor',
        confidence: 'approximate',
        matchedPlace: `${p.district} HQ (${anchor.name})`,
        geoId: p.geo.geoId ?? null,
      };
    }
    report.push({ id: p.id, name: p.name, district: p.district, resolved: anchor ? `district-anchor:${anchor.name}` : 'district-centroid', at: `${p.lat},${p.lng}`, kmFromAnchor: '' });
  }

  n++;
  if (dirty) {
    fs.writeFileSync(CACHE, JSON.stringify(cache, null, 1));
    dirty = false;
  }
  console.log(`[${n}/${targets.length}] #${p.id} ${p.name} -> ${p.geo.method} ${p.geo.matchedPlace} @ ${p.lat},${p.lng}`);
}

fs.writeFileSync(CACHE, JSON.stringify(cache, null, 1));

const dist = {};
for (const p of parks) dist[p.geo.confidence] = (dist[p.geo.confidence] || 0) + 1;
const methods = {};
for (const p of parks) methods[p.geo.method] = (methods[p.geo.method] || 0) + 1;
console.log('\nconfidence:', dist);
console.log('methods:', methods);
fs.writeFileSync(PARKS, JSON.stringify(parks));
console.log(`wrote ${PARKS}`);