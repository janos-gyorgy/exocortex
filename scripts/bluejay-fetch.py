#!/usr/bin/env python3
"""bluejay-fetch.py — wrapper-owned FETCH phase for the Bluejay.

Reads an allowlist of RSS/Atom feed URLs, fetches each, and emits one JSON
object per recent item to stdout (JSON-lines). claude is NOT in this phase.

THE LOAD-BEARING RULE: we read the SUMMARY field only (<description>/<summary>),
never <content:encoded> / full article bodies. Summaries are HTML-stripped and
hard-capped. This is both the lower prompt-injection surface and the natural
fetch shape — the human clicks through by hand from quarantine.

Usage: bluejay-fetch.py FEEDS_FILE [MAX_AGE_DAYS=9] [PER_FEED=10]
Per-feed failures print to stderr and are skipped; the run continues.
"""
import sys, json, re, datetime, urllib.request
import xml.etree.ElementTree as ET

FEEDS_FILE = sys.argv[1]
MAX_AGE_DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 9
PER_FEED = int(sys.argv[3]) if len(sys.argv) > 3 else 10
SUMMARY_CAP = 600
UA = "bluejay/0.1 (+exocortex serendipity reader)"

def local(tag):
    return tag.rsplit("}", 1)[-1].lower()

def strip_html(s):
    s = re.sub(r"(?s)<[^>]+>", " ", s or "")
    s = re.sub(r"&#?\w+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for f in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
              "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            d = datetime.datetime.strptime(s, f)
            return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            pass
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None

now = datetime.datetime.now(datetime.timezone.utc)
cutoff = now - datetime.timedelta(days=MAX_AGE_DAYS)

feeds = []
with open(FEEDS_FILE, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if line and not line.startswith("#"):
            feeds.append(line)

total = 0
for url in feeds:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=20).read()
        root = ET.fromstring(raw)
    except Exception as e:  # noqa: BLE001 — best-effort fetch, skip on any error
        sys.stderr.write(f"  skip {url}: {e}\n")
        continue

    items = [el for el in root.iter() if local(el.tag) in ("item", "entry")]
    n = 0
    for it in items:
        if n >= PER_FEED:
            break
        title = link = summary = ""
        date = None
        for ch in it:
            t = local(ch.tag)
            if t == "title" and not title:
                title = strip_html("".join(ch.itertext()))
            elif t == "link":
                href = ch.get("href")
                if href:
                    if not link or ch.get("rel") in (None, "alternate"):
                        link = href
                elif ch.text and not link:
                    link = ch.text.strip()
            elif t in ("description", "summary") and not summary:
                summary = strip_html("".join(ch.itertext()))
            elif t in ("pubdate", "published", "updated", "date") and date is None:
                date = parse_date("".join(ch.itertext()))
        if date is not None and date < cutoff:
            continue
        if not title and not summary:
            continue
        rec = {
            "feed": url,
            "title": title,
            "summary": summary[:SUMMARY_CAP],
            "url": link,
            "published": date.isoformat() if date else "",
        }
        sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n += 1
        total += 1
    sys.stderr.write(f"  {n:3d} items  {url}\n")

sys.stderr.write(f"total: {total} items from {len(feeds)} feeds\n")
