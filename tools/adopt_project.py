#!/usr/bin/env python3
"""Подключить существующий репозиторий к единому воркфлоу: наложить template/ поверх,
не трогая уже существующие файлы, и добавить проект в projects.yaml.

    python3 tools/adopt_project.py owner/Repo --tagline "..." [--phase idea] [--engine "Godot 4.4"]
    python3 tools/adopt_project.py owner/Repo --tagline "..." --local ~/path/to/clone

Без --local клонирует в ~/Documents/GitHub/<Repo>. Папку Godot находит по project.godot.
После наложения: PLAN.md, коммит, пуш, метки/вехи через sync_plan.py --github.
"""
import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
import sys

import yaml

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(HUB, "template")
REGISTRY = os.path.join(HUB, "projects.yaml")
PALETTE = ["#9b5de5", "#f15bb5", "#fee440", "#00bbf9", "#00f5d4", "#ff7b00", "#8ac926", "#ff595e"]


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def run(cmd, cwd, check=True):
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def find_godot_dir(root):
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if "project.godot" in files:
            return os.path.relpath(cur, root)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", help="owner/Repo на GitHub")
    ap.add_argument("--tagline", required=True)
    ap.add_argument("--name", help="Имя проекта (по умолчанию имя репозитория)")
    ap.add_argument("--phase", default="idea")
    ap.add_argument("--engine", default="Godot 4.4")
    ap.add_argument("--color")
    ap.add_argument("--local", help="Существующий клон; иначе клонируется в --dir")
    ap.add_argument("--dir", default="~/Documents/GitHub")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    with open(REGISTRY, encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    owner_repo = args.repo
    owner, repo_name = owner_repo.split("/")
    name = args.name or repo_name
    slug = slugify(repo_name)
    if any(p["id"] == slug for p in reg["projects"]):
        sys.exit("В projects.yaml уже есть проект с id %s" % slug)

    dest = os.path.expanduser(args.local) if args.local else os.path.join(os.path.expanduser(args.dir), repo_name)
    if not os.path.isdir(dest):
        run(["gh", "repo", "clone", owner_repo, dest], HUB)
    godot_dir = find_godot_dir(dest) or slug
    subst = {
        "{{NAME}}": name, "{{SLUG}}": slug, "{{TAGLINE}}": args.tagline, "{{OWNER}}": owner,
        "{{REPO}}": owner_repo, "{{ENGINE}}": args.engine, "{{GODOT_DIR}}": godot_dir,
        "{{DATE}}": dt.date.today().isoformat(),
    }

    added, skipped = [], []
    for root, dirs, files in os.walk(TEMPLATE):
        rel = os.path.relpath(root, TEMPLATE)
        out_dir = os.path.join(dest, rel) if rel != "." else dest
        os.makedirs(out_dir, exist_ok=True)
        for fn in files:
            if fn == ".DS_Store":
                continue
            src = os.path.join(root, fn)
            dst = os.path.join(out_dir, fn)
            relpath = os.path.normpath(os.path.join(rel, fn))
            if os.path.exists(dst) and fn != "README.md":
                skipped.append(relpath)
                continue
            with open(src, encoding="utf-8") as f:
                text = f.read()
            for k, v in subst.items():
                text = text.replace(k, v)
            if fn == "README.md" and os.path.exists(dst):
                # существующий README оставляем сверху, ссылки шаблона добавляем снизу
                with open(dst, encoding="utf-8") as f:
                    old = f.read().rstrip()
                text = old + "\n\n" + text.split("\n", 2)[2].lstrip() if text.count("\n") > 2 else old
            with open(dst, "w", encoding="utf-8") as f:
                f.write(text)
            shutil.copymode(src, dst)
            added.append(relpath)
    # фаза в project.yaml
    py = os.path.join(dest, "project.yaml")
    if "project.yaml" in added:
        with open(py, encoding="utf-8") as f:
            text = f.read().replace("phase: idea", "phase: " + args.phase)
        with open(py, "w", encoding="utf-8") as f:
            f.write(text)
    print("добавлено:", ", ".join(added) or "ничего")
    print("уже было:", ", ".join(skipped) or "ничего")

    subprocess.run([sys.executable, os.path.join(dest, "tools", "sync_plan.py")], cwd=dest, check=True)
    run(["git", "add", "-A"], dest)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=dest).returncode:
        run(["git", "commit", "-q", "-m", "Adopt gamedev-hub template: CLAUDE.md, docs, plan, skills, project.yaml\n\n"
             "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"], dest)
    if not args.no_push:
        run(["git", "push", "-q"], dest)
        subprocess.run([sys.executable, "tools/sync_plan.py", "--github"], cwd=dest, check=False)
        if args.tagline:
            run(["gh", "repo", "edit", owner_repo, "--description", args.tagline], dest, check=False)

    color = args.color or random.choice(PALETTE)
    local = args.local or os.path.join(args.dir, repo_name)
    with open(REGISTRY, "a", encoding="utf-8") as f:
        f.write("\n  - id: %s\n    name: %s\n    repo: %s\n    local: %s\n    engine: %s\n"
                "    phase: %s\n    tracker: github-issues\n    color: \"%s\"\n    tagline: %s\n"
                % (slug, name, owner_repo, local, args.engine, args.phase, color, json.dumps(args.tagline, ensure_ascii=False)))
    print("projects.yaml: добавлен", slug)


if __name__ == "__main__":
    main()
