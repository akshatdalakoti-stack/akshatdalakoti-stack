"""
Draws the streak card that counts from the day the work actually started.

Every hosted stats card counts from the account's first commit, which for me is
one stray commit in August 2025 -- seven months of empty calendar in front of
the part I care about. The hosted streak card documents a `starting_year`
parameter for exactly this, but that instance ignores it, so the honest range
has to be computed here instead: everything from 2026-03-27 onward, the first
day with real work on it, and nothing before.

So this replaces the hosted card rather than sitting next to it. Same three
figures -- total, current streak, longest streak -- plus the weekly strip the
hosted one has no room for.

Contributions come from the GraphQL API when a token is in the environment --
that is the Actions path. `contributionsCollection` refuses windows longer than
a year, so the range is walked in year-long chunks and summed, which matters
more every year this keeps running. With no token it falls back to a public
mirror of the same calendar, so the script still works on a laptop.

Output is assets/contributions.svg, in the banner's palette. Standard library
only. The workflow runs this by hand; the numbers are a day stale at worst.

Run from the repository root:  python tools/gen_contrib.py
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request

START = dt.date(2026, 3, 27)
USER = os.environ.get("GITHUB_USER", "akshatdalakoti-stack")
OUT = os.path.join("assets", "contributions.svg")

BG = "#05060f"
CRIMSON = "#ff2d46"
ROSE = "#ff6b7d"
BLOOD = "#9e1330"
INK = "#e8ecff"
MUTED = "#8b93b8"
FONT = "'Segoe UI', Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif"

W, H = 495.0, 235.0
PAD = 26.0
PANEL_Y, PANEL_BOTTOM = 26.0, 140.0
BASE_Y, MAX_BAR = 198.0, 42.0

GQL = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def _json(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def from_graphql(token, today):
    """Walk START..today in <= 1 year windows; the API rejects anything wider."""
    days = {}
    window_start = START
    while window_start <= today:
        year_out = window_start.replace(year=window_start.year + 1) - dt.timedelta(days=1)
        window_end = min(year_out, today)
        payload = json.dumps({
            "query": GQL,
            "variables": {
                "login": USER,
                "from": window_start.isoformat() + "T00:00:00Z",
                "to": window_end.isoformat() + "T23:59:59Z",
            },
        }).encode("utf-8")
        body = _json("https://api.github.com/graphql", payload, {
            "Authorization": "bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": USER,
        })
        if body.get("errors"):
            raise RuntimeError(body["errors"])
        weeks = (body["data"]["user"]["contributionsCollection"]
                 ["contributionCalendar"]["weeks"])
        for week in weeks:
            for day in week["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
        window_start = window_end + dt.timedelta(days=1)
    return days


def from_mirror():
    """No token: a public mirror of the same calendar, so this runs anywhere."""
    url = "https://github-contributions-api.jogruber.de/v4/%s?y=all" % USER
    body = _json(url, headers={"User-Agent": USER})
    return {d["date"]: d["count"] for d in body.get("contributions", [])}


def collect():
    today = dt.date.today()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    days = {}
    if token:
        try:
            days = from_graphql(token, today)
        except (urllib.error.URLError, RuntimeError, KeyError, ValueError) as exc:
            print("graphql failed (%s); falling back to the mirror" % exc)
    if not days:
        days = from_mirror()
    parsed = {dt.date.fromisoformat(k): v for k, v in days.items()}
    return {d: v for d, v in parsed.items() if START <= d <= today}, today


def current_streak(days, today):
    """Today counts once there is something on it, but an empty today does not break it."""
    day = today if days.get(today) else today - dt.timedelta(days=1)
    length = 0
    while days.get(day):
        length += 1
        day -= dt.timedelta(days=1)
    return length, day + dt.timedelta(days=1)


def longest_streak(days):
    best, best_end, run, end = 0, START, 0, START
    for day in sorted(days):
        if days[day]:
            run, end = run + 1, day
        else:
            run = 0
        if run > best:
            best, best_end = run, end
    return best, best_end - dt.timedelta(days=best - 1) if best else START, best_end


def weekly(days):
    """(monday, total) per week, in calendar order, so the strip reads left to right."""
    buckets = {}
    for day, count in days.items():
        monday = day - dt.timedelta(days=day.weekday())
        buckets[monday] = buckets.get(monday, 0) + count
    return sorted(buckets.items())


def short(day):
    return day.strftime("%d %b").lstrip("0")


def stamp(day):
    return day.strftime("%d %b %Y").lstrip("0")


def text(x, y, size, fill, body, anchor="middle", weight=None, spacing=None):
    extra = ""
    if weight:
        extra += ' font-weight="%s"' % weight
    if spacing:
        extra += ' letter-spacing="%s"' % spacing
    return ('<text x="%.1f" y="%.1f" text-anchor="%s" font-family="%s" font-size="%g" '
            'fill="%s"%s>%s</text>' % (x, y, anchor, FONT, size, fill, extra, body))


def render(days, today):
    total = sum(days.values())
    streak, streak_from = current_streak(days, today)
    longest, long_from, long_to = longest_streak(days)
    bars = weekly(days) or [(START, 0)]
    peak = max(v for _, v in bars) or 1

    col = (W - 2 * PAD) / 3.0
    centres = [PAD + col * (i + 0.5) for i in range(3)]
    slot = (W - 2 * PAD) / len(bars)
    bar_w = max(1.5, slot - min(3.0, slot * 0.28))

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%g" height="%g" '
           'viewBox="0 0 %g %g" role="img" aria-labelledby="t">' % (W, H, W, H),
           '<title id="t">%d contributions since %s, current streak %d days, '
           'longest %d days</title>' % (total, stamp(START), streak, longest),
           '<rect width="%g" height="%g" rx="10" fill="%s"/>' % (W, H, BG),
           '<rect x="0.5" y="0.5" width="%g" height="%g" rx="9.5" fill="none" '
           'stroke="%s" stroke-opacity="0.45"/>' % (W - 1, H - 1, BLOOD)]

    for x in (PAD + col, PAD + 2 * col):
        out.append('<line x1="%.1f" y1="%g" x2="%.1f" y2="%g" stroke="%s" '
                   'stroke-opacity="0.45"/>' % (x, PANEL_Y, x, PANEL_BOTTOM, BLOOD))

    # Middle panel carries the ring, so the eye lands on the streak the way it
    # does on the card this replaces.
    out.append('<circle cx="%.1f" cy="71" r="30" fill="none" stroke="%s" '
               'stroke-width="2.5" stroke-opacity="0.85"/>' % (centres[1], CRIMSON))

    panels = [
        (centres[0], str(total), INK, "Total Contributions",
         "%s &#8594; present" % short(START)),
        (centres[1], str(streak), CRIMSON, "Current Streak",
         short(streak_from) if streak else short(today)),
        (centres[2], str(longest), INK, "Longest Streak",
         "%s &#8211; %s" % (short(long_from), short(long_to)) if longest else "&#8211;"),
    ]
    for cx, number, colour, label, sub in panels:
        out.append(text(cx, 82, 34, colour, number, weight="700"))
        out.append(text(cx, 108, 12, CRIMSON if colour == CRIMSON else INK, label))
        out.append(text(cx, 128, 10.5, MUTED, sub))

    for i, (monday, value) in enumerate(bars):
        height = max(2.0, MAX_BAR * (value / peak))
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1.5" fill="%s" '
                   'fill-opacity="%.2f"><title>%d in the week of %s</title></rect>'
                   % (PAD + i * slot, BASE_Y - height, bar_w, height, CRIMSON,
                      0.32 + 0.68 * (value / peak), value, stamp(monday)))
    out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-opacity="0.5"/>'
               % (PAD, BASE_Y + 1, W - PAD, BASE_Y + 1, BLOOD))
    out.append(text(PAD, 218, 10, MUTED, "weekly, %d weeks" % len(bars), anchor="start"))
    out.append(text(W - PAD, 218, 10, MUTED, "%s &#8594; %s" % (stamp(START), stamp(today)),
                    anchor="end"))
    out.append('</svg>')
    return "\n".join(out) + "\n"


def main():
    days, today = collect()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(days, today))
    streak, _ = current_streak(days, today)
    print("wrote %s: %d contributions since %s, current streak %d"
          % (OUT, sum(days.values()), START.isoformat(), streak))


if __name__ == "__main__":
    main()
