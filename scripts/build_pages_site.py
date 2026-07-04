#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def copy_data(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir()
    for path in source.iterdir():
        if path.suffix in {".json", ".html", ".md"} or path.name == ".gitkeep":
            shutil.copy2(path, destination / path.name)


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    copy_tree(ROOT / "web", SITE / "web")
    copy_data(ROOT / "data", SITE / "data")

    assets = ROOT / "assets"
    if assets.exists():
        copy_tree(assets, SITE / "assets")

    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    (SITE / "index.html").write_text(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0; url=web/">
    <title>Modern Community Topics</title>
    <link rel="canonical" href="web/">
  </head>
  <body>
    <p><a href="web/">Open Modern Community Topics</a></p>
  </body>
</html>
""",
        encoding="utf-8",
    )
    print(f"Built {SITE}")


if __name__ == "__main__":
    main()
