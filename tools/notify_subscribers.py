#!/usr/bin/env python3
"""Email subscribers when a post goes live.

Buttondown gates its built-in RSS-to-email behind a paid plan, but the API is
available on every plan including free — so this does the same job for nothing.

Runs after a deploy. Finds posts whose publication date is today, checks
Buttondown for an email that already exists for each one, and sends if not.

Safety properties, in order of importance:

  * Duplicate-proof. Before sending it lists existing emails and matches on
    subject. The workflow can be re-run, or fire twice in a day, without a
    subscriber getting the same post twice.
  * Never fails the caller. Any error is reported and the script exits 0. A
    newsletter problem must never break publishing.
  * Sends a teaser, not the post. Body is image + dek + link. A subscriber who
    reads the whole piece in their inbox never reaches the site.

Needs BUTTONDOWN_API_KEY in the environment.

  python tools/notify_subscribers.py            # send for anything due today
  python tools/notify_subscribers.py --dry-run  # show what it would send
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

API = "https://api.buttondown.com/v1/emails"
KEY = os.environ.get("BUTTONDOWN_API_KEY", "").strip()

# How far back to look. One day of slack covers a scheduled run that fires late
# or a deploy that was delayed, without reaching back far enough to resend
# anything already handled (the duplicate check covers that anyway).
LOOKBACK_HOURS = 30


# Bare /v1/emails lists only status=sent,in_flight. An email queued minutes ago
# is still "about_to_send" and would not appear — so a re-run inside that window
# would send it twice. Ask for the in-between states explicitly.
STATUSES = ("about_to_send", "in_flight", "sent", "scheduled")


def existing_subjects(session):
    """Every email subject Buttondown already knows about, across all live states."""
    subjects = set()
    for status in STATUSES:
        url = f"{API}?status={status}"
        for _ in range(10):                   # bounded; we only need recent ones
            r = session.get(url, timeout=30)
            if r.status_code != 200:
                print(f"  could not list existing emails (HTTP {r.status_code}) — "
                      f"not sending, to avoid duplicates")
                return None
            data = r.json()
            for e in data.get("results", []):
                subjects.add((e.get("subject") or "").strip())
            url = data.get("next")
            if not url:
                break
    return subjects


def body_for(p):
    img = p.get("image") or {}
    share = build.SITE["url"] + img["share"] if img.get("share") else ""
    picture = (f'<p><a href="{p["url"]}">'
               f'<img src="{share}" alt="" style="max-width:100%;height:auto;"></a></p>'
               if share else "")
    return (
        f'{picture}'
        f'<p>{p["dek"]}</p>'
        f'<p><a href="{p["url"]}"><strong>Read it on Veiled Antiquity &#8594;</strong></a></p>'
        f'<hr>'
        f'<p style="font-size:13px;color:#777;">You are receiving this because you '
        f'subscribed to Veiled Antiquity. New pieces publish Monday, Wednesday and Friday.</p>'
    )


def main():
    dry = "--dry-run" in sys.argv

    if not KEY and not dry:
        print("  BUTTONDOWN_API_KEY is not set — skipping subscriber notification.")
        print("  Set it as a repository secret to enable this.")
        return

    cutoff = datetime.now() - timedelta(hours=LOOKBACK_HOURS)
    due = [p for p in build.load_posts() if cutoff <= p["dt"] <= datetime.now()]

    if not due:
        print(f"  Nothing published in the last {LOOKBACK_HOURS}h — no email to send.")
        return

    import requests
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Token {KEY}",
        "Content-Type": "application/json",
        # Creating an email with status=about_to_send is refused with a 400
        # (sending_requires_confirmation) unless this header is present. It is
        # only required until the first successful send on a given key, but
        # sending it every time costs nothing and survives a key rotation.
        "X-Buttondown-Live-Dangerously": "true",
    })

    if dry:
        for p in due:
            print(f"  would send: {p['title']}")
            print(f"  body:")
            print("    " + body_for(p).replace("><", ">\n    <"))
        return

    seen = existing_subjects(session)
    if seen is None:
        return                                 # listing failed; do not risk a duplicate

    for p in due:
        subject = p["title"]
        if subject.strip() in seen:
            print(f"  already sent: {subject[:60]}")
            continue

        r = session.post(API, json={
            "subject": subject,
            "body": body_for(p),
            "status": "about_to_send",
        }, timeout=30)

        if r.status_code in (200, 201):
            print(f"  sent: {subject[:60]}")
        else:
            print(f"  FAILED ({r.status_code}) for {subject[:50]}")
            print(f"    {r.text[:300]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                      # never break the deploy
        print(f"  subscriber notification skipped: {e}")
    sys.exit(0)
