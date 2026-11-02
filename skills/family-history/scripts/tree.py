#!/usr/bin/env python3
"""Рабочее древо семьи: импорт, правки с источником, проверка, экспорт.
Исходные файлы не меняются никогда: каждая правка даёт новую версию.

  tree.py new                 tree/tree_v1.json
  tree.py import  файл.ged    tree/tree_v1.json
  tree.py apply   tree_v1.json правки.json tree_v2.json   (журнал рядом: changes.md)
  tree.py audit   tree_v2.json [отчёт.md]
  tree.py compare первое.ged второе.ged [отчёт.md]
  tree.py branches tree_v2.json ID_главного_человека
  tree.py export  tree_v2.json tree_v2.ged
  tree.py pagedata tree_v2.json family.json tree_people.json

Только стандартная библиотека Python.
"""
import datetime
import json
import os
import re
import sys
from collections import Counter, defaultdict

LABELS = ("скан", "индекс", "публикация", "интервью", "семейное", "чужое древо", "вывод")
WEAK = ("чужое древо", "вывод")
EVENT_TAGS = {"BIRT", "DEAT", "BURI", "CHR", "BAPM", "RESI", "OCCU", "EMIG", "IMMI", "NATU", "MILI", "CENS", "EDUC", "RELI", "TITL", "EVEN", "GRAD", "RETI", "PROP"}
THIS_YEAR = datetime.date.today().year


def die(msg):
    sys.exit("Ошибка: " + msg)


def load(path):
    return json.load(open(path, encoding="utf-8"))


def save_new(path, data):
    if os.path.exists(path):
        die(path + " уже есть. Версии не перезаписываются: возьми следующий номер.")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def read_ged_lines(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            if enc == "utf-16" and raw[:2] not in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1").splitlines()


def clean_id(x):
    return x.strip().strip("@")


def empty_tree(source=""):
    return {"meta": {"source": source, "made": datetime.date.today().isoformat()}, "people": {}, "families": {}, "sources": {}, "detached": []}


def parse_ged(path):
    t = empty_tree(os.path.basename(path))
    skipped = Counter()
    rec, kind, ev, last_text = None, None, None, None
    level1 = None
    for line in read_ged_lines(path):
        m = re.match(r"\s*(\d+)\s+(@[^@]+@\s+)?(\S+)\s?(.*)", line)
        if not m:
            continue
        lv, xref, tag, val = int(m[1]), m[2], m[3], m[4].strip()
        if tag in ("CONC", "CONT") and last_text is not None:
            box, key = last_text
            box[key] += ("\n" if tag == "CONT" else "") + val
            continue
        if lv == 0:
            ev, level1, last_text = None, None, None
            kind = tag
            if tag == "INDI":
                rec = t["people"].setdefault(clean_id(xref), {"name": "", "alt": [], "sex": "", "birth": {}, "death": {}, "events": [], "notes": [], "sources": [], "famc": [], "fams": []})
            elif tag == "FAM":
                rec = t["families"].setdefault(clean_id(xref), {"husb": "", "wife": "", "chil": [], "marr": {}, "notes": [], "sources": []})
            elif tag == "SOUR" and xref:
                rec = t["sources"].setdefault(clean_id(xref), {"title": "", "ref": "", "url": "", "label": ""})
            else:
                rec = None
                if tag not in ("HEAD", "TRLR"):
                    skipped[tag] += 1
            continue
        if rec is None:
            continue
        if lv == 1:
            level1, ev, last_text = tag, None, None
            if kind == "INDI":
                if tag == "NAME":
                    if rec["name"]:
                        rec["alt"].append(val)
                    else:
                        rec["name"] = val
                elif tag == "SEX":
                    rec["sex"] = val[:1]
                elif tag in ("FAMC", "FAMS"):
                    rec[tag.lower()].append(clean_id(val))
                elif tag == "BIRT":
                    ev = rec["birth"]
                elif tag == "DEAT":
                    ev = rec["death"]
                elif tag in EVENT_TAGS:
                    ev = {"type": tag, "note": val} if val else {"type": tag}
                    rec["events"].append(ev)
                elif tag == "NOTE":
                    rec["notes"].append(val)
                    last_text = (rec["notes"], len(rec["notes"]) - 1)
                elif tag == "SOUR":
                    rec["sources"].append(clean_id(val)) if val.startswith("@") else add_inline_source(t, rec, val)
                else:
                    skipped[tag] += 1
            elif kind == "FAM":
                if tag == "HUSB":
                    rec["husb"] = clean_id(val)
                elif tag == "WIFE":
                    rec["wife"] = clean_id(val)
                elif tag == "CHIL":
                    rec["chil"].append(clean_id(val))
                elif tag == "MARR":
                    ev = rec["marr"]
                elif tag == "NOTE":
                    rec["notes"].append(val)
                    last_text = (rec["notes"], len(rec["notes"]) - 1)
                elif tag == "SOUR":
                    rec["sources"].append(clean_id(val)) if val.startswith("@") else add_inline_source(t, rec, val)
                else:
                    skipped[tag] += 1
            elif kind == "SOUR":
                if tag == "TITL":
                    rec["title"] = val
                    last_text = (rec, "title")
                elif tag in ("AUTH", "PUBL", "TEXT"):
                    rec["ref"] = (rec["ref"] + " " + val).strip()
                    last_text = (rec, "ref")
                elif tag in ("WWW", "URL", "_URL"):
                    rec["url"] = val
        elif lv == 2 and ev is not None:
            if tag == "DATE":
                ev["date"] = val
            elif tag == "PLAC":
                ev["place"] = val
            elif tag == "NOTE":
                ev["note"] = val
                last_text = (ev, "note")
            elif tag == "SOUR" and kind == "INDI":
                rec["sources"].append(clean_id(val)) if val.startswith("@") else add_inline_source(t, rec, val)
            elif tag == "SOUR" and kind == "FAM":
                rec["sources"].append(clean_id(val)) if val.startswith("@") else add_inline_source(t, rec, val)
        elif lv == 2 and level1 and kind == "INDI" and tag == "SOUR":
            rec["sources"].append(clean_id(val)) if val.startswith("@") else add_inline_source(t, rec, val)
    for p in t["people"].values():
        p["sources"] = list(dict.fromkeys(p["sources"]))
    # связи в GEDCOM бывают записаны только с одной стороны
    for fid, f in t["families"].items():
        for who in (f["husb"], f["wife"]):
            if who in t["people"] and fid not in t["people"][who]["fams"]:
                t["people"][who]["fams"].append(fid)
        for c in f["chil"]:
            if c in t["people"] and fid not in t["people"][c]["famc"]:
                t["people"][c]["famc"].append(fid)
    for pid, p in t["people"].items():
        for fid in p["famc"]:
            f = t["families"].get(fid)
            if f is not None and pid not in f["chil"]:
                f["chil"].append(pid)
        for fid in p["fams"]:
            f = t["families"].get(fid)
            if f is not None and pid not in (f["husb"], f["wife"]):
                f["wife" if p["sex"] == "F" else "husb"] = pid
    t["meta"]["not_imported"] = dict(skipped)
    return t


def add_inline_source(t, rec, val):
    sid = "SRC%d" % (len(t["sources"]) + 1)
    t["sources"][sid] = {"title": val, "ref": "", "url": "", "label": ""}
    rec["sources"].append(sid)


# ---------- правки ----------


def get_field(p, field):
    cur = p
    for part in field.split("."):
        cur = cur.get(part, "") if isinstance(cur, dict) else ""
    return cur


def set_field(p, field, value):
    parts = field.split(".")
    cur = p
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def apply_changes(t, ch):
    for sid, s in ch.get("sources", {}).items():
        if s.get("label") not in LABELS:
            die("источник %s: метка должна быть одной из: %s" % (sid, ", ".join(LABELS)))
        if not s.get("title"):
            die("источник %s без названия" % sid)
        t["sources"][sid] = s
    P, F, log = t["people"], t["families"], []

    def need_src(op):
        src = op.get("src")
        if not src or src not in t["sources"]:
            die("правка %s без источника. Нет источника, нет правки: %s" % (op.get("op"), json.dumps(op, ensure_ascii=False)))
        return src

    def need_who(pid):
        if pid not in P:
            die("нет человека " + str(pid))
        return P[pid]

    def need_fam(fid):
        if fid not in F:
            die("нет семьи " + str(fid))
        return F[fid]

    def cite(p, src):
        if src not in p.setdefault("sources", []):
            p["sources"].append(src)

    def show(pid):
        return plain_name(P[pid]["name"]) if pid in P else str(pid)

    for op in ch.get("ops", []):
        kind = op.get("op")
        if kind == "add_person":
            src = need_src(op)
            pid = op.get("id")
            if not pid or pid in P:
                die("add_person: id пуст или занят: %s" % pid)
            P[pid] = {"name": op["name"], "alt": op.get("alt", []), "sex": op.get("sex", ""), "birth": op.get("birth", {}), "death": op.get("death", {}), "events": op.get("events", []), "notes": [op["note"]] if op.get("note") else [], "sources": [src], "famc": [], "fams": []}
            log.append((plain_name(op["name"]), "нет в древе", "добавлен", src))
        elif kind == "set":
            src = need_src(op)
            p = need_who(op["who"])
            was = get_field(p, op["field"])
            set_field(p, op["field"], op["value"])
            cite(p, src)
            log.append((show(op["who"]), "%s: %s" % (op["field"], was or "пусто"), str(op["value"]), src))
        elif kind == "note":
            src = need_src(op)
            p = need_who(op["who"])
            p.setdefault("notes", []).append(op["text"])
            cite(p, src)
            log.append((show(op["who"]), "", "заметка: " + op["text"][:80], src))
        elif kind == "event":
            src = need_src(op)
            p = need_who(op["who"])
            p.setdefault("events", []).append({k: op[k] for k in ("type", "date", "place", "note") if k in op})
            cite(p, src)
            log.append((show(op["who"]), "", "событие %s %s" % (op.get("type", ""), op.get("date", "")), src))
        elif kind == "cite":
            src = need_src(op)
            cite(need_who(op["who"]), src)
            log.append((show(op["who"]), "", "подтверждено", src))
        elif kind == "add_family":
            src = need_src(op)
            fid = op.get("id")
            if not fid or fid in F:
                die("add_family: id пуст или занят: %s" % fid)
            F[fid] = {"husb": op.get("husb", ""), "wife": op.get("wife", ""), "chil": list(op.get("children", [])), "marr": op.get("marr", {}), "notes": [], "sources": [src]}
            for who in (op.get("husb"), op.get("wife")):
                if who:
                    need_who(who)["fams"].append(fid)
            for c in op.get("children", []):
                need_who(c)["famc"].append(fid)
            log.append((" и ".join(show(x) for x in (op.get("husb"), op.get("wife")) if x), "", "семья, детей: %d" % len(op.get("children", [])), src))
        elif kind == "add_child":
            src = need_src(op)
            f = need_fam(op["family"])
            need_who(op["child"])["famc"].append(op["family"])
            f["chil"].append(op["child"])
            log.append((show(op["child"]), "", "связан с родителями", src))
        elif kind == "set_marriage":
            src = need_src(op)
            f = need_fam(op["family"])
            was = f.get("marr", {})
            f["marr"] = op["marr"]
            f.setdefault("sources", []).append(src)
            log.append(("брак " + op["family"], json.dumps(was, ensure_ascii=False), json.dumps(op["marr"], ensure_ascii=False), src))
        elif kind == "detach":
            if not op.get("why"):
                die("detach: напиши why, почему связь снята")
            f = need_fam(op["family"])
            if op["child"] not in f["chil"]:
                die("в семье %s нет ребёнка %s" % (op["family"], op["child"]))
            f["chil"].remove(op["child"])
            P[op["child"]]["famc"].remove(op["family"])
            t["detached"].append({"child": op["child"], "family": op["family"], "why": op["why"], "was": show(op["child"])})
            log.append((show(op["child"]), "связан с семьёй " + op["family"], "связь снята: " + op["why"], op.get("src", "")))
        elif kind == "merge":
            if not op.get("why"):
                die("merge: напиши why")
            keep, drop = need_who(op["keep"]), need_who(op["drop"])
            for fid in drop["famc"]:
                F[fid]["chil"] = [op["keep"] if x == op["drop"] else x for x in F[fid]["chil"]]
                if fid not in keep["famc"]:
                    keep["famc"].append(fid)
            for fid in drop["fams"]:
                for r in ("husb", "wife"):
                    if F[fid][r] == op["drop"]:
                        F[fid][r] = op["keep"]
                if fid not in keep["fams"]:
                    keep["fams"].append(fid)
            for key in ("notes", "sources", "events"):
                keep.setdefault(key, []).extend(x for x in drop.get(key, []) if x not in keep.get(key, []))
            if drop["name"] != keep["name"]:
                keep.setdefault("alt", []).append(drop["name"])
            log.append((plain_name(keep["name"]), "дубль: " + plain_name(drop["name"]), "объединены: " + op["why"], op.get("src", "")))
            t["detached"].append({"merged": op["drop"], "into": op["keep"], "why": op["why"], "record": drop})
            del P[op["drop"]]
        elif kind == "remove_person":
            if not op.get("why"):
                die("remove_person: напиши why")
            p = need_who(op["who"])
            for fid in p["famc"]:
                F[fid]["chil"].remove(op["who"])
            for fid in p["fams"]:
                for r in ("husb", "wife"):
                    if F[fid][r] == op["who"]:
                        F[fid][r] = ""
            t["detached"].append({"removed": op["who"], "why": op["why"], "record": p})
            log.append((plain_name(p["name"]), "в древе", "снят: " + op["why"], op.get("src", "")))
            del P[op["who"]]
        else:
            die("неизвестная правка: %s" % kind)
    return log


# ---------- проверка ----------


def plain_name(n):
    return re.sub(r"\s+", " ", (n or "?").replace("/", " ")).strip()


def years(s):
    return [int(y) for y in re.findall(r"(?<!\d)(\d{3,4})(?!\d)", s or "") if 900 < int(y) <= THIS_YEAR + 1]


def first_year(ev):
    y = years((ev or {}).get("date", ""))
    return y[0] if y else None


def norm_name(n):
    n = plain_name(n).lower().replace("ё", "е")
    return " ".join(sorted(n.split()))


def relations(t):
    par, ch, sp = defaultdict(list), defaultdict(list), defaultdict(list)
    for f in t["families"].values():
        pa = [x for x in (f.get("husb"), f.get("wife")) if x in t["people"]]
        kids = [c for c in f.get("chil", []) if c in t["people"]]
        for a in pa:
            for b in pa:
                if a != b and b not in sp[a]:
                    sp[a].append(b)
            for c in kids:
                if c not in ch[a]:
                    ch[a].append(c)
        for c in kids:
            for a in pa:
                if a not in par[c]:
                    par[c].append(a)
    return par, ch, sp


PATRONYMIC = re.compile(r"^(.+?)(ович|евич|ьевич|ич|овна|евна|ьевна|ична|инична)$", re.I)


def audit(t):
    P, F = t["people"], t["families"]
    par, ch, sp = relations(t)
    err, check, holes = [], [], []
    tag = lambda pid: "%s [%s]" % (plain_name(P[pid]["name"]), pid)
    for pid, p in P.items():
        b, d = first_year(p.get("birth")), first_year(p.get("death"))
        if b and d and d < b:
            err.append("смерть раньше рождения: %s, %d и %d" % (tag(pid), b, d))
        if b and d and d - b > 105:
            err.append("прожил больше 105 лет: %s, %d–%d" % (tag(pid), b, d))
        if b and not d and THIS_YEAR - b > 110:
            holes.append("нет даты смерти, родился в %d: %s" % (b, tag(pid)))
        moth = [q for q in par[pid] if P[q].get("sex") == "F"]
        fath = [q for q in par[pid] if P[q].get("sex") == "M"]
        if len(moth) > 1 or len(fath) > 1 or len(par[pid]) > 2:
            err.append("больше двух родителей: %s: %s" % (tag(pid), ", ".join(tag(q) for q in par[pid])))
        for q in par[pid]:
            qb, qd = first_year(P[q].get("birth")), first_year(P[q].get("death"))
            if b and qb:
                age = b - qb
                female = P[q].get("sex") == "F"
                if age < 12:
                    err.append("родителю %d лет при рождении ребёнка: %s → %s" % (age, tag(q), tag(pid)))
                elif age < 15 or age > (50 if female else 70):
                    check.append("родителю %d лет при рождении ребёнка: %s → %s" % (age, tag(q), tag(pid)))
            if b and qd and b > qd + (0 if P[q].get("sex") == "F" else 1):
                err.append("ребёнок родился после смерти родителя: %s (ум. %d) → %s (р. %d)" % (tag(q), qd, tag(pid), b))
        # отчество против имени отца
        words = plain_name(p["name"]).split()
        for w in words[1:]:
            m = PATRONYMIC.match(w)
            if m and fath and len(m[1]) >= 2:
                father_first = plain_name(P[fath[0]]["name"]).split()[0].lower().replace("ё", "е")
                if father_first[:2] != m[1].lower().replace("ё", "е")[:2]:
                    check.append("отчество не сходится с именем отца: %s, отец %s" % (tag(pid), tag(fath[0])))
                break
        for s in sp[pid]:
            sb = first_year(P[s].get("birth"))
            if b and sb and pid < s and abs(b - sb) >= 25:
                check.append("разница супругов %d лет: %s и %s" % (abs(b - sb), tag(pid), tag(s)))
        if not par[pid] and not ch[pid] and not sp[pid]:
            holes.append("ни с кем не связан: " + tag(pid))
        srcs = [t["sources"].get(x, {}) for x in p.get("sources", [])]
        if not srcs:
            holes.append("нет ни одного источника: " + tag(pid))
        elif all(s.get("label") in WEAK for s in srcs):
            check.append("держится только на чужом древе или выводе: " + tag(pid))
    for fid, f in F.items():
        m = first_year(f.get("marr"))
        for who in (f.get("husb"), f.get("wife")):
            if who in P and m:
                b, d = first_year(P[who].get("birth")), first_year(P[who].get("death"))
                if b and m < b:
                    err.append("брак в %d, раньше рождения в %d: %s, семья %s" % (m, b, tag(who), fid))
                elif b and m - b < 14:
                    err.append("брак в %d лет: %s, семья %s" % (m - b, tag(who), fid))
                if d and m > d:
                    err.append("брак после смерти: %s, семья %s" % (tag(who), fid))
        for c in f.get("chil", []):
            if c not in P:
                err.append("семья %s ссылается на человека %s, которого нет" % (fid, c))
    # дубли
    seen = defaultdict(list)
    for pid, p in P.items():
        seen[norm_name(p["name"])].append(pid)
    for ids in seen.values():
        if len(ids) < 2:
            continue
        for i, a in enumerate(ids):
            for b_id in ids[i + 1:]:
                ya, yb = first_year(P[a].get("birth")), first_year(P[b_id].get("birth"))
                if ya and yb and abs(ya - yb) > 5:
                    continue
                if set(par[a]) & set(par[b_id]):
                    check.append("одно имя у детей одних родителей (дубль или умерший ребёнок, чьё имя дали младшему): %s и %s" % (tag(a), tag(b_id)))
                else:
                    check.append("возможный дубль: %s и %s" % (tag(a), tag(b_id)))
    # петли
    state = {}

    def walk(x, chain):
        if state.get(x) == 1:
            err.append("петля в родстве: " + " → ".join(chain + [tag(x)]))
            return
        if state.get(x) == 2:
            return
        state[x] = 1
        for q in par[x]:
            walk(q, chain + [tag(x)])
        state[x] = 2

    sys.setrecursionlimit(max(10000, len(P) * 4))
    for pid in P:
        walk(pid, [])
    # обрывки: связные куски
    comp, n = {}, 0
    for pid in P:
        if pid in comp:
            continue
        n += 1
        st = [pid]
        while st:
            x = st.pop()
            if x in comp:
                continue
            comp[x] = n
            st += par[x] + ch[x] + sp[x]
    sizes = Counter(comp.values())
    stats = {"людей": len(P), "семей": len(F), "источников": len(t["sources"]), "кусков древа": len(sizes), "самый большой кусок": max(sizes.values()) if sizes else 0, "без источника": sum(1 for p in P.values() if not p.get("sources"))}
    return err, check, holes, stats


def audit_report(t, name):
    err, check, holes, stats = audit(t)
    out = ["# Проверка древа: " + name, "", "Что считает скрипт: только логику дат и связей. Правду он не знает: чистый отчёт не значит, что древо верное.", ""]
    out += ["- %s: %s" % kv for kv in stats.items()]
    not_imp = t.get("meta", {}).get("not_imported")
    if not_imp:
        out += ["- не перенесено из файла (исходник цел): " + ", ".join("%s %d" % kv for kv in not_imp.items())]
    for title, rows in (("Ошибки: так не бывает", err), ("Проверить: необычно, но возможно", check), ("Дыры", holes)):
        out += ["", "## %s (%d)" % (title, len(rows)), ""] + ["- " + r for r in sorted(set(rows))]
    return "\n".join(out) + "\n"


def tree_any(path):
    return load(path) if path.endswith(".json") else parse_ged(path)


def compare_report(a_path, b_path):
    a, b = tree_any(a_path), tree_any(b_path)
    idx = lambda t: {norm_name(p["name"]): pid for pid, p in t["people"].items()}
    ia, ib = idx(a), idx(b)
    na, nb = os.path.basename(a_path), os.path.basename(b_path)
    out = ["# Сравнение: %s (%d чел.) и %s (%d чел.)" % (na, len(a["people"]), nb, len(b["people"])), "", "Сопоставление только по совпадению имени. Разное написание одного человека попадёт в списки «только там» как двое.", ""]
    out += ["## Только в " + na, ""] + ["- " + plain_name(a["people"][ia[k]]["name"]) for k in sorted(set(ia) - set(ib))]
    out += ["", "## Только в " + nb, ""] + ["- " + plain_name(b["people"][ib[k]]["name"]) for k in sorted(set(ib) - set(ia))]
    out += ["", "## Разные даты у одного имени", ""]
    for k in sorted(set(ia) & set(ib)):
        pa, pb = a["people"][ia[k]], b["people"][ib[k]]
        for field, label in (("birth", "рождение"), ("death", "смерть")):
            da, db = first_year(pa.get(field)), first_year(pb.get(field))
            if da and db and da != db:
                out.append("- %s, %s: %d и %d" % (plain_name(pa["name"]), label, da, db))
    return "\n".join(out) + "\n"


# ---------- разбор веток ----------


def ancestors(pid, par):
    seen, st = set(), [pid]
    while st:
        x = st.pop()
        if x not in seen:
            seen.add(x)
            st += par[x]
    return seen


def descendants(pid, ch):
    seen, st = set(), [pid]
    while st:
        x = st.pop()
        if x not in seen:
            seen.add(x)
            st += ch[x]
    return seen


def branches_report(t, me):
    P = t["people"]
    if me not in P:
        die("нет человека " + me)
    par, ch, _ = relations(t)
    lines = ["Главный: " + plain_name(P[me]["name"]), ""]
    level = [me]
    for _ in range(2):
        level = [q for x in level for q in par[x]]
    if not level:
        level = par[me] or [me]
    for g in level:
        anc = ancestors(g, par)
        all_kin = set()
        for a in anc:
            all_kin |= descendants(a, ch)
        surnames = Counter(w for a in anc for w in re.findall(r"/([^/]+)/", P[a]["name"]))
        top = sorted(anc, key=lambda a: first_year(P[a].get("birth")) or 9999)[:1]
        lines.append("- %s [%s]: прямых предков %d, вместе с боковыми %d; фамилии: %s; самый ранний: %s" % (plain_name(P[g]["name"]), g, len(anc), len(all_kin), ", ".join(s for s, _ in surnames.most_common(4)) or "нет", plain_name(P[top[0]]["name"]) if top else "нет"))
    lines += ["", 'В family.json ветка задаётся так: {"key": "ivanovy", "name": "Ивановы", "from": "ID"}: все предки этого человека и их потомки.']
    return "\n".join(lines) + "\n"


# ---------- данные страницы ----------


def apply_map(s, table):
    for a, b in table:
        s = s.replace(a, b)
    return s


def short_year(d):
    if not d:
        return ""
    ys = years(d)
    if not ys:
        return ""
    if d.upper().startswith("BET") and len(ys) >= 2:
        return "%d/%s" % (ys[0], str(ys[1])[-2:])
    return ("≈" if d.upper().startswith(("ABT", "EST", "CAL")) else "") + str(ys[0])


def page_data(t, cfg):
    P = t["people"]
    me = cfg["me"]
    if me not in P:
        die("family.json: нет человека me = %s" % me)
    ids = {k: "p%d" % i for i, k in enumerate(P)}
    full = cfg.get("name_map", {}).get("full", {})
    tokens = cfg.get("name_map", {}).get("tokens", {})
    places = cfg.get("place_map", [])
    living_mode = cfg.get("living", "no-dates")

    def show_name(raw):
        name = plain_name(raw)
        if name in full:
            return full[name]
        return " ".join(tokens.get(w, w) for w in name.split(" "))

    par, ch, sp = relations(t)
    line = ancestors(me, par)
    out = {}
    hidden = 0
    for k, p in P.items():
        bd, dd = (p.get("birth") or {}).get("date", ""), (p.get("death") or {}).get("date", "")
        by = first_year(p.get("birth"))
        living = not dd and (by is None or THIS_YEAR - by < 100) and k != me and not (p.get("death") or {}).get("place")
        known_dead = bool(cfg.get("known_dead")) and k in cfg["known_dead"]
        living = living and not known_dead
        name = show_name(p["name"])
        bp = apply_map((p.get("birth") or {}).get("place", ""), places)
        dp = apply_map((p.get("death") or {}).get("place", ""), places)
        if living and living_mode in ("no-dates", "first-name"):
            bd, bp = "", ""
            hidden += 1
            if living_mode == "first-name":
                name = name.split(" ")[0] if name else "?"
        b, d = short_year(bd), short_year(dd)
        out[ids[k]] = {"n": name, "y": (b + "–" + d) if d else b, "bp": bp, "dp": dp, "bd": bd, "dd": dd, "s": p.get("sex", ""), "par": [ids[q] for q in par[k]], "sp": [ids[q] for q in sp[k]], "ch": [ids[q] for q in ch[k]], "l": 1 if k in line else 0, "b": ""}

    def resolve(ref):
        if ref in P:
            return ref
        hits = [k for k, p in P.items() if plain_name(p["name"]) == ref]
        if len(hits) != 1:
            die('family.json: "%s": %s' % (ref, "таких двое и больше, укажи id" if hits else "нет такого человека"))
        return hits[0]

    branch = {}
    for br in cfg.get("branches", []):
        s = set()
        if br.get("from"):
            for a in ancestors(resolve(br["from"]), par):
                s |= descendants(a, ch)
        for r in br.get("roots", []):
            s |= descendants(resolve(r), ch)
        branch[br["key"]] = s
        print("ветка %s: %d чел." % (br["key"], len(s)))
    for k in P:
        for br in cfg.get("branches", []):
            if k in line and br.get("from") and k not in ancestors(resolve(br["from"]), par) and k != me:
                continue
            if k in branch[br["key"]]:
                out[ids[k]]["b"] = br["key"]
                break
    print("людей: %d, скрыты даты и места у вероятно живых: %d" % (len(out), hidden))
    return {"people": out, "me": ids[me], "branch": {b: sorted(ids[x] for x in s) for b, s in branch.items()}}


# ---------- экспорт ----------


def ged_text(tag, level, text):
    lines = str(text).split("\n")
    out = []
    for i, line in enumerate(lines):
        chunk, rest = line[:200], line[200:]
        out.append("%d %s %s" % (level if i == 0 else level + 1, tag if i == 0 else "CONT", chunk))
        while rest:
            chunk, rest = rest[:200], rest[200:]
            out.append("%d CONC %s" % (level + 1, chunk))
    return out


def ged_event(tag, ev):
    if not ev:
        return []
    o = ["1 " + tag]
    if ev.get("date"):
        o.append("2 DATE " + ev["date"])
    if ev.get("place"):
        o.append("2 PLAC " + ev["place"])
    if ev.get("note"):
        o += ged_text("NOTE", 2, ev["note"])
    return o


def export_ged(t, path):
    o = ["0 HEAD", "1 SOUR family-history-skill", "1 GEDC", "2 VERS 5.5.1", "2 FORM LINEAGE-LINKED", "1 CHAR UTF-8"]
    for pid, p in t["people"].items():
        o.append("0 @%s@ INDI" % pid)
        o.append("1 NAME " + (p.get("name") or "?"))
        o += ["1 NAME " + a for a in p.get("alt", [])]
        if p.get("sex"):
            o.append("1 SEX " + p["sex"])
        o += ged_event("BIRT", p.get("birth"))
        o += ged_event("DEAT", p.get("death"))
        for ev in p.get("events", []):
            o += ged_event(ev.get("type", "EVEN"), {k: v for k, v in ev.items() if k != "type"})
        for fid in p.get("famc", []):
            o.append("1 FAMC @%s@" % fid)
        for fid in p.get("fams", []):
            o.append("1 FAMS @%s@" % fid)
        for n in p.get("notes", []):
            o += ged_text("NOTE", 1, n)
        for s in p.get("sources", []):
            o.append("1 SOUR @%s@" % s)
    for fid, f in t["families"].items():
        o.append("0 @%s@ FAM" % fid)
        if f.get("husb"):
            o.append("1 HUSB @%s@" % f["husb"])
        if f.get("wife"):
            o.append("1 WIFE @%s@" % f["wife"])
        for c in f.get("chil", []):
            o.append("1 CHIL @%s@" % c)
        o += ged_event("MARR", f.get("marr"))
        for n in f.get("notes", []):
            o += ged_text("NOTE", 1, n)
        for s in f.get("sources", []):
            o.append("1 SOUR @%s@" % s)
    for sid, s in t["sources"].items():
        o.append("0 @%s@ SOUR" % sid)
        o += ged_text("TITL", 1, ("[%s] " % s["label"] if s.get("label") else "") + (s.get("title") or sid))
        if s.get("ref"):
            o += ged_text("TEXT", 1, s["ref"])
        if s.get("url"):
            o.append("1 WWW " + s["url"])
    o.append("0 TRLR")
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")


# ---------- команды ----------


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "new":
        save_new(a[1], empty_tree("с нуля"))
        print("Пустое древо:", a[1])
    elif cmd == "import":
        t = parse_ged(a[1])
        save_new(a[2], t)
        print("Людей %d, семей %d, источников %d. Не перенесено: %s" % (len(t["people"]), len(t["families"]), len(t["sources"]), t["meta"]["not_imported"] or "ничего"))
    elif cmd == "apply":
        t = load(a[1])
        ch = load(a[2])
        log = apply_changes(t, ch)
        save_new(a[3], t)
        journal = os.path.join(os.path.dirname(os.path.abspath(a[3])), "changes.md")
        with open(journal, "a", encoding="utf-8") as j:
            j.write("\n## %s → %s, %s\n\n| Кто | Было | Стало | Источник |\n|---|---|---|---|\n" % (os.path.basename(a[1]), os.path.basename(a[3]), os.path.basename(a[2])))
            for who, was, now, src in log:
                s = t["sources"].get(src, {})
                cell = lambda x: str(x).replace("|", "/").replace("\n", " ")
                j.write("| %s | %s | %s | %s |\n" % (cell(who), cell(was), cell(now), cell("[%s] %s" % (s.get("label", ""), s.get("title", src))) if src else ""))
        err, _, _, stats = audit(t)
        print("Правок %d. Людей %d. Новых ошибок логики в версии: %d" % (len(log), stats["людей"], len(err)))
    elif cmd == "audit":
        report = audit_report(tree_any(a[1]), os.path.basename(a[1]))
        if len(a) > 2:
            open(a[2], "w", encoding="utf-8").write(report)
            print("Отчёт:", a[2])
        else:
            print(report)
    elif cmd == "compare":
        report = compare_report(a[1], a[2])
        if len(a) > 3:
            open(a[3], "w", encoding="utf-8").write(report)
            print("Отчёт:", a[3])
        else:
            print(report)
    elif cmd == "branches":
        print(branches_report(load(a[1]), a[2]))
    elif cmd == "export":
        export_ged(load(a[1]), a[2])
        print("GEDCOM:", a[2])
    elif cmd == "pagedata":
        data = page_data(load(a[1]), load(a[2]))
        json.dump(data, open(a[3], "w", encoding="utf-8"), ensure_ascii=False)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
