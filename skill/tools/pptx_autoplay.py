"""Build a full-bleed 16:9 PowerPoint deck where each video starts by itself when its slide appears.

  uv run --with python-pptx --with lxml python pptx_autoplay.py slides.json -o deck.pptx

slides.json is a list; paths are relative to the JSON file:
  [{"image": "slide1.png", "notes": "...", "alt": "..."},
   {"video": "clip.mp4", "poster": "poster.png", "notes": "...", "alt": "...", "background": "#000000"}]
alt defaults to notes. A video slide without a poster gets one from ffmpeg at 0.5 s. Video slides fade in;
nothing is layered over a video, there are no click-sequence effects and no empty relationship ids.
"""
import argparse, json, pathlib, subprocess, sys, tempfile
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu

W, H = Emu(12192000), Emu(6858000)
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

TIMING = f'''<p:timing xmlns:p="{P}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>
<p:video><p:cMediaNode vol="100000"><p:cTn id="2" fill="hold" display="0"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>
<p:tgtEl><p:spTgt spid="{{spid}}"/></p:tgtEl></p:cMediaNode></p:video></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>'''


def autoplay(slide, movie):
    sld = slide._element
    for old in sld.findall(f"{{{P}}}timing") + sld.findall(f"{{{P}}}transition"):
        sld.remove(old)
    for h in list(movie._element.iter(f"{{{A}}}hlinkClick")):
        if h.get(f"{{{R}}}id") == "":
            del h.attrib[f"{{{R}}}id"]  # keep the element (click-to-pause), drop the empty id PowerPoint chokes on
    anchor = sld.find(f"{{{P}}}clrMapOvr")
    if anchor is None:
        anchor = sld.find(f"{{{P}}}cSld")
    i = list(sld).index(anchor) + 1
    sld.insert(i, etree.fromstring(f'<p:transition xmlns:p="{P}" spd="slow"><p:fade/></p:transition>'))
    sld.insert(i + 1, etree.fromstring(TIMING.format(spid=movie.shape_id)))


def poster_for(video, tmp):
    out = pathlib.Path(tmp) / f"{video.stem}_poster.png"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "0.5", "-i", str(video), "-frames:v", "1", str(out)], check=True)
    if not out.exists():
        sys.exit(f"could not extract a poster from {video}")
    return out


def build(spec, base, out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]
    with tempfile.TemporaryDirectory() as tmp:
        for n, s in enumerate(spec, 1):
            slide = prs.slides.add_slide(blank)
            alt = s.get("alt") or s.get("notes") or ""
            if s.get("video"):
                video = base / s["video"]
                poster = base / s["poster"] if s.get("poster") else poster_for(video, tmp)
                fill = slide.background.fill
                fill.solid()
                fill.fore_color.rgb = RGBColor.from_string(s.get("background", "#000000").lstrip("#"))
                shape = slide.shapes.add_movie(str(video), 0, 0, W, H, poster_frame_image=str(poster), mime_type="video/mp4")
                shape.name = f"Video {n}"
                autoplay(slide, shape)
            elif s.get("image"):
                shape = slide.shapes.add_picture(str(base / s["image"]), 0, 0, W, H)
                shape.name = f"Slide image {n}"
            else:
                sys.exit(f"slide {n} needs an image or a video")
            shape._element.xpath("./*[1]/p:cNvPr")[0].set("descr", alt)
            if s.get("notes"):
                slide.notes_slide.notes_text_frame.text = s["notes"]
        prs.save(out)
    print(f"saved {out} ({len(spec)} slides)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slides")
    ap.add_argument("-o", "--out", default="deck.pptx")
    a = ap.parse_args()
    src = pathlib.Path(a.slides).resolve()
    build(json.loads(src.read_text()), src.parent, a.out)


if __name__ == "__main__":
    main()
