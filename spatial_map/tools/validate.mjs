import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(__dirname, '..', 'data');

const parks = JSON.parse(fs.readFileSync(path.join(DATA, 'parks.json'), 'utf8'));
const seats = JSON.parse(fs.readFileSync(path.join(DATA, 'district-seats.json'), 'utf8'));

function km(lng1, lat1, lng2, lat2) {
  const R = 6371;
  const r = Math.PI / 180;
  const dLat = (lat2 - lat1) * r;
  const dLng = (lng2 - lng1) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

const THRESHOLD_KM = 70;
const rows = parks
  .map((p) => {
    const s = seats[p.district];
    return { p, d: s ? km(p.lng, p.lat, s.lng, s.lat) : NaN };
  })
  .sort((a, b) => b.d - a.d);

console.log('--- parks > 70 km from their district headquarters ---');
for (const { p, d } of rows) {
  if (d > THRESHOLD_KM) {
    console.log(`${d.toFixed(0).padStart(5)}km  #${String(p.id).padEnd(4)} ${p.name.slice(0, 44).padEnd(46)} ${p.district.padEnd(18)} ${p.geo.method.padEnd(16)} ${p.geo.matchedPlace ?? ''}`);
  }
}

const ds = rows.map((r) => r.d);
const q = (f) => ds[Math.min(ds.length - 1, Math.floor(ds.length * f))];
console.log(`\ndistance from district HQ (km): min ${q(0).toFixed(1)}  median ${q(0.5).toFixed(1)}  p90 ${q(0.9).toFixed(1)}  p99 ${q(0.99).toFixed(1)}  max ${ds[0].toFixed(1)}`);
console.log(`over threshold (>${THRESHOLD_KM}km): ${ds.filter((d) => d > THRESHOLD_KM).length}`);

const BBOX = { minLng: 67.5, maxLng: 74.8, minLat: 19.5, maxLat: 25.0 };
const outside = parks.filter((p) => !(p.lng >= BBOX.minLng && p.lng <= BBOX.maxLng && p.lat >= BBOX.minLat && p.lat <= BBOX.maxLat));
console.log(`outside Gujarat bbox: ${outside.length}`);

const conf = {};
const meth = {};
for (const p of parks) {
  conf[p.geo.confidence] = (conf[p.geo.confidence] || 0) + 1;
  meth[p.geo.method] = (meth[p.geo.method] || 0) + 1;
}
console.log('confidence:', conf);
console.log('methods:', meth);
console.log(`total parks: ${parks.length}`);