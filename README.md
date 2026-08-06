# Veiled Antiquity

A complete, ready-to-launch blog about the hidden parts of ancient history — mystery
cults, forbidden rites, suppressed knowledge.

**13 posts written. ~16,700 words. Scheduled 3x/week from 7 August to 4 September 2026.**

Everything here is built and tested. You need to do one thing I can't do for you:
create the account. That's it.

---

## What's in this folder

| Thing | What it is |
|---|---|
| `dist/` | The complete website. 17 pages. Open `dist/index.html` to look at it right now. |
| `wordpress-import.xml` | Every post, ready to upload to WordPress. Pre-scheduled. |
| `content/posts/` | The 13 posts as source files. Edit these, then re-run the build. |
| `build.py` | Rebuilds the site and the WordPress file from the posts. |
| `check.py` | Checks for broken links and missing SEO tags. |
| `.github/workflows/` | The daily job that publishes posts on schedule, by itself. |
| `SEO-STRATEGY.md` | The keyword plan, and what to do in the first week after launch. |
| `MONETISATION.md` | How to switch on affiliate links, newsletter and ads — one ID each. |
| `tools/` | Image sourcing from Wikimedia Commons: find, fetch, optimise. |
| `EDITORIAL-CALENDAR.md` | The schedule, plus 16 post ideas for month two. |

---

## Look at it first

Double-click this file:

```
D:\veiled-antiquity\dist\index.html
```

It opens in your browser. Nothing is published yet — this is just on your computer.

---

# Option A — GitHub Pages (recommended)

Free forever, keeps the custom dark theme, and publishes on schedule by itself. Your part
is about 10 minutes, once.

### 1. Make the account

Sign up at **github.com**. Free plan. No payment details needed.

I can't do this step — creating accounts and entering passwords is off-limits for me.

### 2. Create the repository — the name matters

Click **New repository**. Name it **exactly** this, with your own username:

```
yourusername.github.io
```

> **Don't skip this.** If you name it anything else, GitHub serves the site from a
> sub-folder and every link and stylesheet on the site breaks. The `.github.io` name is
> what puts it at the root.

Set it to **Public**. Don't tick "add a README".

### 3. Tell the site its own address

Open `build.py`. Near the top, find the line starting `"url":` and change it to your
address:

```python
"url": "https://yourusername.github.io",
```

### 4. Upload everything

Open a terminal in `D:\veiled-antiquity` and run these, one block at a time:

```bash
git init && git add . && git commit -m "Veiled Antiquity: month one"
```

```bash
git branch -M main && git remote add origin https://github.com/yourusername/yourusername.github.io.git && git push -u origin main
```

GitHub will pop up a login window on the push. That's you signing in — it's the one bit I
can't do for you.

### 5. Switch Pages on

In the repository: **Settings → Pages**. Under "Source", choose **GitHub Actions** (not
"Deploy from a branch" — this one matters).

Done. Within a couple of minutes the site is live, and from then on it publishes itself:
every morning at 09:05 UTC a scheduled job rebuilds the site and any post whose date has
arrived goes live. Nothing for you to do, ever.

### 6. Tell Google it exists

Go to **search.google.com/search-console**, add your site, submit
`https://yourusername.github.io/sitemap.xml`. Then read `SEO-STRATEGY.md` for week one.

---

# Option B — WordPress

Still fully supported if you get the signup working and prefer the dashboard.

1. Sign up at **wordpress.com**, pick a free plan.
2. **Appearance → Themes** — pick any dark theme. (The custom theme in `static/style.css`
   needs the Business plan, ~$25/month, or self-hosted WordPress.)
3. **Tools → Import → WordPress → Run Importer**, and upload
   `D:\veiled-antiquity\wordpress-import.xml`. Assign posts to your account.
4. All 13 land as **Scheduled** and release themselves on the right dates.
5. **Plugins → Add New** → install **Yoast SEO** or **Rank Math**. The SEO titles,
   descriptions and focus keywords for both plugins are already inside the import file.

The WordPress file is regenerated on every build, so you can switch to this later without
losing anything.

---

## Changing things

**To edit a post:** open the matching file in `content/posts/`, edit the text, then run:

```bash
cd D:\veiled-antiquity && python build.py && python check.py
```

That rebuilds both the website and the WordPress file.

**To change the site name, URL or tagline:** they're at the top of `build.py`, in the
block starting `SITE = {`. Change them and rebuild.

**To change a publish date:** each post file starts with a small settings block. Edit the
`"date"` line and rebuild.

**To see what the site will look like partway through the month:**

```bash
cd D:\veiled-antiquity && python build.py --live --now=2026-08-20
```

That builds the site as it will appear on 20 August — only the posts published by then,
with links to future posts automatically turned into plain text so nothing 404s. They turn
back into links on the morning each post goes live.

---

## A note on the writing

Every post names its sources, and says plainly where the evidence runs out. Several
actively argue *against* the popular version of their subject — the Library of Alexandria
was not destroyed by a famous fire, and the celebrated Oracle of the Dead is probably a
farmhouse.

That's deliberate. Google has spent several years demoting confident, thinly-sourced
content in exactly this niche, and the audience for esoteric history contains a lot of
people who read seriously and can tell the difference. Being the site that says "we don't
know" is a durable position. Being the site that makes things up is not.
