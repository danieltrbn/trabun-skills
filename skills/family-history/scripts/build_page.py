#!/usr/bin/env python3
"""Собирает страницу семейной истории из папки проекта.

  build_page.py <папка проекта>            собрать
  build_page.py init <папка проекта>       завести папку: шаблоны разделов, family.json, бриф

Выход: <проект>/family-history.html (полный файл) и <проект>/dist/family-history.html
(без обёртки, для публикации как Artifact). Текст живёт в page/sections/*.html, порядок задают номера в именах.
"""
import json
import os
import re
import shutil
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL, "assets")
FONTS = "https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&family=Golos+Text:wght@400;600&display=swap"
LEAFLET = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"
SLOTS = 6


def rd(*p):
    return open(os.path.join(*p), encoding="utf-8").read()


def init(root):
    os.makedirs(root, exist_ok=True)
    for d in ("refs", "research", "tree", "versions", "page/sections"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for name in sorted(os.listdir(os.path.join(ASSETS, "sections"))):
        dst = os.path.join(root, "page", "sections", name)
        if not os.path.exists(dst):
            shutil.copy(os.path.join(ASSETS, "sections", name), dst)
    for src, dst in (("family.example.json", "family.json"), ("migration.example.json", "page/migration.json"), ("romance.example.json", "page/romance.json"), ("research-brief.md", "research/BRIEF.md"), ("materials.md", "research/materials.md"), ("route.md", "research/route.md")):
        target = os.path.join(root, dst)
        if not os.path.exists(target):
            shutil.copy(os.path.join(ASSETS, src), target)
    print("Папка готова:", root)


def world_geo():
    topo = json.load(open(os.path.join(ASSETS, "vendor", "countries-50m.json"), encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(refs):
        o = []
        for r in refs:
            pts = arcs[r] if r >= 0 else arcs[~r][::-1]
            o.extend(pts[1:] if o else pts)
        res = []
        for lon, lat in o:
            p = [round(lon, 2), round(lat, 2)]
            if not res or res[-1] != p:
                res.append(p)
        return res

    polys = []
    for g in topo["objects"]["countries"]["geometries"]:
        if g["properties"].get("name") == "Antarctica":
            continue
        for poly in ([g["arcs"]] if g["type"] == "Polygon" else g["arcs"]):
            rings = [r for r in (ring(x) for x in poly) if len(r) >= 4]
            if not rings:
                continue
            lons = [p[0] for p in rings[0]]
            lats = [p[1] for p in rings[0]]
            if len(rings[0]) < 12 and (max(lons) < -130 or min(lons) > 100 or max(lats) < 20):
                continue
            polys.append(rings)
    return {"type": "MultiPolygon", "coordinates": polys}


def check(cfg, people, mig, rom, body):
    keys = [b["key"] for b in cfg.get("branches", [])]
    problems = []
    if len(keys) > SLOTS:
        problems.append("веток больше %d: не хватит цветов" % SLOTS)
    for k in keys:
        if not re.fullmatch(r"[a-z0-9_-]+", k):
            problems.append('ключ ветки "%s": только латиница, цифры, - и _' % k)
    places = mig.get("places", {})
    for i, m in enumerate(mig.get("moves", [])):
        if m.get("f") not in keys:
            problems.append('карта, шаг %d: ветка "%s" не из family.json' % (i + 1, m.get("f")))
        for end in ("a", "b"):
            if m.get(end) not in places:
                problems.append('карта, шаг %d: места "%s" нет в places' % (i + 1, m.get(end)))
            elif m.get(end) not in mig.get("names", {}):
                problems.append('карта: у места "%s" нет названия в names' % m.get(end))
    for k, xy in places.items():
        if not (-90 <= xy[0] <= 90 and -180 <= xy[1] <= 180):
            problems.append('карта: у места "%s" координаты вне земли, порядок [широта, долгота]' % k)
    for c in rom.get("couples", []):
        if c.get("b") not in keys:
            problems.append('пары: "%s", ветка "%s" не из family.json' % (c.get("who"), c.get("b")))
    for key in re.findall(r'data-tree="([^"]+)"', body):
        if key != "all" and key not in keys:
            problems.append('раздел: data-tree="%s", такой ветки нет' % key)
    names = {p["n"] for p in people["people"].values()}
    for start in re.findall(r'data-start="([^"]+)"', body):
        if start not in names:
            problems.append('раздел: data-start="%s", такого человека нет' % start)
    left = sorted(set(re.findall(r"\{\{[^}]*\}\}", body)))
    if left:
        problems.append("не заполнены места в шаблонах: " + ", ".join(left[:8]))
    return problems


def build(root):
    root = os.path.abspath(root)
    cfg = json.load(open(os.path.join(root, "family.json"), encoding="utf-8"))
    people = json.load(open(os.path.join(root, "tree", "tree_people.json"), encoding="utf-8"))
    sec_dir = os.path.join(root, "page", "sections")
    legend_items = ["<span><i style=\"background:var(--c-%s)\"></i>%s</span>" % (b["key"], b["name"]) for b in cfg.get("branches", [])]
    legend = '<div class="tw-key">' + "".join(legend_items) + '<span><i style="background:var(--other)"></i>остальные</span></div>'
    body = "\n".join(rd(sec_dir, s) for s in sorted(os.listdir(sec_dir)) if s.endswith(".html"))
    body = body.replace("<!--legend-->", legend)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    has_map = 'id="mig"' in body
    has_rom = 'id="rom"' in body
    load_opt = lambda name: json.load(open(os.path.join(root, "page", name), encoding="utf-8")) if os.path.exists(os.path.join(root, "page", name)) else {}
    mig = load_opt("migration.json") if has_map else {}
    rom = load_opt("romance.json") if has_rom else {}
    rom.setdefault("lineLabel", "Прямая линия " + cfg.get("me_label_gen", ""))
    problems = check(cfg, people, mig, rom, body)
    if problems:
        print("Страница не собрана, поправь:")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    vars_css = ":root{" + "".join("--c-%s:var(--b%d);" % (b["key"], i + 1) for i, b in enumerate(cfg.get("branches", []))) + "}\n"
    tree_css = "".join(".tw-c.b-%s .tw-s{fill:var(--c-%s)}.c-%s{color:var(--c-%s)}\n" % ((b["key"],) * 4) for b in cfg.get("branches", []))
    leaflet_css = ""
    if has_map or has_rom:
        leaflet_css = re.sub(r"url\(images/[^)]*\)", "none", rd(ASSETS, "vendor", "leaflet.min.css"))
    title = cfg.get("title", "История семьи")
    head = '<title>%s</title>\n<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="%s" rel="stylesheet">\n<style>\n%s\n%s%s%s</style>\n' % (title, FONTS, leaflet_css, rd(ASSETS, "page.css"), vars_css, tree_css)

    js = "const PEOPLE=" + json.dumps(people, ensure_ascii=False, separators=(",", ":")) + ";\n"
    js += "const FAMILY=" + json.dumps({"meLabel": cfg.get("me_label", "")}, ensure_ascii=False) + ";\n"
    if has_map:
        js += "const MIG=" + json.dumps(mig, ensure_ascii=False, separators=(",", ":")) + ";\n"
    if has_rom:
        js += "const ROM=" + json.dumps(rom, ensure_ascii=False, separators=(",", ":")) + ";\n"
    if has_map or has_rom:
        js += "const WORLD=" + json.dumps(world_geo(), separators=(",", ":")) + ";\n"
    js += rd(ASSETS, "tree_layout.js") + "\n" + rd(ASSETS, "tree_widget.js") + "\n"
    if has_map:
        js += rd(ASSETS, "migration_widget.js") + "\n"
    if has_rom:
        js += rd(ASSETS, "romance_widget.js") + "\n"
    js += """(function(){
 const P=PEOPLE.people,me=PEOPLE.me;
 const byName=n=>Object.keys(P).find(k=>P[k].n===n);
 const LAY={W:TREE_W,H:TREE_H};
 const subsetOf=key=>{
  if(key==='all')return Object.keys(P);
  const s=new Set(PEOPLE.branch[key]||[]);
  for(const k of [...s])for(const q of P[k].sp)s.add(q);
  return [...s];
 };
 document.querySelectorAll('[data-tree]').forEach(el=>{
  const key=el.dataset.tree,st=el.dataset.start?byName(el.dataset.start):null;
  LAY[key]=LAY[key]||computeLayout(P,subsetOf(key),me);
  mountTree(el,{P,LAY,key,me,meLabel:FAMILY.meLabel,search:key==='all',start:st||(el.dataset.fit?'fit':me),zoom:+(el.dataset.zoom||.9)});
  if(key!=='all')el.querySelector('.tw-view').classList.add('small');
 });
"""
    if has_map:
        js += " const m=document.getElementById('mig');\n if(m&&typeof L!=='undefined')mountMigration(m,document.getElementById('mig-ui'),document.getElementById('mig-step'),document.getElementById('mig-nav'),MIG,WORLD);\n"
    if has_rom:
        js += " const r=document.getElementById('rom');\n if(r&&typeof L!=='undefined')mountRomance(r,document.getElementById('rom-ui'),document.getElementById('rom-step'),document.getElementById('rom-nav'),document.getElementById('rom-list'),ROM,WORLD);\n"
    js += "})();\n"
    scripts = ('<script src="%s"></script>\n' % LEAFLET if has_map or has_rom else "") + "<script>\n" + js + "</script>\n"

    page = head + "<main>\n" + body + "\n</main>\n" + scripts
    os.makedirs(os.path.join(root, "dist"), exist_ok=True)
    open(os.path.join(root, "dist", "family-history.html"), "w", encoding="utf-8").write(page)
    full = '<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' + head + "</head>\n<body>\n<main>\n" + body + "\n</main>\n" + scripts + "</body>\n</html>\n"
    open(os.path.join(root, "family-history.html"), "w", encoding="utf-8").write(full)
    print("Собрано: %d KB, людей %d" % (len(page.encode()) // 1024, len(people["people"])))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "init":
        init(args[1])
    elif len(args) == 1:
        build(args[0])
    else:
        sys.exit(__doc__)
