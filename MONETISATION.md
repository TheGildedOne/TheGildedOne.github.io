# Monetisation

Everything is built and tested. Nothing is switched on. Each revenue stream turns on by
pasting one ID into the `MONETISATION` block at the top of `build.py`, then rebuilding.

```python
MONETISATION = {
    "amazon_tag": "",          # Amazon Associates tag
    "amazon_domain": "amazon.co.uk",
    "adsense_client": "",      # Google AdSense publisher ID
    "newsletter_action": "",   # email signup form endpoint
    "contact_email": "hello@veiledantiquity.com",
}
```

Leave a field empty and that feature renders **nothing at all** — no empty boxes, no broken
scripts, no placeholder gaps. The site is clean until you're ready.

---

## Already done, no action needed

- **Privacy, Disclosure and Contact pages.** AdSense and Mediavine both check for these
  before approving a site. Written and live at `/privacy/`, `/disclosure/`, `/contact/`.
- **FTC affiliate disclosure**, appearing automatically above any affiliate links, plus a
  full disclosure page. This is a legal requirement, not a courtesy.
- **`rel="sponsored nofollow noopener"`** on every affiliate link — Google requires the
  sponsored attribute, and unmarked affiliate links are a manual-penalty risk.
- **Category pages** at `/category/<name>/` — four extra indexable pages and a proper
  internal-linking hub per topic.
- **Ad slots, styled and reserved.** Space is allocated so ads don't shove the article
  down the page when they load, which is both a ranking factor and the single most
  irritating thing on the ad-supported web.

---

## Turn on in this order

### 1. Affiliate links — do this first

The only stream that earns anything at zero traffic, and this niche suits it: every article
ends with real scholarly books.

Sign up at **Amazon Associates** (`affiliate-program.amazon.co.uk`), get your tag — it looks
like `veiledantiq-21` — and paste it in. Rebuild.

Every modern book in every Sources list becomes a "Find a copy" link automatically. Ancient
texts are skipped deliberately: Livy and Thucydides are public domain, and an affiliate link
on them looks like a shakedown.

> **Timing matters.** Amazon rejects sites with thin content and no traffic, and requires
> qualifying sales within 180 days of approval. Apply once all 13 posts are live and you have
> *some* traffic — realistically month two or three, not now.

**Bookshop.org** is worth considering instead: it pays significantly better on books, and
fits an audience that reads actual scholarship. Tell me and I'll add it alongside Amazon.

### 2. Newsletter — do this early, it compounds

The list is the only asset you own outright. Search rankings and ad rates can be taken away
overnight; an email list can't.

Free tiers worth using: **Buttondown** (cleanest, generous free tier), **Kit** (formerly
ConvertKit), or **MailerLite**. Create a form, copy its POST endpoint into
`newsletter_action`, rebuild. A styled signup block appears at the end of every post.

### 3. Advertising — last, and only at scale

Do **not** apply to AdSense now. A near-empty site gets rejected, and reapplying is harder
than applying.

| Network | Needs | Realistic RPM here |
|---|---|---|
| AdSense | ~nothing, but wants real content | $3–8 |
| Ezoic | ~10k views/mo | $8–15 |
| Journey by Mediavine | ~10k sessions/mo | $12–25 |
| Mediavine | ~50k sessions/mo | $15–30 |
| Raptive | ~100k views/mo | $20–40 |

Thresholds move, so treat these as approximate. Apply to AdSense once you're getting steady
organic traffic — month three or four is realistic. Paste the publisher ID into
`adsense_client` and rebuild; the script and slots wire themselves up.

**One thing I have deliberately not built:** an EEA/UK cookie consent banner. Personalised
advertising to European visitors legally requires one, and Google requires a certified
consent platform rather than a homemade banner. When you're close to running ads, tell me
and I'll wire in a proper CMP. Running ads without it in Europe is a real liability, not a
technicality.

---

## Honest expectations

A new domain sits quiet for 3–6 months regardless of what you do. Nothing is wrong when
that happens.

- **Months 1–3:** effectively zero. Indexing, and the low-competition posts starting to rank.
- **Months 4–6:** the big terms — Library of Alexandria, Eleusinian Mysteries — begin moving.
  Affiliate income might reach pocket money.
- **Months 6–12:** if publishing held steady, ad networks become reachable.

The single biggest factor is whether posts keep appearing after month one. A site that
publishes 13 good posts and stops stays flat forever. `EDITORIAL-CALENDAR.md` has 16 more
scoped and ready.

---

## The thing worth protecting

The reading lists were written before any affiliate programme existed, and no book was added
or promoted because it pays better. Several posts argue against the popular version of their
subject, which is not commercially optimal.

That's the actual asset. In a niche stuffed with confident nonsense, being the site that
says "we don't know" is what earns links from people who know the material — and those links
are what makes the rest of this work.
