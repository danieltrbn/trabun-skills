// Романтическая карта: где встретились пары рода. Шаг — одна пара, стрелки ведут откуда каждый приехал.
function mountRomance(el, ui, cap, nav, list, D, WORLD) {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const colorOf = b => css("--c-" + b);
  const map = L.map(el, { scrollWheelZoom: false, zoomSnap: .25 }).setView([53, 30], 3.5);
  map.attributionControl.setPrefix(false);
  map.attributionControl.addAttribution("Natural Earth");
  const landStyle = () => ({ stroke: true, color: css("--edge"), weight: .6, fillColor: css("--land"), fillOpacity: 1, interactive: false });
  const land = L.geoJSON(WORLD, { style: landStyle, renderer: L.canvas({ padding: 1 }), interactive: false }).addTo(map);
  try { matchMedia("(prefers-color-scheme:dark)").addEventListener("change", () => { land.setStyle(landStyle()); draw(); }); } catch (e) {}
  const layer = L.layerGroup().addTo(map);
  let onlyLine = true, idx = -1;
  const seq = () => D.couples.filter(c => !onlyLine || c.d);
  const heart = (col, big, active) => L.divIcon({ className: "rom-h", html: `<span style="color:${col};font-size:${big ? 30 : active ? 20 : 15}px;opacity:${big || active ? 1 : .75}">♥</span>`, iconSize: [30, 30], iconAnchor: [15, 15] });
  function curve(a, b) {
    const pts = [], dx = b[1] - a[1], dy = b[0] - a[0], len = Math.hypot(dx, dy), bend = Math.min(.22, 3 / (len + 4)) * len;
    const mx = (a[0] + b[0]) / 2 - (dx / (len || 1)) * bend, my = (a[1] + b[1]) / 2 + (dy / (len || 1)) * bend;
    for (let i = 0; i <= 24; i++) { const t = i / 24, u = 1 - t; pts.push([u * u * a[0] + 2 * u * t * mx + t * t * b[0], u * u * a[1] + 2 * u * t * my + t * t * b[1]]); }
    return pts;
  }
  function draw(fit) {
    const s = seq();
    if (idx >= s.length) idx = -1;
    if (idx < 0) { cap.innerHTML = D.lead; nav.querySelector("span").textContent = `${s.length} пар`; }
    else { const c = s[idx]; cap.innerHTML = `<b>${c.who}.</b> ${c.when}, ${c.where}. ${c.t}`; nav.querySelector("span").textContent = `${idx + 1} из ${s.length}`; }
    nav.querySelector("[data-a=prev]").disabled = idx < 0;
    nav.querySelector("[data-a=next]").disabled = idx === s.length - 1;
    [...list.children].forEach(n => { const on = +n.dataset.i === idx; n.classList.toggle("on", on); });
    const size = map.getSize();
    if (!size.x || !size.y) return;
    layer.clearLayers();
    if (idx < 0) {
      s.forEach((c, i) => L.marker(c.at, { icon: heart(colorOf(c.b)), title: c.who }).on("click", () => go(i)).addTo(layer));
      if (fit !== false) map.fitBounds(s.map(c => c.at), { padding: [36, 36], maxZoom: 6 });
      return;
    }
    const c = s[idx], col = colorOf(c.b);
    s.forEach((o, i) => { if (i !== idx) L.marker(o.at, { icon: heart(colorOf(o.b)), title: o.who, opacity: .35 }).on("click", () => go(i)).addTo(layer); });
    const pts = [c.at];
    (c.from || []).forEach(f => {
      const p = [f[0], f[1]];
      pts.push(p);
      L.polyline(curve(p, c.at), { color: col, weight: 3, opacity: .9, dashArray: "2 7", lineCap: "round", interactive: false }).addTo(layer);
      L.circleMarker(p, { radius: 4, color: col, fillColor: col, fillOpacity: 1, weight: 1, interactive: false }).bindTooltip(f[2], { permanent: true, direction: "left", offset: [-6, 0], className: "place" }).addTo(layer);
    });
    L.marker(c.at, { icon: heart(col, true), interactive: false, zIndexOffset: 500 }).bindTooltip(c.where, { permanent: true, direction: "top", offset: [0, -12], className: "place" }).addTo(layer);
    if (fit !== false) { if (pts.length > 1) map.fitBounds(pts, { padding: [70, 70], maxZoom: 5.5 }); else map.setView(c.at, 5.5); }
  }
  function go(i) { idx = i; draw(); }
  function buildList() {
    list.innerHTML = "";
    seq().forEach((c, i) => {
      const b = document.createElement("button");
      b.dataset.i = i;
      b.innerHTML = `<i style="color:${colorOf(c.b)}">♥</i> <span>${c.who}</span> <em>${c.when}</em>`;
      b.onclick = () => { go(i); cap.scrollIntoView({ block: "nearest" }); el.scrollIntoView({ block: "nearest" }); };
      list.appendChild(b);
    });
  }
  [[D.lineLabel || "Прямая линия", true], ["Все пары", false]].forEach(([n, v], k) => {
    const b = document.createElement("button");
    b.textContent = n;
    b.className = k === 0 ? "on" : "";
    b.onclick = () => { [...ui.children].forEach(x => x.classList.remove("on")); b.classList.add("on"); onlyLine = v; idx = -1; buildList(); draw(); };
    ui.appendChild(b);
  });
  nav.addEventListener("click", e => { const a = e.target.dataset.a; if (a === "next" && idx < seq().length - 1) idx++; if (a === "prev" && idx >= 0) idx--; if (a) draw(); });
  map.on("zoomend", () => draw(false));
  buildList();
  const refit = () => { map.invalidateSize(); draw(); };
  draw();
  window.addEventListener("load", refit);
  window.addEventListener("resize", refit);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refit(); });
  if ("IntersectionObserver" in window) { const o = new IntersectionObserver(es => { if (es[0].isIntersecting) { refit(); o.disconnect(); } }); o.observe(el); }
}
