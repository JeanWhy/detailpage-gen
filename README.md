# 상세페이지 자동 생성기 (Landing Page Generator)

브리프 JSON 하나로 **13개 섹션의 고전환·고퀄리티 랜딩페이지(상세페이지)**를 생성합니다.
출력은 **반응형 HTML** — 실제 선택 가능한 텍스트 + 사진 슬롯으로, 텍스트가 선명하고 편집·반응형·브라우저 데모가 모두 됩니다.

**▶ 라이브 데모 (i-Beaute · Sofwave):** https://i-beaute-sofwave.pages.dev
&nbsp;·&nbsp; 소스/사진: [`demo/i-beaute/`](demo/i-beaute/)

> **v2 (현재):** HTML 렌더링. 디자인 시스템(CSS)은 고정이고, 브랜드별로 바뀌는 건 `:root` 변수(컬러/폰트)와 13섹션 콘텐츠뿐 → **JSON만 바꾸면 어떤 업종도 같은 품질**로 나옵니다.
> **v1 (레거시):** 13개 섹션을 이미지로 생성해 PNG로 스티칭하던 방식(`scripts/generate_page.py`, `scripts/stitch_images.py`). 텍스트가 흐릿/깨져 고퀄 데모엔 부적합 — 보존만 해둠.

## 빠른 시작

```bash
# 1) 페이지 생성 (브리프 → HTML)
python3 scripts/build_page.py briefs/i-beaute.json

# 2) 브라우저로 보기
node scripts/preview_server.js output/i-beaute 4599
# → http://localhost:4599
```

이미지가 하나도 없어도 **세이지(또는 브랜드 컬러) 그라데이션 폴백**으로 완성된 모습이 나옵니다.

## 새 업종 페이지 만들기 (3단계)

1. `briefs/<이름>.json` 작성 — 형식은 [briefs/SCHEMA.md](briefs/SCHEMA.md), 예시는 [briefs/i-beaute.json](briefs/i-beaute.json)(뷰티)·[briefs/sample-dental.json](briefs/sample-dental.json)(치과).
2. `python3 scripts/build_page.py briefs/<이름>.json` → `output/<slug>/index.html` 생성.
3. (선택) 사진 슬롯 채우기 — `output/<slug>/assets/`에 `01_hero.jpg` / `04_story.jpg` / `08_clinic.jpg` / `13_cta.jpg` 를 넣거나, `.env`에 `OPENAI_API_KEY` 설정 후 이미지 생성 스크립트 실행.

브랜드 팔레트·폰트는 브리프의 `theme` 블록에서 바꿉니다(컬러 10종 + 폰트 + 그라데이션). i-Beaute는 세이지+골드, 치과 샘플은 네이비+코퍼로 **같은 코드에서 전혀 다른 룩**이 나옵니다.

## 13개 섹션 구조 (전환 설계)

| # | 섹션 | 목적 |
|---|------|------|
| 01 | Hero | 첫인상, 헤드라인, CTA, 핵심 스탯 |
| 02 | Pain | 공감 유발 (3 카드) |
| 03 | Problem | 진짜 원인 재정의 (리프레임) |
| 04 | Story | Before→After 타임라인 |
| 05 | Solution | 제품 한 줄 정의 |
| 06 | How It Works | 단계별 + 신뢰 칩 |
| 07 | Social Proof | 후기 (샘플 표기) |
| 08 | Authority | 제작자/클리닉 신뢰 |
| 09 | Benefits | 포함 내역 + 오퍼 카드 |
| 10 | Risk Removal | FAQ |
| 11 | Comparison | 3열 비교표 |
| 12 | Target Filter | 추천/비추천 |
| 13 | Final CTA | 마무리 + 정보 |

## 파일 구조 (v2)

```
detailpage-gen/
├── scripts/
│   ├── build_page.py          # ★ 브리프 JSON → HTML 제너레이터
│   ├── preview_server.js      # 미리보기 정적 서버
│   ├── generate_demo_images.py# i-Beaute 슬롯 이미지 생성(OpenAI)
│   ├── openai_image.py        # 이미지 API 호출 (슬롯 채우기용으로 재사용)
│   └── generate_page.py       # [레거시] PNG 스티칭 파이프라인
├── briefs/
│   ├── SCHEMA.md              # 브리프 JSON 계약(스키마)
│   ├── i-beaute.json          # 데모: 뷰티 클리닉 (세이지+골드)
│   └── sample-dental.json     # 데모: 치과 임플란트 (네이비+코퍼)
├── output/<slug>/index.html   # 생성 결과 (gitignore)
└── references/                # 카피/디자인 가이드
```

## 설치

```bash
pip install -r requirements.txt   # 이미지 생성 시에만 필요 (requests, pillow, dotenv)
cp .env.example .env              # OPENAI_API_KEY 입력 (이미지 채울 때만)
```

> HTML 생성(`build_page.py`)과 미리보기는 **API 키 없이** 동작합니다. 키는 사진 슬롯을 AI로 채울 때만 필요합니다.

## 라이선스

MIT License
