"""Build a single-page review board: media per item, Love it / Maybe / Not this + a note, and "Copy my picks".

  python build.py items.json -o out/index.html [--title "Round 2"]

items.json:
  {"title": "...", "intro": "...",
   "sections": [{"name": "...", "items": [{"id": "a1", "label": "...", "video": "media/a1.mp4", "image": "...",
                                           "poster": "...", "audio": "...", "notes": "..."}]}]}
Only id and label are required. Media paths are relative to the output HTML and are not copied.
Picks are kept in the viewer's localStorage (keyed by title) and copied as plain text, grouped by section.
"""
import argparse, html, json, pathlib, re, sys

TPL = pathlib.Path(__file__).with_name("page.tpl.html")
E = lambda s: html.escape(str(s), quote=True)


def media(it):
    if it.get("video"):
        poster = it.get("poster") or it.get("image")
        return (f'<div class="media"><video src="{E(it["video"])}"' + (f' poster="{E(poster)}"' if poster else "")
                + ' controls loop muted playsinline preload="metadata"></video></div>')
    if it.get("image"):
        return f'<div class="media"><img src="{E(it["image"])}" alt="{E(it["label"])}" loading="lazy"></div>'
    return ""


def item(it):
    notes = f'<p class="notes">{E(it["notes"])}</p>' if it.get("notes") else ""
    audio = f'<audio controls preload="none" src="{E(it["audio"])}"></audio>' if it.get("audio") else ""
    pick = (f'<div class="pick" data-id="{E(it["id"])}" data-label="{E(it["label"])}">'
            '<button type="button" data-v="love">Love it</button><button type="button" data-v="maybe">Maybe</button>'
            '<button type="button" data-v="no">Not this</button>'
            f'<textarea rows="1" placeholder="Note (optional)" aria-label="Note on {E(it["label"])}"></textarea></div>')
    return f'<article class="item" id="item-{E(it["id"])}">{media(it)}<div class="body"><h3>{E(it["label"])}</h3>{notes}{audio}{pick}</div></article>'


def build(data, out, title=None):
    title = title or data.get("title") or "Review"
    seen, missing, nav, secs = set(), [], [], []
    for n, sec in enumerate(data.get("sections", []), 1):
        for it in sec.get("items", []):
            if not it.get("id") or not it.get("label"):
                sys.exit(f"every item needs an id and a label: {it}")
            if it["id"] in seen:
                sys.exit(f"duplicate item id: {it['id']}")
            seen.add(it["id"])
            missing += [p for k in ("video", "image", "poster", "audio") if (p := it.get(k))
                        and "://" not in p and not (out.parent / p).exists()]
        nav.append(f'<a href="#s{n}"><b>{n}</b>{E(sec["name"])}</a>')
        secs.append(f'<section id="s{n}" data-name="{E(sec["name"])}"><h2><small>{n:02d}</small>{E(sec["name"])}</h2>'
                    f'<div class="grid">{"".join(item(it) for it in sec.get("items", []))}</div></section>')
    intro = "".join(f"<p>{E(p.strip())}</p>" for p in re.split(r"\n\s*\n", data.get("intro", "")) if p.strip())
    fill = {"TITLE": E(title), "TITLE_JSON": json.dumps(title).replace("</", "<\\/"), "INTRO": intro,
            "NAV": "".join(nav), "SECTIONS": "\n".join(secs)}
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: fill[m.group(1)], TPL.read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    for p in missing:
        print(f"warning: missing media {p}", file=sys.stderr)
    print(f"wrote {out} ({len(seen)} items)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("items")
    ap.add_argument("-o", "--out", default="index.html")
    ap.add_argument("--title")
    a = ap.parse_args()
    build(json.loads(pathlib.Path(a.items).read_text()), pathlib.Path(a.out), a.title)


if __name__ == "__main__":
    main()
