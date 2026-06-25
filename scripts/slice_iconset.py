#!/usr/bin/env python3
"""Sydney Icon Pack 슬라이서 — ChatGPT 라벨 시트(흰 배경)를 개별 투명 PNG로 분해.
사용: python3 scripts/slice_iconset.py [<sheets_dir>]
  기본 소스: ~/Downloads/SydneyLandmarkIconSet,  출력: stroll/assets/icons/<slug>.png
각 시트는 (rows×cols) 그리드 + 셀마다 아이콘 위 / 라벨 아래.
라벨은 '아이콘 아래 빈 간격(투명 행)'을 감지해 첫 콘텐츠 밴드만 남겨 제거한다.
"""
import os, sys, glob
from PIL import Image, ImageDraw

SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/SydneyLandmarkIconSet")
OUT = os.path.join(os.path.dirname(__file__), "..", "stroll", "assets", "icons")
OUT = os.path.abspath(OUT); os.makedirs(OUT, exist_ok=True)

def find(frag): return [f for f in glob.glob(os.path.join(SRC, "*.png")) if frag in os.path.basename(f)][0]

# (파일조각, rows, cols, [슬러그 row-major])
SHEETS = [
 ("03_30",2,4,["manly-ferry","watsons-bay-ferry","luna-park","circular-quay","taronga-zoo","mrs-macquaries-chair","kirribilli","barangaroo-reserve"]),
 ("06_15",2,4,["bondi-beach","coogee-beach","bronte-beach","manly-beach","shelly-beach","palm-beach","nielsen-park","balmoral-beach"]),
 ("08_29",2,4,["royal-national-park","blue-mountains","featherdale-wildlife-park","centennial-park","wendys-secret-garden","chinese-garden-of-friendship","hyde-park","observatory-hill"]),
 ("12_32",2,4,["sydney-fish-market","queen-victoria-building","paddys-market","carriageworks","newtown","surry-hills","paddington","glebe"]),
 ("15_06",2,4,["sydney-ferry","sydney-tram","sydney-metro","double-decker-train","opal-card","light-rail-stop","ferry-wharf","airport-train"]),
 ("16_45",2,4,["gelato","meat-pie","fish-and-chips","flat-white","tim-tam","lamington","acai-bowl","brunch"]),
 ("19_39",2,4,["koala","kangaroo","cockatoo","lorikeet","pelican","ibis","possum","wombat"]),
 ("21_36",1,5,["mca","art-gallery-nsw","powerhouse-museum","australian-museum","white-rabbit-gallery"]),
 ("24_38",2,3,["sydney-tower-eye","mrs-macquaries-point","observatory-hill","north-head","hornby-lighthouse","south-head"]),
 ("30_49",2,4,["sydney-opera-house","darling-harbour","barangaroo","circular-quay","taronga-zoo","sydney-harbour-bridge","the-rocks","royal-botanic-garden"]),
]

def remove_bg(im):
    im = im.convert("RGB"); seed = (255, 0, 255); w, h = im.size
    for c in [(0,0),(w-1,0),(0,h-1),(w-1,h-1),(w//2,0),(0,h//2),(w-1,h//2)]:
        ImageDraw.floodfill(im, c, seed, thresh=26)
    im = im.convert("RGBA"); px = im.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][:3] == seed: px[x, y] = (0, 0, 0, 0)
    return im

def slice_icon(cell):
    rgba = remove_bg(cell); w, h = rgba.size; a = rgba.split()[3]
    rowsum = [sum(a.getpixel((x, y)) for x in range(0, w, 3)) for y in range(h)]
    thr = max(rowsum) * 0.02 if max(rowsum) else 1
    bands = []; inb = False
    for y in range(h):
        c = rowsum[y] > thr
        if c and not inb: s = y; inb = True
        if not c and inb: bands.append([s, y]); inb = False
    if inb: bands.append([s, h])
    if not bands: return None
    merged = [bands[0][:]]
    for b in bands[1:]:
        if b[0] - merged[-1][1] < 14: merged[-1][1] = b[1]   # 아이콘 내부 작은 틈은 합침
        else: merged.append(b)
    top, bot = merged[0]                                       # 첫 밴드=아이콘, 이후 밴드=라벨(버림)
    icon = rgba.crop((0, top, w, bot)); bb = icon.getbbox()
    return icon.crop(bb) if bb else icon

def main():
    n = 0
    for frag, rows, cols, slugs in SHEETS:
        sh = Image.open(find(frag)).convert("RGB"); W, H = sh.size; cw, ch = W//cols, H//rows
        i = 0
        for r in range(rows):
            for c in range(cols):
                if i >= len(slugs): break
                ic = slice_icon(sh.crop((c*cw, r*ch, (c+1)*cw, (r+1)*ch)))
                if ic: ic.save(os.path.join(OUT, slugs[i] + ".png")); n += 1
                i += 1
    print(f"saved {n} icons -> {OUT}")

if __name__ == "__main__":
    main()
