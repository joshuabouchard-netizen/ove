"""Render a web page deterministically to stills, video or audio with headless Chromium (Playwright).

  uv run --with playwright python capture.py stills OUTDIR 0 2.5 5 --page page.html [--size 1920x1080] [--query k=v]
  uv run --with playwright python capture.py video OUT.mp4 0 10 --page page.html [--fps 30] [--size 1920x1080] [--crf 15]
  uv run --with playwright python capture.py audio OUT.wav --page page.html [--duration 30]

Add --channel chrome to use the installed Google Chrome instead of Playwright's chromium
(`python -m playwright install chromium` fetches the latter). PAGE is a local path or a URL.

Page contract (`capture=1` is always added to the query string):
  window.__ready = true          set once fonts, images and state are loaded
  window.renderAt(t)             draw the frame at t seconds (may return a promise)
  window.renderAudio(send, dur)  optional; calls send(base64) with interleaved stereo Int16 chunks
                                 at 48 kHz, in order (may return a promise); dur is --duration or null
Video needs even width and height (yuv420p).
"""
import argparse, base64, pathlib, subprocess, sys, wave
from playwright.sync_api import sync_playwright

RATE = 48000


def page_url(page, query):
    url = page if "://" in page else pathlib.Path(page).resolve().as_uri()
    url += ("&" if "?" in url else "?") + "capture=1"
    return url + ("&" + query.lstrip("?&") if query else "")


def open_page(p, a):
    w, h = map(int, a.size.lower().split("x"))
    browser = p.chromium.launch(channel=a.channel, headless=True)
    pg = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    pg.goto(page_url(a.page, a.query))
    pg.wait_for_function("window.__ready === true", timeout=60000)
    return browser, pg


def render(pg, t):
    pg.evaluate("t => window.renderAt(t)", t)


def shot(pg, t, **kw):
    for attempt in range(5):
        try:
            return pg.screenshot(**kw)
        except Exception:
            if attempt == 4:
                raise
            pg.wait_for_timeout(500)
            render(pg, t)


def stills(pg, a):
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in a.times:
        render(pg, t)
        shot(pg, t, path=str(out / f"t{t:07.2f}.png"))
        print(out / f"t{t:07.2f}.png")


def video(pg, a):
    start, end = a.start, a.end
    n0, n1 = round(start * a.fps), round(end * a.fps)
    total = n1 - n0
    if total <= 0:
        sys.exit("END must be after START")
    ff = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(a.fps),
                           "-c:v", "mjpeg", "-i", "-", "-vf", "scale=out_range=tv", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
                           "-pix_fmt", "yuv420p", a.out], stdin=subprocess.PIPE)
    step = max(1, total // 20)
    for k, i in enumerate(range(n0, n1)):
        t = i / a.fps
        render(pg, t)
        ff.stdin.write(shot(pg, t, type="jpeg", quality=95))
        if (k + 1) % step == 0 or k + 1 == total:
            print(f"{a.out}: frame {k + 1}/{total} ({100 * (k + 1) // total}%)", flush=True)
    ff.stdin.close()
    if ff.wait():
        sys.exit(f"ffmpeg failed with code {ff.returncode}")


def audio(pg, a):
    chunks = {}
    pg.expose_function("__captureChunk", lambda i, s: chunks.__setitem__(int(i), base64.b64decode(s)))
    pg.evaluate("""async dur => {
      if (typeof window.renderAudio !== 'function') throw new Error('page has no window.renderAudio');
      const pending = []; let i = 0;
      await window.renderAudio(s => pending.push(window.__captureChunk(i++, s)), dur);
      await Promise.all(pending);
    }""", a.duration)
    pcm = b"".join(chunks[i] for i in sorted(chunks))
    if a.duration:
        pcm = pcm[:round(a.duration * RATE) * 4]
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(RATE)
        w.writeframes(pcm)
    print(f"{a.out}: {len(pcm) // 4 / RATE:.2f}s, {len(chunks)} chunks")


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--page", required=True, help="local HTML path or URL")
    common.add_argument("--query", default="", help="extra query string, e.g. scene=2&bare")
    common.add_argument("--size", default="1920x1080", help="viewport WxH")
    common.add_argument("--channel", default=None, help="browser channel, e.g. chrome (default: Playwright chromium)")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("stills", parents=[common])
    s.add_argument("out")
    s.add_argument("times", nargs="+", type=float)
    v = sub.add_parser("video", parents=[common])
    v.add_argument("out")
    v.add_argument("start", type=float)
    v.add_argument("end", type=float)
    v.add_argument("--fps", type=int, default=30)
    v.add_argument("--crf", type=int, default=15)
    au = sub.add_parser("audio", parents=[common])
    au.add_argument("out")
    au.add_argument("--duration", type=float, default=None)
    a = ap.parse_args()
    with sync_playwright() as p:
        browser, pg = open_page(p, a)
        try:
            {"stills": stills, "video": video, "audio": audio}[a.mode](pg, a)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
