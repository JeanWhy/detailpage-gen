# i-Beaute · Sofwave™ — Demo Landing Page

High-converting, editorial-luxury landing page concept for **i-Beaute Skin + Body** (Chatswood) — Sofwave™ skin-tightening. English. Responsive. Real selectable text + photographic image slots.

## View it

```bash
node scripts/preview_server.js output/i-beaute 4599
# open http://localhost:4599
```

(Or just open `output/i-beaute/index.html` in a browser.)

The page looks finished **without any images** — every photo slot falls back to an elegant sage gradient. Drop in real photos to lift it further.

## Fill the photo slots

The page auto-uses `assets/<slot>.jpg` if present, otherwise keeps the gradient. Slots:

| Slot file            | Where it appears              |
|----------------------|-------------------------------|
| `assets/01_hero.jpg` | Full-bleed hero background     |
| `assets/04_story.jpg`| "Next 12 weeks" split image    |
| `assets/08_clinic.jpg`| Clinic / authority split image |
| `assets/13_cta.jpg`  | Final CTA background           |

Two ways to fill them:

- **Real i-Beaute photos** — drop files with the exact names above into `assets/`.
- **AI-generated** — add `OPENAI_API_KEY` to `.env`, then:
  ```bash
  python3 scripts/generate_demo_images.py
  ```

## Before publishing (honesty checklist)

This is a **concept demo**. Replace these placeholders:

- [ ] **Pricing** — currently "Enquire / see Fresha". Set real figures (`brief.json` → `price`).
- [ ] **Promotion** — "complimentary consultation this month" is a sample offer; confirm.
- [ ] **Testimonials** — the 3 reviews are sample text (marked on-page). Swap for verified client reviews.
- [ ] **Claims** — confirm Sofwave wording (FDA-cleared, no downtime, ~3 months) matches your approved marketing.

## Edit the content

Copy lives directly in `index.html` (one section per `<!-- ## -->` comment, in the 13-section order). Brand colours, fonts and spacing are the CSS variables in `:root` at the top of the file.
