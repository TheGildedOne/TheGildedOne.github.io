# Editorial Calendar

**The queue lives in `content/queue.json`, not here.** That file is what the writing loop
reads and updates, so it is the only accurate list. This document is the reasoning behind the
schedule — the parts a JSON file can't hold.

To see what's coming up and when:

```bash
cd D:\veiled-antiquity && python tools/next_slots.py 6
```

---

## The shape of month one

Thirteen posts, Monday / Wednesday / Friday, 6 August to 4 September 2026.

The first six are all Mystery Cults, deliberately. A new site does better establishing depth
in one topic before spreading out — it gives Google a clear signal about what the site is
*for*. The pillar went first so everything after it had something to link back to.

The two highest-traffic posts (Library of Alexandria, Eleusinian Mysteries) were placed late
enough to benefit from existing internal links rather than launching cold.

---

## Why these topics

Four categories, chosen so they interlock rather than sprawl:

- **Mystery Cults** — the core. Highest search volume, and the reason the site exists.
- **Magic & Ritual** — the non-elite counterpart. Curse tablets and spellbooks are what
  ordinary people left behind, which is a different and largely untold story.
- **Lost & Suppressed** — the mechanism running underneath everything else. Things vanish
  because nobody kept copying them, not because someone burned them.
- **Oracles & Divination** — institutions built around not knowing. Pairs naturally with
  the mystery cults without repeating them.

Posts in different categories still cross-link heavily. That's intentional: it's what turns
four small clusters into one site with a thesis.

---

## Pacing

3×/week is aggressive for sourced material. **If it slips, drop to 2×/week rather than
dropping quality.** Consistency matters to Google; raw volume much less. A site publishing
two solid posts weekly for a year beats one that publishes thirteen and stops.

The archive is evergreen. None of it dates, none needs updating, and all of it keeps working
while the next batch is written.

---

## Topping up the queue

The queue runs dry around mid-October 2026. Add entries to `content/queue.json` before then —
each needs `slug`, `title`, `keyword`, `category`, `status: "pending"`, and an `angle` giving
the writer something to aim at.

Pick topics that can cross-link into what already exists. A post with no natural link to the
rest of the archive is a post nobody reaches from anywhere.
