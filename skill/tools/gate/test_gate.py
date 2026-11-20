"""Check the password gate against a local `wrangler pages dev` server.

  npx wrangler pages dev site --port 8788 --ip 127.0.0.1      (in another terminal, from this folder)
  uv run --with playwright python test_gate.py [--url http://127.0.0.1:8788] [--media /path/in/site.mp4]

Reads SITE_PASSWORD from .dev.vars next to this file and never prints it. Uses the installed Google Chrome
(falls back to Playwright's Chromium). --media defaults to the first video or audio file in site/.
"""
import argparse, pathlib, re, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
MEDIA = {".mp4", ".webm", ".mov", ".m4v", ".mp3", ".m4a", ".wav", ".ogg"}


def password():
    for line in (HERE / ".dev.vars").read_text().splitlines():
        if line.startswith("SITE_PASSWORD"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("no SITE_PASSWORD in .dev.vars")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8788")
    ap.add_argument("--media")
    a = ap.parse_args()
    B, PW = a.url.rstrip("/"), password()
    media = a.media or next(("/" + p.relative_to(HERE / "site").as_posix() for p in sorted((HERE / "site").rglob("*"))
                             if p.suffix.lower() in MEDIA), None)
    if not media:
        sys.exit("no video or audio file in site/; pass --media")
    index = HERE / "site" / "index.html"
    title = re.search(r"<title>(.*?)</title>", index.read_text(), re.S).group(1).strip() if index.exists() else None
    results = []
    check = lambda name, ok, note="": (results.append(ok), print(f"{'PASS' if ok else 'FAIL'}  {name}{'  ' + note if note else ''}"))

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        pg = ctx.new_page()

        r = ctx.request.get(B + media)
        check("media without the cookie is refused", r.status == 401, f"{media} -> {r.status}")
        r = pg.goto(B + "/")
        check("page without the cookie shows the sign-in form", r.status == 200 and pg.locator("input[type=password]").count() == 1)
        check("every response says noindex", r.headers.get("x-robots-tag") == "noindex, nofollow")
        pg.fill("input[type=password]", "not-the-password")
        with pg.expect_navigation() as nav:
            pg.click("button[type=submit]")
        check("wrong password shows an error and stays locked",
              nav.value.status == 401 and pg.locator(".err").count() == 1 and pg.locator("input[type=password]").count() == 1)
        pg.fill("input[type=password]", PW)
        with pg.expect_navigation() as nav:
            pg.click("button[type=submit]")
        opened = pg.locator("input[type=password]").count() == 0 and (title is None or pg.title() == title)
        check("right password opens the index", opened, f"title {pg.title()!r}")
        check("HTML is not cached", (nav.value.headers.get("cache-control") or "") == "no-store")
        r = ctx.request.get(B + media, headers={"Range": "bytes=0-1023"})
        check("range request for media gets 206", r.status == 206 and (r.headers.get("content-range") or "").startswith("bytes 0-1023/")
              and len(r.body()) == 1024, f"{r.status} {r.headers.get('content-range')}")
        check("media is cached privately", r.headers.get("cache-control") == "private, max-age=3600")
        r = ctx.request.get(B + "/robots.txt")
        check("robots.txt disallows everything", r.status == 200 and "Disallow: /" in r.text())
        pg.goto(B + "/__leave")
        locked = pg.locator("input[type=password]").count() == 1 and ctx.request.get(B + media).status == 401
        check("signing out locks the site again", locked)
        browser.close()
    print(f"{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
