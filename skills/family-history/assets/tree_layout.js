const TREE_W = 140, TREE_H = 58;
// Раскладка древа песочными часами вокруг главного человека: предки расходятся вверх,
// боковые родственники спускаются от своих родителей, линии не пересекаются.
// Считается в браузере при открытии страницы, отдельных программ не требует.
function computeLayout(P, subset, rootPerson) {
  const W = TREE_W, H = TREE_H, GAP = 4, SEP = 14, ROW = H + 58;
  const yearOf = k => { const m = /\d{3,4}/.exec(P[k].y || ""); return m ? +m[0] : 9999; };
  return layout(subset, rootPerson);

function layout(subset, rootPerson) {
  const set = new Set(subset);
  const unitOf = {}, units = [];
  for (const k of set) {
    if (unitOf[k] !== undefined) continue;
    const u = [], st = [k], id = units.length;
    unitOf[k] = id;
    while (st.length) {
      const x = st.pop();
      u.push(x);
      for (const s of P[x].sp) if (set.has(s) && unitOf[s] === undefined) { unitOf[s] = id; st.push(s); }
    }
    u.sort((a, b) => (P[a].s === "M" ? 0 : 1) - (P[b].s === "M" ? 0 : 1));
    if (u.length > 2) {
      u.sort((a, b) => P[b].sp.filter(s => set.has(s)).length - P[a].sp.filter(s => set.has(s)).length);
      const hub = u.shift();
      u.splice(Math.ceil(u.length / 2), 0, hub);
    }
    units.push(u);
  }
  const width = i => units[i].length * W + (units[i].length - 1) * GAP;
  const ups = i => { const o = []; for (const k of units[i]) for (const q of P[k].par) if (set.has(q) && unitOf[q] !== i && !o.includes(unitOf[q])) o.push(unitOf[q]); return o; };
  const downs = i => { const o = []; for (const k of units[i]) for (const c of P[k].ch) if (set.has(c) && unitOf[c] !== i && !o.includes(unitOf[c])) o.push(unitOf[c]); return o.sort((a, b) => Math.min(...units[a].map(yearOf)) - Math.min(...units[b].map(yearOf))); };

  // поколения обходом от корня
  const gen = {};
  function assign(i, g) { gen[i] = g; for (const a of ups(i)) if (gen[a] === undefined) assign(a, g - 1); for (const d of downs(i)) if (gen[d] === undefined) assign(d, g + 1); }

  const seen = new Set();
  const shift = (b, dx) => { for (const k in b.x) b.x[k] += dx; for (const g in b.c) { b.c[g][0] += dx; b.c[g][1] += dx; } };
  const merge = (a, b) => { Object.assign(a.x, b.x); for (const g in b.c) { if (a.c[g]) { a.c[g][0] = Math.min(a.c[g][0], b.c[g][0]); a.c[g][1] = Math.max(a.c[g][1], b.c[g][1]); } else a.c[g] = b.c[g].slice(); } };
  // на сколько сдвинуть b вправо от a (dir=1) или влево (dir=-1), чтобы они не задевали друг друга ни в одном ряду
  const gap = (a, b, dir) => {
    let d = dir > 0 ? -Infinity : Infinity, hit = false;
    for (const g in b.c) if (a.c[g]) { hit = true; d = dir > 0 ? Math.max(d, a.c[g][1] + SEP - b.c[g][0]) : Math.min(d, a.c[g][0] - SEP - b.c[g][1]); }
    return hit ? d : null;
  };
  function block(i) {
    seen.add(i);
    const w = width(i);
    const self = { x: { [i]: 0 }, c: { [gen[i]]: [-w / 2, w / 2] } };
    // дети: ряд, по центру под семьёй
    const kids = downs(i).filter(d => !seen.has(d));
    let row = null;
    const tops = [];
    for (const d of kids) {
      if (seen.has(d)) continue;
      const b = block(d);
      if (row) { const dx = gap(row, b, 1); shift(b, dx === null ? 0 : dx); merge(row, b); } else row = b;
      tops.push(d);
    }
    if (row) {
      const mean = tops.reduce((s, d) => s + row.x[d], 0) / tops.length;
      shift(row, -mean);
      // ряд детей не должен задевать саму семью: разные поколения, но проверим на случай кольца
      const dx = gap(self, row, 1);
      if (row.c[gen[i]]) shift(row, dx);
      merge(self, row);
    }
    // родители: мужа налево, жены направо, если родителей двое у разных супругов
    const pars = ups(i).filter(a => !seen.has(a));
    pars.forEach((a, idx) => {
      if (seen.has(a)) return;
      const b = block(a);
      const left = pars.length === 1 ? null : idx < pars.length / 2;
      if (left === null) {
        // одна родительская семья: над собой, боковые родственники уйдут в сторону
        const cx = b.x[a];
        shift(b, -cx);
        const l = gap(self, b, -1), r = gap(self, b, 1);
        if (l !== null || r !== null) { if (Math.abs(l ?? 1e9) <= Math.abs(r ?? 1e9)) { if (l < 0) shift(b, l); } else if (r > 0) shift(b, r); }
      } else {
        // отталкиваем от уже стоящего
        shift(b, -b.x[a]);
        const dx = gap(self, b, left ? -1 : 1);
        if (dx !== null) shift(b, dx);
      }
      merge(self, b);
    });
    return self;
  }

  const rootU = rootPerson && unitOf[rootPerson] !== undefined ? unitOf[rootPerson] : 0;
  assign(rootU, 0);
  const whole = block(rootU);
  // оторванные куски справа
  units.forEach((_, i) => {
    if (seen.has(i)) return;
    assign(i, 0);
    const b = block(i);
    const dx = gap(whole, b, 1);
    shift(b, (dx === null ? Object.values(whole.c).reduce((m, c) => Math.max(m, c[1]), 0) + SEP * 4 - Math.min(...Object.values(b.c).map(c => c[0]))
                          : dx + SEP * 4));
    merge(whole, b);
  });
  // родители встают над детьми, если в их ряду есть место: линии короче
  const rowsByGen = {};
  units.forEach((_, i) => (rowsByGen[gen[i]] = rowsByGen[gen[i]] || []).push(i));
  for (let pass = 0; pass < 3; pass++) {
    for (const g of Object.keys(rowsByGen).map(Number).sort((a, b) => b - a)) {
      const row = rowsByGen[g].sort((a, b) => whole.x[a] - whole.x[b]);
      row.forEach((i, idx) => {
        const kids = downs(i);
        if (!kids.length) return;
        const target = kids.reduce((s, d) => s + whole.x[d], 0) / kids.length;
        const lo = idx ? whole.x[row[idx - 1]] + (width(row[idx - 1]) + width(i)) / 2 + SEP : -Infinity;
        const hi = idx + 1 < row.length ? whole.x[row[idx + 1]] - (width(row[idx + 1]) + width(i)) / 2 - SEP : Infinity;
        whole.x[i] = Math.max(lo, Math.min(hi, target));
      });
    }
  }
  for (const g in whole.c) { const r = rowsByGen[g] || []; if (r.length) whole.c[g] = [Math.min(...r.map(i => whole.x[i] - width(i) / 2)), Math.max(...r.map(i => whole.x[i] + width(i) / 2))]; }
  const gens = Object.values(gen), g0 = Math.min(...gens);
  const minX = Math.min(...Object.values(whole.c).map(c => c[0]));
  const maxX = Math.max(...Object.values(whole.c).map(c => c[1]));
  const cards = {}, out = { w: maxX - minX + 40, h: (Math.max(...gens) - g0) * ROW + H + 40, cards: [], links: [], pairs: [] };
  units.forEach((u, i) => {
    const w = width(i), x0 = whole.x[i] - w / 2 - minX + 20, y = (gen[i] - g0) * ROW + 20;
    u.forEach((k, idx) => { const x = x0 + idx * (W + GAP); cards[k] = [x, y]; out.cards.push([k, Math.round(x), Math.round(y)]); });
    for (let j = 0; j + 1 < u.length; j++) if (P[u[j]].sp.includes(u[j + 1])) out.pairs.push([u[j], u[j + 1]]);
  });
  for (const c of set) {
    const pars = P[c].par.filter(p => set.has(p));
    if (!pars.length) continue;
    const x1 = pars.map(p => cards[p][0] + W / 2).reduce((s, v) => s + v, 0) / pars.length;
    out.links.push([Math.round(x1), Math.round(cards[pars[0]][1] + H), Math.round(cards[c][0] + W / 2), Math.round(cards[c][1]), c]);
  }
  return out;
}
}
