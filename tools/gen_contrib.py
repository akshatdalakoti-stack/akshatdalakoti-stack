"""
Draws the contribution card that counts from the day the work actually started.

Every hosted stats card I could find counts from the account's first commit,
which for me is one stray commit in August 2025 -- nine months of empty calendar
in front of the part I care about. The streak card documents a `starting_year`
parameter, but the hosted instance ignores it, so the honest range has to be
computed here instead: everything from 2026-05-31 onward, and nothing before it.

Contributions come from the GraphQL API when a token is in the environment --
that is the Actions path. `contributionsCollection` refuses windows longer than
a year, so the range is walked in year-long chunks and summed, which matters
more every year this keeps running. With no token it falls back to a public
mirror of the same calendar, so the script still works on a laptop.

Output is assets/contributions.svg: the total, three supporting numbers, and a
weekly bar strip, in the banner's palette. Standard library only.

Run from the repository root:  python tools/gen_contrib.py
"""
import datetime as dt
import json
import os
import urllib.error
import urllib.request

START = dt.date(2026, 5, 31)
START_LABEL = "31 MAY 2026"
USER = os.environ.get("GITHUB_USER", "akshatdalakoti-stack")
OUT = os.path.join("assets", "contributions.svg")

BG = "#05060f"
CRIMSON = "#ff2d46"
ROSE = "#ff6b7d"
BLOOD = "#9e1330"
INK = "#e8ecff"
MUTED = "#8b93b8"
FONT = "'Segoe UI', Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif"

W, H = 495.0, 195.0
PAD = 26.0
BASE_Y, MAX_BAR = 158.0, 44.0

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
    return {d: v for d, v in parsed.items() if START <= d <= today}


def weekly(days):
    """(monday, total) per ISO week, in calendar order, so the strip reads left to right."""
    buckets = {}
    for day, count in days.items():
        monday = day - dt.timedelta(days=day.weekday())
        buckets[monday] = buckets.get(monday, 0) + count
    return sorted(buckets.items())


def stamp(day):
    return day.strftime("%d %b %Y").lstrip("0")


def render(days):
    total = sum(days.values())
    active = sum(1 for v in days.values() if v)
    best_day, best = max(days.items(), key=lambda kv: (kv[1], kv[0]), default=(START, 0))
    last = max(days) if days else START
    bars = weekly(days) or [(START, 0)]
    peak = max(v for _, v in bars) or 1

    slot = (W - 2 * PAD) / len(bars)
    bar_w = max(1.5, slot - min(3.0, slot * 0.28))
    right = W - PAD

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%g" height="%g" '
           'viewBox="0 0 %g %g" role="img" aria-labelledby="t">' % (W, H, W, H),
           '<title id="t">%d contributions since %s</title>' % (total, stamp(START)),
           '<rect width="%g" height="%g" rx="10" fill="%s"/>' % (W, H, BG),
           '<rect x="0.5" y="0.5" width="%g" height="%g" rx="9.5" fill="none" '
           'stroke="%s" stroke-opacity="0.45"/>' % (W - 1, H - 1, BLOOD),
           '<text x="%g" y="38" font-family="%s" font-size="11" letter-spacing="2.4" '
           'fill="%s">SINCE %s</text>' % (PAD, FONT, MUTED, START_LABEL),
           '<text x="%g" y="96" font-family="%s" font-size="52" font-weight="700" '
           'fill="%s">%d</text>' % (PAD, FONT, CRIMSON, total),
           '<text x="%g" y="96" font-family="%s" font-size="13" fill="%s">contributions</text>'
           % (PAD + 30 * len(str(total)) + 12, FONT, INK),
           '<text x="%g" y="58" text-anchor="end" font-family="%s" font-size="12" '
           'fill="%s">%d active days</text>' % (right, FONT, INK, active),
           '<text x="%g" y="80" text-anchor="end" font-family="%s" font-size="12" '
           'fill="%s">busiest: %d on %s</text>'
           % (right, FONT, ROSE, best, best_day.strftime("%d %b").lstrip("0")),
           '<text x="%g" y="102" text-anchor="end" font-family="%s" font-size="11" '
           'fill="%s">last: %s</text>' % (right, FONT, MUTED, stamp(last))]

    for i, (monday, value) in enumerate(bars):
        height = max(2.0, MAX_BAR * (value / peak))
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="1.5" fill="%s" '
                   'fill-opacity="%.2f"><title>%d in the week of %s</title></rect>'
                   % (PAD + i * slot, BASE_Y - height, bar_w, height, CRIMSON,
                      0.32 + 0.68 * (value / peak), value, stamp(monday)))

    out.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-opacity="0.5"/>'
               % (PAD, BASE_Y + 1, W - PAD, BASE_Y + 1, BLOOD))
    out.append('<text x="%g" y="178" font-family="%s" font-size="10" fill="%s">'
               'weekly, %d weeks</text>' % (PAD, FONT, MUTED, len(bars)))
    out.append('<text x="%g" y="178" text-anchor="end" font-family="%s" font-size="10" '
               'fill="%s">refreshed daily</text>' % (right, FONT, MUTED))
    out.append('</svg>')
    return "\n".join(out) + "\n"


def main():
    days = collect()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render(days))
    print("wrote %s: %d contributions over %d days"
          % (OUT, sum(days.values()), len(days)))


if __name__ == "__main__":
    main()
