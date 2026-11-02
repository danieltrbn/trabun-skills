// Просмотрщик древа: перетаскивание, щипок, поиск, карточка человека с переходом к родным.
function mountTree(root, opts) {
  const { P, LAY, key, me, search } = opts;
  const L = LAY[key], W = LAY.W, H = LAY.H, NS = "http://www.w3.org/2000/svg";
  const pos = {};
  L.cards.forEach(c => pos[c[0]] = c);
  root.classList.add("tw");
  root.innerHTML = `<div class="tw-bar">${search ? `<input class="tw-q" type="search" placeholder="Найти человека" aria-label="Найти человека"><div class="tw-res" hidden></div>` : ""}<button data-a="me">${opts.meLabel || "К началу"}</button><button data-a="fit">Вся ветка</button><button data-a="in" aria-label="Крупнее">+</button><button data-a="out" aria-label="Мельче">−</button></div><div class="tw-view"><svg class="tw-svg"><g class="tw-g"></g></svg></div><div class="tw-card" hidden></div>`;
  const view = root.querySelector(".tw-view"), svg = root.querySelector("svg"), g = root.querySelector(".tw-g"), card = root.querySelector(".tw-card");
  const el = (n, a, t) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (t) e.textContent = t; return e; };
  const links = document.createDocumentFragment();
  L.links.forEach(([x1, y1, x2, y2, c]) => {
    const m = (y1 + y2) / 2;
    links.appendChild(el("path", { d: `M${x1} ${y1}C${x1} ${m} ${x2} ${m} ${x2} ${y2}`, class: "tw-l" + (P[c].l ? " on" : "") }));
  });
  g.appendChild(links);
  (L.pairs || []).forEach(([a, b]) => {
    const A = pos[a], B = pos[b];
    if (A && B) g.appendChild(el("path", { d: `M${Math.min(A[1], B[1]) + W} ${A[2] + H / 2}H${Math.max(A[1], B[1])}`, class: "tw-l" + (P[a].l && P[b].l ? " on" : "") }));
  });
  const wrap = (s, n) => { const w = s.split(" "), o = []; let c = ""; for (const x of w) { if ((c + " " + x).trim().length > n && c) { o.push(c); c = x; } else c = (c + " " + x).trim(); } if (c) o.push(c); if (o.length > 2) { o[1] = o.slice(1).join(" "); o.length = 2; if (o[1].length > n + 1) o[1] = o[1].slice(0, n) + "…"; } return o; };
  const nodes = {};
  L.cards.forEach(([k, x, y]) => {
    const p = P[k];
    const n = el("g", { transform: `translate(${x} ${y})`, class: "tw-c b-" + (p.b || "x") + (p.l ? " line" : "") + (k === me ? " me" : ""), tabindex: 0, role: "button", "aria-label": p.n + (p.y ? ", " + p.y : "") });
    n.appendChild(el("rect", { width: W, height: H, rx: 7 }));
    n.appendChild(el("rect", { width: 4, height: H - 12, x: 5, y: 6, rx: 2, class: "tw-s" }));
    const t = wrap(p.n, 15);
    t.forEach((s, i) => n.appendChild(el("text", { x: 15, y: 19 + i * 15, class: "tw-n" }, s)));
    n.appendChild(el("text", { x: 15, y: H - 8, class: "tw-y" }, p.y || ""));
    n.addEventListener("click", ev => { if (!moved) { show(k); ev.stopPropagation(); } });
    n.addEventListener("keydown", ev => { if (ev.key === "Enter") show(k); });
    g.appendChild(n);
    nodes[k] = n;
  });
  let s = 1, tx = 0, ty = 0, moved = false;
  const apply = () => g.setAttribute("transform", `translate(${tx} ${ty}) scale(${s})`);
  const size = () => { const r = view.getBoundingClientRect(); return [r.width || 600, r.height || 480]; };
  const fit = () => { const [w, h] = size(); s = Math.min(w / L.w, h / L.h, 1) * .98; tx = (w - L.w * s) / 2; ty = (h - L.h * s) / 2; apply(); };
  const center = (k, z) => { const c = pos[k]; if (!c) return; const [w, h] = size(); s = z || Math.max(s, .9); tx = w / 2 - (c[1] + W / 2) * s; ty = h / 2 - (c[2] + H / 2) * s; apply(); };
  const zoom = (f, cx, cy) => { const [w, h] = size(); cx = cx ?? w / 2; cy = cy ?? h / 2; const n = Math.min(2.4, Math.max(.03, s * f)); tx = cx - (cx - tx) * n / s; ty = cy - (cy - ty) * n / s; s = n; apply(); };
  // перетаскивание и щипок
  const pts = new Map();
  let last = null, dist = 0;
  view.addEventListener("pointerdown", e => { pts.set(e.pointerId, e); last = [e.clientX, e.clientY]; moved = false; if (pts.size === 2) { const [a, b] = [...pts.values()]; dist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY); } });
  view.addEventListener("pointermove", e => {
    if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, e);
    if (pts.size === 1 && last) {
      const dx = e.clientX - last[0], dy = e.clientY - last[1];
      if (!moved && Math.hypot(dx, dy) < 4) return;
      if (!moved) { try { view.setPointerCapture(e.pointerId); } catch (x) {} }
      moved = true; tx += dx; ty += dy; last = [e.clientX, e.clientY]; apply();
    } else if (pts.size === 2) {
      const [a, b] = [...pts.values()], d = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), r = view.getBoundingClientRect();
      moved = true;
      if (dist) zoom(d / dist, (a.clientX + b.clientX) / 2 - r.left, (a.clientY + b.clientY) / 2 - r.top);
      dist = d;
    }
  });
  const up = e => { pts.delete(e.pointerId); if (pts.size === 1) last = (v => [v.clientX, v.clientY])([...pts.values()][0]); else last = null; dist = 0; };
  view.addEventListener("pointerup", up); view.addEventListener("pointercancel", up);
  view.addEventListener("wheel", e => { e.preventDefault(); if (e.ctrlKey || e.metaKey) { const r = view.getBoundingClientRect(); zoom(e.deltaY < 0 ? 1.12 : .89, e.clientX - r.left, e.clientY - r.top); } else { tx -= e.deltaX; ty -= e.deltaY; apply(); } }, { passive: false });
  const place = p => [p.bd, p.bp].filter(Boolean).join(", ");
  const dateRu = d => (d || "").replace(/\bABT\b/g, "около").replace(/\bBET\b/g, "между").replace(/\bAND\b/g, "и").replace(/\bEST\b/g, "около").replace(/\b(BEF|BEFORE)\b/g, "до").replace(/\b(AFT|AFTER)\b/g, "после").replace(/\bJAN\b/g, "января").replace(/\bFEB\b/g, "февраля").replace(/\bMAR\b/g, "марта").replace(/\bAPR\b/g, "апреля").replace(/\bMAY\b/g, "мая").replace(/\bJUN\b/g, "июня").replace(/\bJUL\b/g, "июля").replace(/\bAUG\b/g, "августа").replace(/\bSEP\b/g, "сентября").replace(/\bOCT\b/g, "октября").replace(/\bNOV\b/g, "ноября").replace(/\bDEC\b/g, "декабря");
  function row(label, list) {
    if (!list.length) return "";
    return `<p><span>${label}</span> ${list.map(k => (pos[k] ? `<button data-go="${k}">${P[k].n}</button>` : `<b>${P[k].n}</b>`)).join(", ")}</p>`;
  }
  function show(k) {
    const p = P[k];
    Object.values(nodes).forEach(n => n.classList.remove("sel"));
    if (nodes[k]) nodes[k].classList.add("sel");
    const sib = [...new Set(p.par.flatMap(q => P[q].ch))].filter(c => c !== k);
    card.hidden = false;
    card.innerHTML = `<h4>${p.n}</h4>` +
      (p.bd || p.bp ? `<p><span>${p.s === "F" ? "Родилась" : "Родился"}</span> ${[dateRu(p.bd), p.bp].filter(Boolean).join(", ")}</p>` : "") +
      (p.dd || p.dp ? `<p><span>${p.s === "F" ? "Умерла" : "Умер"}</span> ${[dateRu(p.dd), p.dp].filter(Boolean).join(", ")}</p>` : "") +
      row("Родители", p.par) + row(p.s === "F" ? "Муж" : "Жена", p.sp) + row("Дети", p.ch) + row("Братья и сёстры", sib);
    card.querySelectorAll("[data-go]").forEach(b => b.onclick = () => { center(b.dataset.go); show(b.dataset.go); });
  }
  root.querySelector(".tw-bar").addEventListener("click", e => {
    const a = e.target.dataset && e.target.dataset.a;
    if (a === "fit") fit();
    if (a === "in") zoom(1.3);
    if (a === "out") zoom(.77);
    if (a === "me") { center(me, 1); show(me); }
  });
  if (search) {
    const q = root.querySelector(".tw-q"), res = root.querySelector(".tw-res");
    q.addEventListener("input", () => {
      const v = q.value.trim().toLowerCase();
      res.hidden = v.length < 2;
      if (v.length < 2) return;
      const hit = L.cards.map(c => c[0]).filter(k => P[k].n.toLowerCase().includes(v)).slice(0, 12);
      res.innerHTML = hit.length ? hit.map(k => `<button data-go="${k}">${P[k].n} <i>${P[k].y}</i></button>`).join("") : "<em>Никого не нашлось</em>";
      res.querySelectorAll("button").forEach(b => b.onclick = () => { res.hidden = true; q.value = ""; center(b.dataset.go, 1); show(b.dataset.go); });
    });
  }
  const start = () => { if (opts.start === "fit") fit(); else { center(opts.start || me, opts.zoom || .9); } };
  start();
  if ("IntersectionObserver" in window) { const o = new IntersectionObserver(es => { if (es[0].isIntersecting) { start(); o.disconnect(); } }); o.observe(view); }
  return { show, center };
}
