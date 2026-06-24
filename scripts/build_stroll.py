#!/usr/bin/env python3
"""
하루 여행기 빌드 파이프라인 (한 방에 전체 재생성).

사용법:
  python3 scripts/build_stroll.py                 # 기본 소스 폴더에서 빌드
  python3 scripts/build_stroll.py --src "<폴더>"   # 다른 사진 폴더로
  python3 scripts/build_stroll.py --no-video       # 영상 변환 건너뛰기(빠름)

흐름: EXIF(GPS·시각) 추출 → 정류장 클러스터링 → 역지오코딩(지명 자동) →
      이동수단 추정 → 경로 스냅(Valhalla) → 영상 6초 클립 변환 → data.json + assets

사진을 추가/삭제한 뒤 이 스크립트만 다시 돌리면 경로가 새로 그려진다.
"""
import os, sys, json, glob, math, subprocess, argparse, time
from datetime import datetime
from PIL import Image, ExifTags

def _load_gkey():
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env):
            if line.startswith("GOOGLE_MAPS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("GOOGLE_MAPS_API_KEY", "")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = "/Users/jean/Documents/Today's stroll/Photos-3-001"
OUT = os.path.join(ROOT, "stroll")

# ── 수동 보정값(이벤트 브리프) ─────────────────────────────────
# GPS는 "어디·언제"(뼈대)만 준다. "무슨 이벤트·집·출발선·제목·톤" 같은 의미는
# 그날 거기 있던 사람만 안다 → 폴더별 brief.json에서 주입한다(없으면 순수 자동).
# 스키마:
#   title           오프닝/마무리 제목 (없으면 "오늘 하루")
#   date            "YYYY.MM.DD" (없으면 사진 EXIF에서 자동)
#   waypoints[]     사진 없는 경유지(환승역·귀가). after_index(0=첫 정류장 뒤,"end"=맨끝),
#                   name, lat, lon, time, mode, icon(기본 🚉)
#   mode_overrides{}  특정 정류장으로 들어가는 구간 이동수단 강제 (name 기준)
#   name_overrides{}  역지오코딩이 애매하게 잡은 지명 교정
#   hero_photos[]   오프닝 훅 대표 컷(첫 장=풀스크린 히어로). 비우면 첫 사진 자동
#   merge[]         GPS 노이즈로 쪼개진 연속 정류장 병합. names[], into{name,lat,lon}
#   rail_routes[]   기차 구간을 실제 통과 역들로 그림. between[출발명,도착명], stations[]
# 예시는 시드니 폴더의 brief.json 참고.
WAYPOINTS = []
MODE_OVERRIDES = {}
NAME_OVERRIDES = {}
HERO_PHOTOS = []
MERGE = []
RAIL_ROUTES = []
HERO_MASK = None   # 히어로 컷아웃에서 지울 영역 [x0,y0,x1,y1] (0~1 비율) — 같이 잡힌 타인 제거용
HERO_CUTOUT = True  # False면 컷아웃/흰 테두리 없이 보정한 사진 그대로 히어로로

# ── 테마 프리셋 ──────────────────────────────────────────────
# brief의 "theme" 한 줄이 아래 묶음을 기본값으로 깔아준다(개별 필드로 덮어쓰기 가능).
#   force_mode/collapse_dupes/hero_cutout = 빌드 동작, accent = 강조색(경로선·칩),
#   pace = 연출(feature stop 컷 수·도보/영상 체류시간) → data.json으로 앱에 전달.
DEFAULT_PACE = {"feature": 9, "route": 1, "photo": 760, "video": 3000}
THEMES = {
    # 러닝/운동: 속도감(빠른 컷, route 1컷), 러닝 고정, 보정 사진 히어로(테두리X), 쨍한 레드
    "run":   {"force_mode": "run", "collapse_dupes": True, "hero_cutout": False,
              "accent": "#ff5a4d", "pace": {"feature": 7, "route": 1, "photo": 560, "video": 3000}},
    # 도심 하루: 여유로운 페이싱, 자동 이동수단, 사진 그대로 히어로, 브랜드 코랄
    "city":  {"force_mode": None, "collapse_dupes": True, "hero_cutout": False,
              "accent": "#ff6b5e", "pace": {"feature": 9, "route": 1, "photo": 780, "video": 3000}},
    # 교외·자연: 더 느긋, 그린 강조색 (지형 타일은 추후)
    "nature": {"force_mode": None, "collapse_dupes": True, "hero_cutout": False,
               "accent": "#3f9d6b", "pace": {"feature": 9, "route": 1, "photo": 900, "video": 3200}},
}


def load_brief(src):
    """폴더별 이벤트 브리프(brief.json)를 읽어 수동 보정값으로 주입한다."""
    p = os.path.join(src, "brief.json")
    if os.path.exists(p):
        b = json.load(open(p, encoding="utf-8"))
        print(f"      브리프: {os.path.basename(p)}  «{b.get('title','(제목 자동)')}»")
    else:
        b = {}
        print("      브리프 없음 → 순수 자동 (제목·이동수단 GPS로만 추정)")
    # 테마가 기본값을 깔고, 브리프에 명시된 값이 우선한다
    t = THEMES.get(b.get("theme"), {})
    if b.get("theme") and not t:
        print(f"      ⚠️ 알 수 없는 theme '{b.get('theme')}' — 무시")
    for k in ("force_mode", "collapse_dupes", "hero_cutout", "accent", "pace"):
        if k not in b and k in t:
            b[k] = t[k]
    if b.get("theme") in THEMES:
        print(f"      테마: {b['theme']}")
    for k, d in (("waypoints", []), ("mode_overrides", {}), ("name_overrides", {}),
                 ("hero_photos", []), ("merge", []), ("rail_routes", []),
                 ("landmarks", []), ("force_mode", None), ("collapse_dupes", False),
                 ("copy", {}), ("hero_mask", None), ("hero_cutout", True),
                 ("theme", None), ("accent", None), ("pace", DEFAULT_PACE)):
        b.setdefault(k, d)
    return b
# ────────────────────────────────────────────────────────────

GPSIFD = {v: k for k, v in ExifTags.GPSTAGS.items()}
EXIF   = {v: k for k, v in ExifTags.TAGS.items()}

def to_deg(val, ref):
    dec = float(val[0]) + float(val[1]) / 60 + float(val[2]) / 3600
    return -dec if ref in ("S", "W") else dec

def hav(a, b):
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dla, dlo = la2 - la1, lo2 - lo1
    h = math.sin(dla/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlo/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def curl_json(url, post=None):
    cmd = ["curl", "-s", "--max-time", "25", "-A", "stroll/1.0"]
    if post is not None:
        cmd += ["-X", "POST", "-H", "Content-Type: application/json", "-d", post]
    cmd += [url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout)

# ── 1. 미디어 읽기 + 웹용 리사이즈 ──────────────────────────
def extract_media(src):
    photo_dir = os.path.join(OUT, "assets/photos")
    poster_dir = os.path.join(OUT, "assets/posters")
    os.makedirs(photo_dir, exist_ok=True); os.makedirs(poster_dir, exist_ok=True)
    media = []
    kept_photos, kept_posters = set(), set()
    photo_paths = sorted(set(
        glob.glob(os.path.join(src, "*.jpg")) + glob.glob(os.path.join(src, "*.JPG")) +
        glob.glob(os.path.join(src, "*.jpeg")) + glob.glob(os.path.join(src, "*.JPEG"))))
    for p in photo_paths:
        img = Image.open(p); ex = img.getexif()
        exififd = ex.get_ifd(0x8769); gps = ex.get_ifd(0x8825)
        dt = exififd.get(EXIF.get("DateTimeOriginal")) or ex.get(EXIF.get("DateTime"))
        lat = lon = None
        if gps and gps.get(GPSIFD["GPSLatitude"]):
            lat = to_deg(gps[GPSIFD["GPSLatitude"]], gps.get(GPSIFD["GPSLatitudeRef"]))
            lon = to_deg(gps[GPSIFD["GPSLongitude"]], gps.get(GPSIFD["GPSLongitudeRef"]))
        if not dt:
            continue
        t = datetime.strptime(str(dt), "%Y:%m:%d %H:%M:%S")
        name = os.path.basename(p)
        img = img.convert("RGB")
        o = ex.get(EXIF.get("Orientation"))
        if o == 3: img = img.rotate(180, expand=True)
        elif o == 6: img = img.rotate(270, expand=True)
        elif o == 8: img = img.rotate(90, expand=True)
        w, h = img.size
        if w > 1080: img = img.resize((1080, int(h * 1080 / w)))
        img.save(os.path.join(photo_dir, name), quality=82, optimize=True)
        kept_photos.add(name)
        media.append({"file": name, "type": "photo", "t": t, "lat": lat, "lon": lon})

    for p in sorted(glob.glob(os.path.join(src, "*.mp4")) + glob.glob(os.path.join(src, "*.MP4"))):
        name = os.path.basename(p)
        try:
            t = datetime.strptime(name.split(".")[0], "%Y%m%d_%H%M%S")
        except ValueError:
            continue
        poster = name.replace(".mp4", ".jpg").replace(".MP4", ".jpg")
        op = os.path.join(poster_dir, poster)
        if not os.path.exists(op):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "quiet", "-i", p,
                            "-vf", "scale=1080:-2", "-frames:v", "1", op])
        kept_posters.add(poster)
        media.append({"file": poster, "type": "video", "src_mp4": name, "t": t, "lat": None, "lon": None})

    media.sort(key=lambda m: m["t"])
    # 보간: GPS 없는 영상은 시간상 가까운 사진 위치를 빌려옴
    known = [m for m in media if m["lat"] is not None]
    for m in media:
        if m["lat"] is None and known:
            best = min(known, key=lambda k: abs((k["t"] - m["t"]).total_seconds()))
            m["lat"], m["lon"] = best["lat"], best["lon"]
    # 삭제된 원본의 잔여 산출물 청소
    for f in os.listdir(photo_dir):
        if f not in kept_photos: os.remove(os.path.join(photo_dir, f))
    for f in os.listdir(poster_dir):
        if f not in kept_posters: os.remove(os.path.join(poster_dir, f))
    return media

# ── 2. 정류장 클러스터링 ────────────────────────────────────
def cluster(media, max_m=180, max_gap=600):
    clusters, cur = [], []
    for m in media:
        if not cur:
            cur = [m]; continue
        cen = (sum(x["lat"] for x in cur)/len(cur), sum(x["lon"] for x in cur)/len(cur))
        gap = (m["t"] - cur[-1]["t"]).total_seconds()
        if hav(cen, (m["lat"], m["lon"])) > max_m or gap > max_gap:
            clusters.append(cur); cur = [m]
        else:
            cur.append(m)
    if cur: clusters.append(cur)
    return clusters

# ── 3. 역지오코딩 (지명 자동) ───────────────────────────────
def _rev(lat, lon, zoom):
    d = curl_json(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom={zoom}&addressdetails=1")
    return d.get("address", {}), d.get("name")

def geocode(lat, lon):
    try:
        a16, name = _rev(lat, lon, 16)
        sub = a16.get("suburb") or a16.get("neighbourhood")
        if sub:
            return sub
        subprocess.run(["sleep", "1.1"])
        a14, _ = _rev(lat, lon, 14)          # 교외(suburb)가 없으면 더 넓게
        return (a14.get("suburb") or a14.get("town") or a14.get("city_district")
                or a16.get("road") or name or "어딘가")
    except Exception:
        return "어딘가"

# ── 4. 경로 스냅 (Valhalla) / 곡선(arc) ─────────────────────
def decode_polyline6(s):
    coords = []; idx = lat = lng = 0; n = len(s)
    while idx < n:
        for j in range(2):
            shift = result = 0
            while True:
                b = ord(s[idx]) - 63; idx += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if result & 1 else (result >> 1)
            if j == 0: lat += d
            else: lng += d
        coords.append([lat/1e6, lng/1e6])
    return coords

def valhalla(a, b, costing):
    body = json.dumps({"locations": [{"lat": a[0], "lon": a[1]}, {"lat": b[0], "lon": b[1]}],
                       "costing": costing, "directions_options": {"units": "kilometers"}})
    d = curl_json("https://valhalla1.openstreetmap.de/route", post=body)
    pts = []
    for lg in d["trip"]["legs"]:
        pts += decode_polyline6(lg["shape"])
    return pts

def arc(a, b, bow=0.16, n=32):
    mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
    dx, dy = b[0]-a[0], b[1]-a[1]
    cx, cy = mx - dy*bow, my + dx*bow
    out = []
    for i in range(n+1):
        t = i/n
        x = (1-t)**2*a[0] + 2*(1-t)*t*cx + t*t*b[0]
        y = (1-t)**2*a[1] + 2*(1-t)*t*cy + t*t*b[1]
        out.append([round(x, 6), round(y, 6)])
    return out

# 역 좌표 조회(캐시) — Nominatim 검색
_STATION_CACHE = os.path.join(OUT, "stations.json")
def _load_stations():
    if os.path.exists(_STATION_CACHE):
        return json.load(open(_STATION_CACHE))
    return {}
def station_coord(name, cache):
    if name in cache:
        return cache[name]
    import urllib.parse
    q = urllib.parse.quote(f"{name} railway station, Sydney NSW Australia")
    try:
        d = curl_json(f"https://nominatim.openstreetmap.org/search?format=json&q={q}&limit=1")
        if d:
            cache[name] = [round(float(d[0]["lat"]), 6), round(float(d[0]["lon"]), 6)]
            subprocess.run(["sleep", "1.1"])
            return cache[name]
    except Exception:
        pass
    return None

def rail_geom(A, B, a_name, b_name, cache):
    for r in RAIL_ROUTES:
        if [a_name, b_name] == r["between"]:
            names = r["stations"]
        elif [b_name, a_name] == r["between"]:
            names = list(reversed(r["stations"]))
        else:
            continue
        pts, mids = [], []
        for i, nm in enumerate(names):
            c = station_coord(nm, cache)
            if not c:
                continue
            pts.append(c)
            if 0 < i < len(names)-1:
                mids.append({"name": nm, "lat": c[0], "lon": c[1]})
        if len(pts) < 2:
            return None, []
        pts[0] = [A[0], A[1]]; pts[-1] = [B[0], B[1]]   # 끝점은 실제 정류장과 정확히 연결
        return [[round(p[0], 6), round(p[1], 6)] for p in pts], mids
    return None, []

# ── Google Directions (정밀 경로: 기차=선로, 페리=항로, 도보=보도) ──
GKEY = _load_gkey()
def decode_polyline5(s):
    coords = []; idx = lat = lng = 0; n = len(s)
    while idx < n:
        for j in range(2):
            shift = result = 0
            while True:
                b = ord(s[idx]) - 63; idx += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if result & 1 else (result >> 1)
            if j == 0: lat += d
            else: lng += d
        coords.append([lat / 1e5, lng / 1e5])
    return coords

def google_leg(a, b, mode):
    if not GKEY:
        return None
    base = "https://maps.googleapis.com/maps/api/directions/json"
    try:
        if mode in ("walk", "ride", "run"):
            gm = "driving" if mode == "ride" else "walking"  # 러닝도 보도 경로(walking)로 스냅
            d = curl_json(f"{base}?origin={a[0]},{a[1]}&destination={b[0]},{b[1]}&mode={gm}&key={GKEY}")
            if d.get("status") != "OK":
                return None
            return [[round(p[0], 6), round(p[1], 6)] for p in decode_polyline5(d["routes"][0]["overview_polyline"]["points"])]
        # transit: 기차/트램/페리 — 실제 노선 step만 추출
        dep = int(time.time()) + 86400
        tm = {"train": "&transit_mode=train", "tram": "&transit_mode=tram"}.get(mode, "")
        d = curl_json(f"{base}?origin={a[0]},{a[1]}&destination={b[0]},{b[1]}&mode=transit{tm}&departure_time={dep}&key={GKEY}")
        if d.get("status") != "OK":
            return None
        WANT = {"train": ("HEAVY_RAIL", "RAIL", "COMMUTER_TRAIN", "SUBWAY", "METRO_RAIL", "HIGH_SPEED_TRAIN"),
                "tram": ("TRAM", "LIGHT_RAIL", "STREET_CAR", "CABLE_CAR"),
                "ferry": ("FERRY",)}
        want = WANT.get(mode, ("FERRY",))
        seg = []
        for s in d["routes"][0]["legs"][0]["steps"]:
            if s.get("travel_mode") == "TRANSIT":
                vt = s.get("transit_details", {}).get("line", {}).get("vehicle", {}).get("type", "")
                if vt in want:
                    seg += decode_polyline5(s["polyline"]["points"])
        if len(seg) < 2:
            return None
        return ([[round(a[0], 6), round(a[1], 6)]] +
                [[round(p[0], 6), round(p[1], 6)] for p in seg] +
                [[round(b[0], 6), round(b[1], 6)]])
    except Exception as e:
        print(f"   google_leg fail ({e})")
        return None

def leg_geom(a, b, mode):
    if mode in ("walk", "ride", "run"):
        try:
            g = valhalla(a, b, "auto" if mode == "ride" else "pedestrian")
            if g and len(g) >= 2: return g
        except Exception as e:
            print(f"   valhalla fail ({e}); arc fallback")
        return arc(a, b, 0.05, 12)
    if mode == "ferry": return arc(a, b, 0.16, 30)
    if mode in ("train", "tram"): return arc(a, b, 0.10, 40)
    return [a, b]

# ── 5. 영상 6초 클립 변환 ───────────────────────────────────
def transcode_videos(src, media, skip):
    vdir = os.path.join(OUT, "assets/videos")
    os.makedirs(vdir, exist_ok=True)
    wanted = {m["src_mp4"] for m in media if m["type"] == "video"}
    for f in os.listdir(vdir):
        if f not in wanted: os.remove(os.path.join(vdir, f))
    if skip:
        return
    for name in sorted(wanted):
        out = os.path.join(vdir, name)
        if os.path.exists(out):
            continue
        srcf = os.path.join(src, name)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", srcf, "-t", "6", "-an",
                        "-vf", "scale=540:-2,fps=24", "-c:v", "libx264", "-crf", "30",
                        "-preset", "veryfast", "-movflags", "+faststart", out])

# ── 오프닝 훅: 인물 컷아웃 + 흰 테두리 스티커 (rembg) ─────────
def make_hero_sticker(orig_path):
    # 원본 고해상도에서 생성 → Ken Burns 줌해도 선명(번짐 방지). 채도/대비/샤픈으로 쨍하게.
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    outdir = os.path.join(OUT, "assets/hook"); os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(orig_path))[0]   # 소스별 캐시(데이터셋 바뀌면 새로 생성)
    outp = os.path.join(outdir, f"hero-{stem}.png")
    rel = f"assets/hook/hero-{stem}.png"
    if os.path.exists(outp) and os.path.getmtime(outp) >= os.path.getmtime(orig_path):
        return rel
    TW = 1600                                            # 뷰포트 1080 + 줌 여유분
    base = ImageOps.exif_transpose(Image.open(orig_path).convert("RGB"))
    if base.width != TW:
        base = base.resize((TW, round(base.height * TW / base.width)), Image.LANCZOS)
    base = ImageEnhance.Brightness(base).enhance(1.12)
    base = ImageEnhance.Color(base).enhance(1.3)         # 쨍하게(채도↑)
    base = ImageEnhance.Contrast(base).enhance(1.1)
    base = base.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))
    W, H = base.size
    if not HERO_CUTOUT:                  # 컷아웃/흰 테두리 없이 보정한 사진 그대로 히어로로
        base.convert("RGB").save(outp, quality=94)
        print(f"   히어로(컷아웃·테두리 없이 보정 사진) → {rel}")
        return rel
    try:
        from rembg import remove, new_session
        hseg = new_session("u2net_human_seg")     # 사람만 분리(기둥 등 전경 제외)
    except Exception as e:
        print(f"   rembg 없음 → 스티커 건너뜀 ({e})")
        return None
    bg = base
    cut = remove(base.convert("RGBA"), session=hseg)
    alpha = cut.split()[3]
    # 컷아웃에 같이 잡힌 '떨어진 타인'(중앙 주제와 안 붙은 가장자리 조각) 제거
    try:
        import numpy as np
        from scipy import ndimage
        am = np.array(alpha); mask = am > 60
        lbl, n = ndimage.label(mask)
        if n > 1:
            sizes = ndimage.sum(mask, lbl, range(1, n + 1))
            big_idx = int(np.argmax(sizes)) + 1; big = sizes.max()
            xs = np.indices(mask.shape)[1]
            keep = np.zeros_like(mask)
            for i in range(1, n + 1):
                if sizes[i - 1] < big * 0.04:        # 자잘한 노이즈 무시
                    continue
                comp = lbl == i
                cx = xs[comp].mean()                 # 조각의 가로 중심
                if i == big_idx or (0.20 * W <= cx <= 0.90 * W):
                    keep |= comp                     # 가장 큰 덩어리 + 중앙대 조각만 유지
            alpha = Image.fromarray(np.where(keep, am, 0).astype("uint8"))
            cut = Image.merge("RGBA", (*cut.split()[:3], alpha))
            if int(n) - 1:
                print(f"   컷아웃 조각 {n}개 중 가장자리 타인 정리")
    except Exception as e:
        print(f"   컷아웃 정리 건너뜀 ({e})")
    # 브리프 지정 영역(같이 잡힌 타인 등) 비우기 — [x0,y0,x1,y1] 비율, 가장자리는 부드럽게
    if HERO_MASK:
        from PIL import ImageDraw
        x0, y0, x1, y1 = HERO_MASK
        clr = Image.new("L", (W, H), 255)
        ImageDraw.Draw(clr).rectangle([int(x0*W), int(y0*H), int(x1*W), int(y1*H)], fill=0)
        clr = clr.filter(ImageFilter.GaussianBlur(8))
        import numpy as _np
        alpha = Image.fromarray((_np.array(alpha) * (_np.array(clr)/255.0)).astype("uint8"))
        cut = Image.merge("RGBA", (*cut.split()[:3], alpha))
        print(f"   히어로 마스크 적용 {HERO_MASK}")
    # 흰 테두리: 실루엣을 자연스럽게 따라가는 얇은 윤곽(과한 두께 X)
    dil = alpha.filter(ImageFilter.MaxFilter(23)).filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: 255 if v > 80 else 0)
    white = Image.new("RGBA", (W, H), (255, 255, 255, 255)); white.putalpha(dil)
    sh_a = dil.filter(ImageFilter.GaussianBlur(20)).point(lambda v: int(v * 0.45))
    sh = Image.new("RGBA", (W, H), (20, 20, 28, 255)); sh.putalpha(sh_a)
    canvas = bg.convert("RGBA")
    canvas.alpha_composite(sh, (12, 20)); canvas.alpha_composite(white); canvas.alpha_composite(cut)
    canvas.convert("RGB").save(outp, quality=94)
    print(f"   히어로 스티커 생성(고해상도 {TW}px) → {rel}")
    return rel

# ── 메인 ────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()
    src = os.path.expanduser(args.src)
    if not os.path.isdir(src):
        sys.exit(f"소스 폴더 없음: {src}")

    global WAYPOINTS, MODE_OVERRIDES, NAME_OVERRIDES, HERO_PHOTOS, MERGE, RAIL_ROUTES, HERO_MASK, HERO_CUTOUT
    BRIEF = load_brief(src)
    WAYPOINTS = BRIEF["waypoints"]; MODE_OVERRIDES = BRIEF["mode_overrides"]
    NAME_OVERRIDES = BRIEF["name_overrides"]; HERO_PHOTOS = BRIEF["hero_photos"]
    MERGE = BRIEF["merge"]; RAIL_ROUTES = BRIEF["rail_routes"]; HERO_MASK = BRIEF["hero_mask"]
    HERO_CUTOUT = BRIEF["hero_cutout"]

    print(f"[1/5] 미디어 읽기 + 리사이즈  ({src})")
    media = extract_media(src)
    print(f"      사진 {sum(1 for m in media if m['type']=='photo')}장, "
          f"영상 {sum(1 for m in media if m['type']=='video')}개")

    print("[2/5] 정류장 클러스터링")
    clusters = cluster(media)
    stops = []
    for i, c in enumerate(clusters):
        cen = (sum(x["lat"] for x in c)/len(c), sum(x["lon"] for x in c)/len(c))
        mode = "start"
        if i > 0:
            d = hav((stops[-1]["lat"], stops[-1]["lon"]), cen)
            dt = (c[0]["t"] - prev_t1).total_seconds()/60
            spd = (d/1000)/((dt/60) if dt > 0 else .001)
            mode = "walk" if spd < 7 else ("ferry" if spd < 25 else "ride")
        stops.append({"lat": round(cen[0], 6), "lon": round(cen[1], 6),
                      "t0": c[0]["t"].strftime("%H:%M"), "t1": c[-1]["t"].strftime("%H:%M"),
                      "mode_in": mode,
                      "media": [{"file": m["file"], "type": m["type"],
                                 "time": m["t"].strftime("%H:%M"),
                                 **({"video": "assets/videos/" + m["src_mp4"]} if m["type"] == "video" else {})}
                                for m in c]})
        prev_t1 = c[-1]["t"]
    print(f"      {len(stops)}개 정류장")

    # force_mode: 전 구간 한 가지 이동수단으로 고정(예: 러닝 이벤트) → 속도 오분류 무력화
    if BRIEF["force_mode"]:
        for s in stops[1:]:
            s["mode_in"] = BRIEF["force_mode"]
        print(f"      이동수단 고정 → {BRIEF['force_mode']}")

    print("[3/5] 역지오코딩 (지명 자동)")
    for s in stops:
        nm = geocode(s["lat"], s["lon"])
        s["name"] = NAME_OVERRIDES.get(nm, nm)
        subprocess.run(["sleep", "1.1"])
    # 페리 위에서 연속으로 찍힌 점은 '페리 위'로
    for i, s in enumerate(stops):
        if s["mode_in"] == "ferry" and i > 0 and stops[i-1]["mode_in"] == "ferry":
            s["name"] = "페리 위"
    # landmarks: 좌표로 아는 지점 이름을 덮어쓴다(출발선·반환점·집 등). 먼저 잡힌 것 우선.
    for s in stops:
        for lm in BRIEF["landmarks"]:
            if hav((s["lat"], s["lon"]), (lm["lat"], lm["lon"])) <= lm.get("r", 120):
                s["name"] = lm["name"]
                if lm.get("feature"):     # 출발·결승·기념 등 = 여러 장 느긋하게(연출)
                    s["feature"] = True
                break
    # 연속 노이즈 정류장 병합 (지그재그 제거)
    def find_merge(name):
        for mg in MERGE:
            if name in mg["names"]:
                return mg
        return None
    merged_stops, i = [], 0
    while i < len(stops):
        mg = find_merge(stops[i]["name"])
        if mg:
            grp, j = [], i
            while j < len(stops) and stops[j]["name"] in mg["names"]:
                grp.append(stops[j]); j += 1
            merged_stops.append({
                "lat": mg["into"]["lat"], "lon": mg["into"]["lon"],
                "t0": grp[0]["t0"], "t1": grp[-1]["t1"], "mode_in": grp[0]["mode_in"],
                "name": mg["into"]["name"],
                "media": [m for g in grp for m in g["media"]]})
            i = j
        else:
            merged_stops.append(stops[i]); i += 1
    stops = merged_stops

    # collapse_dupes: 연속으로 같은 이름인 정류장을 하나로(landmarks 후 지그재그 정리)
    if BRIEF["collapse_dupes"]:
        collapsed = []
        for s in stops:
            if collapsed and collapsed[-1]["name"] == s["name"]:
                collapsed[-1]["t1"] = s["t1"]
                collapsed[-1]["media"] += s["media"]
            else:
                collapsed.append(s)
        if len(collapsed) < len(stops):
            print(f"      연속 중복 병합 {len(stops)} → {len(collapsed)}곳")
        stops = collapsed

    # 경유지(환승역·귀가) 삽입
    def wp_stop(wp):
        return {"lat": wp["lat"], "lon": wp["lon"], "t0": wp["time"], "t1": wp["time"],
                "mode_in": wp["mode"], "name": wp["name"], "waypoint": True,
                "icon": wp.get("icon", "🚉"), "media": []}
    # 숫자 인덱스는 뒤에서부터(인덱스 안 밀리게), "end"는 나열 순서대로 맨 끝에
    for wp in sorted([w for w in WAYPOINTS if w["after_index"] != "end"],
                     key=lambda w: -w["after_index"]):
        if wp["after_index"] < len(stops):
            stops.insert(wp["after_index"]+1, wp_stop(wp))
    for wp in [w for w in WAYPOINTS if w["after_index"] == "end"]:
        stops.append(wp_stop(wp))

    for i, s in enumerate(stops):
        s["id"] = i + 1

    print("[4/5] 경로 스냅 (Google Directions 우선: 선로/항로/보도)" if GKEY else "[4/5] 경로 스냅 (Valhalla/곡선 — Google 키 없음)")
    stations = _load_stations()
    legs = []
    for i in range(1, len(stops)):
        A, B = stops[i-1], stops[i]
        a, b = [A["lat"], A["lon"]], [B["lat"], B["lon"]]
        mode = MODE_OVERRIDES.get(B["name"], B["mode_in"])
        rail_stations = []
        if mode == "train":
            _, rail_stations = rail_geom(a, b, A["name"], B["name"], stations)  # 역 점(틱)용
        src_label = "google"
        g = google_leg(a, b, mode)
        if not g:                       # Google 실패 → 기존 방식
            src_label = "fallback"
            if mode == "train":
                g, _rs = rail_geom(a, b, A["name"], B["name"], stations)
                if not g: g = leg_geom(a, b, mode)
            else:
                g = leg_geom(a, b, mode)
        leg = {"from": A["id"], "to": B["id"], "mode": mode, "geom": g}
        if rail_stations:
            leg["rail_stations"] = rail_stations
        legs.append(leg)
        extra = f"  via {len(rail_stations)}역" if rail_stations else ""
        print(f"      {A['name']} → {B['name']}  [{mode}/{src_label}]  {len(g)}pts{extra}")
    json.dump(stations, open(_STATION_CACHE, "w"), ensure_ascii=False, indent=1)

    print("[5/5] 영상 클립 변환" + ("  (건너뜀)" if args.no_video else ""))
    transcode_videos(src, media, args.no_video)

    # 실제 경로 길이로 거리 집계 + 이동수단별 분해
    def geom_len(g):
        return sum(hav(g[i-1], g[i]) for i in range(1, len(g)))
    agg = {}
    for lg in legs:
        km = geom_len(lg["geom"]) / 1000
        a = agg.setdefault(lg["mode"], {"km": 0.0, "count": 0})
        a["km"] += km; a["count"] += 1
    LABEL = {"walk": "도보", "ferry": "페리", "train": "기차", "ride": "차", "run": "러닝", "tram": "트램"}
    modes = [{"mode": k, "label": LABEL.get(k, k), "km": round(v["km"], 1), "count": v["count"]}
             for k, v in sorted(agg.items(), key=lambda kv: -kv[1]["km"])]
    total = sum(v["km"] for v in agg.values())
    real_stops = [s for s in stops if not s.get("waypoint")]
    data = {"title": BRIEF.get("title") or "오늘 하루",
            "date": BRIEF.get("date") or media[0]["t"].strftime("%Y.%m.%d"),
            "copy": BRIEF["copy"],
            "theme": BRIEF["theme"], "accent": BRIEF["accent"], "pace": BRIEF["pace"],
            "total_km": round(total, 1),
            "n_photos": sum(1 for m in media if m["type"] == "photo"),
            "n_videos": sum(1 for m in media if m["type"] == "video"),
            "n_stops": len(real_stops),
            "modes": modes,
            "span": [media[0]["t"].strftime("%H:%M"), media[-1]["t"].strftime("%H:%M")],
            "stops": stops, "legs": legs}

    # 오프닝 훅: 히어로 컷 + 플래시 몽타주(대표 사진 몇 장)
    photos_only = [m for m in media if m["type"] == "photo"]
    hero_present = [f for f in HERO_PHOTOS if any(m["file"] == f for m in photos_only)]
    rest = [m for m in photos_only if m["file"] not in HERO_PHOTOS]
    flash = []
    if len(hero_present) > 1:
        flash.append("assets/photos/" + hero_present[1])
    if rest:
        for frac in (0.22, 0.5, 0.78):
            flash.append("assets/photos/" + rest[int(len(rest) * frac)]["file"])
    hero_file = hero_present[0] if hero_present else (photos_only[0]["file"] if photos_only else "")
    hero_rel = ""
    if hero_file:
        orig = os.path.join(src, hero_file)
        hero_rel = (make_hero_sticker(orig) if os.path.exists(orig) else None) or ("assets/photos/" + hero_file)
    data["hook"] = {"hero": hero_rel, "flash": flash}

    with open(os.path.join(OUT, "data.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"\n완료 → {OUT}/data.json  ({data['total_km']}km, {len(real_stops)}곳, "
          f"{data['n_photos']}장, {data['n_videos']}영상)")

if __name__ == "__main__":
    main()
