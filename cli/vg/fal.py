"""fal.ai media models through fal's queue API: image-to-video (Kling, Veo, Wan, Hailuo...), video-to-video
edits, image models, sound effects (ElevenLabs via fal), Stable Audio.

One key (FAL_KEY in the environment or VG_HOME/.env). It is never printed or written to job files.
Inputs given as local files are sent as data URIs (fine for stills and short audio; very large videos should
be uploaded somewhere first and passed by URL). Every call prints the model, the request id and, when fal
publishes it, the unit price; the authoritative bill is the fal dashboard (fal.ai/dashboard/usage).

Request flow: POST https://queue.fal.run/<model> with the model's JSON input, poll the returned status_url
until COMPLETED, then GET the response_url and download every media URL it contains.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import time
from pathlib import Path

import httpx

from vg import config, costs

QUEUE = "https://queue.fal.run"
MEDIA_EXT = (".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".m4a", ".flac", ".ogg")


class FalError(RuntimeError):
    pass


def _key() -> str:
    if key := config.secret("FAL_KEY"):
        return key
    raise FalError(f"FAL_KEY not set: put FAL_KEY=... in {config.env_file()} (or export it)")


def has_key() -> bool:
    return bool(config.secret("FAL_KEY"))


def _headers() -> dict:
    return {"Authorization": f"Key {_key()}", "Content-Type": "application/json"}


def data_uri(path: str | Path) -> str:
    p = Path(path); mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def price_info(model: str) -> tuple[float, str] | None:
    """(unit price in USD, unit) as fal publishes it for the endpoint, or None if the pricing API doesn't answer."""
    try:
        r = httpx.get("https://api.fal.ai/v1/models/pricing", params={"endpoint_id": model}, headers=_headers(), timeout=20)
        if r.status_code == 200:
            for p in r.json().get("prices", []):
                if p.get("endpoint_id") == model and p.get("unit_price") is not None:
                    return float(p["unit_price"]), str(p.get("unit", ""))
    except Exception:
        pass
    return None


def price(model: str) -> str | None:
    """Unit price as a readable string, or None."""
    info = price_info(model)
    return f"${info[0]} per {info[1]} (USD)" if info else None


def estimate(info: tuple[float, str] | None, saved: list[Path]) -> float | None:
    """What a finished job probably cost: unit price times seconds of output, or per image/output.

    fal returns no charge per call, so this is an estimate for the local ledger; fal.ai/dashboard/usage is the
    bill of record. Units priced on input (characters, compute seconds) give None.
    """
    if not info or not saved:
        return None
    unit_price, unit = info; unit = unit.lower()
    if "second" in unit and "compute" not in unit:
        import subprocess
        try:
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        str(saved[0])], capture_output=True, text=True, check=True).stdout.strip())
        except Exception:
            return None
        return round(unit_price * dur, 4)
    if unit.rstrip("s") in ("image", "video", "output", "request", "unit", "clone", "generation"):
        return round(unit_price * len(saved), 4)
    return None


def schema(model: str) -> list[str]:
    """Input fields of an endpoint, read from fal's public OpenAPI document (no key needed).

    One line per field: name, type, required or the default, and the start of its description. The field
    names differ between models (`text` vs `prompt`, `image_url` vs `image_urls`, `tail_image_url` vs
    `end_image_url`), so look before the first paid call.
    """
    r = httpx.get("https://fal.ai/api/openapi/queue/openapi.json", params={"endpoint_id": model}, timeout=30)
    if r.status_code != 200:
        return []
    doc = r.json(); schemas = doc.get("components", {}).get("schemas", {})
    body = None
    for path, ops in doc.get("paths", {}).items():
        post = ops.get("post") if isinstance(ops, dict) else None
        if post and "requestBody" in post and "{request_id}" not in path:
            ref = post["requestBody"].get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "")
            body = schemas.get(ref.rsplit("/", 1)[-1]); break
    if not body:
        return []
    required = set(body.get("required", []))
    out = []
    for name, f in body.get("properties", {}).items():
        typ = f.get("type") or ("enum" if "enum" in f else "") or ("|".join(x.get("type", "?") for x in f.get("anyOf", [])) if "anyOf" in f else "object")
        if "enum" in f: typ += " " + "/".join(map(str, f["enum"]))[:80]
        flag = "REQUIRED" if name in required else (f"default {json.dumps(f['default'])}" if "default" in f else "optional")
        desc = (f.get("description") or "").replace("\n", " ")[:90]
        out.append(f"{name:24} {typ:28} {flag:22} {desc}")
    return out


def _urls(obj) -> list[str]:
    found = []
    if isinstance(obj, dict):
        for v in obj.values(): found += _urls(v)
    elif isinstance(obj, list):
        for v in obj: found += _urls(v)
    elif isinstance(obj, str) and obj.startswith("https://") and obj.split("?")[0].lower().endswith(MEDIA_EXT):
        found.append(obj)
    return found


def run(model: str, args: dict, out: Path, *, timeout_s: int = 1800, poll_s: float = 5.0) -> list[Path]:
    """Submit one job, wait for it, download its media. Returns the saved paths (out, out-2, ...)."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120) as c:
        r = c.post(f"{QUEUE}/{model}", headers=_headers(), json=args)
        if r.status_code >= 400:
            costs.attempt("ove", "fal", model=model, op="run", status=r.status_code)
            raise FalError(f"submit HTTP {r.status_code}: {r.text[:800]}")
        job = r.json(); rid = job.get("request_id"); status_url, response_url = job.get("status_url"), job.get("response_url")
        if not (status_url and response_url):
            raise FalError(f"unexpected submit response: {json.dumps(job)[:500]}")
        print(f"fal {model} request {rid}", flush=True)
        (out.parent / f"{out.stem}.fal-job.json").write_text(json.dumps({"model": model, "request_id": rid, "status_url": status_url, "response_url": response_url}, indent=2))
        t0 = time.time(); last = None
        while True:
            s = c.get(status_url, headers=_headers()).json(); st = s.get("status")
            if st != last: print(f"  {st}", flush=True); last = st
            if st == "COMPLETED": break
            if st in ("FAILED", "ERROR", "CANCELLED"):
                costs.attempt("ove", "fal", model=model, op="run", request_id=rid, error=st)
                raise FalError(f"job {rid} {st}: {json.dumps(s)[:800]}")
            if time.time() - t0 > timeout_s:
                costs.attempt("ove", "fal", model=model, op="run", request_id=rid, error="timeout")
                raise FalError(f"job {rid} still {st} after {timeout_s}s (check status_url later; it may still bill)")
            time.sleep(poll_s)
        res = c.get(response_url, headers=_headers())
        if res.status_code >= 400:
            raise FalError(f"result HTTP {res.status_code}: {res.text[:800]}")
        body = res.json(); (out.parent / f"{out.stem}.fal-result.json").write_text(json.dumps(body, indent=2))
        urls = _urls(body)
        if not urls:
            raise FalError(f"no media in result: {json.dumps(body)[:800]}")
        saved = []
        for i, u in enumerate(urls):
            ext = Path(u.split("?")[0]).suffix
            dest = out if i == 0 and out.suffix.lower() == ext.lower() else (out.with_suffix(ext) if i == 0 else out.with_name(f"{out.stem}-{i + 1}{ext}"))
            with c.stream("GET", u, timeout=600) as d:
                d.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in d.iter_bytes(): f.write(chunk)
            saved.append(dest)
        info = price_info(model)
        usd = estimate(info, saved)
        costs.record("ove", "fal", usd=usd, model=model, op="run", request_id=rid,
                     unit_price=f"${info[0]} per {info[1]}" if info else None, estimated=usd is not None)
        if usd is not None:
            print(f"cost about ${usd:.4f} (estimated from fal's unit price)", flush=True)
        return saved
