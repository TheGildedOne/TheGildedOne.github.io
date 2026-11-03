#!/usr/bin/env python3
"""One-off: remove utm_ tracking tags from site links in the Buttondown archive.

Temporary. Added and removed on 2026-11-02; it lives in git history if needed.

Old newsletter emails in Buttondown's public archive link to the site with utm_
tags, so Google keeps indexing the tagged copies of seven posts instead of the
real addresses. This rewrites only those links, only in emails already sent,
and checks after each change that nothing but the tags moved.

  python tools/strip_archive_utm.py           # read-only: report what it finds
  python tools/strip_archive_utm.py --apply   # change the emails

Needs BUTTONDOWN_API_KEY. Runs on GitHub, where that key lives.
"""

import os
import re
import sys
import time
import urllib.parse

import requests

API = "https://api.buttondown.com/v1/emails"
SITE_LINK = re.compile(r"https?://(?:www\.)?veiledantiquity\.com[^\s\"'<>)\]]*")


def strip(url):
    """The same address with every utm_ parameter removed, other parameters kept."""
    parts = urllib.parse.urlsplit(url.replace("&amp;", "&"))
    kept = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(kept)))


def clean(body):
    return SITE_LINK.sub(lambda m: strip(m.group(0)) if "utm_" in m.group(0) else m.group(0), body)


def sent_emails(session):
    url, out = f"{API}?status=sent", []
    while url:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        out += data.get("results", [])
        url = data.get("next")
    return out


def main():
    key = os.environ.get("BUTTONDOWN_API_KEY", "").strip()
    if not key:
        sys.exit("  BUTTONDOWN_API_KEY is not set")
    apply = "--apply" in sys.argv
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {key}", "Content-Type": "application/json"})

    emails = sent_emails(session)
    print(f"  {len(emails)} sent emails")
    if emails:
        sample = emails[0]
        print(f"  fields on an email: {sorted(sample)}")
        for k, v in sorted(sample.items()):
            if any(w in k.lower() for w in ("utm", "track", "analytic", "link")):
                print(f"    {k} = {v!r}")

    # The tags turned out not to be in the email text: Buttondown adds them when it
    # renders the archive, from the tracking setting each email was sent with. So
    # count them on the public archive page itself.
    tagged = []
    for e in emails:
        page = requests.get(e["absolute_url"], timeout=30).text
        n = len(re.findall(r"veiledantiquity\.com[^\s\"'<>]*utm_", page))
        if n:
            tagged.append(e)
            print(f"  {n:>2} tagged links on the archive page: {e.get('subject', '')[:60]}")
    print(f"  {len(tagged)} archive pages carry tagged links")

    print(f"  archival_mode values in use: {sorted({str(e.get('archival_mode')) for e in emails})}")

    # Re-saving did not redraw the links (tested 2026-11-02), so --apply takes the
    # tagged emails out of the public archive instead. Subscribers are unaffected,
    # and setting archival_mode back to its old value restores them.
    for e in tagged if apply else []:
        r = session.patch(f"{API}/{e['id']}", json={"archival_mode": "disabled"}, timeout=30)
        if r.status_code != 200:
            print(f"     FAILED ({r.status_code}): {r.text[:300]}")
            continue
        after = session.get(f"{API}/{e['id']}", timeout=30).json()
        page = requests.get(e["absolute_url"], timeout=30)
        same = after.get("body") == e["body"] and after.get("status") == e["status"]
        print(f"     hidden {e['id']} (was {e.get('archival_mode')}): "
              f"now {after.get('archival_mode')}, page HTTP {page.status_code}, "
              f"text unchanged {same}: {e.get('subject', '')[:50]}")
        time.sleep(1)


if __name__ == "__main__":
    main()
