# Veiled Antiquity

A blog about the deliberately hidden parts of ancient history — mystery cults, forbidden
rites, suppressed knowledge.

**Live at [veiledantiquity.com](https://veiledantiquity.com).** It writes and publishes
itself; the sections below are for when you want to change something.

---

## How it runs

| What | When | Where |
|---|---|---|
| **Publishing** | Mon / Wed / Fri, 09:05 UTC | GitHub Actions — rebuilds and deploys; posts appear on their own date |
| **Writing** | Saturdays, 10:00 local | A scheduled Claude task following `WRITING-LOOP.md` |
| **Indexing** | every deploy | Sitemap + IndexNow ping to Bing |

Nothing here needs a person. Posts are committed with **future dates** and `build.py --live`
holds them back until due, so there are always several days between a post being written and
anyone reading it.

---

## Layout

| Path | What it is |
|---|---|
| `content/posts/` | The posts. A JSON metadata header, then HTML. This is the source of truth. |
| `content/queue.json` | What gets written next, in order. The writing loop reads this. |
| `content/images.json` | Generated image manifest — credits, dimensions, formats. |
| `build.py` | Builds the site. All configuration lives at the top. |
| `check.py` | Validates links, images, alt text, SEO tags, structured data. |
| `tools/` | Image sourcing and encoding, citation verification, slot allocation. |
| `templates/`, `static/` | Page shells and the stylesheet, fonts, images. |
| `public/` | Files copied to the site root verbatim (CNAME, verification files). |
| `docs/` | Strategy notes: SEO, monetisation, editorial calendar. |
| `WRITING-LOOP.md` | The procedure the Saturday writer follows. Kept at root — the scheduled task points at this path. |

`dist/` and `wordpress-import.xml` are build output and aren't committed. Both regenerate
with `python build.py`.

---

## Changing things

**Edit a post** — open its file in `content/posts/`, edit, then:

```bash
cd D:\veiled-antiquity && python build.py && python check.py && git add -A && git commit -m "..." && git push
```

The push deploys it. `check.py` must pass — it catches dead links, missing alt text and
over-long meta descriptions before they ship.

**Preview a future date** — see the site as it will look partway through the schedule:

```bash
cd D:\veiled-antiquity && python build.py --live --now=2026-09-20
```

Links to not-yet-published posts flatten to plain text automatically, so nothing 404s.

**Change the site name, URL, or a publish date** — the `SITE` block at the top of `build.py`,
or the `"date"` line in a post's metadata header.

**Switch on money** — `MONETISATION` block at the top of `build.py`. Every field is inert
until filled in. See `docs/MONETISATION.md` for what to enable and when.

---

## Adding a post by hand

The Saturday loop does this automatically, but if you're writing one yourself:

1. Copy an existing file in `content/posts/` and rewrite it. Keep the metadata header shape.
2. Add the slug and Wikimedia search terms to `PICKS` in `tools/fetch_images.py`, then:
   ```bash
   python tools/fetch_images.py && python tools/optimise_images.py
   python tools/modern_images.py && python tools/make_share_images.py
   ```
3. `python tools/verify_sources.py` — every modern book is checked against Open Library.
   **This must pass.** A fabricated citation is the one failure that would sink the site.
4. `python build.py && python check.py`, then commit and push.

---

## On the writing

Every post names its sources and says plainly where the evidence runs out. Several argue
against the popular version of their subject — the Library of Alexandria was not destroyed by
a famous fire, and the celebrated Oracle of the Dead is probably a farmhouse.

That is the point, not a stylistic quirk. Google has spent years demoting confident,
thinly-sourced content in exactly this niche, and the audience for esoteric history contains a
lot of people who read seriously and can tell the difference. Being the site that says
"we don't know" is a durable position.
