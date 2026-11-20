"""Self-test for key_screen.py: synthesize phone plates with known screen corners, key them, check the error.

uv run --with opencv-python-headless --with numpy python tools/key_screen_test.py [--keep DIR]

Each plate is a noisy grey background, a dark perspective-warped phone with rounded corners, a pure green
rounded screen and a skin-coloured thumb over one long edge. Passes when every recovered corner is within 2 px.
"""
import argparse, json, pathlib, subprocess, sys, tempfile
import cv2, numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import key_screen as ks

W, H = 1600, 1200
SS = 4
BODY = (760, 1560)
SCREEN = (40, 40, 720, 1520)


def rounded(x0, y0, x1, y1, r, n=24):
    pts = []
    for cx, cy, a0 in [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]:
        t = np.radians(np.linspace(a0, a0 + 90, n))
        pts += list(zip(cx + r * np.cos(t), cy + r * np.sin(t)))
    return np.array(pts, np.float32)


def warp(pts, M):
    return cv2.perspectiveTransform(pts[None], M)[0]


def ss(pts):
    return np.round(((pts + 0.5) * SS - 0.5) * 16).astype(np.int32)


def fill(img, pts, color):
    cv2.fillPoly(img, [ss(pts)], color, cv2.LINE_8, shift=4)


def plate(rng, angle, skew):
    bw, bh = BODY
    c, s = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    hw, hh = 250, 513
    dst = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]], np.float32)
    dst *= np.array([[1 - skew, 1], [1 - skew, 1], [1 + skew, 1], [1 + skew, 1]], np.float32)
    dst = dst @ np.array([[c, s], [-s, c]], np.float32) + [W / 2 + rng.uniform(-80, 80), H / 2 + rng.uniform(-40, 40)]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [bw, 0], [bw, bh], [0, bh]]), dst.astype(np.float32))
    img = np.full((H * SS, W * SS, 3), 128, np.uint8)
    fill(img, warp(rounded(0, 0, bw, bh, 110), M), (34, 33, 36))
    x0, y0, x1, y1 = SCREEN
    fill(img, warp(rounded(x0, y0, x1, y1, 80), M), (0, 255, 0))
    tip = warp(np.float32([[x1 - 50, y0 + 0.55 * (y1 - y0)]]), M)[0]
    out = warp(np.float32([[bw + 260, y0 + 0.62 * (y1 - y0)]]), M)[0]
    ctr = (tip + out) / 2
    ang = np.degrees(np.arctan2(*(out - tip)[::-1]))
    cv2.ellipse(img, tuple(ss(ctr)), (int(np.linalg.norm(out - tip) / 2 * SS * 16), 75 * SS * 16),
                ang, 0, 360, (128, 160, 214), -1, cv2.LINE_8, shift=4)
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
    img = cv2.GaussianBlur(img, (0, 0), 0.6).astype(np.float32) + rng.normal(0, 6, img.shape)
    truth = warp(np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), M)
    return img.clip(0, 255).astype(np.uint8), truth, tip + 0.07 * (out - tip)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", help="also write the plates and the key outputs here")
    a = ap.parse_args()
    rng = np.random.default_rng(3)
    worst, ok = 0.0, True
    for i, (angle, skew) in enumerate([(0, 0.0), (8, 0.06), (-11, -0.08), (17, 0.1), (-4, 0.12)]):
        img, truth, tip = plate(rng, angle, skew)
        bg, ov, meta = ks.key(img, stage=(1920, 1080), screen=(402, 874), grow=1.0)
        quad = np.array(meta["quad"])
        err = np.linalg.norm(quad - truth, axis=1).max()
        worst = max(worst, err)
        qs = np.array(meta["quad_stage"])
        s = max(1920 / W, 1080 / H)
        stage_ok = np.allclose(qs, quad * s - [(W * s - 1920) / 2, (H * s - 1080) / 2], atol=0.02)
        Hm = ks.homography([(0, 0), (402, 0), (402, 874), (0, 874)], qs)
        mapped = cv2.perspectiveTransform(np.float32([[[0, 0], [402, 0], [402, 874], [0, 874]]]), Hm)[0]
        css_ok = np.abs(mapped - qs).max() < 0.01 and meta["css"].startswith("matrix3d(")
        ctr = np.round(truth.mean(0)).astype(int)
        th = np.round(tip).astype(int)
        alpha_ok = ov[ctr[1], ctr[0], 3] < 10 and ov[th[1], th[0], 3] > 245 and ov[5, 5, 3] == 255
        spill_ok = int(bg[ctr[1], ctr[0], 1]) < 40
        passed = err < 2 and stage_ok and css_ok and alpha_ok and spill_ok
        ok &= passed
        print(f"plate {i}: angle {angle:+} skew {skew:+.2f}  max corner error {err:.2f} px  stage {stage_ok}  "
              f"css {css_ok}  alpha {alpha_ok}  despill {spill_ok}  {'PASS' if passed else 'FAIL'}")
        if a.keep:
            d = pathlib.Path(a.keep); d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"plate{i}.jpg"), img)
    with tempfile.TemporaryDirectory() as tmp:
        src = pathlib.Path(a.keep or tmp) / "cli_plate.png"
        cv2.imwrite(str(src), plate(rng, 6, 0.05)[0])
        pre = pathlib.Path(a.keep or tmp) / "cli" / "phone"
        r = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("key_screen.py")), str(src), str(pre),
                            "--stage", "1920x1080", "--grow", "1.012"], capture_output=True, text=True)
        files = all(pathlib.Path(f"{pre}{s}").exists() for s in ("_bg.jpg", "_ov.png", ".json"))
        cli_ok = r.returncode == 0 and files and "matrix3d(" in r.stdout and json.loads(pathlib.Path(f"{pre}.json").read_text())["grow"] == 1.012
        print(f"command line run: {'PASS' if cli_ok else 'FAIL'}" + ("" if cli_ok else "\n" + r.stdout + r.stderr))
        ok &= cli_ok
    print(f"worst corner error {worst:.2f} px -> {'ALL PASS' if ok else 'FAILED'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
