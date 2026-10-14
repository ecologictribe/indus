import fs from 'node:fs';
import path from 'node:path';

const SRC = process.argv[2];
const OUT = process.argv[3];

const raw = JSON.parse(fs.readFileSync(SRC, 'utf8'));
console.log('features:', raw.features.length);
console.log('sample props:', JSON.stringify(raw.features[0].properties));

const gj = raw.features.filter((f) => {
  const p = f.properties || {};
  const blob = JSON.stringify(p).toLowerCase();
  return blob.includes('gujarat');
});
console.log('gujarat features:', gj.length);
for (const f of gj) console.log(' -', JSON.stringify(f.properties));

// Ramer-Douglas-Peucker simplification on a lon/lat ring.
function rdp(points, eps) {
  if (points.length <= 2) return points;
  let maxDist = -1;
  let idx = 0;
  const [ax, ay] = points[0];
  const [bx, by] = points[points.length - 1];
  const dx = bx - ax;
  const dy = by - ay;
  const denom = Math.hypot(dx, dy) || 1e-12;
  for (let i = 1; i < points.length - 1; i++) {
    const [px, py] = points[i];
    const d = Math.abs(dy * px - dx * py + bx * ay - by * ax) / denom;
    if (d > maxDist) {
      maxDist = d;
      idx = i;
    }
  }
  if (maxDist > eps) {
    const left = rdp(points.slice(0, idx + 1), eps);
    const right = rdp(points.slice(idx), eps);
    return left.slice(0, -1).concat(right);
  }
  return [points[0], points[points.length - 1]];
}

function simplifyRing(ring, eps) {
  let pts = ring.map((c) => [c[0], c[1]]);
  // Drop the duplicated closing vertex: RDP degenerates on zero-length baselines.
  if (pts.length > 2) {
    const a = pts[0];
    const b = pts[pts.length - 1];
    if (a[0] === b[0] && a[1] === b[1]) pts = pts.slice(0, -1);
  }
  const out = rdp(pts, eps);
  if (out.length < 3) return [pts[0], pts[1] ?? pts[0], pts[2] ?? pts[0]];
  out.push(out[0]);
  return out.map(([x, y]) => [Number(x.toFixed(4)), Number(y.toFixed(4))]);
}

function simplifyGeom(geom, eps) {
  if (!geom) return geom;
  if (geom.type === 'Polygon') {
    return { type: 'Polygon', coordinates: geom.coordinates.map((r) => simplifyRing(r, eps)) };
  }
  if (geom.type === 'MultiPolygon') {
    return {
      type: 'MultiPolygon',
      coordinates: geom.coordinates.map((poly) => poly.map((r) => simplifyRing(r, eps))),
    };
  }
  return geom;
}

const EPS = 0.012;
const features = gj.map((f) => {
  const g = simplifyGeom(f.geometry, EPS);
  return {
    type: 'Feature',
    properties: { ...f.properties },
    geometry: g,
  };
});

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ type: 'FeatureCollection', features }));
console.log('wrote', OUT, fs.statSync(OUT).size, 'bytes');