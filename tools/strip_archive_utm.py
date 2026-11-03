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

    in_body = 0
    for e in emails:
        body = e.get("body") or ""
        n = len(re.findall(r"veiledantiquity\.com[^\s\"'<>]*utm_", body))
        if not n:
            continue
        in_body += 1
        print(f"  {n:>2} tagged links in the body: {e.get('subject', '')[:60]}")
        if not apply:
            continue

        new = clean(body)
        r = session.patch(f"{API}/{e['id']}", json={"body": new}, timeout=30)
        if r.status_code != 200:
            print(f"     FAILED ({r.status_code}): {r.text[:200]}")
            continue
        after = session.get(f"{API}/{e['id']}", timeout=30).json().get("body") or ""
        ok = "utm_" not in after and clean(body) == after
        print(f"     {'fixed' if ok else 'CHECK BY HAND'}")
        time.sleep(1)

    print(f"  {in_body} emails have tagged links written into their body")
    if not in_body:
        print("  The tags are not in the email text, so Buttondown adds them when it shows")
        print("  the archive. Editing the emails will not remove them.")


if __name__ == "__main__":
    main()
