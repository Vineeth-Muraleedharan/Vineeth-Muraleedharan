#!/usr/bin/env python3
"""
Fetch a user's public GitHub contribution calendar — no token, no GraphQL API.

GitHub serves the calendar as a public HTML fragment at
    https://github.com/users/<username>/contributions
(the same fragment the profile page itself embeds). We scrape that,
and write data/contributions.json with the raw per-day data plus a
few derived stats (current streak, longest streak, best day, monthly
totals) that render_heatmap_svg.py and the README stats footer use.

Usage:
    python scripts/fetch_contributions.py [username]

If no username is given, falls back to $GITHUB_REPOSITORY_OWNER (set
automatically inside GitHub Actions) and then to a hardcoded default.
"""

import os
import re
import sys
import json
import datetime
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "Vineeth-Muraleedharan"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# "9 contributions on October 4th." / "No contributions on October 19th."
TOOLTIP_RE = re.compile(
    r"(?P<count>No|\d[\d,]*)\s+contributions?\s+on\s+(?P<when>.+?)\.?\s*$",
    re.IGNORECASE,
)
TOTAL_RE = re.compile(r"([\d,]+)\s+contributions?\s+in the last year", re.IGNORECASE)


def get_username() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.environ.get("GITHUB_REPOSITORY_OWNER", DEFAULT_USERNAME)


def fetch_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_days(html: str):
    """Return a list of {date, count, level} dicts, oldest first."""
    soup = BeautifulSoup(html, "html.parser")

    # Map id -> tooltip text, for the "<tool-tip for=...>N contributions
    # on Month Day.</tool-tip>" markup GitHub currently uses.
    tooltip_by_for = {}
    for tip in soup.find_all(["tool-tip", "span"]):
        for_id = tip.get("for")
        if for_id:
            tooltip_by_for[for_id] = tip.get_text(strip=True)

    cells = soup.select("td.ContributionCalendar-day[data-date]") or soup.select(
        "[data-date]"
    )

    days = []
    for cell in cells:
        date_str = cell.get("data-date")
        if not date_str:
            continue
        level = cell.get("data-level")
        level = int(level) if level is not None and level.isdigit() else None

        count = None
        cell_id = cell.get("id")
        tooltip_text = tooltip_by_for.get(cell_id, "")
        m = TOOLTIP_RE.search(tooltip_text)
        if m:
            raw = m.group("count")
            count = 0 if raw.lower() == "no" else int(raw.replace(",", ""))

        if count is None:
            # Fall back to a direct data-count attribute if present (older markup),
            # else assume 0 for a day we genuinely can't read.
            dc = cell.get("data-count")
            count = int(dc) if dc and dc.isdigit() else 0

        if level is None:
            # Rough bucket so rendering still has something to key off of.
            level = 0 if count == 0 else 1 if count <= 3 else 2 if count <= 6 else 3 if count <= 9 else 4

        days.append({"date": date_str, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def parse_total(html: str, days):
    m = TOTAL_RE.search(html)
    if m:
        return int(m.group(1).replace(",", ""))
    return sum(d["count"] for d in days)


def compute_stats(days):
    if not days:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "best_day": None,
            "monthly": {},
        }

    # Longest streak: longest run of consecutive days with count > 0.
    longest = cur = 0
    for d in days:
        if d["count"] > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    # Current streak: walk backward from the most recent day.
    current = 0
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        else:
            break

    best = max(days, key=lambda d: d["count"])
    best_day = {"date": best["date"], "count": best["count"]} if best["count"] > 0 else None

    monthly = defaultdict(int)
    for d in days:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] += d["count"]

    return {
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best_day,
        "monthly": dict(sorted(monthly.items())),
    }


def main():
    username = get_username()
    html = fetch_html(username)
    days = parse_days(html)
    total = parse_total(html, days)
    stats = compute_stats(days)

    out = {
        "username": username,
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "total_contributions": total,
        "days": days,
        "stats": stats,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/contributions.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(
        f"wrote data/contributions.json: {len(days)} days, "
        f"{total} total contributions, "
        f"current streak {stats['current_streak']}, longest {stats['longest_streak']}"
    )


if __name__ == "__main__":
    main()
