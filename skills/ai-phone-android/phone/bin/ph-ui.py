import re, sys
import xml.etree.ElementTree as ET

data = sys.stdin.read()
if not data.strip():
    sys.exit("ph-ui: пустой дамп — экран, возможно, защищён или анимируется, попробуй ещё раз или ph-shot")
root = ET.fromstring(data)
for n in root.iter("node"):
    a = n.attrib
    text, desc = a.get("text", ""), a.get("content-desc", "")
    rid = a.get("resource-id", "").split("/")[-1]
    flags = [f for f in ("clickable", "scrollable", "checked", "focused") if a.get(f) == "true"]
    if a.get("class", "").endswith("EditText"):
        flags.append("input")
    if not (text or desc or flags):
        continue
    m = re.findall(r"\d+", a.get("bounds", ""))
    if len(m) != 4:
        continue
    x1, y1, x2, y2 = map(int, m)
    print(f"({(x1 + x2) // 2},{(y1 + y2) // 2}) {text!r}" + (f" desc={desc!r}" if desc else "")
          + (f" id={rid}" if rid else "") + (f" [{' '.join(flags)}]" if flags else ""))
