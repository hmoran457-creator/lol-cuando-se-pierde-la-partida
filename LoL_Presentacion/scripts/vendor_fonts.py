r"""Download the deck's webfonts locally so it works with no internet.

A classroom projector on bad wifi is the expected case, so nothing in the deck may
depend on a CDN. This pulls the woff2 files from Google Fonts and rewrites the
@font-face CSS to point at local relative paths.
"""
from __future__ import annotations

import pathlib
import re
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE.parent / "assets" / "fonts"
FONTS.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

FAMILIES = {
    "archivo": "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=block",
    "jetbrainsmono": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=block",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main() -> None:
    chunks = []
    for name, css_url in FAMILIES.items():
        css = get(css_url).decode("utf-8")
        urls = sorted(set(re.findall(r"https://fonts\.gstatic\.com[^)]+\.woff2", css)))
        print(f"{name}: {len(urls)} woff2 file(s)")
        for i, u in enumerate(urls):
            fname = f"{name}-{i}.woff2"
            dest = FONTS / fname
            if not dest.exists():
                dest.write_bytes(get(u))
            print(f"  {fname}  {dest.stat().st_size/1024:.0f} KB")
            css = css.replace(u, f"./fonts/{fname}")
        chunks.append(f"/* ---- {name} ---- */\n{css}")

    out = FONTS.parent / "fonts.css"
    out.write_text("\n".join(chunks), encoding="utf-8")

    total = sum(f.stat().st_size for f in FONTS.glob("*.woff2"))
    print(f"\nwrote {out}")
    print(f"total font payload: {total/1024:.0f} KB")

    # prove the local paths are what the CSS now references
    remaining = re.findall(r"https://fonts\.gstatic\.com", out.read_text(encoding="utf-8"))
    print(f"remaining remote font refs: {len(remaining)} (must be 0)")


if __name__ == "__main__":
    main()
