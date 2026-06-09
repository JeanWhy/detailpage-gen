# 나만의 상세페이지 생성기 — 셋업 가이드

원본 `uxjoseph/landing-page-generator`를 포크해서 **이미지 백엔드를 Gemini → OpenAI로 교체**하고
**i-Beaute 데모(Sofwave)**로 커스텀한 버전입니다.

## 1. 무엇이 바뀌었나 (Gemini → OpenAI)

| 구분 | 변경 |
|------|------|
| `scripts/openai_image.py` | **신규.** OpenAI Images API 어댑터. `gemini_api.py`와 **함수 시그니처 동일**(드롭인). |
| `scripts/generate_page.py` | import 한 줄만 교체 (`gemini_api` → `openai_image`). 나머지 파이프라인 그대로. |
| `scripts/gemini_api.py.bak` | 기존 Gemini 모듈 (참고용 보관, 미사용). |
| `.env.example` | `OPENAI_API_KEY` + `OPENAI_IMAGE_MODEL` 로 변경. |
| `create_sample_brief()` | 샘플을 **i-Beaute Sofwave**(영문·AUD·세이지그린·Fresha 예약)로 교체. |

**기술 메모**
- 추가 SDK 설치 없음 — `requests`로 REST 직접 호출(기존 의존성 그대로).
- OpenAI는 임의 픽셀(1200×600 등)을 지원하지 않아, 섹션 종횡비를 허용 크기
  (`1536×1024` / `1024×1024` / `1024×1536`)로 매핑 → `stitch_images.py`가 전부 **1200px 너비로 정규화**.
- 모델은 `gpt-image-1` 기본. **gpt-image-1은 일부 계정에서 조직 인증(ID verification)이 필요**할 수 있음.
  막히면 `.env`에 `OPENAI_IMAGE_MODEL=dall-e-3` 로 폴백.

## 2. 실행

```bash
pip install -r requirements.txt
cp .env.example .env          # .env 에 OPENAI_API_KEY 입력

python3 scripts/openai_image.py        # 연결 테스트
python3 scripts/generate_page.py       # i-Beaute Sofwave 데모 13섹션 생성 → 스티칭
```

⚠️ 비용: 이미지 13장 × OpenAI 이미지 단가(고화질 기준 장당 수센트~). 한 페이지에 보통 $1~3 수준.
첫 실행은 섹션 1~2개로 줄여서(`agents`/`generate_page.py`에서) 톤·텍스트 품질부터 확인 권장.

## 3. "내 레포"로 만들기

```bash
cd detailpage-gen
git init && git add -A && git commit -m "Fork: OpenAI backend + i-Beaute demo"
# GitHub에서 빈 레포 생성 후:
git remote add origin https://github.com/JeanWhy/<레포이름>.git
git branch -M main && git push -u origin main
```

- `.gitignore`에 `.env` / `output/` 포함되어 있는지 확인(키·결과물 커밋 방지).
- 컨설팅 자산으로 재사용하려면 브랜드/브리프 부분만 `references/`나 `create_sample_brief()`에서 교체.

## 4. 데모 전에 꼭 (i-Beaute 맥락)

- **가격·프로모는 PLACEHOLDER** (`CONFIRM_ON_FRESHA` / `PLACEHOLDER_PROMO`) — Fresha 실값으로 교체.
  가짜 후기/수치를 넣은 채로 포르티아에게 보이지 말 것. 보여줄 땐 "sample concept"으로 명시.
- 그쪽 예약은 **Fresha**(Square 아님), 브랜드는 **파스텔 그린** — WE SKIN(골드/Oko)과 시각적으로 분리.
- 영문 텍스트가 이미지에 박히면 깨질 수 있음 → 깨진 섹션만 후보정.

## 5. SEO 수주용 데모라는 점 (포지셔닝 1줄)

이 도구의 출력은 **이미지 통짜 페이지**라 검색엔진이 글자를 못 읽음.
→ 이미지 버전은 **"비주얼 컨셉/무드"** 제안으로, 실제 *SEO 증명*은 같은 카피를
**시맨틱 HTML**(WE SKIN 방식: `<h1>`·alt·meta·schema.org)로 옮긴 버전으로.
둘을 같이 들고 가는 게 "예쁘다 + 검색에 강하다"를 동시에 보여주는 가장 센 그림.
