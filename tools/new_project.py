#!/usr/bin/env python3
"""Создать новый игровой проект из template/ и подключить его к хабу.

    python3 tools/new_project.py "My Game" --tagline "Одна фраза про игру"
    python3 tools/new_project.py "My Game" --tagline "..." --renderer mobile --private
    python3 tools/new_project.py "My Game" --tagline "..." --no-github    # только папка

Что делает: копирует template/ с подстановкой имён, кладёт минимальный project.godot,
git init + первый коммит, `gh repo create` + push, создаёт метки на GitHub через sync_plan.py,
дописывает проект в projects.yaml хаба.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="Имя игры, оно же имя репозитория (пробелы станут дефисами)")
    ap.add_argument("--tagline", required=True, help="Одна фраза про игру")
    ap.add_argument("--engine", default="Godot 4.4")
    ap.add_argument("--renderer", default="forward_plus", choices=["forward_plus", "mobile", "gl_compatibility"])
    ap.add_argument("--dir", default="~/Games", help="Куда класть папку проекта")
    ap.add_argument("--color", help="Цвет в календаре хаба, hex")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--no-github", action="store_true", help="Не создавать репозиторий на GitHub")
    ap.add_argument("--no-godot", action="store_true", help="Не создавать project.godot")
    args = ap.parse_args()

    with open(REGISTRY, encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    owner = reg["owner"]
    repo_name = args.name.replace(" ", "-")
    slug = slugify(args.name)
    if any(p["id"] == slug for p in reg["projects"]):
        sys.exit("В projects.yaml уже есть проект с id %s" % slug)
    dest = os.path.join(os.path.expanduser(args.dir), repo_name)
    if os.path.exists(dest):
        sys.exit("Папка уже существует: %s" % dest)

    feature = {"forward_plus": "Forward Plus", "mobile": "Mobile", "gl_compatibility": "GL Compatibility"}[args.renderer]
    version = re.search(r"\d+\.\d+", args.engine)
    subst = {
        "{{NAME}}": args.name, "{{SLUG}}": slug, "{{TAGLINE}}": args.tagline, "{{OWNER}}": owner,
        "{{REPO}}": "%s/%s" % (owner, repo_name), "{{ENGINE}}": args.engine, "{{GODOT_DIR}}": slug,
        "{{DATE}}": dt.date.today().isoformat(),
    }

    # 1. template
    for root, dirs, files in os.walk(TEMPLATE):
        rel = os.path.relpath(root, TEMPLATE)
        out_dir = os.path.join(dest, rel) if rel != "." else dest
        os.makedirs(out_dir, exist_ok=True)
        for fn in files:
            if fn == ".DS_Store":
                continue
            src = os.path.join(root, fn)
            with open(src, encoding="utf-8") as f:
                text = f.read()
            for k, v in subst.items():
                text = text.replace(k, v.replace('"', '\\"') if fn.endswith((".yaml", ".yml")) else v)
            dst = os.path.join(out_dir, fn)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(text)
            shutil.copymode(src, dst)
    print("template ->", dest)

    # 2. godot
    if not args.no_godot:
        gdir = os.path.join(dest, slug)
        for sub in ("scenes", "scripts", "resources", "assets", "debug"):
            os.makedirs(os.path.join(gdir, sub), exist_ok=True)
            open(os.path.join(gdir, sub, ".gitkeep"), "w").close()
        with open(os.path.join(gdir, "project.godot"), "w", encoding="utf-8") as f:
            f.write('; Engine configuration file.\nconfig_version=5\n\n[application]\n\n'
                    'config/name="%s"\nconfig/features=PackedStringArray("%s", "%s")\n\n'
                    '[rendering]\n\nrenderer/rendering_method="%s"\n'
                    % (args.name, version.group(0) if version else "4.4", feature, args.renderer))
        print("godot project ->", gdir)

    # 3. PLAN.md + git
    subprocess.run([sys.executable, os.path.join(dest, "tools", "sync_plan.py")], cwd=dest, check=True)
    run(["git", "init", "-q", "-b", "main"], dest)
    run(["git", "add", "-A"], dest)
    run(["git", "commit", "-q", "-m", "Scaffold %s from gamedev-hub template" % args.name], dest)

    # 4. github
    repo = "%s/%s" % (owner, repo_name)
    if not args.no_github:
        res = run(["gh", "repo", "create", repo, "--private" if args.private else "--public",
                   "--source", dest, "--push", "--description", args.tagline], dest, check=False)
        if res.returncode:
            print(res.stderr)
            sys.exit("gh repo create не удался; папка %s создана, повторите вручную" % dest)
        print(res.stdout.strip())
        subprocess.run([sys.executable, "tools/sync_plan.py", "--github"], cwd=dest, check=False)

    # 5. registry
    color = args.color or random.choice(PALETTE)
    entry = (
        "\n  - id: %s\n    name: %s\n    repo: %s\n    local: %s\n    engine: %s\n"
        "    phase: idea\n    tracker: github-issues\n    color: \"%s\"\n    tagline: %s\n"
        % (slug, args.name, repo, os.path.join(args.dir, repo_name), args.engine, color,
           json.dumps(args.tagline, ensure_ascii=False)))
    with open(REGISTRY, "a", encoding="utf-8") as f:
        f.write(entry)
    print("projects.yaml: добавлен", slug)

    print("\nГотово.\n  Проект: %s\n  GitHub: https://github.com/%s\n"
          "  Дальше: заполнить docs/GDD.md, правки плана в docs/plan.yaml + `python3 tools/sync_plan.py --github`,\n"
          "  закоммитить projects.yaml в хабе, чтобы дашборд подхватил проект." % (dest, repo))


if __name__ == "__main__":
    main()
