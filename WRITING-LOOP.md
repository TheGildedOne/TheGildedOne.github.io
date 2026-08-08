# The Writing Loop

The procedure for the scheduled writing run. Written to be followed by Claude with no
human in the room, so it is explicit about the things that are easy to get wrong.

**Runs:** weekly, Saturday 10:00 local.
**Writes:** the next three queue entries, dated for the following week.
**Ships:** on the scheduled date, unless Imran says otherwise in the meantime.

---

## Why the timing is safe

Posts are committed with **future dates**. `build.py --live` only publishes what has come
due, so a post written on Saturday for the following Monday sits in the repo, visible to
Imran, for days before any reader sees it.

That buffer is the whole safety model. It means the loop can run unattended without any
single run being able to put something wrong in front of an audience the same day.

**Never write a post dated within 48 hours.** If the queue has slipped and the next slot is
tomorrow, skip that slot and write for the one after.

---

## Procedure

### 1. Check the state

```bash
cd D:\veiled-antiquity && python tools/next_slots.py 3
```

Gives you what to write, the slots to write into, and the exact `date` value for the first.
If the queue is empty, stop and tell Imran — do not invent topics to fill a schedule.

### 2. Research before writing

Search for each topic. **Do not write from memory.** The failure mode here is a confident
paragraph about an excavation that did not happen, and it is not detectable by rereading
your own prose.

For each post, establish before drafting:
- The primary ancient sources, with book and section numbers
- The modern scholarship, with real authors, titles and years
- Where scholars actually disagree — that disagreement is usually the article's spine
- At least one concrete physical object, site or document to anchor the opening

### 3. Write it

Follow the house voice. It is documented in memory as `imran-writing-voice`, and the short
version is:

- **Open with a scene, an object or a person.** Never a thesis statement.
- **No methodology asides.** Do not explain to the reader how carefully you are working.
- **End sections on the concrete detail, not the moral.** Trust the reader to draw it.
- Short paragraphs, contractions, a joke where one genuinely fits.
- **~1,000 words.** 1,300 is too long unless it has earned it.
- Say "we don't know" plainly where that is the answer. It is usually the better story.

**The single-source rule — this is where posts go wrong.** A famous anecdote is famous because
it is a good story, not because it is well attested. Before you narrate one as events, ask: how
many ancient writers report this, how long after the fact, and does anyone who *should* have
mentioned it fail to? If the answer is one source, or one source contradicted by silence
elsewhere, **say so in the body of the post** — not only in the FAQ, and not by quietly
attributing it ("Plutarch says…") and moving on. Attribution is not a caveat; a reader skims
past it.

Two failures caught in review, as the pattern to watch for: Plutarch is the only source for
Philip II meeting Olympias at Samothrace, and the chronology barely allows it. Josephus is the
only source for the Paulina scandal, and Tacitus and Suetonius record the same expulsion
without it. Both were written up as narrative before being corrected.

You may still open with the story — it is a good hook. Follow it immediately with what the
evidence actually supports.

Structural requirements, all enforced by `check.py`:
- JSON metadata header matching the existing posts exactly
- `seo_title` ≤ 62 characters, `description` ≤ 158
- 5 FAQ entries phrased as questions people actually type
- 4–6 sources, real ones
- 2–4 hand-written internal links to existing posts
- `related` listing 2–3 slugs

### 4. Add an image

```bash
# add the slug and search terms to PICKS in tools/fetch_images.py, then:
python tools/fetch_images.py
python tools/optimise_images.py
python tools/modern_images.py         # responsive AVIF — most of the page weight
python tools/make_share_images.py     # social preview cards
```

All four are required. Skipping `modern_images.py` ships a post whose hero image is roughly
eight times heavier than it needs to be on a phone.

Ancient material only — the object, the site, or the manuscript. **No Renaissance paintings,
no modern reconstructions, no artists' impressions.** Public domain or CC only; the credit
lines render automatically and must not be stripped.

### 4b. Consider the Start Here page

Almost everything about a new post wires itself up — nav, sitemap, RSS, related posts,
prev/next, schema, analytics, the signup block. **The one exception is `/start-here/`**,
which is hand-curated in the `START_HERE` list at the top of `build.py`.

If a new post genuinely belongs in one of those sections, add its slug there. If it doesn't
fit any of them, leave it alone — the page is valuable *because* it's a selection rather
than a list of everything. Don't add posts just to keep it current, and don't let any one
section grow past four entries.

### 5. Verify the citations — this gate is not optional

```bash
python tools/verify_sources.py
```

Every modern book is checked against Open Library. **If anything comes back unconfirmed,
resolve it before committing.** Either fix the citation or remove it. Do not commit a post
with an unverified book in it.

A fabricated source is the single failure that would destroy this site's position. It is
also exactly the mistake an LLM makes without noticing.

### 6. Build and validate

```bash
python build.py && python check.py
```

Both must pass clean. `check.py` covers links, images, alt text, SEO tag lengths, JSON-LD
and heading structure.

### 7. Commit, push, and mark the queue

Flip each written entry in `content/queue.json` from `"pending"` to `"written"`.

```bash
git add -A && git commit -m "Add posts for w/c <date>" && git push
```

### 8. Report to Imran

Short. Titles, dates, word counts, anything uncertain, and how many queue entries remain.

**Flag explicitly** if you cut a claim for lack of evidence, if a source was hard to
confirm, or if two sources contradict each other. Those are the things worth a human
glance, and burying them in a tidy summary is how the safety model quietly stops working.

---

## Stop and ask rather than guessing

- Queue empty, or fewer entries than slots
- A citation that cannot be verified and cannot be replaced
- A topic that turns out to rest on one contested paper
- Anything that would require changing the site's structure, design or schedule
- Anything touching money: affiliate tags, ad code, consent banners

---

## What this loop must never do

- Publish same-day. The buffer is the safety model.
- Invent a source, a date, an excavation, or a scholar.
- Quietly drop a topic because it turned out to be hard. Say so instead.
- Lean speculative for traffic. "Lost civilisations" gets clicks and costs the audience
  this site is actually for.
- Strip an image credit. CC BY and CC BY-SA require attribution as a licence condition.
