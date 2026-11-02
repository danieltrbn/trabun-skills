// Карта: как каждая ветка шла по миру. Один шаг — одно большое переселение.
function mountMigration(el, ui, cap, nav, D, WORLD) {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const P = D.places;
  const map = L.map(el, { scrollWheelZoom: false, worldCopyJump: false, zoomSnap: .25 }).setView([52, 25], 3.5);
  map.attributionControl.setPrefix(false);
  map.attributionControl.addAttribution("Natural Earth");
  const landStyle = () => ({ stroke: true, color: css("--edge"), weight: .6, fillColor: css("--land"), fillOpacity: 1, interactive: false });
  const land = L.geoJSON(WORLD, { style: landStyle, renderer: L.canvas({ padding: 1 }), interactive: false }).addTo(map);
  try { matchMedia("(prefers-color-scheme:dark)").addEventListener("change", () => { land.setStyle(landStyle()); draw(); }); } catch (e) {}
  const layer = L.layerGroup().addTo(map);
  const colorOf = f => css("--c-" + f);
  function curve(a, b) {
    const pts = [], dx = b[1] - a[1], dy = b[0] - a[0], len = Math.hypot(dx, dy), bend = Math.min(.22, 3 / (len + 4)) * len;
    const mx = (a[0] + b[0]) / 2 - (dx / (len || 1)) * bend, my = (a[1] + b[1]) / 2 + (dy / (len || 1)) * bend;
    for (let i = 0; i <= 28; i++) { const t = i / 28, u = 1 - t; pts.push([u * u * a[0] + 2 * u * t * mx + t * t * b[0], u * u * a[1] + 2 * u * t * my + t * t * b[1]]); }
    return pts;
  }
  function arrow(pts, color) {
    const a = map.latLngToLayerPoint(pts[pts.length - 3]), b = map.latLngToLayerPoint(pts[pts.length - 1]), ang = Math.atan2(b.y - a.y, b.x - a.x), s = 11;
    const p1 = map.layerPointToLatLng(L.point(b.x - s * Math.cos(ang - .45), b.y - s * Math.sin(ang - .45)));
    const p2 = map.layerPointToLatLng(L.point(b.x - s * Math.cos(ang + .45), b.y - s * Math.sin(ang + .45)));
    return L.polygon([pts[pts.length - 1], p1, p2], { color, fillColor: color, fillOpacity: 1, weight: 1, interactive: false });
  }
  const tabs = D.tabs;
  let tab = tabs[0].k, step = 0;
  const seq = () => (tab === "all" ? D.moves : D.moves.filter(m => m.f === tab));
  function caption(s) {
    if (tab === "all") { cap.innerHTML = D.allCaption; nav.hidden = true; }
    else { const m = s[step]; cap.innerHTML = `<b>${m.w}.</b> ${m.t}`; nav.hidden = false; nav.querySelector("span").textContent = `${step + 1} из ${s.length}`; nav.querySelector("[data-a=prev]").disabled = step === 0; nav.querySelector("[data-a=next]").disabled = step === s.length - 1; }
  }
  function draw(fit) {
    caption(seq());
    // пока карта не видна (фоновая вкладка, скрытый фрейм), считать по нулевому размеру нельзя
    const size = map.getSize();
    if (!size.x || !size.y) return;
    layer.clearLayers();
    const s = seq(), bounds = [];
    const shown = tab === "all" ? s : s.slice(0, step + 1);
    const labelled = {};
    shown.forEach((m, i) => {
      const cur = tab === "all" || i === shown.length - 1;
      const col = colorOf(m.f), a = P[m.a], b = P[m.b];
      const pts = curve(a, b);
      L.polyline(pts, { color: col, weight: cur ? 4 : 2.5, opacity: cur ? 1 : .55, dashArray: m.h ? "2 7" : null, lineCap: "round", interactive: false }).addTo(layer);
      if (cur) bounds.push(...pts);
      [m.a, m.b].forEach(k => { if (!labelled[k]) { labelled[k] = 1; const c = L.circleMarker(P[k], { radius: cur ? 5 : 3.5, color: col, fillColor: col, fillOpacity: 1, weight: 1, interactive: false }).addTo(layer); if (tab !== "all" || D.keyPlaces.includes(k)) c.bindTooltip(D.names[k], { permanent: true, direction: "right", offset: [6, 0], className: "place" }); } });
    });
    if (fit !== false) {
      if (tab === "all") map.fitBounds(s.flatMap(m => curve(P[m.a], P[m.b])), { padding: [24, 24], maxZoom: 7 });
      else if (bounds.length) map.fitBounds(bounds, { padding: [46, 46], maxZoom: 7 });
    }
    shown.forEach((m, i) => { if (tab === "all" || i === shown.length - 1) arrow(curve(P[m.a], P[m.b]), colorOf(m.f)).addTo(layer); });
  }
  tabs.forEach(t => { const b = document.createElement("button"); b.textContent = t.n; b.className = t.k === tab ? "on" : ""; b.onclick = () => { [...ui.children].forEach(c => c.classList.remove("on")); b.classList.add("on"); tab = t.k; step = 0; draw(); }; ui.appendChild(b); });
  nav.addEventListener("click", e => { const a = e.target.dataset.a; if (a === "next" && step < seq().length - 1) step++; if (a === "prev" && step > 0) step--; if (a) draw(); });
  map.on("zoomend", () => draw(false));
  const refit = () => { map.invalidateSize(); draw(); };
  draw();
  window.addEventListener("load", refit);
  window.addEventListener("resize", refit);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refit(); });
  if ("IntersectionObserver" in window) { const o = new IntersectionObserver(es => { if (es[0].isIntersecting) { refit(); o.disconnect(); } }); o.observe(el); }
}
