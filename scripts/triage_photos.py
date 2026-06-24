"""
사진 비전 선별(triage) — 하루 여행기 폴라로이드용 자동 큐레이션.

각 사진을 OpenAI 비전 모델로 읽어 분류/품질점수/캡션/안내판여부를 매겨
`<src>/triage.json` (파일명 → 결과)에 저장한다. build_stroll.py가 이걸 읽어
안내판·흐림·중복을 빼고, stop 성격에 따라 베스트 컷만 고르고, 폴라로이드에
캡션을 붙인다.

사용법:
  python3 scripts/triage_photos.py --src "<폴더>"   [--force] [--workers 4]

의존성: requests, Pillow, python-dotenv  (추가 SDK 없음, REST 직접 호출)
캐시: 이미 분석된 파일은 건너뜀(--force 로 재분석). 중간 저장으로 중단돼도 재개 가능.
"""

import os, sys, io, json, base64, argparse, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image, ImageOps
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
URL = "https://api.openai.com/v1/chat/completions"

SYSTEM = (
    "너는 여행 vlog 사진 에디터야. 인스타 릴스에 넣을 '오늘 하루' 폴라로이드로 "
    "쓸 만한 사진을 고른다. 사진 1장을 보고 아래 JSON만 출력해."
)
SCHEMA = (
    "{"
    '"category": "selfie|person|scenery|food|action|object|info|other 중 하나, '
    'info=코스맵·안내판·포스터·스크린샷·표지판처럼 텍스트/도표 위주 정보이미지", '
    '"is_info": true/false (코스맵·안내판·스크린샷 등 \'순간\'이 아니면 true), '
    '"people": 0~9 (대략 인원수), '
    '"quality": 1~5 (폴라로이드로서의 매력. 5=히어로감, 1=흐림·중복·버릴것), '
    '"blurry": true/false, '
    '"caption": "8~16자 한국어 캡션(담백한 메모 톤, 마침표 없이). 인물이면 분위기, 풍경이면 장소느낌", '
    '"highlight": true/false (출발·완주·메달 등 결정적 순간이면 true)'
    "}"
)

_lock = threading.Lock()


def _b64(path, max_dim=512):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode()


def analyze(path, max_dim=512, retries=2):
    b = _b64(path, max_dim)
    payload = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": f"이 사진을 평가해서 이 스키마의 JSON으로만 답해:\n{SCHEMA}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}", "detail": "low"}},
            ]},
        ],
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    for k in range(retries + 1):
        try:
            r = requests.post(URL, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"]
                return json.loads(txt)
            if r.status_code in (429, 500, 502, 503) and k < retries:
                time.sleep(2 * (k + 1)); continue
            return {"error": f"{r.status_code}: {r.text[:160]}"}
        except Exception as e:
            if k < retries:
                time.sleep(1.5 * (k + 1)); continue
            return {"error": str(e)}


def main():
    if not API_KEY:
        sys.exit("OPENAI_API_KEY 없음 (.env 확인)")
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-dim", type=int, default=512)
    args = ap.parse_args()
    src = os.path.expanduser(args.src)
    out = os.path.join(src, "triage.json")

    files = sorted([f for f in os.listdir(src)
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))])
    cache = {}
    if os.path.exists(out) and not args.force:
        cache = json.load(open(out, encoding="utf-8"))
    todo = [f for f in files if f not in cache or "error" in cache.get(f, {})]
    print(f"사진 {len(files)}장, 분석 대상 {len(todo)}장 (캐시 {len(files)-len(todo)}장 재사용) · 모델 {MODEL}")

    done = [0]

    def work(f):
        res = analyze(os.path.join(src, f), args.max_dim)
        with _lock:
            cache[f] = res
            done[0] += 1
            if done[0] % 10 == 0 or done[0] == len(todo):
                json.dump(cache, open(out, "w"), ensure_ascii=False, indent=1)
                print(f"  …{done[0]}/{len(todo)} 저장")
        return f, res

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for fut in as_completed([ex.submit(work, f) for f in todo]):
            f, res = fut.result()
            if "error" in res:
                print(f"  ⚠️ {f}: {res['error']}")

    json.dump(cache, open(out, "w"), ensure_ascii=False, indent=1)

    # 요약
    ok = [v for v in cache.values() if "error" not in v]
    info = sum(1 for v in ok if v.get("is_info"))
    blur = sum(1 for v in ok if v.get("blurry"))
    hi = sum(1 for v in ok if v.get("highlight"))
    from collections import Counter
    cats = Counter(v.get("category", "?") for v in ok)
    q = Counter(v.get("quality", 0) for v in ok)
    print(f"\n완료 → {out}")
    print(f"  분류: {dict(cats)}")
    print(f"  품질분포(1~5): {dict(sorted(q.items()))}")
    print(f"  안내판/정보 {info} · 흐림 {blur} · 하이라이트 {hi}")


if __name__ == "__main__":
    main()
