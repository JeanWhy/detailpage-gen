"""
생성된 페이지를 '단일 HTML 파일'로 번들링합니다.
assets/ 의 이미지를 base64로 HTML 안에 내장 → 파일 하나만 보내면
더블클릭으로 바로 열립니다(인터넷 없어도 폰트만 시스템 폰트로 폴백).

사용법:
    python3 scripts/bundle_single_file.py output/i-beaute
    → output/i-beaute/i-beaute-demo.html  (자기완결 단일 파일)
"""

import sys
import base64
from pathlib import Path

ASSET_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif")


def mime_for(data: bytes, ext: str) -> str:
    """확장자보다 실제 매직바이트를 우선해 정확한 MIME을 고릅니다."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return "image/avif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp", ".avif": "image/avif", ".gif": "image/gif"}.get(ext, "application/octet-stream")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/bundle_single_file.py <output_dir> [out.html]")
        sys.exit(1)

    out_dir = Path(sys.argv[1])
    src_html = out_dir / "index.html"
    if not src_html.exists():
        print(f"Not found: {src_html}")
        sys.exit(1)

    slug = out_dir.name
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else out_dir / f"{slug}-demo.html"

    html = src_html.read_text(encoding="utf-8")

    # assets/<name>.<ext> → data URI 맵
    photos = {}
    assets = out_dir / "assets"
    if assets.is_dir():
        for f in sorted(assets.iterdir()):
            if f.suffix.lower() in ASSET_EXTS:
                data = f.read_bytes()
                uri = f"data:{mime_for(data, f.suffix.lower())};base64,{base64.b64encode(data).decode()}"
                photos[f.stem] = uri

    if not photos:
        print("이미지가 없어 그라데이션 폴백 상태로 번들합니다(파일은 여전히 단독 동작).")

    # 사진을 JS 없이 CSS로 직접 박아넣음 → 모바일 미리보기/Quick Look(JS 제한)에서도
    # 사진까지 렌더됨. data-photo 요소에 data-img 속성 + 인라인 --img 를 주입.
    for name, uri in photos.items():
        needle = f'data-photo="{name}"'
        inject = f"{needle} data-img style=\"--img:url('{uri}')\""
        html = html.replace(needle, inject, 1)

    dest.write_text(html, encoding="utf-8")
    kb = dest.stat().st_size / 1024
    print(f"단일 파일 생성: {dest}  ({kb:,.0f} KB, 이미지 {len(photos)}장 내장)")
    print("→ 이 파일 하나만 보내면 더블클릭으로 열립니다 (JS 없어도 사진·내용 모두 표시).")


if __name__ == "__main__":
    main()
