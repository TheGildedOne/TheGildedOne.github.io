# Monetisation

Everything is built and tested. Nothing is switched on. Each revenue stream turns on by
pasting one ID into the `MONETISATION` block at the top of `build.py`, then rebuilding.

```python
MONETISATION = {
    "amazon_tag": "",          # Amazon Associates tag
    "amazon_domain": "amazon.co.uk",
    "adsense_client": "",      # Google AdSense publisher ID
    "newsletter_action": "",   # email signup form endpoint
    "ga4_id": "",              # Google Analytics 4 measurement ID
    "plausible_domain": "",    # or Plausible, if you prefer cookie-free
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

- **Social share cards.** Every post has a generated 1200×630 preview image with its
  headline set over the artwork. A raw photo crop reads as generic in a feed; a card with
  the headline reads as an article and gets clicked. Regenerate with
  `python tools/make_share_images.py`.
- **Start Here page** at `/start-here/` — six curated routes into the archive. Readers
  arriving from search on a single post have no reason to click a second; this gives them one.
- **Previous / next links** on every post. Ad revenue is priced per 1,000 pageviews, so a
  second post read doubles what a visit earns.
- **IndexNow** — every deploy notifies Bing (and therefore Copilot and a slice of AI
  search) of new URLs instantly instead of waiting to be crawled. Google ignores the
  protocol and uses its own schedule; that's expected.

---

## Turn on in this order

### 0. Analytics — do this before anything else

You cannot tune what you cannot see, and ad networks expect a site to have analytics before
they'll approve it. **Google Analytics 4** is free and the safest default: create a property
at analytics.google.com, copy the measurement ID (`G-XXXXXXXXXX`) into `ga4_id`, rebuild.

If you'd rather not run Google's tracker, **Plausible** is cookie-free and needs no consent
banner — set `plausible_domain` instead. It's about $9/month.

What to watch: which posts pull steady organic clicks, and pages-per-session. The first tells
you what to write more of; the second tells you what a visitor is worth.


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

#### New-post emails, without the $9/month

Buttondown's built-in RSS-to-email is a Basic-plan feature. Its **API is free on every
plan**, so `tools/notify_subscribers.py` does the same job from the publish workflow: after
each deploy it finds anything published in the last 30 hours and sends a teaser — share
image, dek, and a link back to the site.

To turn it on, add a repository secret named `BUTTONDOWN_API_KEY` (Buttondown → Settings →
Programming → API key; GitHub → Settings → Secrets and variables → Actions → New secret).
Until that secret exists the step prints a note and does nothing.

Three things keep it safe:

* It sends a **teaser, not the post**. Someone who reads the whole piece in their inbox
  never visits the site, sees an ad, or clicks an affiliate link.
* It is **duplicate-proof** — before sending it asks Buttondown for every email already in
  `about_to_send`, `in_flight`, `sent` or `scheduled` state and skips matching subjects.
  Re-run the workflow as often as you like.
* It **never fails the deploy**. Any error is printed and the step exits 0.

Preview what would go out, without sending or needing a key:

```
python tools/notify_subscribers.py --dry-run
```

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
