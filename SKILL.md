---
name: landing-page-generator
description: |
  고전환 상세페이지(랜딩페이지) 자동 생성 스킬 (v2 · HTML).
  제품/서비스 정보를 인테이크로 수집 → 13섹션 카피·테마 작성 →
  briefs/<slug>.json 으로 조립 → scripts/build_page.py 로 반응형 HTML 생성.
  Use when: 상세페이지/랜딩페이지/제품 소개·판매 페이지 생성 요청 시
model: sonnet
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# 상세페이지 생성기 (Landing Page Generator) · v2

브리프 JSON 하나로 13섹션 고퀄리티 **반응형 HTML** 페이지를 만든다.
디자인 시스템(CSS)은 고정, 브랜드별로 바뀌는 건 `theme`(컬러/폰트)와 13섹션 콘텐츠뿐 →
**브리프만 바꾸면 어떤 업종도 동일 품질.**

## 실행 흐름 (intake부터)

```
[1] 01-intake     질문으로 원자료 수집      → output/<slug>/intake.json
[2] 02-research   타겟분석 → 13섹션 골격     → output/<slug>/research.json
[3] 03-copy       13섹션 카피(SCHEMA 형식)   → output/<slug>/copy.json
[4] 04-design     theme(컬러10+폰트) 결정    → output/<slug>/theme.json
[5] 05-assemble   합쳐서 briefs/<slug>.json  → build_page.py → output/<slug>/index.html
                  (선택) 단일파일 번들 · Cloudflare 배포
```

각 단계 정의: [agents/01-intake.md](agents/01-intake.md) · [02-research](agents/02-research.md) ·
[03-copy](agents/03-copy.md) · [04-design-direction](agents/04-design-direction.md) ·
[05-assemble](agents/05-assemble.md). 최종 입력 형식 계약: **[briefs/SCHEMA.md](briefs/SCHEMA.md)**.

## 오케스트레이션 방법

`agents/*.md`는 자동 등록 서브에이전트가 아니라 **이 스킬이 따르는 단계 정의**다.
오케스트레이터(메인 에이전트)는 각 단계를 순서대로 수행한다 — 단계별로 `Task`로 서브에이전트를
띄우거나, 직접 해당 .md 지침대로 진행한다. 1단계(intake)는 항상 사용자와 대화로 시작.

> **트리거:** 사용자가 "상세페이지 만들자 / intake부터 시작" 하면 [1]부터 진행.
> 이미 `intake.json`/`copy.json` 등이 있으면 해당 단계부터 이어서.

## 핵심 명령 (05에서 실행)
```bash
python3 scripts/build_page.py briefs/<slug>.json output/<slug>   # 렌더
node scripts/preview_server.js output/<slug> 4599               # 미리보기
python3 scripts/bundle_single_file.py output/<slug>             # 단일파일(첨부/오프라인)
```
이미지 슬롯(`01_hero/04_story/08_clinic/13_cta`)은 `output/<slug>/assets/<name>.jpg` 있으면 사용,
없으면 테마 그라데이션으로 폴백 → **사진 없이도 즉시 데모 가능.**

## 정직성 (필수)
가짜 후기·가격·수치·긴급성 금지. 실제 값만 사용하고, 미확정이면 placeholder임을 페이지·
`footer.disclaimer`에 명시. 상세: `briefs/SCHEMA.md`의 체크리스트.

## 참조
- [briefs/SCHEMA.md](briefs/SCHEMA.md) — 브리프 계약(필수)
- [briefs/i-beaute.json](briefs/i-beaute.json) · [briefs/sample-dental.json](briefs/sample-dental.json) — 완성 예시
- [references/](references/) — 카피/디자인 가이드
- 레거시(v1, PNG 스티칭): `scripts/generate_page.py` — 더 이상 기본 흐름 아님
