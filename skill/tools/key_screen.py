"""Key the green screen out of a phone photo so a live HTML screen can sit inside it.

uv run --with opencv-python-headless --with numpy python tools/key_screen.py plate.jpg OUTPREFIX \
    [--stage 1920x1080] [--screen 402x874] [--grow 1.0]

Writes
  OUTPREFIX_bg.jpg  the photo with green spill removed around the screen
  OUTPREFIX_ov.png  the same photo, transparent only where the screen is (a thumb over the screen stays on top)
  OUTPREFIX.json    {"image_size", "quad", "stage", "quad_stage", "grow", "screen", "css"}
and prints a CSS transform that maps a --screen sized element (transform-origin: 0 0) onto the screen quad,
in stage pixels, assuming the photo is scaled to cover the stage and centred (object-fit: cover).
Corners are TL, TR, BR, BL. Each comes from straight lines fitted to the middle of the two sides that meet
there, so rounded screen corners and a finger over one edge do not pull it.
"""
import argparse, json, pathlib, sys
import cv2, numpy as np


def greenness(img):
    b, g, r = [img[..., i].astype(np.float32) for i in range(3)]
    return np.clip((g - np.maximum(r, b) - 28) / 70, 0, 1)


def find_quad(mask):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if n < 2:
        sys.exit("no green screen found")
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255
    k = max(3, round(max(m.shape) / 100) | 1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    cnt = max(cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)[:, 0, :].astype(np.float64)
    hull = cv2.convexHull(cnt.astype(np.float32))
    eps = 0.01 * cv2.arcLength(hull, True)
    approx = cv2.approxPolyDP(hull, eps, True)
    while len(approx) > 4:
        eps *= 1.15
        approx = cv2.approxPolyDP(hull, eps, True)
    if len(approx) != 4:
        sys.exit("the green area is not four-sided")
    q = approx[:, 0, :].astype(np.float64)
    c = q.mean(0)
    q = q[np.argsort(np.arctan2(q[:, 1] - c[1], q[:, 0] - c[0]))]
    q = np.roll(q, -np.argmin(q.sum(1)), 0)
    lines = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        L = np.linalg.norm(b - a); u = (b - a) / L; nrm = np.array([-u[1], u[0]])
        rel = cnt - a; along, off = rel @ u, rel @ nrm
        pts = cnt[(along > 0.18 * L) & (along < 0.82 * L) & (np.abs(off) < 0.04 * L + 6)].astype(np.float32)
        if len(pts) > 10:
            vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
            lines.append((np.array([x0, y0]), np.array([vx, vy])))
        else:
            lines.append((a, u))
    out = []
    for i in range(4):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        t = np.linalg.solve(np.array([d1, -d2]).T, p2 - p1)
        out.append(p1 + t[0] * d1)
    return np.array(out)


def despill(img, screen, radius):
    near = cv2.distanceTransform((~screen).astype(np.uint8), cv2.DIST_L2, 5) < radius
    b, g, r = [img[..., i].astype(np.float32) for i in range(3)]
    g2 = np.where(near, np.minimum(g, b + 0.42 * (r - b)), g)
    return cv2.merge([b, g2, r]).clip(0, 255).astype(np.uint8)


def overlay(img, gr, quad):
    c = quad.mean(0)
    region = np.zeros(img.shape[:2], np.uint8)
    cv2.fillConvexPoly(region, np.round((quad - c) * 1.03 + c).astype(np.int32), 1)
    alpha = cv2.GaussianBlur(1 - gr, (0, 0), 0.7)
    alpha = np.where(region > 0, alpha, 1)
    return np.dstack([img, (alpha * 255).round().astype(np.uint8)])


def cover(quad, size, stage):
    (w, h), (sw, sh) = size, stage
    s = max(sw / w, sh / h)
    return quad * s - [(w * s - sw) / 2, (h * s - sh) / 2]


def homography(src, dst):
    A, rhs = [], []
    for (x, y), (u, v) in zip(src, dst):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        rhs += [u, v]
    return np.append(np.linalg.solve(np.array(A, float), np.array(rhs, float)), 1).reshape(3, 3)


def matrix3d(quad, w, h):
    a, b, c, d, e, f, g, hh, _ = homography([(0, 0), (w, 0), (w, h), (0, h)], quad).ravel()
    vals = [a, d, 0, g, b, e, 0, hh, 0, 0, 1, 0, c, f, 0, 1]
    return "matrix3d(" + ", ".join(np.format_float_positional(float(v), precision=10, trim="-") for v in vals) + ")"


def size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def key(img, stage=(1920, 1080), screen=(402, 874), grow=1.0):
    h, w = img.shape[:2]
    gr = greenness(img)
    quad = find_quad(gr > 0.5)
    clean = despill(img, gr > 0.05, 420 * max(w, h) / 2560)
    qs = cover(quad, (w, h), stage)
    qc = (qs - qs.mean(0)) * grow + qs.mean(0)
    r2 = lambda q: [[round(float(x), 2), round(float(y), 2)] for x, y in q]
    meta = {"image_size": [w, h], "quad": r2(quad), "stage": list(stage), "quad_stage": r2(qs),
            "grow": grow, "screen": list(screen), "css": matrix3d(qc, *screen)}
    return clean, overlay(clean, gr, quad), meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plate"); ap.add_argument("outprefix")
    ap.add_argument("--stage", type=size, default=(1920, 1080), help="stage size WxH the photo covers")
    ap.add_argument("--screen", type=size, default=(402, 874), help="CSS size WxH of the screen element")
    ap.add_argument("--grow", type=float, default=1.0, help="expand the quad about its centre, e.g. 1.012")
    a = ap.parse_args()
    img = cv2.imread(a.plate)
    if img is None:
        sys.exit(f"cannot read {a.plate}")
    bg, ov, meta = key(img, a.stage, a.screen, a.grow)
    out = pathlib.Path(a.outprefix); out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(f"{out}_bg.jpg", bg, [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(f"{out}_ov.png", ov)
    pathlib.Path(f"{out}.json").write_text(json.dumps(meta, indent=1))
    sw, sh = a.screen
    print("quad (image px):", meta["quad"])
    print("quad (stage px):", meta["quad_stage"])
    print(f".screen {{ position: absolute; left: 0; top: 0; width: {sw}px; height: {sh}px; "
          f"transform-origin: 0 0; transform: {meta['css']}; }}")


if __name__ == "__main__":
    main()
