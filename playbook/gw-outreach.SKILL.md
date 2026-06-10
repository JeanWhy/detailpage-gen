---
name: gw-outreach
description: Run the Grace & Why prospect→pitch pipeline for a Sydney clinic. Given a clinic name, Instagram handle, or a suburb to scan, it does recon, fit-scores, builds & deploys a sample demo landing page + a proposal, drafts personalized outreach (KR+EN DM + email), and outputs a human action checklist. Use whenever the user wants to pitch a new clinic / says "new target", "new prospect", "pitch <clinic>", or wants to scan a suburb for prospects. Instagram following & DM sending stay manual (account safety).
---

# Grace & Why — Clinic Outreach Pipeline

Turns one input (a clinic, an IG handle, or a suburb) into a **ready-to-send pitch package**. This codifies the manual playbook used to land the first prospect (Miso Beauty Lab). See memory: `business-direction`, `miso-beauty-lab-prospect`, `swipe-file`.

## Golden rules (never break)
1. **Verified data only.** Never fabricate reviews, ratings, names, addresses, prices. Mark anything unconfirmed as a `⟨placeholder⟩`. A prospect with **no verifiable reputation anywhere = do NOT pitch** (lesson: The Skin Beauty had 520 IG followers, owner-only comments, zero community reviews → dropped).
2. **AHPRA / TGA compliance is the moat.** Australian rules ban testimonials for *regulated* procedures. Use real review quotes ONLY for general experience / facials / spa / non-regulated services. **Never pair review quotes or "best/guaranteed" claims with HIFU, laser, injectables, or other cosmetic-medical treatments.**
3. **Account safety > speed.** The agent only *prepares* the IG target list and DM drafts. The human follows accounts and sends DMs manually (slowly). Mass follow/DM = shadowban/ban = dead channel.
4. **Sample-placeholder discipline.** Demos carry a clear "sample concept" ribbon + disclaimer. Real photos, exact hours, pricing, founder credentials = `⟨placeholders⟩` until the clinic confirms.
5. **Pretty ≠ booked.** Every section must earn the booking. Lead with the clinic's single biggest, most concrete gap (e.g. "Google says you're permanently closed").

## Inputs
- A specific clinic name (e.g. "L'Amour Skin Clinic, Strathfield"), OR
- An Instagram handle (e.g. `@lamour.skin.clinic`), OR
- A suburb to scan ("find a prospect in Strathfield") → run Step 1 in discovery mode and pick the best-fit before continuing.

---

## Pipeline

### Step 1 — Recon (research subagent)
Spawn a research agent (general-purpose) to gather, with **confidence levels + sources**:
- **Google**: star rating + review count, AND Google Maps listing status (active / "permanently closed" / no listing). The status is often the strongest hook.
- **Reputation evidence** (gating): real review quotes (Google/Fresha/Naver/호주 카페) with name + date. Fresha pages are publicly readable — prioritize.
- **Web presence**: real website? Instagram-only? broken/dated/locked "Opening Soon"? URL + assessment.
- **Services** (flag which are regulated: HIFU/laser/injectables), signature treatment, **founder/owner name**, years, Korean-trained?
- **Contact**: phone, email, address, hours, booking method, IG handle, follower count.
- **Brand tone & language** (Korean/English mix).

### Step 2 — Fit score (GO / NO-GO)
Score on: **verified good reviews** (gating) × **weak/broken web** × **high-ticket services** × **warm/local (Korean Sydney)**.
- **GO** = verifiable reputation + a concrete web/Google gap. Pick the strongest single hook.
- **NO-GO** = no verifiable reputation anywhere → stop, report why, suggest a different target. Don't build a demo on a guess.

### Step 3 — Build the demo
1. Copy the template: `cp -R demo/miso-beauty-lab/index.html output/<slug>/index.html` (slug = clinic-suburb, lowercase-hyphen).
2. Re-skin — **replace ALL Miso-specific data**: clinic name/logo, hero hook, services, real review quotes (AHPRA-safe only), founder (Authority section), contact (phone/IG/address), final CTA. Pick a **distinct warm/cool palette** so it doesn't look templated (Miso=honey, Skin Beauty=rose, i-Beaute=sage — choose a new one; vars `--rose/--deep/--blush/--mist/--gold/--grad1/--grad2`).
3. Mark unknowns as `⟨placeholder⟩`. Keep the demo ribbon + disclaimer.
4. **Verify render**: serve locally (`scripts/preview_server.js` / Claude_Preview), screenshot hero + reviews + final CTA, and check **no horizontal overflow on desktop (1280) AND mobile (375)**.
5. Optional upgrades from `swipe-file`: mesh-gradient hero (no-photo clinics), first-person founder story, tasteful "booked out this month" scarcity element.

### Step 4 — Deploy the demo (Cloudflare Pages)
```bash
npx wrangler pages project create <slug> --production-branch main
npx wrangler pages deploy output/<slug> --project-name <slug> --branch main
```
Live URL = `https://<slug>.pages.dev`. Verify with `curl -sIL` (200, image/png for assets; note `.html` 308-redirects to clean URL).

### Step 5 — Build & deploy the proposal
1. Copy `demo/grace-and-why-miso/miso-proposal.html` → `output/grace-and-why-<slug>/miso-proposal.html` (or `<slug>-proposal.html`).
2. Re-skin: lead with **this clinic's** specific gap, set the demo link to `https://<slug>.pages.dev/`, keep pricing (Essentials A$900 / **Grace Care A$1,200+A$390/mo** / Growth A$1,200+A$690/mo — adjust if told), contact already = `hello.gracewhy@gmail.com` + `@grace.and.why` + `grace-and-why.pages.dev`.
3. Deploy as project `grace-and-why-<slug>`. Share URL = clean `/<file>` (no `.html`).

### Step 6 — Drafts + human checklist
Produce, tailored to the clinic's hook:
- **Instagram DM, 2-step (KR + EN):** (1) opener, no link, helpful tone, names the specific gap, offers a free sample → invites reply. (2) after reply: demo link + proposal link + offer a 10-min call. Templates below.
- **Email** (subject + body, KR/EN) with both links.
- **Human action checklist:**
  1. Verify the clinic is **operating** (2-min): IG booking shows future slots? recent post within 2–3 weeks? phone answers?
  2. **Follow** the clinic 1–2 days before DMing; like 1–2 recent posts (so they recognize @grace.and.why).
  3. Send DM step 1 → on reply, send links → offer call.

**Output:** a "Send Package for ⟨Clinic⟩" summary — fit verdict, the hook, live demo + proposal links, DM/email drafts, and the checklist.

---

## Reusable assets

**Contact (already live):** email `hello.gracewhy@gmail.com` · IG `@grace.and.why` · site `grace-and-why.pages.dev`
**Brand:** ink `#1C1A17` / paper `#FBF9F5` / gold `#A8803C`; Cormorant Garamond + Jost.
**Templates:** demo `demo/miso-beauty-lab/index.html` · proposal `demo/grace-and-why-miso/miso-proposal.html`. Save outputs under `output/<slug>/`; sync committed copies to `demo/<slug>/`.
**Pricing (AUD):** Essentials A$900 once · Grace Care A$1,200 + A$390/mo (recommended) · Growth Partner A$1,200 + A$690/mo.
**Prospect pipeline (warm-up + future targets):** see `business-direction` memory follow-list (Eastwood/Chatswood/Strathfield/Epping/Lidcombe/CBD/Rhodes Korean clinics).

### DM template — step 1 (Korean)
```
안녕하세요 ⟨원장님 이름⟩님! 저는 Jean이라고 해요 —
시드니에서 한인 클리닉 웹사이트를 만들고 있어요. ⟨클리닉⟩ ⟨칭찬 한 줄⟩ 😍

근데 한 가지 알려드리고 싶어서요. ⟨구체적 갭 — 예: 구글에 검색하니 "영구 폐업"으로 떠요 / 웹사이트가 없어서 검색하는 새 손님이 못 찾아요⟩.
이렇게 잘하시는데 너무 아깝더라고요.

제가 ⟨클리닉⟩용으로 샘플 페이지를 하나 만들어봤는데, 보여드려도 될까요?
무료예요 — 그냥 꼭 아셨으면 해서요 🙏
```
### DM template — step 1 (English)
```
Hi ⟨Owner⟩! I'm Jean — I build websites for Korean clinics in Sydney,
and I'm a fan of ⟨Clinic⟩ ⟨one specific compliment⟩ 😍

Quick heads-up though: ⟨specific gap — e.g. when I Googled you, your
listing shows as "permanently closed," so new customers can't find you⟩.
You're clearly thriving, so it seemed a shame.

I actually put together a little sample page for ⟨Clinic⟩ to show what I mean.
Want me to send it over? No charge — just thought you'd want to know 🙏
```
### DM step 2 (on reply)
`여기요 🙂 → ⟨demo⟩ (실제 후기로 만들었어요). 구글 복구 + 오픈 방법/가격 → ⟨proposal⟩. 편하시면 10분 통화도 좋아요!`

---

## Notes
- This skill lives at `.claude/skills/gw-outreach/SKILL.md` (gitignored). The version-controlled master is `playbook/gw-outreach.SKILL.md` — edit there and re-copy if lost.
- Future improvement: a fully generic demo template (placeholders only) to avoid re-stripping Miso data each run. For now, re-skin carefully and grep the output for leftover "Miso"/"Eastwood"/"0414" before deploying.
- Keep adding good references to `swipe-file` memory as you find them.
