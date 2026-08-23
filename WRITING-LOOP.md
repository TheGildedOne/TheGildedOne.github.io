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

### 1b. Top up the queue if it is running low

`next_slots.py` prints a **QUEUE LOW** warning when fewer than six topics remain. When you
see it, add new entries to `content/queue.json` until there are at least sixteen — about five
weeks of publishing — *before* you start writing this batch.

This is the one step that keeps the site self-sustaining, and it is also the easiest place to
wreck it. A weak topic is worse than a gap: it publishes, it ranks for nothing, and it dilutes
what the site is about.

**First, ask the data what to write.** Before inventing topics, run:

```bash
python tools/gsc_pull.py       # refresh Search Console data
python tools/gsc_topics.py     # what the archive is already ranking for
```

Both exit cleanly and say so if there are no credentials or no data yet, so this is safe to
run at any point. When there *is* data, an `ORPHAN` result is the best topic signal available:
a query the site already earns impressions for through a page that is not about it. That is
demand you have measured rather than guessed.

Proposals are candidates, not decisions — they still have to clear all five criteria below.
`gsc_topics.py` also refuses queries matching its blocked-terms list regardless of traffic,
because the highest-volume queries in this niche are exactly the ones that would wreck the
site's position.

**Every new topic must clear all five:**

1. **A specific object, site, text, or event** — not a theme. "The Piacenza Liver" works.
   "Etruscan religion" does not.
2. **At least three modern scholarly sources you can actually name**, plus a primary source.
   If you cannot name them before writing, you cannot verify them afterwards — drop it.
3. **It fits one of the four existing categories.** If it needs a fifth, it does not belong.
4. **It cross-links to at least two posts that already exist.** A post nothing links to is a
   post nobody reaches. Name the links in the `angle` field.
5. **There is something genuinely unresolved in it** — a contested reading, a gap in the
   evidence, a popular story the sources do not support. That tension is the article. A topic
   where everything is settled produces an encyclopedia entry, and nobody reads those.

**Hard limits.** No speculative or fringe framing — no lost civilisations, no suppressed
ancient technology, no ancient aliens, however much traffic it would draw. Nothing that
duplicates an existing post's subject. Nothing that requires a language or body of scholarship
you cannot actually check.

Write each entry with `slug`, `title`, `keyword`, `category`, `"status": "pending"` and an
`angle` of one or two sentences saying what the piece argues and which existing posts it links
to. **List every topic you added at the top of your report** — new topics are the highest-risk
thing this loop does unsupervised, and they should be the first thing a human sees.

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

**No em dashes.** Imran asked for this on 2026-08-13, after 461 of them piled up across the
first 29 posts. Enforced by `check.py` for any post dated 2026-10-13 or later; earlier posts
are grandfathered and must not be retro-edited.

This is a rewrite instruction, not a find-and-replace one. Do **not** substitute a hyphen or
an en dash: that looks worse and still fails the check. Recast the sentence instead. The em
dash was doing one of three jobs, and each has a better replacement:

| It was doing this | Use instead |
| --- | --- |
| Dropping in an aside | Commas, or brackets if it is a true parenthesis |
| Pivoting for effect | A full stop. The pause is usually stronger as two sentences |
| Expanding on a noun | A colon |

En dashes stay. They carry number and date ranges (`440&ndash;430 BCE`, `432d&ndash;438d`),
which is correct typography and not what was being complained about.

Watch the parts that are easy to forget: the `dek`, the `description`, the FAQ answers, and
the **image caption in `tools/fetch_images.py`** — `check.py` checks all four.

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

**At least 1200px wide.** The hero renders at 700px CSS, so anything smaller is visibly
soft on a phone. `check.py` enforces this for posts dated 2026-10-20 or later. Commons
usually has a large version; if the only image of an object is small, pick a different
object rather than shipping a blurry one.

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

It now checks **journal articles as well as books**: modern books go to Open Library,
quoted article titles go to Crossref and then OpenAlex. Articles used to be skipped, which
was the larger hole, because a convincing article title, journal and year is trivial to
invent and impossible to catch by reading. A journal named with no quoted article title is
still skipped, since there is nothing falsifiable to look up.

Expect book chapters and pre-1990 European journals to come back NOT FOUND even when they
are perfectly real: Crossref indexes neither well. Confirm those by hand and add them to
`VERIFIED_BY_HAND` in the script with a note on how you checked, rather than deleting a good
citation to make the gate go quiet.

The script reports two kinds of failure and they mean opposite things:

- **NOT FOUND** — Open Library answered and had nothing close. Treat as a possible
  fabrication. Confirm the book independently or cut it. This is the one that matters.
- **UNREACHABLE** — the lookup failed even after three retries. That is a statement about
  the network, not about the citation. Re-run it. Open Library times out often enough that
  a single run's failures are close to random; two consecutive runs will usually disagree
  about which titles failed.

Never resolve an UNREACHABLE by assuming the book is fine because you remember it. Re-run
until you get an answer, or verify it against another catalogue and say in your report that
you did.

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

## If this loop stops running

On 2026-08-22 the task fired and wrote nothing. The cause was not the code: the
working folder configured on the scheduled task, `D:\proof&Rebook`, had been
deleted. The task could not start, but the trigger still recorded a completed run
and the site kept publishing from its backlog, so nothing surfaced for a week.

Two things follow.

**The task's working folder must be `D:\veiled-antiquity`.** It is the repo the
loop actually works in, so it cannot go stale while there is any work to do. If the
task chat shows *"Working folder no longer exists"*, or the run history shows
**Skipped**, that is this failure.

**How to actually fix it (corrected 2026-08-22).** The folder picker did not work:
clicking it opened forked conversations and left the folder unchanged. The fix that
*did* work was to delete the task and recreate it **from a session already running in
`D:\veiled-antiquity`**, because a new task inherits the working folder of whatever
session creates it. That inheritance is the whole mechanism, so it cuts both ways:
recreating from a session in the wrong folder just reproduces the bug while looking
like a repair. Check the session's `pwd` before recreating.

The prompt lives at `~/.claude/scheduled-tasks/veiled-antiquity-writing-loop/SKILL.md`
and is left on disk when a task is deleted, so it can be copied straight back in.
`update_scheduled_task` still has no working-folder parameter; the folder is app
state and cannot be set from a session by any other route.

**`tools/check_runway.py` now guards against the silent version.** It runs as its
own job in the publish workflow, on GitHub's machines rather than Imran's, and fails
the run when fewer than 35 days of scheduled posts remain. A failed run emails him.
It is deliberately independent of the deploy job: a warning about the future must
never stop today's post going out.

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
