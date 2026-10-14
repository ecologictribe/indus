import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', 'data', 'osm-gujarat-places.json');

const ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.private.coffee/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.osm.ch/api/interpreter',
  'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
];

const HEADERS = {
  'User-Agent': 'GujaratIndustrialEstatesAtlas/1.0 (research dataset build)',
  Accept: 'application/json',
};

// (south, west, north, east) - Gujarat with a small margin into neighbouring states.
const BBOX = '19.9,67.9,25.0,74.7';
const PLACES = '^(city|town|borough|village|hamlet|municipality|suburb|neighbourhood|quarter|isolated_dwelling)$';

const query = `[out:json][timeout:180];
(
  node["place"~"${PLACES}"](${BBOX});
  way["place"~"${PLACES}"](${BBOX});
  relation["place"~"${PLACES}"](${BBOX});
);
out center tags;`;

let raw = null;
for (const ep of ENDPOINTS) {
  for (const mode of ['post', 'get']) {
    try {
      process.stdout.write(`${mode} ${ep.replace('https://', '')}… `);
      const init =
        mode === 'get'
          ? { headers: HEADERS }
          : {
              method: 'POST',
              headers: { ...HEADERS, 'Content-Type': 'application/x-www-form-urlencoded' },
              body: new URLSearchParams({ data: query }).toString(),
            };
      const url = mode === 'get' ? `${ep}?data=${encodeURIComponent(query)}` : ep;
      const res = await fetch(url, init);
      if (!res.ok) {
        console.log(`HTTP ${res.status}`);
        await new Promise((r) => setTimeout(r, 4000));
        continue;
      }
      const text = await res.text();
      let body;
      try {
        body = JSON.parse(text);
      } catch {
        console.log('non-JSON response');
        await new Promise((r) => setTimeout(r, 4000));
        continue;
      }
      if (!body.elements || !body.elements.length) {
        console.log('empty result set');
        continue;
      }
      console.log(`ok, ${body.elements.length} elements`);
      raw = body.elements;
      break;
    } catch (e) {
      console.log(`error: ${e.message}`);
      await new Promise((r) => setTimeout(r, 4000));
    }
  }
  if (raw) break;
}

if (!raw) {
  console.error('all Overpass endpoints failed');
  process.exit(1);
}

const out = [];
for (const el of raw) {
  const t = el.tags || {};
  const lat = el.lat ?? el.center?.lat;
  const lon = el.lon ?? el.center?.lon;
  if (typeof lat !== 'number' || typeof lon !== 'number') continue;

  const names = new Set();
  for (const key of ['name', 'name:en', 'name:hi', 'name:gu', 'alt_name', 'official_name', 'short_name', 'loc_name']) {
    const v = t[key];
    if (typeof v === 'string' && v.trim()) {
      for (const piece of v.split(/[,;/]/)) {
        const p = piece.trim();
        if (p && p.length <= 80) names.add(p);
      }
    }
  }
  if (!names.size) continue;

  out.push({
    id: `${el.type}/${el.id}`,
    names: [...names],
    lat: Number(lat.toFixed(5)),
    lng: Number(lon.toFixed(5)),
    place: t.place,
    pop: Number(t.population || 0) || null,
    county: t['addr:county'] || t['addr:district'] || null,
    state: t['addr:state'] || 'Gujarat',
  });
}

fs.writeFileSync(OUT, JSON.stringify(out));
const places = new Map();
for (const r of out) places.set(r.place, (places.get(r.place) || 0) + 1);
console.log(`\nwrote ${OUT}: ${out.length} named places`);
console.log('by place type:', [...places.entries()].sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}=${v}`).join(', '));