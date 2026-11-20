"""Action-cut motion graphics for "The Climb". Scene lengths come from timing.json, so
they can be re-timed to the voice-over and re-rendered for free.

Full-frame: manim -qh --fps 30 -r 1920,1080 --format mp4 -o t07 scenes.py T07
Overlays (O01, O08) render with alpha: add -t --format mov, then composite over their clips.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
from manim import *


T = json.loads((Path(__file__).parent / "timing.json").read_text())
HOT = "#FF6B3D"
# palette: a deep green ground, one bright accent per subject (water cyan, sun yellow)
BG = "#0F2A1D"
WATER = "#4FD1E8"
TISSUE = "#7BC47F"
SUN = "#FFD34E"
INK = "#F3F1E7"
SOIL = "#2B2117"
config.background_color = BG


def h2o(scale=1.0):
    """A water molecule: one oxygen, two hydrogens at the real ~104.5° angle."""
    o = Circle(radius=0.26, color=WATER, fill_opacity=1, stroke_width=0)
    hs = VGroup()
    for ang in (90 + 52.25, 90 - 52.25):
        d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang)), 0])
        hs.add(Circle(radius=0.14, color=INK, fill_opacity=1, stroke_width=0).move_to(d * 0.32))
    m = VGroup(hs, o)  # hydrogens behind the oxygen
    return m.scale(scale)


def bond(a, b, width=4, opacity=1.0):
    return DashedLine(a, b, dash_length=0.08, color=WATER, stroke_width=width).set_opacity(opacity)



def sun(radius=0.45):
    disc = Circle(radius=radius, color=SUN, fill_opacity=1, stroke_width=0)
    rays = VGroup(*[
        Line(ORIGIN, RIGHT * 0.32, color=SUN, stroke_width=4).shift(RIGHT * (radius + 0.12)).rotate(a, about_point=ORIGIN)
        for a in np.linspace(0, TAU, 12, endpoint=False)
    ])
    return VGroup(disc, rays)


FONT = os.environ.get("SCENE_FONT", "Avenir Next" if sys.platform == "darwin" else "DejaVu Sans")
HEAVY = dict(font=FONT, weight=HEAVY)


def shake(frame, run_time=0.3, amp=0.18, seed=0):
    """Camera shake that decays to rest; deterministic (seeded) so re-renders match."""
    rng = np.random.default_rng(seed)
    centre = frame.get_center().copy()
    offs = rng.normal(size=(48, 3)) * np.array([1, 1, 0])

    def upd(m, a):
        m.move_to(centre + offs[min(int(a * 47), 47)] * amp * (1 - a))

    return UpdateFromAlphaFunc(frame, upd, run_time=run_time, rate_func=linear)


def slam(mob, run_time=0.14):
    """Text punches in from big and transparent to its size."""
    mob.save_state()
    mob.scale(1.9).set_opacity(0)
    return Restore(mob, run_time=run_time, rate_func=rush_into)


def speed_lines(n=26, seed=1, colour=INK, direction=DOWN):
    rng = np.random.default_rng(seed)
    lines = VGroup()
    for _ in range(n):
        x, y = rng.uniform(-7.5, 7.5), rng.uniform(-4.5, 4.5)
        length = rng.uniform(0.8, 2.2)
        lines.add(Line([x, y, 0], [x, y + length, 0], color=colour, stroke_width=rng.uniform(1.5, 4)).set_opacity(rng.uniform(0.15, 0.45)))
    return lines


class Timed(MovingCameraScene):
    """Pads the scene with a hold so it lasts exactly its slot in timing.json."""

    key = ""

    def pad(self):
        rem = T[self.key] - self.renderer.time
        if rem > 0.02:
            self.play(self.camera.frame.animate.scale(1 - 0.03 * rem), run_time=rem, rate_func=linear)


# ---------------------------------------------------------------- overlays (transparent)


class O01(Scene):
    """THE CLIMB, slammed in on the splash."""

    def construct(self):
        title = Text("THE CLIMB", color=INK, font_size=150, **HEAVY)
        title.set_stroke(BLACK, 6, background=True)
        self.wait(0.95)
        self.play(slam(title, 0.16))
        self.play(title.animate.scale(1.04), run_time=T["O01"] - 0.95 - 0.16, rate_func=linear)


class O08(Scene):
    """116 m counter with a rising ruler, lower-left over the redwood."""

    def construct(self):
        ruler = Line([-6.2, -2.3, 0], [-6.2, -2.29, 0], color=SUN, stroke_width=8)
        value = ValueTracker(0)
        # Text, not DecimalNumber: DecimalNumber needs LaTeX, which isn't installed
        num = always_redraw(lambda: Text(f"{int(round(value.get_value()))} m", color=INK, font_size=120, **HEAVY)
                            .set_stroke(BLACK, 4, background=True).move_to([-5.7, -1.2, 0], aligned_edge=LEFT))
        label = Text("height of the tallest tree on Earth", color=INK, font_size=42, font=FONT, weight=BOLD)
        label.set_stroke(BLACK, 4, background=True).move_to([-5.7, -2.2, 0], aligned_edge=LEFT)
        self.add(ruler, num, label)
        top = [-6.2, 3.4, 0]
        self.play(
            value.animate.set_value(116),
            ruler.animate.put_start_and_end_on([-6.2, -2.3, 0], top),
            run_time=T["O08"] * 0.7, rate_func=rush_from,
        )
        num.clear_updaters()
        unit = VMobject()
        self.play(Indicate(VGroup(num, unit), color=SUN, scale_factor=1.12), run_time=0.4)
        rem = T["O08"] - self.renderer.time
        if rem > 0.02:
            self.wait(rem)


# ---------------------------------------------------------------- full-frame


class T03(Timed):
    key = "T03"

    def construct(self):
        f = self.camera.frame
        a = Text("NO HEART.", color=INK, font_size=170, **HEAVY)
        b = Text("NO PUMP.", color=SUN, font_size=170, **HEAVY)
        t1, t2 = T["T03_hits"]  # "no heart", "no pump" in the voice-over
        self.wait(t1)
        self.play(slam(a), shake(f, 0.3, 0.25, seed=3))
        self.wait(t2 - self.renderer.time)
        self.remove(a)
        self.play(slam(b), shake(f, 0.3, 0.3, seed=4))
        self.pad()


class T07(Timed):
    """The chain, violently: molecules rip out of the pore one after another and the column whips up."""

    key = "T07"
    SP = 0.82

    def construct(self):
        f = self.camera.frame
        top_y = 2.35
        walls = VGroup(
            Line([-0.62, -6, 0], [-0.62, top_y, 0], color=TISSUE, stroke_width=8),
            Line([0.62, -6, 0], [0.62, top_y, 0], color=TISSUE, stroke_width=8),
            Line([-8, top_y, 0], [-1.4, top_y, 0], color=TISSUE, stroke_width=8),
            Line([1.4, top_y, 0], [8, top_y, 0], color=TISSUE, stroke_width=8),
        )
        guards = VGroup(*[Ellipse(width=0.9, height=1.6, color=TISSUE, fill_opacity=0.35, stroke_width=4).move_to([x, top_y + 0.55, 0]) for x in (-0.95, 0.95)])
        sunny = sun(0.55).move_to([5.4, 3.0, 0])
        chain = VGroup(*[h2o(0.95).move_to([0, top_y - 0.45 - i * self.SP, 0]) for i in range(12)])
        bonds = always_redraw(lambda: VGroup(*[bond(chain[i].get_bottom(), chain[i + 1].get_top()) for i in range(len(chain) - 1)]))
        self.add(walls, guards, sunny, chain, bonds)

        # before "grip": the column creeps up as one molecule drifts out of the pore
        first = chain[0]
        chain.add(h2o(0.95).move_to(chain[-1].get_center() + DOWN * self.SP))
        self.play(first.animate.shift(UP * 1.6 + RIGHT * 0.9).set_opacity(0),
                  *[m.animate.shift(UP * self.SP) for m in chain[1:]], run_time=T["T07_grip"] - 0.05, rate_func=smooth)
        chain.remove(first)
        self.remove(first)
        # "grip each other": every bond flares at once, with a punch
        grip = Text("GRIP", color=SUN, font_size=110, **HEAVY).move_to([-4.2, 0.3, 0])
        self.play(*[Indicate(b, color=SUN, scale_factor=1.0) for b in bonds.submobjects], slam(grip), shake(f, 0.3, 0.12, seed=5), run_time=0.5)
        self.play(FadeOut(grip), run_time=0.25)

        # "yanks the whole chain": accelerating rips, each a snap of the column plus a shake
        beats = [0.55, 0.45, 0.38, 0.32, 0.28, 0.25, 0.22, 0.2]
        for k, t in enumerate(beats):
            top = chain[0]
            chain.add(h2o(0.95).move_to(chain[-1].get_center() + DOWN * self.SP))
            side = RIGHT if k % 2 == 0 else LEFT
            lines = speed_lines(seed=10 + k, colour=WATER)
            self.add(lines)
            self.play(
                top.animate.shift(UP * 2.2 + side * 1.6).set_opacity(0),
                *[m.animate.shift(UP * self.SP) for m in chain[1:]],
                lines.animate.shift(DOWN * 6).set_opacity(0),
                Rotate(sunny[1], PI / 10),
                shake(f, t, 0.06 + 0.012 * k, seed=20 + k),
                run_time=t, rate_func=rush_from,
            )
            chain.remove(top)
            self.remove(top, lines)
        self.pad()


class T09(Timed):
    """Pull too hard: the column stretches thin, glows hot and trembles."""

    key = "T09"

    def construct(self):
        f = self.camera.frame
        n, sp = 7, 0.78
        wl = Line([-0.62, -5, 0], [-0.62, 5, 0], color=TISSUE, stroke_width=8)
        wr = Line([0.62, -5, 0], [0.62, 5, 0], color=TISSUE, stroke_width=8)
        mols = VGroup(*[h2o(0.95).move_to([0, (n - 1) / 2 * sp - i * sp, 0]) for i in range(n)])
        heat = ValueTracker(0)
        bonds = always_redraw(lambda: VGroup(*[
            bond(mols[i].get_bottom(), mols[i + 1].get_top(), width=4 - 2.5 * heat.get_value()).set_color(
                interpolate_color(ManimColor(WATER), ManimColor(HOT), heat.get_value()))
            for i in range(n - 1)
        ]))
        self.add(wl, wr, mols, bonds)
        for m in mols:
            m.add_updater(lambda m, dt: m.shift(RIGHT * 0.03 * heat.get_value() * np.sin(self.renderer.time * 90 + m.get_y() * 7)))
        D = T[self.key]
        self.play(
            *[m.animate.shift(UP * 0.38 * ((n - 1) / 2 - i)) for i, m in enumerate(mols)],
            wl.animate.become(ArcBetweenPoints([-0.62, -5, 0], [-0.62, 5, 0], angle=-0.16).set_stroke(TISSUE, 8)),
            wr.animate.become(ArcBetweenPoints([0.62, -5, 0], [0.62, 5, 0], angle=0.16).set_stroke(TISSUE, 8)),
            heat.animate.set_value(1),
            f.animate.scale(0.82),
            run_time=D - 0.05, rate_func=rush_into,
        )
        self.pad()


class T10(Timed):
    """SNAP: white flash, the bubble blasts open, shockwave rings, the halves fly apart."""

    key = "T10"

    def construct(self):
        f = self.camera.frame
        f.scale(0.82)
        n, sp = 7, 0.78 + 0.38
        wl = ArcBetweenPoints([-0.62, -5, 0], [-0.62, 5, 0], angle=-0.16).set_stroke(TISSUE, 8)
        wr = ArcBetweenPoints([0.62, -5, 0], [0.62, 5, 0], angle=0.16).set_stroke(TISSUE, 8)
        mols = VGroup(*[h2o(0.95).move_to([0, (n - 1) / 2 * sp - i * sp, 0]) for i in range(n)])
        bonds = VGroup(*[bond(mols[i].get_bottom(), mols[i + 1].get_top(), width=1.5).set_color(HOT) for i in range(n - 1)])
        self.add(wl, wr, mols, bonds)
        mid = 3
        gap = (mols[mid - 1].get_bottom() + mols[mid].get_top()) / 2
        flash = Rectangle(width=30, height=20, fill_color=WHITE, fill_opacity=1, stroke_width=0)
        bubble = Circle(radius=0.05, color=INK, stroke_width=6).move_to(gap)
        rings = VGroup(*[Circle(radius=0.1, color=INK, stroke_width=5 - i).move_to(gap) for i in range(3)])
        word = Text("SNAP", color=INK, font_size=115, **HEAVY).move_to([3.1, 0.4, 0])
        self.add(flash)
        self.play(
            FadeOut(flash, rate_func=rush_from),
            FadeOut(bonds[mid - 1], run_time=0.05),
            bubble.animate.scale(14),
            *[r.animate.scale(40 + 25 * i).set_stroke(opacity=0) for i, r in enumerate(rings)],
            VGroup(*mols[:mid], *bonds[: mid - 1]).animate.shift(UP * 1.3),
            VGroup(*mols[mid:], *bonds[mid:]).animate.shift(DOWN * 1.3),
            slam(word, 0.12),
            shake(f, 0.6, 0.35, seed=7),
            run_time=0.6, rate_func=rush_from,
        )
        self.pad()


class T11(Timed):
    """The pop races past the range of human hearing."""

    key = "T11"

    def construct(self):
        axis = NumberLine(x_range=[0, 4.3, 1], length=12, include_ticks=False, color=INK).shift(DOWN * 1.8)
        x = axis.n2p
        band = Rectangle(width=x(3)[0] - x(0)[0], height=3.0, fill_color=INK, fill_opacity=0.12, stroke_width=0)
        band.move_to((x(0) + x(3)) / 2 + UP * 1.5)
        band_label = Text("what you can hear", color=INK, font_size=34, font=FONT).move_to(band.get_center())
        ticks = VGroup(*[
            VGroup(Line(x(v) + UP * 0.12, x(v) + DOWN * 0.12, color=INK, stroke_width=3),
                   Text(s, color=INK, font_size=24, font=FONT).next_to(x(v), DOWN, buff=0.25))
            for v, s in ((0, "20 Hz"), (3, "20 kHz"), (3.7, "100 kHz"))
        ])
        self.add(axis, ticks, band, band_label)
        # a pulse that races in from the left, crosses the hearing band, and lands past it
        dot = Dot(x(0) + UP * 0.02, color=SUN, radius=0.12)
        trace = TracedPath(dot.get_center, stroke_color=SUN, stroke_width=5, dissipating_time=0.35)
        self.add(trace, dot)
        spike_x = x(3.54)
        self.play(dot.animate.move_to(spike_x), run_time=0.55, rate_func=rush_into)
        spike = VMobject(color=SUN, stroke_width=7).set_points_as_corners([
            spike_x + LEFT * 0.6, spike_x + LEFT * 0.15, spike_x + UP * 2.9, spike_x + RIGHT * 0.12,
            spike_x + RIGHT * 0.22 + UP * 1.0, spike_x + RIGHT * 0.32, spike_x + RIGHT * 0.7,
        ])
        pop = Text("POP", color=SUN, font_size=90, **HEAVY).next_to(spike, UP, buff=0.2)
        self.play(Create(spike), slam(pop), FadeOut(dot), shake(self.camera.frame, 0.35, 0.12, seed=9), run_time=0.35)
        self.play(Indicate(spike, color=SUN, scale_factor=1.1), run_time=0.5)
        self.pad()


class T13(Timed):
    """Sunlight lasers in and rips a water molecule apart."""

    key = "T13"

    def construct(self):
        f = self.camera.frame
        mol = h2o(3.4).move_to([0.6, -0.4, 0])
        hs, o = mol[0], mol[1]
        self.add(mol)
        self.play(mol.animate.scale(1.06), run_time=0.45, rate_func=there_and_back)
        start, end = np.array([-8.5, 5.5, 0]), o.get_center()
        beam = Line(start, start, color=SUN, stroke_width=26)
        core = Line(start, start, color=WHITE, stroke_width=8)
        self.play(beam.animate.put_start_and_end_on(start, end), core.animate.put_start_and_end_on(start, end), run_time=0.22, rate_func=rush_into)
        flash = Rectangle(width=30, height=20, fill_color=SUN, fill_opacity=0.85, stroke_width=0)
        self.add(flash)
        self.play(
            FadeOut(flash, rate_func=rush_from),
            hs[0].animate.shift(LEFT * 5 + DOWN * 2).set_opacity(0.15),
            hs[1].animate.shift(RIGHT * 5 + DOWN * 2.5).set_opacity(0.15),
            o.animate.set_color(SUN),
            shake(f, 0.6, 0.32, seed=11),
            run_time=0.6, rate_func=rush_from,
        )
        self.play(FadeOut(beam), FadeOut(core), o.animate.set_color(WATER), run_time=0.35)
        self.pad()


class T14(Timed):
    """Two oxygens slam together into O₂ and rocket out of the leaf."""

    key = "T14"

    def construct(self):
        f = self.camera.frame
        a = Circle(radius=0.55, color=WATER, fill_opacity=1, stroke_width=0).move_to([-5, -1.5, 0])
        b = a.copy().move_to([5, -1.5, 0])
        self.add(a, b)
        self.play(a.animate.move_to([-0.5, -1.5, 0]), b.animate.move_to([0.5, -1.5, 0]), run_time=0.35, rate_func=rush_into)
        o2 = VGroup(a, b)
        label = Text("O₂", color=INK, font_size=80, **HEAVY).next_to(o2, RIGHT, buff=0.35)
        self.play(slam(label), shake(f, 0.3, 0.2, seed=13), run_time=0.2)
        rocket = VGroup(o2, label)
        trail = TracedPath(o2.get_bottom, stroke_color=WATER, stroke_width=10, dissipating_time=0.4)
        lines = speed_lines(seed=14, colour=WATER)
        self.add(trail, lines)
        rest = T[self.key] - self.renderer.time
        self.play(rocket.animate.shift(UP * 7.5), lines.animate.shift(DOWN * 7).set_opacity(0), run_time=rest, rate_func=rush_into)


class T16(Timed):
    """End card on the beat."""

    key = "T16"

    def construct(self):
        f = self.camera.frame
        a = Text("GO WATER", color=INK, font_size=150, **HEAVY)
        b = Text("YOUR PLANTS.", color=SUN, font_size=150, **HEAVY)
        VGroup(a, b).arrange(DOWN, buff=0.35).scale_to_fit_width(11.5)
        drop = VGroup(
            Circle(radius=0.28, color=WATER, fill_opacity=1, stroke_width=0),
            Triangle(color=WATER, fill_opacity=1, stroke_width=0).scale(0.27).shift(UP * 0.3),
        ).next_to(b, RIGHT, buff=0.35)
        self.play(slam(a), shake(f, 0.3, 0.22, seed=15))
        self.wait(0.2)
        self.play(slam(b), shake(f, 0.3, 0.22, seed=16))
        self.play(FadeIn(drop, shift=DOWN * 0.6), run_time=0.3)
        hold = T[self.key] - self.renderer.time - 0.5
        if hold > 0:  # a slow push-in while the final hit rings out
            self.play(f.animate.scale(0.94), run_time=hold, rate_func=linear)
        self.play(FadeOut(VGroup(a, b, drop)), f.animate.scale(0.98), run_time=0.5)
