# 브리프 JSON 스키마

`scripts/build_page.py`가 읽는 입력 형식입니다. 이 JSON 하나가 13섹션 페이지 전체를 결정합니다.
가장 빠른 길은 [i-beaute.json](i-beaute.json) 또는 [sample-dental.json](sample-dental.json)을 복사해 값만 바꾸는 것입니다.

## 텍스트 규칙
- **`*_html` 로 끝나는 필드**(`headline_html`, `title_html`, `mark_html`, `body`, `body_html`, `logo_text`, 히어로 stat의 `n`)는 **HTML이 그대로 들어갑니다.** `<em>`(이탤릭 강조), `<br>`, `<b>`, `&nbsp;`, `&#8209;`(줄안바뀜 하이픈) 사용 가능.
- 그 외 일반 텍스트 필드는 자동 이스케이프됩니다(`&` `<` `>` 안전). 그냥 평문으로 쓰세요.

## 최상위 구조

```jsonc
{
  "meta":   { "slug", "lang", "title", "description" },   // slug = 출력 폴더명
  "theme":  { "colors", "gradients?", "fonts" },          // 브랜드 룩
  "brand":  { "logo_text", "booking_url" },               // booking_url = 모든 예약 버튼 링크
  "sticky_cta": { "title", "sub", "button" },             // 모바일 하단 고정바
  "nav_cta": "Book a Consultation",                       // 헤더 우상단 버튼

  "hero":       { ... }, "pain":     { ... }, "problem": { ... },
  "story":      { ... }, "solution": { ... }, "how":     { ... },
  "proof":      { ... }, "authority":{ ... }, "benefits":{ ... },
  "comparison": { ... }, "target":   { ... }, "faq":     { ... },
  "final":      { ... }, "footer":   { ... }
}
```

## theme

```jsonc
"theme": {
  "colors": {
    "sage": "#7C9885",       // 주조색 (체크/아이콘/강조)
    "deep_sage": "#5C7567",  // 어두운 섹션 배경 (problem, authority)
    "pale_sage": "#C9D6CC",  // 히어로 이탤릭 강조 / 미디어 폴백 밝은쪽
    "mist": "#EAF0EB",       // 밝은 틴트 배경 (solution, comparison)
    "gold": "#B08D57",       // 골드 액센트 (CTA, eyebrow)
    "gold_soft": "#C7A878",  // 부드러운 골드
    "charcoal": "#2B2B2B",   // 헤드라인/딥 카드/푸터 배경
    "ink": "#3A3A36",        // 본문
    "cream": "#FBFAF7",      // 기본 배경
    "sand": "#F3EEE4"        // 보조 밝은 배경 (pain, proof, faq)
  },
  "gradients": {             // (선택) 히어로/미디어/final 폴백 그라데이션
    "grad1": "#6f8a7c",      // 밝은쪽
    "grad2": "#3f514a",      // 어두운쪽
    "overlay_rgb": "40,46,42"// 사진 위 오버레이 RGB (어두운 톤 권장)
  },
  "fonts": {
    "serif": "'Cormorant Garamond', Georgia, serif",   // 헤드라인
    "sans":  "'Jost', system-ui, sans-serif",          // 본문
    "google":"https://fonts.googleapis.com/css2?family=...&display=swap"
  }
}
```
> 컬러 이름(sage 등)은 역할 슬롯일 뿐입니다 — 치과 샘플은 같은 슬롯에 네이비/틸을 넣어 전혀 다른 룩을 만듭니다.

## 섹션별 필드 (요약)

| 섹션 | 핵심 필드 |
|------|-----------|
| `hero` | `photo?`, `badge`, `headline_html`, `sub`, `cta_primary{label,href}`, `cta_secondary?`, `stats[]{n,l}` |
| `pain` | `eyebrow`, `title_html`, `cards[]{icon,title,body}` (icon: face·bottle·sun·heart·spark·clock·check) |
| `problem` | `eyebrow`, `title_html`, `lede`, `points[]{n,title,body}` |
| `story` | `photo?`, `reverse?`, `eyebrow`, `title_html`, `timeline[]{when,title,body}` |
| `solution` | `eyebrow`, `mark_html` (`<b>`로 핵심어 강조), `tag` |
| `how` | `eyebrow`, `title_html`, `lede?`, `steps[]{title,body}` (번호 자동), `chips[]` |
| `proof` | `eyebrow`, `title_html`, `quotes[]{quote,name,meta}`, `sample_note?` |
| `authority` | `photo?`, `reverse?`, `eyebrow`, `title_html`, `body`(html), `creds[]` |
| `benefits` | `eyebrow`, `title`, `items[]{title,body}`, `offer{eyebrow,title,was,price,price_small,bullets[],button_label,fine}` |
| `comparison` | `eyebrow`, `title_html`, `columns[3]`, `own_index`(강조열), `rows[]{feat,cells[]{t,k}}` (k: `yes`/`no`) |
| `target` | `eyebrow`, `title`, `yes{title,items[]}`, `no{title,items[]}` |
| `faq` | `eyebrow`, `title`, `items[]{q,a}` |
| `final` | `photo?`, `eyebrow`, `title_html`, `body`, `button_label`, `info[]{t,body_html}` |
| `footer` | `line`, `link_label`, `disclaimer` |

## 이미지 슬롯
`photo` 값(`01_hero`, `04_story`, `08_clinic`, `13_cta`)은 `output/<slug>/assets/<photo>.jpg`를 찾습니다.
- 파일이 있으면 사진을 덮고, 없으면 테마 그라데이션으로 폴백.
- 가로형 권장: hero, final / 세로형 권장: story, clinic.

## 정직성 체크리스트 (데모 → 실배포 전)
- [ ] `proof.quotes` — 검증된 실제 후기로 교체 (샘플은 `sample_note`로 페이지에 표기됨)
- [ ] `benefits.offer.price` / `was` / `fine` — 실제 가격·조건 확인
- [ ] `hero.stats`, `comparison` 등 수치/주장 — 출처·규정 확인
- [ ] `footer.disclaimer` — 업종 규정(의료광고 등) 반영
