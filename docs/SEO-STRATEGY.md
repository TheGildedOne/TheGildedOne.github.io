# SEO & Marketing Plan — Veiled Antiquity

Everything technical is already done and built into the site. This document covers the
part that needs a human: the first week after launch, and where the traffic actually
comes from in this niche.

---

## What's already built in

You don't need to do any of this — it's in the pages.

- **Unique title tag + meta description on every page**, all inside Google's length limits
- **Canonical URLs** so nothing competes with itself
- **JSON-LD structured data** — `BlogPosting`, `Organization`, `WebSite`, `BreadcrumbList`,
  and `FAQPage` on every post, and `WebSite` + `Organization` on the home page (which is where
  Google reads the site's name from)
- **FAQ blocks** on every post — 5 real questions each, formatted to be eligible for
  Google's expandable answer boxes
- **Open Graph + Twitter cards** so links look right when shared
- **Internal linking** — every post links to 2–4 others by hand, plus an automatic
  "Continue the descent" block
- **A pillar-and-cluster structure** (explained below)
- `sitemap.xml` with a true last-changed date per page, `robots.txt`, RSS feed
- **Fast, accessible, mobile-first**: one small script (the analytics consent check), one
  stylesheet, AVIF images, semantic headings, skip links, visible focus states,
  `prefers-reduced-motion` respected

---

## Where it stands: 1 October 2026, eight weeks in

**10 clicks and 551 impressions from Google in 90 days.** Average position 23.9. The last 28
days against the 28 before: impressions 279 vs 272 (flat), clicks 4 vs 6, average position
17.6 vs 30.3 (much better). So Google is ranking the pages higher and showing them no more
often. That is what a new site with no links from other sites looks like: it gets tried near
the top for narrow searches and stays far down for the big ones ("curse tablets" at 85,
"sibylline books" at 61, "library of alexandria" past 50).

Three things were found that day, none of which any existing check could see.

**1. Google had ten of twenty-four posts at the wrong address, or not at all.** Buttondown
adds tracking tags to every link in the newsletter (`?utm_source=veiled&utm_medium=email...`),
and its public archive at buttondown.com/veiled carries the same tagged links. Google found
seven posts through that archive first, indexed the tagged address, and never fetched the
real one, despite the canonical tag, the sitemap and every internal link pointing at it. The
posts still earned impressions, under the tagged address, which is why the totals looked
normal. `tools/check_indexing.py` now asks Google about every page and reports this; the
Saturday loop ends its report with that line. The cure has two halves, both Imran's:
switch off UTM tracking at buttondown.com/settings/tracking, and request indexing of each
clean address in Search Console.

**2. The sitemap claimed every page changed three times a week.** One shared `<lastmod>`,
the date of the newest post. Google only uses that field while it finds it accurate. Each
page now carries the date of the last commit that touched it.

**3. The target keywords had stopped being things people search for.** The first 24 posts
aimed at real phrases. Of the next 29, 23 aimed at several topics glued together
("cumaean sibyl cave cumae"), and their search titles followed. The subjects were fine and
mostly have searchers; the titles just did not use their words. All 29 were retitled before
publishing, `check.py` now requires the keyword's words in the title or description, and
`tools/keyword_demand.py` tests a phrase against Google's autocomplete before a topic goes in
the queue.

Also fixed the same day: the home page's main image loaded as a 596 KB JPEG instead of the
75 KB AVIF that already existed; breadcrumbs pointed at an anchor instead of the category
page; IndexNow resubmitted all 35 URLs on every deploy instead of only the changed ones.

**What on-site work cannot fix** is the thing holding the big terms down: almost nobody links
here. Almost, because one site does, and it found us on its own. Rogue Classicism's daily RC
Bulletin has listed 17 posts under "From the Blogosphere" since 20 August 2026, nearly every
one published, with clean links. (This section first said "nobody links here yet". That was
an assumption nobody had checked; it was found by reading their bulletins on 2026-10-01.)
One site linking often is still one site, and what moves the big terms is more of them.
The list under "Where the audience actually is" below is still the plan, and it is still
work only a person can do.

---

## The keyword map

The strategy is **pillar and cluster**. One big authoritative guide, twelve supporting
posts that all link back to it. Google reads that pattern as topical authority, and it
works especially well for a new site with no backlinks.

**Pillar:** *Mystery Cults of the Ancient World* → targets `ancient mystery cults`

| # | Post | Target keyword | Why this one |
|---|---|---|---|
| 1 | Mystery Cults Guide | ancient mystery cults | Pillar. Broad, evergreen, high intent |
| 2 | Eleusinian Mysteries | eleusinian mysteries | **Highest volume term in the whole niche** |
| 3 | The Kykeon Question | kykeon eleusis | Long-tail, very low competition, high engagement |
| 4 | Orphic Gold Tablets | orphic gold tablets | Low competition, strong link-attraction |
| 5 | Mithras & the Tauroctony | mithras tauroctony | Steady search demand, visually shareable |
| 6 | Villa of the Mysteries | villa of the mysteries | High volume — big tourism search overlap |
| 7 | Greek Magical Papyri | greek magical papyri | Cult favourite; the occult audience's gateway |
| 8 | Curse Tablets | ancient curse tablets | Rising interest; Bath angle pulls UK traffic |
| 9 | Sibylline Books | sibylline books | Underserved. Genuinely little good writing exists |
| 10 | Damnatio Memoriae | damnatio memoriae | Steady evergreen; gets cited in discussions |
| 11 | Library of Alexandria | library of alexandria | **Biggest volume of all — the traffic magnet** |
| 12 | Oracle of the Dead | necromanteion ephyra | Niche, but you'd rank #1 fast |
| 13 | Piacenza Liver | piacenza liver | Almost no competition. Easy first win |

**How to read this:** posts 11 and 2 are the traffic. Posts 12, 13 and 3 are the *fast*
wins — so little competition that you can rank within weeks, which builds the site's
credibility with Google while the big ones mature.

Both big posts are contrarian on purpose. "Nobody burned the Library of Alexandria" is a
correction of something most people believe, and corrections earn links and shares far
better than agreement does.

---

## Week one — do these, in order

**1. Google Search Console.** search.google.com/search-console → add the site → verify →
submit the sitemap. Nothing happens in search until you do this.

**2. Bing Webmaster Tools.** Same thing at bing.com/webmasters. Takes 3 minutes and also
feeds ChatGPT's web results, which increasingly matters.

**3. Request indexing on the pillar post.** In Search Console, paste the pillar post's URL
into the top search bar, then click "Request Indexing". Do the same for the Alexandria
post.

**4. Set up one social account.** Not four. Pick one and post consistently:
   - **Reddit** is where this audience actually lives — but read the rules first, most
     history subs ban self-promotion. Participate genuinely for a few weeks before ever
     linking. This is the single highest-value channel and the easiest to get banned from.
   - **Bluesky / X** — decent for classicists and archaeologists, who are active and share
     each other's work.
   - **Pinterest** — surprisingly strong for this niche. The Villa of the Mysteries and
     Mithras posts are visual.

**5. Add images.** This is the one real gap. Every post would benefit from 1–2 pictures,
and the Villa of the Mysteries post genuinely needs them. Use **Wikimedia Commons** and
filter for public domain — most ancient artefacts are freely usable. Write real alt text
describing the object; it's both an accessibility requirement and an SEO signal.

---

## Where the audience actually is

Ranked by realistic value for a new site:

1. **Reddit** — r/AskHistorians (extremely strict, but a cited answer is gold),
   r/ancientrome, r/ancientgreece, r/occult, r/AlternativeHistory. Contribute first.
2. **Wikipedia citations** — a genuinely underrated move. If a post covers something
   Wikipedia handles thinly and your sources are solid, a citation drives steady traffic
   for years. Only do this where the post genuinely adds something.
3. **Academic and classics blogs** — this niche's writers link generously to careful work.
   The rigour of these posts is the thing that earns those links.
4. **YouTube essayists** — channels covering ancient history need sourced research.
   Well-cited articles get used and credited.
5. **Newsletter** — start collecting emails early. In a niche this specific, a small
   engaged list beats a big indifferent one.

---

## Honest expectations

New domains sit in a slow patch for roughly 3–6 months. Nothing is wrong when that
happens; it's the normal pattern.

- **Month 1:** near zero. Indexing, nothing more.
- **Month 2–3:** first rankings on the low-competition posts — Piacenza, Ephyra, kykeon.
- **Month 4–6:** the big terms start moving. Alexandria and Eleusis begin climbing.
- **Month 6–12:** if publishing held steady, the pillar starts ranking and the cluster
  lifts with it.

The single biggest factor is **whether you keep publishing after this month runs out.**
Sites that stop at 13 posts stay flat. `EDITORIAL-CALENDAR.md` has 16 more ideas ready to
go, with keywords already chosen.

---

## Search Console emails you can ignore

Google mails you whenever a *new* reason appears in the Page Indexing report. Most of these
are informational, not faults, and two in particular will recur on this site forever because
of how it is hosted. Checked against the live site on 2026-08-15 and confirmed benign.

**"Page with redirect"** is the two alternate domains doing their job:

```
https://www.veiledantiquity.com/   301   https://veiledantiquity.com/
https://thegildedone.github.io/    301   veiledantiquity.com
```

One canonical domain with everything else pointing at it is the correct setup. If these ever
stopped redirecting, *that* would be the problem.

**"Alternate page with proper canonical tag"** is GitHub Pages serving every page at two
addresses, `/posts/foo/` and `/posts/foo/index.html`. Google occasionally finds the `.html`
form, reads the canonical, and indexes the clean URL instead. The phrase "proper canonical
tag" is Google confirming the markup is right. Verified that we do not cause it: no internal
link anywhere in `dist/` points at an `index.html`, the sitemap contains none, and every page
self-canonicalises.

**"Discovered / Crawled, currently not indexed"** is ordinary for a young site with little
authority. Google queues the page and returns. It resolves as the archive grows.

The figure worth watching instead is **how many sitemap pages Google has indexed at their
real address**. Do not count by hand, and do not trust the Sitemaps report: on 2026-08-15 this
section said "11 of 11", and by 1 October ten posts were indexed at the wrong address or not
at all while every report still looked healthy. Ask Google page by page:

```bash
python tools/check_indexing.py
```

Reasons that *are* worth opening the report for, because each means something is actually
wrong: **Duplicate without user-selected canonical**, **Soft 404**, **Blocked by robots.txt**,
**Excluded by noindex**, **Server error (5xx)**, **Redirect error**.

## Things that would actively hurt

- **AI-generated filler to hit a quota.** This niche's readers notice, and Google's
  helpful-content system targets exactly this pattern.
- **Drifting speculative.** "Lost civilisations" and "suppressed ancient technology" get
  more clicks in the short term and permanently change which audience you have. It also
  makes the citations and links from serious readers impossible.
- **Buying links.** Fastest route to a manual penalty.
- **Thin posts.** Better one 1,500-word piece a week than three 400-word ones.
