"""
OpenAI Images API로 상세페이지 섹션 이미지를 생성하는 모듈.
gemini_api.py의 드롭인 대체 — 함수 시그니처(generate_image / generate_all_sections /
test_api_connection)가 동일하므로 generate_page.py는 import 한 줄만 바꾸면 됩니다.

기본 모델: gpt-image-1 (필요시 OPENAI_IMAGE_MODEL=dall-e-3 로 폴백)
의존성: requests, Pillow(불필요), python-dotenv  → 추가 SDK 설치 없음(REST 직접 호출)
"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# gpt-image-1 = 텍스트 렌더링/사실성 우수(단, 일부 계정은 org verification 필요).
# 사용 불가 시 .env 에 OPENAI_IMAGE_MODEL=dall-e-3 지정.
MODEL_NAME = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_API_URL = "https://api.openai.com/v1/images/generations"


def _map_size(width: int, height: int, model: str) -> str:
    """
    섹션의 (width,height)를 OpenAI가 허용하는 크기로 매핑.
    OpenAI는 임의 픽셀을 지원하지 않으므로 가장 가까운 종횡비로 보냄.
    이후 stitch_images.py가 전부 1200px 너비로 리사이즈하므로 너비는 자동 정규화됨.
    """
    ratio = width / max(height, 1)
    if model == "dall-e-3":
        if ratio >= 1.4:
            return "1792x1024"   # landscape
        if ratio <= 0.72:
            return "1024x1792"   # portrait
        return "1024x1024"
    # gpt-image-1 (default)
    if ratio >= 1.3:
        return "1536x1024"       # landscape
    if ratio <= 0.77:
        return "1024x1536"       # portrait
    return "1024x1024"


def generate_image(
    prompt: str,
    output_path: str,
    width: int = 1200,
    height: int = 1200,
) -> Optional[str]:
    """
    OpenAI Images API로 이미지 1장 생성 후 저장.
    반환: 저장 경로 또는 None(실패).
    """
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in .env")
        return None

    # 사실적 사진 스타일 + 크기 가이드를 프롬프트에 강제 주입(영문/서구 클리닉 맥락).
    full_prompt = f"""Generate a PHOTOREALISTIC professional image for a luxury skin clinic landing page.

=== LAYOUT ===
- Aspect ratio close to {width}x{height}. Full-bleed composition, content fills the frame.
- Leave clean, uncluttered negative space so headline text can sit over the image comfortably.

=== ULTRA-REALISTIC PHOTOGRAPHY STYLE (MANDATORY) ===
CAMERA: Shot on professional DSLR (Canon 5D Mark IV / Sony A7R IV), sharp detail,
  natural depth of field, professional colour grading.
HUMAN MODELS (when shown):
- Real, diverse models (Caucasian / East-Asian / mixed) with NATURAL skin texture,
  visible pores and fine detail — NOT airbrushed plastic, NOT uncanny-valley AI faces.
- Calm, confident, natural expressions. Individual hair strands visible.
PRODUCT / DEVICE PHOTOGRAPHY:
- Clean clinical-luxury feel: medical-grade device, soft towels, glass dropper bottles.
- Realistic reflections and material textures.
LIGHTING: Soft diffused studio lighting, gentle shadows, subtle rim light for skin glow.
PALETTE: Soft sage-green and warm neutrals (clinic brand), bright and airy.
STYLE REFERENCE: Aesop / Mecca Cosmetica / SkinCeuticals / La Mer editorial;
  modern Australian skin-clinic aesthetic; Vogue beauty editorial quality.
ABSOLUTELY AVOID: cartoon, illustration, vector, flat graphic-design look,
  plastic skin, generic stock-photo feel, visible AI artifacts.

=== TEXT IN IMAGE ===
- Keep any baked-in text MINIMAL and in clean, correctly-spelled ENGLISH only.
- Prefer no text or a single short word; long copy will be added later as real HTML.

=== CONTENT ===
{prompt}
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    size = _map_size(width, height, MODEL_NAME)
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "n": 1,
        "size": size,
    }
    if MODEL_NAME == "gpt-image-1":
        payload["quality"] = "high"          # gpt-image-1 은 항상 b64 반환
    else:
        payload["response_format"] = "b64_json"  # dall-e-3 폴백

    try:
        print(f"Calling OpenAI: {MODEL_NAME} @ {size}")
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

        result = response.json()
        data = result.get("data", [])
        if not data:
            print("Error: No image data in response")
            print(json.dumps(result, indent=2)[:800])
            return None

        b64 = data[0].get("b64_json")
        if not b64:
            print("Error: response had no b64_json")
            return None

        image_bytes = base64.b64decode(b64)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_bytes)

        print(f"Image saved: {output_path}")
        return output_path

    except requests.exceptions.Timeout:
        print("Error: Request timed out (180s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed - {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_all_sections(prompts_file: str, output_dir: str, delay_between: float = 2.0) -> list:
    """모든 섹션 이미지를 순차 생성(레이트리밋 방지 딜레이 포함)."""
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    generated, total = [], len(prompts_data)
    for i, (key, sec) in enumerate(prompts_data.items(), 1):
        print(f"\n[{i}/{total}] Generating {key}...")
        out = os.path.join(output_dir, sec.get("filename", f"{key}.png"))
        res = generate_image(sec["prompt"], out, sec.get("width", 1200), sec.get("height", 600))
        if res:
            generated.append(res)
        else:
            print(f"Warning: Failed to generate {key}")
        if i < total:
            print(f"Waiting {delay_between}s...")
            time.sleep(delay_between)

    print(f"\nGeneration complete: {len(generated)}/{total} images")
    return generated


def test_api_connection() -> bool:
    """OpenAI 키/연결 확인 (모델 목록 조회로 가볍게 테스트)."""
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found")
        return False
    print(f"API Key found: {OPENAI_API_KEY[:8]}...  Model: {MODEL_NAME}")
    try:
        r = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=30,
        )
        if r.status_code == 200:
            print("OpenAI connection successful!")
            return True
        print(f"API test failed: {r.status_code} - {r.text[:300]}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return False


if __name__ == "__main__":
    test_api_connection()
