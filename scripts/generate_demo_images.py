"""
i-Beaute 데모 페이지의 이미지 슬롯을 채웁니다.

output/i-beaute/index.html 은 assets/<slot>.jpg 가 있으면 CSS 그라데이션 폴백
위에 실사 사진을 덮어씁니다. 이 스크립트는 각 슬롯에 맞는 사진을 생성합니다.

사용법:
    1) .env 에 OPENAI_API_KEY 설정 (.env.example 참고)
    2) pip install -r requirements.txt
    3) python3 scripts/generate_demo_images.py

키가 없으면 안내만 출력하고 종료합니다(페이지는 폴백 상태로 이미 데모 가능).
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.openai_image import generate_image, test_api_connection

ASSETS_DIR = PROJECT_ROOT / "output" / "i-beaute" / "assets"

# 슬롯별 장면 프롬프트. openai_image.generate_image 가 photoreal/sage 클리닉
# 스타일 프리앰블을 자동으로 덧붙이므로 여기서는 '무엇을 담을지'만 기술합니다.
SLOTS = {
    "01_hero": {
        "width": 1536, "height": 1024,
        "prompt": (
            "Wide editorial hero shot for a luxury skin clinic. A poised woman in her "
            "early 40s with a clean, lifted jawline and natural, radiant skin, looking "
            "calmly off-camera. Soft sage-green and warm neutral tones, bright airy "
            "studio light, lots of negative space on the LEFT side for a headline. "
            "Aesop / La Mer beauty-editorial mood. No text."
        ),
    },
    "04_story": {
        "width": 1024, "height": 1536,
        "prompt": (
            "Serene portrait of a woman in her late 30s to 40s touching her own "
            "jawline and neck, eyes closed, a subtle confident smile, fresh firm skin. "
            "Soft diffused light, sage and cream palette, spa-luxe atmosphere. "
            "Vertical composition. No text."
        ),
    },
    "08_clinic": {
        "width": 1024, "height": 1536,
        "prompt": (
            "Interior of a calm, premium skin and body clinic treatment room: a "
            "modern non-invasive ultrasound device on a clean trolley, soft folded "
            "towels, a glass dropper bottle, warm timber and sage-green accents, "
            "natural window light. Empty, immaculate, inviting. Vertical composition. No text."
        ),
    },
    "13_cta": {
        "width": 1536, "height": 1024,
        "prompt": (
            "Wide, tranquil close of a woman with luminous, firm, healthy skin in soft "
            "focus, gentle golden-hour light, deep sage and warm neutral tones, "
            "spacious and calm with room for a centered headline overlay. "
            "High-end skincare campaign mood. No text."
        ),
    },
}


def main():
    print("=== i-Beaute 데모 이미지 생성 ===\n")
    if not test_api_connection():
        print(
            "\nAPI 키가 없어 이미지 생성을 건너뜁니다.\n"
            "페이지는 세이지 그라데이션 폴백 상태로 이미 미리보기 가능합니다.\n"
            "키를 넣은 뒤 다시 실행하면 슬롯이 실사 사진으로 채워집니다."
        )
        return

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    slots = list(SLOTS.items())
    ok = 0
    for i, (name, cfg) in enumerate(slots, 1):
        out = ASSETS_DIR / f"{name}.jpg"
        print(f"\n[{i}/{len(slots)}] {name} → {out.name}")
        res = generate_image(cfg["prompt"], str(out), cfg["width"], cfg["height"])
        if res:
            ok += 1
        if i < len(slots):
            time.sleep(2)

    print(f"\n완료: {ok}/{len(slots)} 생성. 브라우저를 새로고침하면 사진이 적용됩니다.")


if __name__ == "__main__":
    main()
