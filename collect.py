#!/usr/bin/env python3
"""
collect.py — pull public comments from r/soccer using Reddit's no-auth JSON API.

No Reddit account or API key required. Run this on your own machine (a normal
home/college IP works; datacenter IPs get 403'd).

Usage:
    python3 collect.py                 # default: r/soccer, ~300 comments
    python3 collect.py --sub soccer --target 300 --threads 25

Outputs (in ./data):
    comments.csv               every collected comment (id, score, length, body, permalink)
    sample_for_labeling.txt    40 comments spread across the score range, for reading

Why this design:
- r/soccer "posts" are mostly link/video/news with no body text. The actual
  discourse (hot takes vs. analysis vs. banter) lives in the COMMENTS, so we
  collect comments, not submissions.
- We pull from several hot threads to get a mix of match-thread reactions and
  longer discussion threads.
"""
import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) takemeter-research/0.1"


def get(url):
    """GET a Reddit .json endpoint, politely, with retries."""
    for attempt in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 403, 500, 502, 503):
                wait = 3 * (attempt + 1)
                print(f"  HTTP {e.code} on {url} — retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except Exception as e:  # noqa: BLE001 - transient network issues
            print(f"  {type(e).__name__}: {e} — retrying", file=sys.stderr)
            time.sleep(3)
    raise SystemExit(f"Giving up on {url} (Reddit may be rate-limiting or blocking your IP)")


def walk_comments(node, out):
    """Recursively flatten a comment listing into out=[dict, ...]."""
    if not isinstance(node, dict):
        return
    kind = node.get("kind")
    data = node.get("data", {})
    if kind == "t1":  # a comment
        body = (data.get("body") or "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            out.append({
                "id": data.get("id", ""),
                "score": data.get("score", 0),
                "length": len(body),
                "body": body,
                "permalink": "https://reddit.com" + data.get("permalink", ""),
            })
    # descend into replies / listing children
    replies = data.get("replies")
    if isinstance(replies, dict):
        for child in replies.get("data", {}).get("children", []):
            walk_comments(child, out)
    for child in data.get("children", []) if kind == "Listing" else []:
        walk_comments(child, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", default="soccer")
    ap.add_argument("--target", type=int, default=300, help="min comments to collect")
    ap.add_argument("--threads", type=int, default=25, help="hot threads to pull from")
    ap.add_argument("--min-len", type=int, default=15, help="drop comments shorter than this")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    os.makedirs("data", exist_ok=True)

    print(f"Fetching hot threads from r/{args.sub} ...")
    listing = get(f"https://www.reddit.com/r/{args.sub}/hot.json?limit={args.threads}&raw_json=1")
    posts = [c["data"] for c in listing["data"]["children"] if not c["data"].get("stickied")]

    seen, comments = set(), []
    for i, p in enumerate(posts, 1):
        if len(comments) >= args.target:
            break
        permalink = p.get("permalink", "")
        title = p.get("title", "")[:70]
        print(f"[{i}/{len(posts)}] {title!r} ...")
        try:
            thread = get(f"https://www.reddit.com{permalink}.json?limit=500&raw_json=1")
        except SystemExit as e:
            print(f"  skipped: {e}", file=sys.stderr)
            continue
        if len(thread) > 1:
            walk_comments(thread[1], comments)
        # dedupe + length filter, in place
        kept = []
        for c in comments:
            if c["id"] in seen or c["length"] < args.min_len:
                continue
            seen.add(c["id"])
            kept.append(c)
        comments = kept
        print(f"   total kept so far: {len(comments)}")
        time.sleep(1.5)  # be polite to Reddit

    if not comments:
        raise SystemExit("Collected 0 comments. If you saw repeated HTTP 403s, your IP is "
                         "blocked — try a different network or use the PRAW variant.")

    # write full CSV
    csv_path = os.path.join("data", "comments.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "score", "length", "body", "permalink"])
        w.writeheader()
        w.writerows(comments)

    # write a readable 40-comment sample spread across the score range
    ranked = sorted(comments, key=lambda c: c["score"], reverse=True)
    n = min(40, len(ranked))
    step = max(1, len(ranked) // n)
    sample = ranked[::step][:n]
    random.shuffle(sample)
    sample_path = os.path.join("data", "sample_for_labeling.txt")
    with open(sample_path, "w", encoding="utf-8") as f:
        for j, c in enumerate(sample, 1):
            f.write(f"=== #{j}  (score {c['score']}, {c['length']} chars) ===\n")
            f.write(c["body"] + "\n\n")

    print(f"\nDone. {len(comments)} comments -> {csv_path}")
    print(f"40-comment reading sample -> {sample_path}")


if __name__ == "__main__":
    main()
