#!/usr/bin/env python3
"""desk-dedup.py — trusted post-filter for the forager birds.

Runs in the TRUSTED wrapper, AFTER the sandboxed collide agent and AFTER the
blast-radius check. Removes from today's quarantine file any find that:
  (a) already appeared in a PRIOR quarantine file for this bird — the history
      is the ledger, no separate state is kept; or
  (b) is muted by hand in quarantine/desk-dismissed.md.

It only ever rewrites or removes the single QFILE it is handed, so the wrapper's
blast-radius guarantee is untouched and the untrusted agent is unchanged. Keys
are computed identically to HQ's desk_key(), so a key you mute on the board is
the same key the birds skip at the source.

Usage: desk-dedup.py <qdir> <qfile> <dismissed-md>
"""
import os
import re
import sys


def desk_key(title, link):
    base = link or title
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:80]


def clean(s):
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    return s.replace("**", "").replace("`", "").strip()


def split_blocks(text):
    """-> (header_text, [(raw_block, key), ...]). raw_block keeps original text."""
    parts = re.split(r"(?m)^## +", text)
    header = parts[0]
    out = []
    for b in parts[1:]:
        head, _, body = b.partition("\n")
        title = clean(head)
        m = re.search(r"https?://\S+", body)
        link = m.group(0).rstrip(").,") if m else ""
        out.append(("## " + b, desk_key(title, link)))
    return header, out


def keys_in(path):
    try:
        _, bl = split_blocks(open(path, encoding="utf-8").read())
        return {k for _, k in bl}
    except OSError:
        return set()


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: desk-dedup.py <qdir> <qfile> <dismissed-md>")
    qdir, qfile, dismissed = sys.argv[1], sys.argv[2], sys.argv[3]

    seen = set()
    if os.path.isdir(qdir):
        for fn in os.listdir(qdir):
            p = os.path.join(qdir, fn)
            if (not fn.endswith(".md") or fn == "README.md"
                    or os.path.abspath(p) == os.path.abspath(qfile)):
                continue
            seen |= keys_in(p)
    try:
        for ln in open(dismissed, encoding="utf-8"):
            m = re.match(r"^- +(\S+)", ln)
            if m:
                seen.add(m.group(1).strip())
    except OSError:
        pass

    try:
        text = open(qfile, encoding="utf-8").read()
    except OSError:
        return
    header, bl = split_blocks(text)
    kept = [raw for raw, k in bl if k not in seen]
    dropped = len(bl) - len(kept)
    if not kept:
        os.remove(qfile)
        print(f"desk-dedup: all {len(bl)} find(s) already seen/muted -> removed {os.path.basename(qfile)}")
        return
    with open(qfile, "w", encoding="utf-8") as f:
        f.write(header + "".join(kept))
    print(f"desk-dedup: kept {len(kept)}, dropped {dropped} already-seen/muted")


if __name__ == "__main__":
    main()
