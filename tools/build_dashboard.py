#!/usr/bin/env python3
"""Собирает дашборд gamedev-hub из projects.yaml и GitHub API.

    python3 tools/build_dashboard.py            # README.md, docs/data.json, docs/calendar.svg
    python3 tools/build_dashboard.py --offline  # перерисовать из docs/data.json без сети

Токен: переменная GITHUB_TOKEN, иначе `gh auth token`.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from zoneinfo import ZoneInfo

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "projects.yaml")
README = os.path.join(ROOT, "README.md")
DATA_JSON = os.path.join(ROOT, "docs", "data.json")
CALENDAR_SVG = os.path.join(ROOT, "docs", "calendar.svg")
API = "https://api.github.com"

PHASES = ["idea", "prototype", "vertical-slice", "content", "polish", "released", "paused", "archived"]
PHASE_LABEL = {
    "idea": "идея", "prototype": "прототип", "vertical-slice": "вертикальный срез",
    "content": "контент", "polish": "полировка", "released": "выпущена",
    "paused": "на паузе", "archived": "в архиве",
}


# ---------------------------------------------------------------- GitHub API

def token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        return ""


TOKEN = None


def api(path, params=None, raw=False, ok404=False):
    global TOKEN
    if TOKEN is None:
        TOKEN = token()
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.raw" if raw else "application/vnd.github+json")
    req.add_header("User-Agent", "gamedev-hub")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8")
            return body if raw else json.loads(body)
    except urllib.error.HTTPError as e:
        if e.code == 404 and ok404:
            return None
        sys.exit("GitHub API %s -> %s %s" % (path, e.code, e.read()[:200]))


def paginate(path, params=None, limit=5000):
    params = dict(params or {})
    params["per_page"] = 100
    page = 1
    out = []
    while True:
        params["page"] = page
        chunk = api(path, params)
        if not chunk:
            break
        out.extend(chunk)
        if len(chunk) < 100 or len(out) >= limit:
            break
        page += 1
    return out


# ---------------------------------------------------------------- collect

def collect(reg):
    tz = ZoneInfo(reg.get("timezone", "UTC"))
    since = str(reg.get("since", "2020-01-01"))
    activity = defaultdict(lambda: defaultdict(int))  # date -> project id -> commits
    today = dt.datetime.now(tz).date()
    projects = []
    for p in reg["projects"]:
        repo = p["repo"]
        info = api("/repos/" + repo)
        meta = api("/repos/%s/contents/project.yaml" % repo, raw=True, ok404=True)
        try:
            meta = yaml.safe_load(meta) or {} if meta else {}
        except yaml.YAMLError as e:
            print("WARN %s: project.yaml не парсится, использую реестр (%s)" % (repo, str(e).splitlines()[0]))
            meta = {}
        commits = paginate("/repos/%s/commits" % repo, {"since": since + "T00:00:00Z"})
        days = defaultdict(int)
        for c in commits:
            d = c["commit"]["author"]["date"]
            local = dt.datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(tz).date()
            days[local.isoformat()] += 1
            activity[local.isoformat()][p["id"]] += 1
        last_commit = max(days) if days else None
        last_msg = commits[0]["commit"]["message"].splitlines()[0] if commits else ""
        last30 = sum(n for d, n in days.items() if (today - dt.date.fromisoformat(d)).days < 30)

        tracker = meta.get("tracker", p.get("tracker", "none"))
        progress = {"done": 0, "total": 0, "open": 0, "milestones": []}
        if tracker == "github-issues":
            issues = [i for i in paginate("/repos/%s/issues" % repo, {"state": "all"}) if "pull_request" not in i]
            progress["total"] = len(issues)
            progress["done"] = sum(1 for i in issues if i["state"] == "closed")
            progress["open"] = progress["total"] - progress["done"]
            for m in api("/repos/%s/milestones" % repo, {"state": "all", "sort": "due_on"}):
                progress["milestones"].append({
                    "title": m["title"], "open": m["open_issues"], "closed": m["closed_issues"],
                    "state": m["state"],
                })
            progress["milestones"].sort(key=lambda m: m["title"])
        elif tracker == "tasks-yaml":
            raw = api("/repos/%s/contents/tasks.yaml" % repo, raw=True, ok404=True)
            if raw:
                tasks = (yaml.safe_load(raw) or {}).get("tasks", [])
                progress["total"] = len(tasks)
                progress["done"] = sum(1 for t in tasks if t.get("status") == "done")
                progress["open"] = progress["total"] - progress["done"]

        projects.append({
            "id": p["id"],
            "name": p["name"],
            "repo": repo,
            "url": info["html_url"],
            "engine": meta.get("engine", p.get("engine", "")),
            "phase": meta.get("phase", p.get("phase", "idea")),
            "tagline": meta.get("tagline", p.get("tagline", info.get("description") or "")),
            "next": meta.get("next", ""),
            "store": meta.get("store", p.get("store") or ""),
            "tracker": tracker,
            "color": p.get("color", "#888888"),
            "commits_total": len(commits),
            "active_days": len(days),
            "commits_30d": last30,
            "last_commit": last_commit,
            "last_message": last_msg,
            "pushed_at": info.get("pushed_at"),
            "progress": progress,
        })
    return {
        "generated_at": dt.datetime.now(tz).isoformat(timespec="minutes"),
        "timezone": reg.get("timezone", "UTC"),
        "since": since,
        "owner": reg.get("owner"),
        "projects": projects,
        "activity": {d: dict(v) for d, v in sorted(activity.items())},
    }


# ---------------------------------------------------------------- render: svg

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def render_calendar_svg(data, weeks=53):
    tz = ZoneInfo(data["timezone"])
    today = dt.datetime.now(tz).date()
    end = today + dt.timedelta(days=6 - today.weekday())  # end of this week (Sunday)
    start = end - dt.timedelta(weeks=weeks) + dt.timedelta(days=1)
    colors = {p["id"]: p["color"] for p in data["projects"]}
    names = {p["id"]: p["name"] for p in data["projects"]}
    act = data["activity"]
    maxc = max([sum(v.values()) for v in act.values()] or [1])

    cell, gap, left, top = 12, 3, 32, 20
    w = left + weeks * (cell + gap) + 8
    h = top + 7 * (cell + gap) + 36
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="10">' % (w, h, w, h)]
    out.append('<style>text{fill:#8b949e}</style>')
    for i, lab in ((0, "Пн"), (2, "Ср"), (4, "Пт")):
        out.append('<text x="0" y="%d">%s</text>' % (top + i * (cell + gap) + cell - 2, lab))
    last_month = None
    d = start
    for wk in range(weeks):
        x = left + wk * (cell + gap)
        for wd in range(7):
            day = d.isoformat()
            y = top + wd * (cell + gap)
            if d.day <= 7 and d.month != last_month and wd == d.weekday():
                if wd == 0 or last_month is None:
                    out.append('<text x="%d" y="%d">%s</text>' % (x, top - 7, d.strftime("%b")))
                    last_month = d.month
            if d > today:
                d += dt.timedelta(days=1)
                continue
            v = act.get(day)
            if not v:
                out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="#8b949e" fill-opacity="0.18"/>'
                           % (x, y, cell, cell))
            else:
                total = sum(v.values())
                op = 0.45 + 0.55 * min(1.0, total / max(1, maxc * 0.6))
                items = sorted(v.items(), key=lambda kv: -kv[1])
                title = "%s: " % day + ", ".join("%s %d" % (names.get(k, k), n) for k, n in items)
                out.append('<g><title>%s</title>' % title)
                if len(items) == 1:
                    out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s" fill-opacity="%.2f"/>'
                               % (x, y, cell, cell, colors.get(items[0][0], "#888"), op))
                else:
                    yy = y
                    for k, n in items:
                        hh = round(cell * n / total)
                        out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="%.2f"/>'
                                   % (x, yy, cell, max(1, hh), colors.get(k, "#888"), op))
                        yy += hh
                out.append('</g>')
            d += dt.timedelta(days=1)
    # legend
    lx, ly = left, top + 7 * (cell + gap) + 14
    for p in data["projects"]:
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>' % (lx, ly, cell, cell, p["color"]))
        label = "%s · %d дн." % (p["name"], p["active_days"])
        out.append('<text x="%d" y="%d">%s</text>' % (lx + cell + 5, ly + cell - 2, label))
        lx += cell + 5 + int(len(label) * 5.6) + 18
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- render: readme

def bar(done, total, width=10):
    if not total:
        return "—"
    filled = round(width * done / total)
    return "`%s%s` %d%%" % ("█" * filled, "░" * (width - filled), round(100 * done / total))


def render_readme(data):
    owner = data["owner"]
    lines = []
    lines.append("# gamedev-hub")
    lines.append("")
    lines.append("Контрольная панель по всем игровым проектам. Генерируется автоматически из "
                 "[`projects.yaml`](projects.yaml) и GitHub API, руками не правится.")
    lines.append("")
    lines.append("**Дашборд:** https://%s.github.io/gamedev-hub/ · **Процесс:** [WORKFLOW.md](WORKFLOW.md) · "
                 "**Шаблон проекта:** [template/](template/)" % owner.lower())
    lines.append("")
    lines.append("## Проекты")
    lines.append("")
    lines.append("| Игра | Фаза | Движок | Прогресс | Открыто | Последний коммит | 30 дн. | Всего |")
    lines.append("|---|---|---|---|--:|---|--:|--:|")
    for p in sorted(data["projects"], key=lambda p: p["last_commit"] or "", reverse=True):
        pr = p["progress"]
        prog = bar(pr["done"], pr["total"]) + (" (%d/%d)" % (pr["done"], pr["total"]) if pr["total"] else "")
        last = ("%s" % p["last_commit"]) if p["last_commit"] else "—"
        store = " · [App Store](%s)" % p["store"] if p.get("store") else ""
        lines.append("| **[%s](%s)**%s<br><sub>%s</sub> | %s | %s | %s | %s | %s<br><sub>%s</sub> | %d | %d |" % (
            p["name"], p["url"], store, p["tagline"], PHASE_LABEL.get(p["phase"], p["phase"]), p["engine"],
            prog, pr["open"] if pr["total"] else "—", last, p["last_message"][:60].replace("|", "/"),
            p["commits_30d"], p["commits_total"]))
    lines.append("")
    lines.append("## Активность")
    lines.append("")
    lines.append("Каждая клетка — день; цвет — игра, над которой шла работа; две игры в день делят клетку.")
    lines.append("")
    lines.append("![calendar](docs/calendar.svg)")
    lines.append("")
    for p in data["projects"]:
        ms = [m for m in p["progress"]["milestones"] if m["open"] + m["closed"]]
        if not ms and not p["next"]:
            continue
        lines.append("### %s" % p["name"])
        lines.append("")
        if p["next"]:
            lines.append("Дальше: %s" % p["next"])
            lines.append("")
        for m in ms:
            tot = m["open"] + m["closed"]
            lines.append("- %s %s %d/%d%s" % (m["title"], bar(m["closed"], tot), m["closed"], tot,
                                              " · закрыта" if m["state"] == "closed" else ""))
        lines.append("")
    lines.append("## Как пользоваться")
    lines.append("")
    lines.append("- Добавить или изменить проект: правка `projects.yaml`, коммит. Фазу удобнее держать в "
                 "`project.yaml` самого проекта, хаб её подхватит.")
    lines.append("- Пересобрать вручную: `python3 tools/build_dashboard.py` (нужен `gh auth login` или `GITHUB_TOKEN`).")
    lines.append("- Новый проект: `python3 tools/new_project.py MyGame --tagline \"...\"`.")
    lines.append("- Автосборка: раз в сутки и при каждом пуше, см. `.github/workflows/dashboard.yml`.")
    lines.append("")
    lines.append("<sub>Обновлено %s (%s)</sub>" % (data["generated_at"], data["timezone"]))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="перерисовать из docs/data.json")
    args = ap.parse_args()
    with open(REGISTRY, encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    if args.offline:
        with open(DATA_JSON, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = collect(reg)
        os.makedirs(os.path.dirname(DATA_JSON), exist_ok=True)
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    with open(CALENDAR_SVG, "w", encoding="utf-8") as f:
        f.write(render_calendar_svg(data))
    with open(README, "w", encoding="utf-8") as f:
        f.write(render_readme(data))
    for p in data["projects"]:
        pr = p["progress"]
        print("%-18s %-16s commits=%-4d days=%-3d last=%s progress=%d/%d" % (
            p["name"], p["phase"], p["commits_total"], p["active_days"], p["last_commit"], pr["done"], pr["total"]))


if __name__ == "__main__":
    main()
